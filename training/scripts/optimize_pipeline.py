#!/usr/bin/env python3
"""
Training Pipeline Optimizer

Automatically runs the full training pipeline with hyperparameter optimization
to meet the target metrics from ML_ENGINE_SPEC.md.

Target Metrics:
- AUC-ROC ≥ 0.92
- Precision@1% ≥ 0.70
- Recall@5% FPR ≥ 0.65
- Calibration error (Brier score) ≤ 0.02
"""

import subprocess
import sys
import re
import shutil
from pathlib import Path
from typing import Dict, Optional, List, Tuple
import json


class TrainingAttempt:
    """Stores results from a single training attempt"""
    def __init__(self, attempt_num: int, params: Dict, metrics: Dict):
        self.attempt_num = attempt_num
        self.params = params
        self.metrics = metrics

    def passes_targets(self) -> bool:
        """Check if this attempt meets all target metrics"""
        return (
            self.metrics.get('auc', 0) >= 0.92 and
            self.metrics.get('precision_1pct', 0) >= 0.70 and
            self.metrics.get('recall_5fpr', 0) >= 0.65 and
            self.metrics.get('brier_score', 1.0) <= 0.02
        )

    def score(self) -> float:
        """Calculate overall score for ranking attempts"""
        # Weighted average of normalized metrics
        auc_score = self.metrics.get('auc', 0) / 0.92
        prec_score = self.metrics.get('precision_1pct', 0) / 0.70
        recall_score = self.metrics.get('recall_5fpr', 0) / 0.65
        calib_score = max(0, 1 - self.metrics.get('brier_score', 1.0) / 0.02)

        return 0.4 * auc_score + 0.3 * prec_score + 0.2 * recall_score + 0.1 * calib_score


def run_command(cmd: List[str], description: str) -> Tuple[bool, str]:
    """Run a shell command and capture output"""
    print(f"\n{'='*60}")
    print(f"{description}")
    print(f"{'='*60}")
    print(f"Command: {' '.join(cmd)}\n")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False
        )

        output = result.stdout + result.stderr
        print(output)

        return result.returncode == 0, output

    except Exception as e:
        print(f"ERROR: {e}")
        return False, str(e)


def extract_metrics_from_training(output: str) -> Dict[str, float]:
    """Parse training output to extract metrics"""
    metrics = {}

    # Extract validation AUC
    auc_match = re.search(r'Validation AUC:\s+([\d.]+)', output)
    if auc_match:
        metrics['auc'] = float(auc_match.group(1))

    # Extract Precision@1%
    prec_match = re.search(r'Precision@1%:\s+([\d.]+)', output)
    if prec_match:
        metrics['precision_1pct'] = float(prec_match.group(1))

    # Extract Recall@5%FPR
    recall_match = re.search(r'Recall@5%FPR:\s+([\d.]+)', output)
    if recall_match:
        metrics['recall_5fpr'] = float(recall_match.group(1))

    return metrics


def extract_calibration_metric(output: str) -> float:
    """Parse calibration output to extract Brier score"""
    # Look for post-calibration Brier score
    brier_match = re.search(r'Brier score:\s+([\d.]+)\s+\(before:', output)
    if brier_match:
        return float(brier_match.group(1))
    return 1.0


def modify_training_script(params: Dict) -> None:
    """Modify train_lightgbm.py with new hyperparameters"""
    script_path = Path("training/scripts/train_lightgbm.py")

    with open(script_path, 'r') as f:
        lines = f.readlines()

    # Find the start and end of the params dict
    start_idx = None
    end_idx = None

    for i, line in enumerate(lines):
        if 'params = {' in line:
            start_idx = i
        if start_idx is not None and line.strip() == '}':
            end_idx = i
            break

    if start_idx is None or end_idx is None:
        print("ERROR: Could not find params dict in training script")
        return

    # Build new params dict with proper indentation
    new_params_lines = ["    params = {\n"]
    for key, value in params.items():
        if isinstance(value, str):
            new_params_lines.append(f"        '{key}': '{value}',\n")
        elif isinstance(value, bool):
            new_params_lines.append(f"        '{key}': {value},\n")
        else:
            new_params_lines.append(f"        '{key}': {value},\n")
    new_params_lines.append("    }\n")

    # Replace the params dict
    new_lines = lines[:start_idx] + new_params_lines + lines[end_idx+1:]

    with open(script_path, 'w') as f:
        f.writelines(new_lines)


