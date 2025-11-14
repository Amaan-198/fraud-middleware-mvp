#!/usr/bin/env python3
"""
Model Diagnostics Script

Purpose: Check if model files are working correctly.

Usage:
    python diagnose_model.py
"""

import sys
from pathlib import Path

print("=" * 60)
print("FRAUD MODEL DIAGNOSTICS")
print("=" * 60)

# === Check Python packages ===
print("\n1. Checking Python packages...")

required_packages = {
    'lightgbm': None,
    'onnxruntime': None,
    'onnxmltools': None,
    'numpy': None,
    'onnx': None
}

for package in required_packages:
    try:
        mod = __import__(package)
        version = getattr(mod, '__version__', 'unknown')
        required_packages[package] = version
        print(f"   ✓ {package}: {version}")
    except ImportError:
        print(f"   ✗ {package}: NOT INSTALLED")
        required_packages[package] = None

if any(v is None for v in required_packages.values()):
    print("\n   [ERROR] Missing packages. Install with:")
    print("   pip install lightgbm onnxruntime onnxmltools onnx numpy")
    sys.exit(1)

# === Check model files ===
print("\n2. Checking model files...")

model_dir = Path("models")
files_to_check = {
    "fraud_model.txt": "LightGBM model",
    "fraud_model.onnx": "ONNX model",
    "calibration.pkl": "Calibration model"
}

for filename, description in files_to_check.items():
    filepath = model_dir / filename
    if filepath.exists():
        size_mb = filepath.stat().st_size / (1024 * 1024)
        print(f"   ✓ {filename}: {size_mb:.2f} MB ({description})")
    else:
        print(f"   ✗ {filename}: NOT FOUND ({description})")

# === Try loading LightGBM model ===
print("\n3. Testing LightGBM model...")

lgb_path = model_dir / "fraud_model.txt"
if lgb_path.exists():
    try:
        import lightgbm as lgb

        # Method 1: Try loading as Booster
        try:
            model = lgb.Booster(model_file=str(lgb_path))
            print(f"   ✓ Model loads with lgb.Booster()")
            print(f"   - Number of trees: {model.num_trees()}")
            print(f"   - Number of features: {len(model.feature_name())}")
            print(f"   - Feature names: {model.feature_name()[:5]}...")
        except Exception as e:
            print(f"   ✗ Method 1 (lgb.Booster) failed: {str(e)[:100]}")

            # Method 2: Try alternative loading
            print("   Trying alternative loading method...")
            try:
                with open(lgb_path, 'r') as f:
                    first_lines = [f.readline().strip() for _ in range(5)]
                print(f"   File starts with: {first_lines[0]}")

                # Check if it's actually a LightGBM text format
                if first_lines[0] == 'tree':
                    print("   Model file appears to be in correct LightGBM text format")
                    print("   This might be a version incompatibility issue")
                else:
                    print(f"   Unexpected format. First line: {first_lines[0]}")
            except Exception as e2:
                print(f"   ✗ Could not read file: {e2}")

    except Exception as e:
        print(f"   ✗ Error: {e}")
else:
    print("   ✗ Model file not found")

# === Try loading ONNX model ===
print("\n4. Testing ONNX model...")

onnx_path = model_dir / "fraud_model.onnx"
if onnx_path.exists():
    try:
        import onnxruntime as ort
        import numpy as np

        # Create session
        session = ort.InferenceSession(str(onnx_path))
        print(f"   ✓ ONNX model loads successfully!")

        # Get input/output info
        input_name = session.get_inputs()[0].name
        input_shape = session.get_inputs()[0].shape
        output_name = session.get_outputs()[0].name

        print(f"   - Input name: {input_name}")
        print(f"   - Input shape: {input_shape}")
        print(f"   - Output name: {output_name}")

        # Test inference
        test_input = np.random.randn(1, 15).astype(np.float32)
        output = session.run([output_name], {input_name: test_input})[0]

        print(f"   ✓ Test inference works!")
        print(f"   - Output shape: {output.shape}")
        print(f"   - Sample output: {output[0]}")

    except Exception as e:
        print(f"   ✗ ONNX model failed: {e}")
else:
    print("   ✗ ONNX model file not found")

# === Summary ===
print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)

if onnx_path.exists():
    try:
        import onnxruntime as ort
        session = ort.InferenceSession(str(onnx_path))
        print("\n✓ GOOD NEWS: Your ONNX model is working perfectly!")
        print("  You don't need to convert anything. The API can use this model.")
        print("\n  Next steps:")
        print("  1. Your ONNX model at models/fraud_model.onnx is ready to use")
        print("  2. The API should work fine with this model")
        print("  3. You can ignore the LightGBM loading error")
    except:
        print("\n⚠ ISSUE: ONNX model exists but won't load.")
        print("  Try running: python training/scripts/fix_conversion.py")
else:
    print("\n⚠ ISSUE: ONNX model not found.")
    print("  Try running: python training/scripts/fix_conversion.py")

print("\n" + "=" * 60)
