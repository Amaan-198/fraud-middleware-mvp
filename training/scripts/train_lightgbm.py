#!/usr/bin/env python3
"""
LightGBM Training Script

Purpose: Train LightGBM model according to ML_ENGINE_SPEC.md

Usage:
    python train_lightgbm.py --input data/processed/ieee_features.csv --output models/fraud_model.txt
"""

import argparse
from pathlib import Path

import pandas as pd
import numpy as np
import lightgbm as lgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, precision_score, recall_score


def train_model(input_path: str, output_path: str, val_output_dir: str):
    """
    Train LightGBM fraud detection model.

    Args:
        input_path: Path to processed features CSV
        output_path: Path to save trained model
        val_output_dir: Directory to save validation scores/labels for calibration
    """
    print(f"Loading dataset from {input_path}...")

    try:
        df = pd.read_csv(input_path)
        print(f"Loaded {len(df):,} samples")
    except FileNotFoundError:
        print(f"ERROR: File not found: {input_path}")
        print("Please run prepare_dataset.py first to generate the processed dataset")
        return

    # Separate features and target
    target_col = "is_fraud"
    if target_col not in df.columns:
        print(f"ERROR: Target column '{target_col}' not found in dataset")
        return

    X = df.drop(columns=[target_col])
    y = df[target_col]

    print(f"Features: {len(X.columns)} columns")
    print(f"Fraud rate: {y.mean():.2%}")

    # === Data Splitting (60/20/20) ===

    print("\nSplitting data (60% train, 20% val, 20% test)...")

    # First split: 60% train, 40% temp
    X_train, X_temp, y_train, y_temp = train_test_split(
        X, y, test_size=0.4, random_state=42, stratify=y
    )

    # Second split: 50% of temp -> 20% val, 20% test
    X_val, X_test, y_val, y_test = train_test_split(
        X_temp, y_temp, test_size=0.5, random_state=42, stratify=y_temp
    )

    print(f"  Train: {len(X_train):,} samples ({y_train.mean():.2%} fraud)")
    print(f"  Val:   {len(X_val):,} samples ({y_val.mean():.2%} fraud)")
    print(f"  Test:  {len(X_test):,} samples ({y_test.mean():.2%} fraud)")

    # === Handle Class Imbalance ===

    # Calculate scale_pos_weight for imbalanced classes (fraud is ~1-5% of data)
    fraud_ratio = y_train.mean()
    scale_pos_weight = (1 - fraud_ratio) / fraud_ratio
    print(f"\nClass imbalance ratio: {scale_pos_weight:.1f}:1 (non-fraud:fraud)")
    print(f"Using scale_pos_weight={scale_pos_weight:.2f}")

    # === Model Training ===

    print("\nTraining LightGBM model...")

    # Parameters from ML_ENGINE_SPEC.md
    params = {
        'objective': 'binary',
        'metric': 'auc',
        'num_leaves': 31,
        'max_depth': 6,
        'learning_rate': 0.1,
        'feature_fraction': 0.8,
        'bagging_fraction': 0.9,
        'bagging_freq': 5,
        'min_child_samples': 20,
        'lambda_l1': 0.1,
        'lambda_l2': 0.1,
        'scale_pos_weight': scale_pos_weight,
        'verbose': -1,
        'seed': 42
    }

    # Create LightGBM datasets
    train_data = lgb.Dataset(X_train, label=y_train)
    val_data = lgb.Dataset(X_val, label=y_val, reference=train_data)

    # Train model (100 trees per spec)
    num_trees = 100
    callbacks = [
        lgb.log_evaluation(period=10),
        lgb.early_stopping(stopping_rounds=20, verbose=True)
    ]

    model = lgb.train(
        params,
        train_data,
        num_boost_round=num_trees,
        valid_sets=[train_data, val_data],
        valid_names=['train', 'val'],
        callbacks=callbacks
    )

    print(f"\n✓ Training complete ({model.num_trees()} trees)")

    # === Model Evaluation ===

    print("\nEvaluating model...")

    # Validation set
    val_preds = model.predict(X_val)
    val_auc = roc_auc_score(y_val, val_preds)

    # Calculate precision at 1% threshold (high precision requirement)
    threshold_1pct = np.percentile(val_preds, 99)  # Top 1% predictions
    val_preds_binary = (val_preds >= threshold_1pct).astype(int)
    precision_1pct = precision_score(y_val, val_preds_binary, zero_division=0)

    # Calculate recall at 5% FPR
    # Sort predictions and find threshold at 95th percentile of non-fraud
    non_fraud_preds = val_preds[y_val == 0]
    threshold_5pct_fpr = np.percentile(non_fraud_preds, 95)
    val_preds_5fpr = (val_preds >= threshold_5pct_fpr).astype(int)
    recall_5fpr = recall_score(y_val, val_preds_5fpr)

    print(f"  Validation AUC: {val_auc:.4f} (target: >0.92)")
    print(f"  Precision@1%:   {precision_1pct:.4f} (target: >0.70)")
    print(f"  Recall@5%FPR:   {recall_5fpr:.4f} (target: >0.65)")

    # Test set
    test_preds = model.predict(X_test)
    test_auc = roc_auc_score(y_test, test_preds)
    print(f"  Test AUC:       {test_auc:.4f}")

    # Feature importance
    print("\nTop 10 features:")
    feature_importance = pd.DataFrame({
        'feature': X_train.columns,
        'importance': model.feature_importance(importance_type='gain')
    }).sort_values('importance', ascending=False)

    for idx, row in feature_importance.head(10).iterrows():
        print(f"  {row['feature']:20s} {row['importance']:8.0f}")

    # === Save Model Artifacts ===

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"\nSaving model to {output_path}...")
    model.save_model(str(output_path))

    # Save validation predictions for calibration
    val_output_dir = Path(val_output_dir)
    val_output_dir.mkdir(parents=True, exist_ok=True)

    val_scores_path = val_output_dir / "val_scores.npy"
    val_labels_path = val_output_dir / "val_labels.npy"

    print(f"Saving validation scores to {val_scores_path}...")
    np.save(val_scores_path, val_preds)
    np.save(val_labels_path, y_val.values)

    print(f"\n✓ Training complete!")
    print(f"  Model: {output_path}")
    print(f"  Val scores: {val_scores_path}")
    print(f"  Val labels: {val_labels_path}")
    print(f"\nNext steps:")
    print(f"  1. Run calibrate_model.py to train probability calibrator")
    print(f"  2. Run convert_to_onnx.py to convert model to ONNX format")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train LightGBM fraud detection model")
    parser.add_argument(
        "--input",
        type=str,
        default="data/processed/ieee_features.csv",
        help="Path to processed features CSV"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="models/fraud_model.txt",
        help="Path to save trained LightGBM model"
    )
    parser.add_argument(
        "--val-output",
        type=str,
        default="models",
        help="Directory to save validation scores/labels"
    )

    args = parser.parse_args()
    train_model(args.input, args.output, args.val_output)
