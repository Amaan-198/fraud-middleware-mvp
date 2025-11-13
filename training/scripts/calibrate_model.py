#!/usr/bin/env python3
"""
Model Calibration Script

Purpose: Train an isotonic regression calibrator to convert raw model scores
         to calibrated probabilities.

Usage:
    python calibrate_model.py --scores models/val_scores.npy --labels models/val_labels.npy --output models/calibration.pkl
"""

import argparse
import pickle
from pathlib import Path

import numpy as np
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import brier_score_loss, log_loss


def calibrate_model(scores_path: str, labels_path: str, output_path: str):
    """
    Train isotonic regression calibrator on validation scores.

    Args:
        scores_path: Path to validation scores (.npy file)
        labels_path: Path to validation labels (.npy file)
        output_path: Path to save calibrator (.pkl file)
    """
    print(f"Loading validation scores from {scores_path}...")

    try:
        val_scores = np.load(scores_path)
        val_labels = np.load(labels_path)
    except FileNotFoundError as e:
        print(f"ERROR: File not found: {e.filename}")
        print("Please run train_lightgbm.py first to generate validation scores")
        return

    print(f"Loaded {len(val_scores):,} validation samples")
    print(f"Score range: [{val_scores.min():.4f}, {val_scores.max():.4f}]")
    print(f"Fraud rate: {val_labels.mean():.2%}")

    # === Check Pre-Calibration Metrics ===

    print("\nPre-calibration metrics:")

    # Brier score (measures calibration quality, lower is better)
    brier_before = brier_score_loss(val_labels, val_scores)
    print(f"  Brier score: {brier_before:.4f}")

    # Log loss (another calibration metric, lower is better)
    # Clip to avoid log(0)
    scores_clipped = np.clip(val_scores, 1e-7, 1 - 1e-7)
    logloss_before = log_loss(val_labels, scores_clipped)
    print(f"  Log loss:    {logloss_before:.4f}")

    # === Train Isotonic Regression Calibrator ===

    print("\nTraining isotonic regression calibrator...")

    # IsotonicRegression fits a monotonic function that maps raw scores -> calibrated probabilities
    # out_of_bounds='clip' ensures predictions outside training range are clipped to [0, 1]
    calibrator = IsotonicRegression(out_of_bounds='clip')
    calibrator.fit(val_scores, val_labels)

    print(f"✓ Calibrator trained ({len(calibrator.X_thresholds_)} threshold points)")

    # === Evaluate Calibration ===

    print("\nEvaluating calibration...")

    # Apply calibration to validation set
    calibrated_scores = calibrator.predict(val_scores)

    # Post-calibration metrics
    brier_after = brier_score_loss(val_labels, calibrated_scores)
    logloss_after = log_loss(val_labels, np.clip(calibrated_scores, 1e-7, 1 - 1e-7))

    print(f"  Brier score: {brier_after:.4f} (before: {brier_before:.4f})")
    print(f"  Log loss:    {logloss_after:.4f} (before: {logloss_before:.4f})")

    calibration_error = abs(brier_after - brier_before)
    print(f"  Calibration improvement: {brier_before - brier_after:.4f}")

    # Check calibration error target from ML_ENGINE_SPEC.md
    target_calibration_error = 0.02
    if brier_after < target_calibration_error:
        print(f"  ✓ Calibration error < {target_calibration_error:.2f} (target met)")
    else:
        print(f"  ⚠ Calibration error >= {target_calibration_error:.2f} (target not met)")

    # === Analyze Calibration Curve ===

    print("\nCalibration bins (predicted vs actual):")

    # Divide predictions into 10 bins and check calibration
    n_bins = 10
    bins = np.linspace(0, 1, n_bins + 1)

    for i in range(n_bins):
        bin_mask = (calibrated_scores >= bins[i]) & (calibrated_scores < bins[i + 1])
        if bin_mask.sum() == 0:
            continue

        bin_pred_mean = calibrated_scores[bin_mask].mean()
        bin_true_mean = val_labels[bin_mask].mean()
        bin_count = bin_mask.sum()

        print(f"  [{bins[i]:.1f}, {bins[i+1]:.1f}): "
              f"pred={bin_pred_mean:.3f}, true={bin_true_mean:.3f}, n={bin_count:6d}")

    # === Save Calibrator ===

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"\nSaving calibrator to {output_path}...")

    with open(output_path, 'wb') as f:
        pickle.dump(calibrator, f)

    # Check file size
    file_size_kb = output_path.stat().st_size / 1024
    print(f"✓ Calibrator saved ({file_size_kb:.1f} KB)")

    print(f"\n✓ Calibration complete!")
    print(f"  Calibrator: {output_path}")
    print(f"\nNext step:")
    print(f"  Run convert_to_onnx.py to convert LightGBM model to ONNX format")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Calibrate fraud detection model")
    parser.add_argument(
        "--scores",
        type=str,
        default="models/val_scores.npy",
        help="Path to validation scores (.npy file)"
    )
    parser.add_argument(
        "--labels",
        type=str,
        default="models/val_labels.npy",
        help="Path to validation labels (.npy file)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="models/calibration.pkl",
        help="Path to save calibrator (.pkl file)"
    )

    args = parser.parse_args()
    calibrate_model(args.scores, args.labels, args.output)
