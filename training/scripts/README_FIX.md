# ONNX Model Conversion Fix

If you're getting errors when trying to convert your LightGBM model to ONNX, these scripts will help.

## Quick Fix (Recommended)

**Just run this one command:**

```bash
python training/scripts/fix_all.py
```

This will automatically:
1. ✅ Check if your ONNX model already works (it probably does!)
2. 🔄 If not, try to convert it
3. 🔧 If conversion fails, retrain with your LightGBM version
4. 📊 Calibrate probabilities
5. ✅ Verify everything works

## Individual Scripts

If you want more control, run these scripts individually:

### 1. Diagnose Issues
```bash
python training/scripts/diagnose_model.py
```
- Checks what's working and what's not
- Shows package versions
- Tests model loading
- **Run this first to understand the problem**

### 2. Fix Conversion
```bash
python training/scripts/fix_conversion.py
```
- Tries to convert existing LightGBM model to ONNX
- Uses robust error handling
- Tests multiple loading methods
- **Use this if your model exists but won't convert**

### 3. Retrain Model
```bash
python training/scripts/quick_retrain.py
```
- Retrains model with your optimized hyperparameters
- Uses your current LightGBM version (ensures compatibility)
- Saves validation data for calibration
- **Use this if conversion keeps failing**

### 4. Calibrate Model
```bash
python training/scripts/calibrate_model.py
```
- Calibrates probability outputs
- Improves prediction reliability
- **Run after successful conversion**

## Common Issues

### Issue 1: "Model format error, expect a tree here"
**Cause:** LightGBM version mismatch between training and conversion.

**Solution:**
```bash
python training/scripts/quick_retrain.py
python training/scripts/fix_conversion.py
```

### Issue 2: "ONNX model exists but won't load"
**Cause:** ONNX/ONNXRuntime version incompatibility.

**Solution:**
```bash
pip install --upgrade onnxruntime onnx
python training/scripts/fix_conversion.py
```

### Issue 3: "Dataset not found"
**Cause:** Need to prepare dataset first.

**Solution:**
```bash
python training/scripts/prepare_dataset.py
python training/scripts/quick_retrain.py
```

## What Each File Does

- **diagnose_model.py**: Diagnostic tool - checks what's working
- **fix_conversion.py**: Smart converter - tries multiple methods
- **quick_retrain.py**: Fast retraining - uses your optimized params
- **fix_all.py**: Master script - runs everything automatically

## Notes

- Your ONNX model probably already works! Run `diagnose_model.py` first.
- The original `convert_to_onnx.py` is still there and works fine if you have no version issues.
- These scripts use your optimized hyperparameters from `training_summary.json`.

## Still Having Issues?

1. Check Python package versions:
   ```bash
   pip list | grep -E "(lightgbm|onnx|numpy)"
   ```

2. Try upgrading packages:
   ```bash
   pip install --upgrade lightgbm onnxruntime onnxmltools onnx
   ```

3. Make sure you're in your virtual environment:
   ```bash
   # Windows
   .venv\Scripts\activate

   # Linux/Mac
   source .venv/bin/activate
   ```

4. Check that your dataset exists:
   ```bash
   ls data/processed/ieee_features.csv
   ```
