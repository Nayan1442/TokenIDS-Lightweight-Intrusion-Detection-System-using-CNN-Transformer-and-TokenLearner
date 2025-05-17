# TokenIDS-Lightweight-Intrusion-Detection-System-using-CNN-Transformer-and-TokenLearner

Achieving **99.56% accuracy** on the NSL-KDD dataset, this project introduces a novel, lightweight hybrid architecture combining CNN, Transformer with Learnable Positional Encoding, TokenLearner, SE blocks, and Bi-Directional Cross-Attention for effective Intrusion Detection.

## 🔍 Overview

Intrusion Detection Systems (IDS) are critical for ensuring cybersecurity in networks. This model leverages both local and global feature extraction via:
- **CNN** for local pattern learning
- **Transformer** with **Learnable Positional Encoding** for global dependency capture
- **TokenLearner** to dynamically reduce feature tokens
- **Squeeze-and-Excitation (SE)** block for channel-wise attention
- **Bi-Directional Cross-Attention** between CNN and Transformer outputs
- **Attention Pooling** for robust feature aggregation

## 🚀 Key Features
- Achieves **99.56% accuracy** on the NSL-KDD dataset
- Lightweight design with < 200K trainable parameters
- Attention-based fusion and pooling for high discrimination
- Visualization support: ROC, PR Curve, Confusion Matrix, Training plots

## 📊 Results

| Metric        | Score     |
|---------------|-----------|
| Accuracy      | 99.56%    |
| AUC-ROC       | > 0.99    |
| Precision     | High      |
| Recall        | High      |

## 📁 Dataset

We use the **NSL-KDD** dataset:
- [KDDTrain+.txt](https://www.unb.ca/cic/datasets/nsl.html)
- Categorical features are one-hot encoded
- Features scaled using RobustScaler

## 🏗️ Architecture

Input ➝ CNN ➝ SE Block ➝ TokenLearner ┐
├── Cross-Attention ➝ Pooling ➝ Dense ➝ Output
Input ➝ Transformer ➝ TokenLearner ───┘


## 🧪 How to Run

### Prerequisites

- Python ≥ 3.7
- TensorFlow ≥ 2.10
- pandas, numpy, sklearn, seaborn, matplotlib

### Training
python ids_detection.py



