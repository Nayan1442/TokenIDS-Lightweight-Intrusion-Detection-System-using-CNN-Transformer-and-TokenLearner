# -*- coding: utf-8 -*-
"""IDS detection

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1d9NLWrTAVnUGAObvYlM08NW31HQV4XNp
"""

# Imports and Data Preparation
from google.colab import drive
drive.mount('/content/drive')

import numpy as np
import pandas as pd
import tensorflow as tf
from tensorflow.keras import layers, models, initializers
from sklearn.model_selection import train_test_split
from sklearn.utils import class_weight
from sklearn.preprocessing import RobustScaler
from sklearn.metrics import classification_report, confusion_matrix, roc_curve, auc, precision_recall_curve
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.manifold import TSNE

# Load dataset
data = pd.read_csv("/content/drive/MyDrive/nsl-kdd/KDDTrain+.txt", header=None)
columns = ['duration','protocol_type','service','flag','src_bytes','dst_bytes','land','wrong_fragment','urgent','hot',
           'num_failed_logins','logged_in','num_compromised','root_shell','su_attempted','num_root','num_file_creations',
           'num_shells','num_access_files','num_outbound_cmds','is_host_login','is_guest_login','count','srv_count',
           'serror_rate','srv_serror_rate','rerror_rate','srv_rerror_rate','same_srv_rate','diff_srv_rate',
           'srv_diff_host_rate','dst_host_count','dst_host_srv_count','dst_host_same_srv_rate','dst_host_diff_srv_rate',
           'dst_host_same_src_port_rate','dst_host_srv_diff_host_rate','dst_host_serror_rate','dst_host_srv_serror_rate',
           'dst_host_rerror_rate','dst_host_srv_rerror_rate','outcome','level']

data.columns = columns
data['outcome'] = data['outcome'].apply(lambda x: 0 if x == 'normal' else 1)
data.drop(columns=['level'], inplace=True)

# One-hot encode categorical features
cat_cols = ['protocol_type', 'service', 'flag', 'land', 'logged_in', 'is_guest_login', 'is_host_login']
data = pd.get_dummies(data, columns=cat_cols)

X = data.drop('outcome', axis=1)
y = data['outcome']

# Train-test split
x_train, x_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Feature scaling
scaler = RobustScaler()
x_train = scaler.fit_transform(x_train)
x_test = scaler.transform(x_test)

# Reshape
x_train = x_train.reshape((-1, x_train.shape[1], 1))
x_test = x_test.reshape((-1, x_test.shape[1], 1))

class TokenLearner(layers.Layer):
    def __init__(self, num_tokens=4):  # reduced tokens
        super().__init__()
        self.num_tokens = num_tokens

    def build(self, input_shape):
        _, seq_len, channels = input_shape
        self.attention = layers.Dense(self.num_tokens, activation='softmax')
        self.projection = layers.Dense(channels)

    def call(self, x):
        attn = self.attention(x)  # shape: (batch, seq_len, num_tokens)
        attn = tf.transpose(attn, perm=[0, 2, 1])  # (batch, num_tokens, seq_len)
        tokens = tf.matmul(attn, x)  # (batch, num_tokens, channels)
        return self.projection(tokens)