def get_hyperparameter_configs() -> List[Dict]:
    """Generate different hyperparameter configurations to try"""

    # Base configuration from the spec
    base_config = {
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
        'verbose': -1,
        'seed': 42
    }

    configs = []

    # Config 1: Ultra-deep, maximum expressiveness
    config1 = base_config.copy()
    config1.update({
        'num_leaves': 200,
        'max_depth': 15,
        'learning_rate': 0.015,
        'feature_fraction': 1.0,
        'bagging_fraction': 1.0,
        'min_child_samples': 3,
        'lambda_l1': 0.0,
        'lambda_l2': 0.0,
    })
    configs.append(config1)

    # Config 2: Very high capacity, minimal regularization
    config2 = base_config.copy()
    config2.update({
        'num_leaves': 180,
        'max_depth': 14,
        'learning_rate': 0.02,
        'feature_fraction': 0.98,
        'bagging_fraction': 0.98,
        'min_child_samples': 5,
        'lambda_l1': 0.005,
        'lambda_l2': 0.005,
    })
    configs.append(config2)

    # Config 3: Extreme capacity with slight reg
    config3 = base_config.copy()
    config3.update({
        'num_leaves': 160,
        'max_depth': 13,
        'learning_rate': 0.025,
        'feature_fraction': 0.95,
        'bagging_fraction': 0.95,
        'min_child_samples': 8,
        'lambda_l1': 0.02,
        'lambda_l2': 0.02,
    })
    configs.append(config3)

    return configs


def backup_model_files():
    """Backup current model files"""
    files_to_backup = [
        'models/fraud_model.txt',
        'models/fraud_model.onnx',
        'models/calibration.pkl'
    ]

    for file_path in files_to_backup:
        path = Path(file_path)
        if path.exists():
            backup_path = path.with_suffix(path.suffix + '.backup')
            shutil.copy2(path, backup_path)
            print(f"Backed up {path} to {backup_path}")


def restore_best_model(attempt: TrainingAttempt):
    """Restore model files from a specific attempt"""
    temp_dir = Path(f"models/attempt_{attempt.attempt_num}")

    if temp_dir.exists():
        files = [
            ('fraud_model.txt', 'models/fraud_model.txt'),
            ('fraud_model.onnx', 'models/fraud_model.onnx'),
            ('calibration.pkl', 'models/calibration.pkl')
        ]

        for src_file, dest_file in files:
            src = temp_dir / src_file
            if src.exists():
                shutil.copy2(src, dest_file)
                print(f"Restored {dest_file}")


def save_attempt_artifacts(attempt_num: int):
    """Save current model artifacts for this attempt"""
    temp_dir = Path(f"models/attempt_{attempt_num}")
    temp_dir.mkdir(parents=True, exist_ok=True)

    files = [
        'models/fraud_model.txt',
        'models/fraud_model.onnx',
        'models/calibration.pkl'
    ]

    for file_path in files:
        path = Path(file_path)
        if path.exists():
            shutil.copy2(path, temp_dir / path.name)


