# Training Scripts

This directory contains scripts to train the fraud detection model for the Allianz MVP.

## Overview

The training pipeline consists of 4 steps:

1. **prepare_dataset.py** - Load and preprocess IEEE-CIS dataset
2. **train_lightgbm.py** - Train LightGBM model
3. **calibrate_model.py** - Calibrate probability scores
4. **convert_to_onnx.py** - Convert to ONNX format

## Prerequisites

```bash
pip install pandas numpy lightgbm scikit-learn onnx onnxmltools onnxruntime
```

## Dataset

Download the IEEE-CIS Fraud Detection dataset from Kaggle:
https://www.kaggle.com/c/ieee-fraud-detection/data

Place the dataset at: `data/raw/ieee-fraud.csv`

## Usage

### Step 1: Prepare Dataset

```bash
python training/scripts/prepare_dataset.py \
  --input data/raw/ieee-fraud.csv \
  --output data/processed/ieee_features.csv
```

**Output:**
- `data/processed/ieee_features.csv` - Processed dataset with 15 features + target

**What it does:**
- Loads raw IEEE-CIS CSV
- Computes 15 features from `FEATURE_CONTRACT.md`
- Adds `is_fraud` target label (0/1)
- Handles missing values

### Step 2: Train Model

```bash
python training/scripts/train_lightgbm.py \
  --input data/processed/ieee_features.csv \
  --output models/fraud_model.txt \
  --val-output models
```

**Output:**
- `models/fraud_model.txt` - Trained LightGBM model
- `models/val_scores.npy` - Validation predictions (for calibration)
- `models/val_labels.npy` - Validation labels (for calibration)

**What it does:**
- Splits data 60/20/20 (train/val/test)
- Handles class imbalance with `scale_pos_weight`
- Trains LightGBM with params from `ML_ENGINE_SPEC.md`
- Evaluates AUC, precision@1%, recall@5%FPR
- Saves validation scores for calibration

**Target metrics:**
- AUC-ROC: >0.92
- Precision@1%: >0.70
- Recall@5% FPR: >0.65

### Step 3: Calibrate Model

```bash
python training/scripts/calibrate_model.py \
  --scores models/val_scores.npy \
  --labels models/val_labels.npy \
  --output models/calibration.pkl
```

**Output:**
- `models/calibration.pkl` - Isotonic regression calibrator (~50KB)

**What it does:**
- Fits `IsotonicRegression` on validation scores
- Converts raw model scores → calibrated probabilities
- Evaluates Brier score and log loss
- Analyzes calibration curve

**Target:**
- Calibration error: <0.02

### Step 4: Convert to ONNX

```bash
python training/scripts/convert_to_onnx.py \
  --input models/fraud_model.txt \
  --output models/fraud_model.onnx \
  --n-features 15
```

**Output:**
- `models/fraud_model.onnx` - ONNX model (~2.5MB)

**What it does:**
- Converts LightGBM → ONNX format
- Validates ONNX model structure
- Tests inference latency
- Compares ONNX vs LightGBM predictions

**Target:**
- Inference latency: <20ms
- Model size: ~2.5MB

## Complete Pipeline

Run all steps in sequence:

```bash
# 1. Prepare dataset
python training/scripts/prepare_dataset.py

# 2. Train model
python training/scripts/train_lightgbm.py

# 3. Calibrate
python training/scripts/calibrate_model.py

# 4. Convert to ONNX
python training/scripts/convert_to_onnx.py
```

## Output Artifacts

After running the complete pipeline:

```
models/
├── fraud_model.txt       # LightGBM model (training artifact)
├── fraud_model.onnx      # ONNX model (used by API)
├── calibration.pkl       # Calibrator (used by API)
├── val_scores.npy        # Validation scores (training artifact)
└── val_labels.npy        # Validation labels (training artifact)
```

## API Integration

The API (`api/models/ml_engine.py`) uses:
- `models/fraud_model.onnx` - For inference
- `models/calibration.pkl` - For score calibration

## Notes

- These are **simple, runnable skeletons** for the MVP
- Feature engineering is simplified compared to production
- Some features are mocked (graph features, IP reputation)
- Focus is on end-to-end pipeline, not perfect accuracy
- See `docs/ML_ENGINE_SPEC.md` for full model specification
- See `docs/FEATURE_CONTRACT.md` for feature definitions

## TODOs

Each script has inline TODOs for areas that need real data:
- [ ] Set correct IEEE-CIS dataset path
- [ ] Implement proper rolling window features
- [ ] Add real IP/ASN reputation lookups
- [ ] Optimize feature computation for speed
