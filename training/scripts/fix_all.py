#!/usr/bin/env python3
"""
Master Fix Script - Automatically fix model conversion issues

Purpose: Diagnose and fix ONNX conversion issues automatically.
This script will:
1. Check if ONNX model already works (if yes, you're done!)
2. If not, try to convert existing LightGBM model
3. If that fails, retrain with current LightGBM version
4. Convert to ONNX
5. Calibrate probabilities

Usage:
    python fix_all.py
"""

import subprocess
import sys
from pathlib import Path

def run_script(script_name, description):
    """Run a Python script and return success status."""
    print("\n" + "=" * 60)
    print(f"Running: {description}")
    print("=" * 60)

    script_path = Path(__file__).parent / script_name

    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=False,
            text=True
        )
        return result.returncode == 0
    except Exception as e:
        print(f"Error running {script_name}: {e}")
        return False

def main():
    print("\n" + "=" * 60)
    print("FRAUD MODEL - AUTOMATIC FIX")
    print("=" * 60)
    print("\nThis script will automatically fix your ONNX conversion issues.")
    print("It will try multiple strategies until it succeeds.\n")

    # Step 1: Diagnose
    print("\n📋 STEP 1: Diagnosing current state...")
    run_script("diagnose_model.py", "Diagnosis")

    # Check if ONNX already works
    onnx_path = Path("models/fraud_model.onnx")
    if onnx_path.exists():
        try:
            import onnxruntime as ort
            session = ort.InferenceSession(str(onnx_path))
            print("\n✅ GOOD NEWS: Your ONNX model already works!")
            print("   No conversion needed. You're all set!")
            return True
        except:
            print("\n⚠️  ONNX model exists but won't load. Will try to fix...")

    # Step 2: Try conversion
    print("\n🔄 STEP 2: Attempting ONNX conversion...")
    if run_script("fix_conversion.py", "ONNX Conversion"):
        print("\n✅ Conversion successful!")

        # Step 3: Calibrate
        print("\n📊 STEP 3: Calibrating probabilities...")
        if Path("training/scripts/calibrate_model.py").exists():
            run_script("calibrate_model.py", "Probability Calibration")

        print("\n" + "=" * 60)
        print("✅ ALL DONE! Your model is ready to use.")
        print("=" * 60)
        return True
    else:
        print("\n⚠️  Conversion failed. This usually means a version incompatibility.")
        print("   Trying to retrain with your current LightGBM version...\n")

        # Step 3: Retrain if conversion failed
        print("\n🔧 STEP 3: Retraining model...")
        if not run_script("quick_retrain.py", "Model Retraining"):
            print("\n❌ Retraining failed. Please check your dataset.")
            return False

        # Step 4: Convert again
        print("\n🔄 STEP 4: Converting retrained model...")
        if not run_script("fix_conversion.py", "ONNX Conversion"):
            print("\n❌ Conversion still failing. Please check error messages above.")
            return False

        # Step 5: Calibrate
        print("\n📊 STEP 5: Calibrating probabilities...")
        if Path("training/scripts/calibrate_model.py").exists():
            run_script("calibrate_model.py", "Probability Calibration")

        print("\n" + "=" * 60)
        print("✅ ALL DONE! Your model has been retrained and converted.")
        print("=" * 60)
        return True

if __name__ == "__main__":
    try:
        success = main()
        if success:
            print("\n✅ Success! Your model is ready to use in the API.")
            print("\nYou can now run:")
            print("  uvicorn api.main:app --reload")
        else:
            print("\n❌ Something went wrong. Check the errors above.")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)
