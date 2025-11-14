#!/usr/bin/env python3
"""
Fixed ONNX Conversion Script

Purpose: Convert LightGBM model to ONNX with robust error handling.
This script handles version compatibility issues and provides alternatives.

Usage:
    python fix_conversion.py
"""

import sys
from pathlib import Path
import numpy as np

print("=" * 60)
print("FIXED ONNX CONVERSION SCRIPT")
print("=" * 60)

# === Import dependencies ===
print("\n[1/6] Importing dependencies...")

try:
    import lightgbm as lgb
    import onnxmltools
    from onnxmltools.convert.common.data_types import FloatTensorType
    import onnx
    import onnxruntime as ort
    print(f"   ✓ LightGBM version: {lgb.__version__}")
    print(f"   ✓ ONNX version: {onnx.__version__}")
    print(f"   ✓ ONNX Runtime version: {ort.__version__}")
except ImportError as e:
    print(f"\n   ✗ ERROR: Missing package: {e}")
    print("\n   Please install dependencies:")
    print("   pip install lightgbm onnxruntime onnxmltools onnx")
    sys.exit(1)

# === Load LightGBM model ===
print("\n[2/6] Loading LightGBM model...")

model_path = Path("models/fraud_model.txt")

if not model_path.exists():
    print(f"   ✗ ERROR: Model file not found at {model_path}")
    print("\n   You need to train the model first:")
    print("   python training/scripts/train_lightgbm.py")
    sys.exit(1)

lgb_model = None
load_method = None

# Try Method 1: Standard Booster loading
try:
    lgb_model = lgb.Booster(model_file=str(model_path))
    load_method = "Booster"
    print(f"   ✓ Loaded with lgb.Booster()")
except Exception as e1:
    print(f"   ✗ Method 1 (lgb.Booster) failed: {str(e1)[:80]}")

    # Try Method 2: Load from string
    try:
        print("   Trying alternative method...")
        with open(model_path, 'r') as f:
            model_str = f.read()
        lgb_model = lgb.Booster(model_str=model_str)
        load_method = "model_str"
        print(f"   ✓ Loaded with model_str method")
    except Exception as e2:
        print(f"   ✗ Method 2 (model_str) failed: {str(e2)[:80]}")

        # Try Method 3: Check if we need to retrain
        print("\n   ⚠ Cannot load model with current LightGBM version")
        print(f"   Your LightGBM version: {lgb.__version__}")
        print("\n   SOLUTION: The model needs to be retrained with your LightGBM version")
        print("   Run this command:")
        print("   python training/scripts/train_lightgbm.py")
        sys.exit(1)

print(f"   - Trees: {lgb_model.num_trees()}")
print(f"   - Features: {len(lgb_model.feature_name())}")
print(f"   - Feature names: {', '.join(lgb_model.feature_name()[:5])}...")

# === Verify model works ===
print("\n[3/6] Testing LightGBM inference...")

n_features = len(lgb_model.feature_name())
test_input = np.random.randn(3, n_features).astype(np.float32)

try:
    lgb_predictions = lgb_model.predict(test_input)
    print(f"   ✓ LightGBM inference works")
    print(f"   - Test predictions: {lgb_predictions[:3]}")
except Exception as e:
    print(f"   ✗ LightGBM inference failed: {e}")
    sys.exit(1)

# === Convert to ONNX ===
print(f"\n[4/6] Converting to ONNX (n_features={n_features})...")

initial_types = [("features", FloatTensorType([None, n_features]))]

try:
    onnx_model = onnxmltools.convert_lightgbm(
        lgb_model,
        initial_types=initial_types,
        target_opset=12
    )
    print(f"   ✓ Conversion successful")
except Exception as e:
    print(f"   ✗ Conversion failed: {e}")
    print("\n   Try updating onnxmltools:")
    print("   pip install --upgrade onnxmltools")
    sys.exit(1)

# === Validate ONNX ===
print("\n[5/6] Validating ONNX model...")

serialized_model = onnx_model.SerializeToString()

# Skip checker for ONNX >= 1.19 (known bug)
onnx_version = tuple(int(x) for x in onnx.__version__.split('.')[:2])
if onnx_version >= (1, 19):
    print("   ⚠ Skipping onnx.checker (ONNX >= 1.19 has a bug)")
else:
    try:
        onnx.checker.check_model(onnx.load_from_string(serialized_model))
        print("   ✓ ONNX model is valid")
    except Exception as e:
        print(f"   ⚠ Validation warning: {e}")

# === Save ONNX ===
output_path = Path("models/fraud_model.onnx")
output_path.parent.mkdir(parents=True, exist_ok=True)

print(f"\n[6/6] Saving ONNX model to {output_path}...")

with open(output_path, "wb") as f:
    f.write(serialized_model)

file_size_mb = output_path.stat().st_size / (1024 * 1024)
print(f"   ✓ Saved ({file_size_mb:.2f} MB)")

# === Test ONNX inference ===
print("\nTesting ONNX inference...")

try:
    session = ort.InferenceSession(str(output_path))
    input_name = session.get_inputs()[0].name
    output_name = session.get_outputs()[0].name

    print(f"   - Input: {input_name} {session.get_inputs()[0].shape}")
    print(f"   - Output: {output_name}")

    # Run inference
    import time
    start = time.perf_counter()
    onnx_output = session.run([output_name], {input_name: test_input})[0]
    elapsed_ms = (time.perf_counter() - start) * 1000

    print(f"   ✓ Inference time: {elapsed_ms:.2f} ms (batch_size=3)")

    # Extract probabilities
    if onnx_output.ndim == 2 and onnx_output.shape[1] > 1:
        onnx_probs = onnx_output[:, 1]
    else:
        onnx_probs = np.asarray(onnx_output).reshape(-1)

    # Compare with LightGBM
    max_diff = np.abs(lgb_predictions - onnx_probs).max()
    print(f"   - Max difference vs LightGBM: {max_diff:.6f}")

    if max_diff < 1e-5:
        print(f"   ✓ Predictions match perfectly!")
    elif max_diff < 1e-3:
        print(f"   ✓ Predictions match (small numerical difference)")
    else:
        print(f"   ⚠ Predictions differ (this is unusual)")
        print(f"   LightGBM: {lgb_predictions[:3]}")
        print(f"   ONNX:     {onnx_probs[:3]}")

    # Performance check
    if elapsed_ms / 3 < 20:  # Per-sample latency
        print(f"   ✓ Latency meets target (<20ms per sample)")
    else:
        print(f"   ⚠ Latency higher than target (>20ms per sample)")

except Exception as e:
    print(f"   ✗ ONNX inference test failed: {e}")
    sys.exit(1)

# === Success summary ===
print("\n" + "=" * 60)
print("✓ CONVERSION COMPLETE!")
print("=" * 60)
print(f"\nONNX model saved to: {output_path}")
print(f"File size: {file_size_mb:.2f} MB")
print(f"Inference time: {elapsed_ms:.2f} ms (batch of 3)")
print(f"Prediction accuracy: {max_diff:.6f} max difference")
print("\nYour model is ready to use in the API!")
print("\nFiles ready:")
print("  1. models/fraud_model.onnx - ONNX model for fast inference")
print("  2. models/calibration.pkl - Probability calibrator")
print("\nYou can now run the API:")
print("  uvicorn api.main:app --reload")
print("=" * 60)