def main():
    print("="*80)
    print("FRAUD MODEL TRAINING PIPELINE OPTIMIZER")
    print("="*80)
    print("\nTarget Metrics:")
    print("  - AUC-ROC ≥ 0.92")
    print("  - Precision@1% ≥ 0.70")
    print("  - Recall@5% FPR ≥ 0.65")
    print("  - Calibration error (Brier score) ≤ 0.02")
    print()

    # Verify processed data exists
    data_path = Path("data/processed/ieee_features.csv")
    if not data_path.exists():
        print(f"ERROR: Processed features not found at {data_path}")
        print("Please ensure the data file exists before running training.")
        sys.exit(1)

    print(f"✓ Found processed features: {data_path}")

    # Backup existing models
    backup_model_files()

    # Get hyperparameter configurations to try
    configs = get_hyperparameter_configs()
    print(f"\nWill try {len(configs)} different hyperparameter configurations")

    attempts: List[TrainingAttempt] = []
    best_attempt: Optional[TrainingAttempt] = None

    # Try each configuration
    for i, config in enumerate(configs, 1):
        print(f"\n{'#'*80}")
        print(f"# ATTEMPT {i}/{len(configs)}")
        print(f"{'#'*80}")

        print(f"\nHyperparameters:")
        for key, value in config.items():
            if key not in ['objective', 'metric', 'verbose', 'seed', 'scale_pos_weight']:
                print(f"  {key}: {value}")

        # Modify training script with new params
        modify_training_script(config)

        # Step 1: Train model
        success, train_output = run_command(
            ["python", "training/scripts/train_lightgbm.py"],
            f"STEP 1: Training LightGBM model (Attempt {i})"
        )

        if not success:
            print(f"✗ Training failed for attempt {i}")
            continue

        # Extract training metrics
        train_metrics = extract_metrics_from_training(train_output)

        # Step 2: Calibrate model
        success, calib_output = run_command(
            ["python", "training/scripts/calibrate_model.py"],
            f"STEP 2: Calibrating model (Attempt {i})"
        )

        if not success:
            print(f"✗ Calibration failed for attempt {i}")
            continue

        # Extract calibration metric
        brier_score = extract_calibration_metric(calib_output)
        train_metrics['brier_score'] = brier_score

        # Step 3: Convert to ONNX
        success, onnx_output = run_command(
            ["python", "training/scripts/convert_to_onnx.py"],
            f"STEP 3: Converting to ONNX (Attempt {i})"
        )

        if not success:
            print(f"✗ ONNX conversion failed for attempt {i}")
            continue

        # Create attempt record
        attempt = TrainingAttempt(i, config, train_metrics)
        attempts.append(attempt)

        # Save artifacts for this attempt
        save_attempt_artifacts(i)

        # Print summary
        print(f"\n{'='*60}")
        print(f"ATTEMPT {i} SUMMARY")
        print(f"{'='*60}")
        print(f"AUC-ROC:          {attempt.metrics.get('auc', 0):.4f}  (target: ≥0.92)")
        print(f"Precision@1%:     {attempt.metrics.get('precision_1pct', 0):.4f}  (target: ≥0.70)")
        print(f"Recall@5% FPR:    {attempt.metrics.get('recall_5fpr', 0):.4f}  (target: ≥0.65)")
        print(f"Calibration (Brier): {attempt.metrics.get('brier_score', 1.0):.4f}  (target: ≤0.02)")
        print(f"Overall Score:    {attempt.score():.4f}")

        if attempt.passes_targets():
            print(f"\n✓ PASSED - All targets met!")
            best_attempt = attempt
            break
        else:
            print(f"\n✗ FAILED - Some targets not met")
            failed = []
            if attempt.metrics.get('auc', 0) < 0.92:
                failed.append(f"AUC ({attempt.metrics.get('auc', 0):.4f} < 0.92)")
            if attempt.metrics.get('precision_1pct', 0) < 0.70:
                failed.append(f"Precision ({attempt.metrics.get('precision_1pct', 0):.4f} < 0.70)")
            if attempt.metrics.get('recall_5fpr', 0) < 0.65:
                failed.append(f"Recall ({attempt.metrics.get('recall_5fpr', 0):.4f} < 0.65)")
            if attempt.metrics.get('brier_score', 1.0) > 0.02:
                failed.append(f"Brier ({attempt.metrics.get('brier_score', 1.0):.4f} > 0.02)")

            print(f"  Failed metrics: {', '.join(failed)}")

        # Update best attempt if this is better
        if best_attempt is None or attempt.score() > best_attempt.score():
            best_attempt = attempt

    # Final summary
    print(f"\n{'#'*80}")
    print(f"# FINAL RESULTS")
    print(f"{'#'*80}")

    if not attempts:
        print("\n✗ No successful training attempts")
        sys.exit(1)

    print(f"\nCompleted {len(attempts)} training attempts")

    # Print all attempts
    print(f"\n{'='*80}")
    print("ALL ATTEMPTS:")
    print(f"{'='*80}")
    print(f"{'Attempt':<8} {'AUC':<8} {'Prec@1%':<9} {'Recall@5%':<11} {'Brier':<8} {'Score':<8} {'Status'}")
    print(f"{'-'*80}")

    for attempt in attempts:
        status = "PASS ✓" if attempt.passes_targets() else "FAIL ✗"
        print(f"{attempt.attempt_num:<8} "
              f"{attempt.metrics.get('auc', 0):<8.4f} "
              f"{attempt.metrics.get('precision_1pct', 0):<9.4f} "
              f"{attempt.metrics.get('recall_5fpr', 0):<11.4f} "
              f"{attempt.metrics.get('brier_score', 1.0):<8.4f} "
              f"{attempt.score():<8.4f} "
              f"{status}")

    # Restore best model
    print(f"\n{'='*80}")
    print(f"BEST MODEL: Attempt {best_attempt.attempt_num}")
    print(f"{'='*80}")
    print(f"AUC-ROC:          {best_attempt.metrics.get('auc', 0):.4f}  (target: ≥0.92)")
    print(f"Precision@1%:     {best_attempt.metrics.get('precision_1pct', 0):.4f}  (target: ≥0.70)")
    print(f"Recall@5% FPR:    {best_attempt.metrics.get('recall_5fpr', 0):.4f}  (target: ≥0.65)")
    print(f"Calibration (Brier): {best_attempt.metrics.get('brier_score', 1.0):.4f}  (target: ≤0.02)")
    print(f"Overall Score:    {best_attempt.score():.4f}")

    if best_attempt.passes_targets():
        print(f"\n✓✓✓ BEST MODEL PASSES ALL TARGETS ✓✓✓")
    else:
        print(f"\n⚠ Best model does NOT pass all targets")
        print(f"Consider:")
        print(f"  - Collecting more training data")
        print(f"  - Engineering better features")
        print(f"  - Trying more hyperparameter combinations")

    # Restore best model files
    print(f"\nRestoring best model artifacts to models/...")
    restore_best_model(best_attempt)

    print(f"\n{'='*80}")
    print("FINAL MODEL ARTIFACTS:")
    print(f"{'='*80}")
    print("  models/fraud_model.txt")
    print("  models/fraud_model.onnx")
    print("  models/calibration.pkl")

    print(f"\n✓ Training pipeline complete!")

    # Save summary
    summary = {
        'best_attempt': best_attempt.attempt_num,
        'total_attempts': len(attempts),
        'metrics': best_attempt.metrics,
        'passes_all_targets': best_attempt.passes_targets(),
        'hyperparameters': best_attempt.params
    }

    summary_path = Path("models/training_summary.json")
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2)

    print(f"Training summary saved to {summary_path}")


if __name__ == "__main__":
    main()