class SEBlock(layers.Layer):
    def __init__(self, channels, reduction=8):  # smaller reduction
        super().__init__()
        self.pool = layers.GlobalAveragePooling1D()
        self.fc1 = layers.Dense(channels // reduction, activation='relu')
        self.fc2 = layers.Dense(channels, activation='sigmoid')

    def call(self, x):
        squeeze = self.pool(x)
        excite = self.fc1(squeeze)
        excite = self.fc2(excite)
        excite = tf.expand_dims(excite, 1)
        return x * excite

class LearnablePositionalEncoding(layers.Layer):
    def __init__(self, seq_len, d_model):
        super().__init__()
        self.seq_len = seq_len
        self.d_model = d_model

    def build(self, input_shape):
        self.pe = self.add_weight(
            name="pos_embedding",
            shape=(1, self.seq_len, self.d_model),
            initializer="random_normal",
            trainable=True
        )

    def call(self, x):
        return x + self.pe[:, :tf.shape(x)[1], :]

class AttentionPooling(layers.Layer):
    def __init__(self, units):
        super(AttentionPooling, self).__init__()
        self.W = layers.Dense(units, activation='tanh')
        self.V = layers.Dense(1)

    def call(self, inputs):
        scores = self.V(self.W(inputs))
        weights = tf.nn.softmax(scores, axis=1)
        return tf.reduce_sum(inputs * weights, axis=1)

def build_light_model(input_shape):
    inputs = layers.Input(shape=input_shape)

    # --- CNN Path ---
    cnn = layers.Conv1D(32, 3, padding='same', activation='relu')(inputs)
    cnn = layers.BatchNormalization()(cnn)
    cnn = SEBlock(32)(cnn)
    cnn_feat = TokenLearner(num_tokens=4)(cnn)  # output shape (batch, 4, 32)

    # --- Transformer Path ---
    d_model = 32
    trans = layers.Dense(d_model)(inputs)
    trans = LearnablePositionalEncoding(input_shape[0], d_model)(trans)
    trans = layers.LayerNormalization()(trans)
    trans_feat = TokenLearner(num_tokens=4)(trans)  # output shape (batch, 4, 32)

    # --- Bi-Directional Cross-Attention ---
    attn1 = layers.MultiHeadAttention(num_heads=1, key_dim=16)(cnn_feat, trans_feat)
    attn2 = layers.MultiHeadAttention(num_heads=1, key_dim=16)(trans_feat, cnn_feat)
    merged = layers.Concatenate()([attn1, attn2])  # shape (batch, 4, 32*2)

    # --- Pooling + Dense ---
    pooled = layers.GlobalAveragePooling1D()(merged)
    x = layers.Dense(64, activation='relu')(pooled)
    x = layers.Dropout(0.3)(x)
    outputs = layers.Dense(1, activation='sigmoid')(x)

    model = models.Model(inputs, outputs)
    model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])
    return model

model = build_light_model((x_train.shape[1], 1))
model.summary()

class_weights = class_weight.compute_class_weight('balanced', classes=np.unique(y_train), y=y_train)
class_weights = dict(zip(np.unique(y_train), class_weights))

history = model.fit(x_train, y_train,
                    validation_data=(x_test, y_test),
                    epochs=30,
                    batch_size=256,
                    class_weight=class_weights,
                    verbose=1)

# --- Plot Training Curves ---
def plot_history(hist):
    plt.figure(figsize=(12, 4))
    plt.subplot(1, 2, 1)
    plt.plot(hist.history['accuracy'], label='Train Acc')
    plt.plot(hist.history['val_accuracy'], label='Val Acc')
    plt.title('Accuracy')
    plt.grid(True)
    plt.legend()

    plt.subplot(1, 2, 2)
    plt.plot(hist.history['loss'], label='Train Loss')
    plt.plot(hist.history['val_loss'], label='Val Loss')
    plt.title('Loss')
    plt.grid(True)
    plt.legend()
    plt.show()

plot_history(history)

# --- Evaluation ---
y_pred = model.predict(x_test)
y_pred_binary = (y_pred > 0.5).astype(int)

print("\nClassification Report:")
print(classification_report(y_test, y_pred_binary))

# Confusion Matrix
cm = confusion_matrix(y_test, y_pred_binary)
sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', xticklabels=["Normal", "Attack"], yticklabels=["Normal", "Attack"])
plt.title('Confusion Matrix')
plt.xlabel('Predicted')
plt.ylabel('Actual')
plt.show()

# ROC Curve
fpr, tpr, _ = roc_curve(y_test, y_pred)
roc_auc = auc(fpr, tpr)
plt.plot(fpr, tpr, label='AUC = {:.2f}'.format(roc_auc), color='darkorange')
plt.plot([0, 1], [0, 1], 'k--')
plt.title('ROC Curve')
plt.xlabel('FPR')
plt.ylabel('TPR')
plt.grid(True)
plt.legend()
plt.show()

# Precision-Recall Curve
precision, recall, _ = precision_recall_curve(y_test, y_pred)
plt.plot(recall, precision, color='purple')
plt.title('Precision-Recall Curve')
plt.xlabel('Recall')
plt.ylabel('Precision')
plt.grid(True)
plt.show()