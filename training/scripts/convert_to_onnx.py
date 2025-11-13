#!/usr/bin/env python3
"""
ONNX Conversion Script

Purpose: Convert LightGBM model to ONNX format for fast inference.

Usage:
    python convert_to_onnx.py --input models/fraud_model.txt --output models/fraud_model.onnx
"""

import argparse
from pathlib import Path

import numpy as np
import lightgbm as lgb
import onnx
import onnxmltools
from onnxmltools.convert.common.data_types import FloatTensorType
import onnxruntime as ort


def convert_to_onnx(input_path: str, output_path: str, n_features: int = 15):
    """
    Convert LightGBM model to ONNX format.

    Args:
        input_path: Path to LightGBM model (.txt file)
        output_path: Path to save ONNX model (.onnx file)
        n_features: Number of input features (default: 15 per FEATURE_CONTRACT.md)
    """
    print(f"Loading LightGBM model from {input_path}...")

    try:
        lgb_model = lgb.Booster(model_file=input_path)
    except Exception as e:
        print(f"ERROR: Failed to load LightGBM model: {e}")
        print("Please run train_lightgbm.py first to generate the model")
        return

    print(f"✓ Loaded model with {lgb_model.num_trees()} trees")
    print(f"  Feature names: {lgb_model.feature_name()[:5]}... ({len(lgb_model.feature_name())} total)")

    # === Convert to ONNX ===

    print(f"\nConverting to ONNX format (input shape: [None, {n_features}])...")

    # Define input type: batch_size x n_features (batch_size=None for dynamic)
    initial_types = [('features', FloatTensorType([None, n_features]))]

    try:
        onnx_model = onnxmltools.convert_lightgbm(
            lgb_model,
            initial_types=initial_types,
            target_opset=12  # ONNX opset version
        )
    except Exception as e:
        print(f"ERROR: ONNX conversion failed: {e}")
        return

    print(f"✓ Conversion successful")

    # === Validate ONNX Model ===

    print("\nValidating ONNX model...")

    try:
        onnx.checker.check_model(onnx_model)
        print("✓ ONNX model is valid")
    except Exception as e:
        print(f"⚠ ONNX validation warning: {e}")

    # === Save ONNX Model ===

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"\nSaving ONNX model to {output_path}...")

    with open(output_path, 'wb') as f:
        f.write(onnx_model.SerializeToString())

    # Check file size
    file_size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"✓ ONNX model saved ({file_size_mb:.2f} MB)")

    # Target size from ML_ENGINE_SPEC.md is ~2.5MB
    target_size_mb = 2.5
    if file_size_mb > target_size_mb * 2:
        print(f"⚠ Model size ({file_size_mb:.2f} MB) is larger than target ({target_size_mb} MB)")

    # === Test Inference ===

    print("\nTesting ONNX inference...")

    # Create ONNX Runtime session
    try:
        session = ort.InferenceSession(str(output_path))
    except Exception as e:
        print(f"ERROR: Failed to create ONNX session: {e}")
        return

    # Get input/output names
    input_name = session.get_inputs()[0].name
    output_name = session.get_outputs()[0].name

    print(f"  Input name:  {input_name}")
    print(f"  Output name: {output_name}")

    # Generate random test input
    test_input = np.random.randn(5, n_features).astype(np.float32)

    # Run inference
    import time
    start = time.perf_counter()

    onnx_output = session.run([output_name], {input_name: test_input})[0]

    elapsed_ms = (time.perf_counter() - start) * 1000
    print(f"  Inference time: {elapsed_ms:.2f} ms (batch_size=5)")

    # Check output shape and values
    print(f"  Output shape: {onnx_output.shape}")
    print(f"  Sample predictions: {onnx_output[:3, 1]}")  # Probability of class 1 (fraud)

    # Latency target from ML_ENGINE_SPEC.md is <20ms
    latency_target_ms = 20
    if elapsed_ms > latency_target_ms:
        print(f"⚠ Inference time ({elapsed_ms:.2f} ms) exceeds target ({latency_target_ms} ms)")
        print(f"  Note: This is a batch of 5. Single inference should be faster.")
    else:
        print(f"✓ Inference time meets target (<{latency_target_ms} ms)")

    # === Compare with LightGBM ===

    print("\nComparing ONNX vs LightGBM predictions...")

    # Get predictions from original LightGBM model
    lgb_output = lgb_model.predict(test_input)

    # ONNX outputs probabilities for both classes, take class 1
    onnx_probs = onnx_output[:, 1]

    # Calculate max difference
    max_diff = np.abs(lgb_output - onnx_probs).max()
    print(f"  Max prediction difference: {max_diff:.6f}")

    if max_diff < 1e-5:
        print(f"✓ Predictions match (difference < 1e-5)")
    else:
        print(f"⚠ Predictions differ by {max_diff:.6f}")
        print(f"  LightGBM: {lgb_output[:3]}")
        print(f"  ONNX:     {onnx_probs[:3]}")

    # === Summary ===

    print(f"\n✓ ONNX conversion complete!")
    print(f"  Model: {output_path} ({file_size_mb:.2f} MB)")
    print(f"  Inference time: {elapsed_ms:.2f} ms (batch_size=5)")
    print(f"\nModel artifacts ready:")
    print(f"  1. {output_path} - ONNX model for inference")
    print(f"  2. models/calibration.pkl - Probability calibrator")
    print(f"\nYou can now use these models in the API (api/models/ml_engine.py)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert LightGBM model to ONNX")
    parser.add_argument(
        "--input",
        type=str,
        default="models/fraud_model.txt",
        help="Path to LightGBM model (.txt file)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="models/fraud_model.onnx",
        help="Path to save ONNX model (.onnx file)"
    )
    parser.add_argument(
        "--n-features",
        type=int,
        default=15,
        help="Number of input features (default: 15)"
    )

    args = parser.parse_args()
    convert_to_onnx(args.input, args.output, args.n_features)
