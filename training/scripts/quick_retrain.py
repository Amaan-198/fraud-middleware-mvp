#!/usr/bin/env python3
"""
Quick Retrain Script - Uses Optimized Hyperparameters

Purpose: Retrain model with your optimized hyperparameters from training_summary.json
This ensures compatibility with your current LightGBM version.

Usage:
    python quick_retrain.py
"""

import json
from pathlib import Path
import pandas as pd
import numpy as np
import lightgbm as lgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, precision_score, recall_score

print("=" * 60)
print("QUICK RETRAIN WITH OPTIMIZED HYPERPARAMETERS")
print("=" * 60)

# === Load hyperparameters ===
print("\n[1/5] Loading optimized hyperparameters...")

summary_path = Path("models/training_summary.json")
if summary_path.exists():
    with open(summary_path) as f:
        summary = json.load(f)
    params = summary['hyperparameters']
    print(f"   ✓ Loaded from training_summary.json")
    print(f"   Previous metrics: AUC={summary['metrics']['auc']:.4f}")
else:
    # Fallback to default optimized params
    print("   ⚠ training_summary.json not found, using defaults")
    params = {
        'objective': 'binary',
        'metric': 'auc',
        'num_leaves': 160,
        'max_depth': 13,
        'learning_rate': 0.025,
        'feature_fraction': 0.95,
        'bagging_fraction': 0.95,
        'bagging_freq': 5,
        'min_child_samples': 8,
        'lambda_l1': 0.02,
        'lambda_l2': 0.02,
        'verbose': -1,
        'seed': 42
    }

print(f"   Hyperparameters:")
for key, value in params.items():
    if key not in ['verbose', 'seed']:
        print(f"     - {key}: {value}")

# === Load dataset ===
print("\n[2/5] Loading dataset...")

data_path = Path("data/processed/ieee_features.csv")
if not data_path.exists():
    print(f"   ✗ ERROR: Dataset not found at {data_path}")
    print("\n   Run this first:")
    print("   python training/scripts/prepare_dataset.py")
    exit(1)

df = pd.read_csv(data_path)
print(f"   ✓ Loaded {len(df):,} samples")

# Separate features and target
target_col = "is_fraud"
if target_col not in df.columns:
    print(f"   ✗ ERROR: Target column '{target_col}' not found")
    exit(1)

X = df.drop(columns=[target_col])
y = df[target_col]

print(f"   - Features: {len(X.columns)} columns")
print(f"   - Fraud rate: {y.mean():.2%}")

# === Split data ===
print("\n[3/5] Splitting data (60% train, 20% val, 20% test)...")

X_train, X_temp, y_train, y_temp = train_test_split(
    X, y, test_size=0.4, random_state=42, stratify=y
)

X_val, X_test, y_val, y_test = train_test_split(
    X_temp, y_temp, test_size=0.5, random_state=42, stratify=y_temp
)

print(f"   - Train: {len(X_train):,} ({y_train.mean():.2%} fraud)")
print(f"   - Val:   {len(X_val):,} ({y_val.mean():.2%} fraud)")
print(f"   - Test:  {len(X_test):,} ({y_test.mean():.2%} fraud)")

# Calculate class imbalance
fraud_ratio = y_train.mean()
scale_pos_weight = (1 - fraud_ratio) / fraud_ratio
params['scale_pos_weight'] = scale_pos_weight
print(f"   - Class weight: {scale_pos_weight:.2f}")

# === Train model ===
print("\n[4/5] Training LightGBM model...")

train_data = lgb.Dataset(X_train, label=y_train)
val_data = lgb.Dataset(X_val, label=y_val, reference=train_data)

callbacks = [
    lgb.log_evaluation(period=20),
    lgb.early_stopping(stopping_rounds=20, verbose=True)
]

# Train with dynamic num_boost_round based on learning_rate
# Lower learning rate = more trees needed
lr = params['learning_rate']
num_boost_round = int(100 / lr) if lr < 0.1 else 100

print(f"   Training {num_boost_round} rounds (lr={lr})...")

model = lgb.train(
    params,
    train_data,
    num_boost_round=num_boost_round,
    valid_sets=[train_data, val_data],
    valid_names=['train', 'val'],
    callbacks=callbacks
)

print(f"\n   ✓ Training complete ({model.num_trees()} trees)")

# === Evaluate ===
print("\n[5/5] Evaluating model...")

val_preds = model.predict(X_val)
val_auc = roc_auc_score(y_val, val_preds)

# Precision at top 1%
threshold_1pct = np.percentile(val_preds, 99)
val_preds_1pct = (val_preds >= threshold_1pct).astype(int)
precision_1pct = precision_score(y_val, val_preds_1pct, zero_division=0)

# Recall at 5% FPR
non_fraud_preds = val_preds[y_val == 0]
threshold_5fpr = np.percentile(non_fraud_preds, 95)
val_preds_5fpr = (val_preds >= threshold_5fpr).astype(int)
recall_5fpr = recall_score(y_val, val_preds_5fpr)

test_preds = model.predict(X_test)
test_auc = roc_auc_score(y_test, test_preds)

print("\n   Validation Metrics:")
print(f"     - AUC:           {val_auc:.4f} (target: >0.92)")
print(f"     - Precision@1%:  {precision_1pct:.4f} (target: >0.70)")
print(f"     - Recall@5%FPR:  {recall_5fpr:.4f} (target: >0.65)")
print(f"\n   Test Metrics:")
print(f"     - AUC:           {test_auc:.4f}")

# Top features
print("\n   Top 10 Features:")
feature_importance = pd.DataFrame({
    'feature': X_train.columns,
    'importance': model.feature_importance(importance_type='gain')
}).sort_values('importance', ascending=False)

for idx, row in feature_importance.head(10).iterrows():
    print(f"     {row['feature']:20s} {row['importance']:8.0f}")

# === Save model ===
print("\n" + "=" * 60)
print("Saving model artifacts...")

models_dir = Path("models")
models_dir.mkdir(exist_ok=True)

# Save LightGBM model
lgb_path = models_dir / "fraud_model.txt"
model.save_model(str(lgb_path))
print(f"   ✓ Saved LightGBM model: {lgb_path}")

# Save validation predictions for calibration
np.save(models_dir / "val_scores.npy", val_preds)
np.save(models_dir / "val_labels.npy", y_val.values)
print(f"   ✓ Saved validation data for calibration")

# Update training summary
summary = {
    "metrics": {
        "auc": float(val_auc),
        "precision_1pct": float(precision_1pct),
        "recall_5fpr": float(recall_5fpr),
        "test_auc": float(test_auc)
    },
    "hyperparameters": params,
    "n_features": len(X_train.columns),
    "n_trees": model.num_trees()
}

with open(models_dir / "training_summary.json", 'w') as f:
    json.dump(summary, f, indent=2)
print(f"   ✓ Updated training_summary.json")

# === Next steps ===
print("\n" + "=" * 60)
print("✓ TRAINING COMPLETE!")
print("=" * 60)
print("\nNext steps:")
print("  1. Run: python training/scripts/fix_conversion.py")
print("     (Converts model to ONNX format)")
print("\n  2. Run: python training/scripts/calibrate_model.py")
print("     (Calibrates probability outputs)")
print("\n  3. Run: python training/scripts/diagnose_model.py")
print("     (Verify everything works)")
print("=" * 60)
