# Stage 2: ML Engine Specification

## Model Architecture

- **Algorithm:** LightGBM (gbdt)
- **Trees:** 100
- **Leaves:** 31
- **Depth:** 6
- **Learning rate:** 0.1
- **Training data:** IEEE-CIS Fraud Detection (~500k transactions)

## Model Pipeline

### 1. Feature Extraction

Input: Raw transaction → Output: 15 features
Location: `api/utils/features.py`
Latency budget: 10ms

### 2. Inference

Input: Features → Output: Raw score [0,1]
Model: `models/fraud_model.onnx`
Runtime: ONNX Runtime
Latency budget: 20ms

### 3. Calibration

Input: Raw score → Output: Calibrated probability
Method: Isotonic regression
Model: `models/calibration.pkl`
Latency budget: 5ms

### 4. Explanation

Input: Features + Model → Output: Top 3 features
Method: TreeSHAP (precomputed trees)
Latency budget: 5ms

## Training Pipeline

Location: `training/notebooks/02_training.ipynb`

### Data Prep

1. Load IEEE-CIS fraud dataset
2. Engineer 15 features matching contract
3. Train/val/test split (60/20/20)
4. Handle class imbalance (1:20 fraud ratio)

### Model Training

```python
params = {
    'objective': 'binary',
    'metric': 'auc',
    'num_leaves': 31,
    'learning_rate': 0.1,
    'feature_fraction': 0.8,
    'bagging_fraction': 0.9,
    'min_child_samples': 20,
    'lambda_l1': 0.1,
    'lambda_l2': 0.1
}
```

### Calibration

```python
from sklearn.isotonic import IsotonicRegression
calibrator = IsotonicRegression(out_of_bounds='clip')
calibrator.fit(val_scores, val_labels)
```

### ONNX Conversion

```python
import onnxmltools
onnx_model = onnxmltools.convert_lightgbm(
    lgb_model,
    initial_types=[('features', FloatTensorType([None, 15]))]
)
```

## Model Metrics

- AUC-ROC: >0.92
- Precision@1%: >0.70
- Recall@5% FPR: >0.65
- Calibration error: <0.02

## Model Artifacts

```
models/
├── fraud_model.onnx      # 2.5MB
├── calibration.pkl       # 50KB
├── shap_values.npz       # 500KB (precomputed)
└── thresholds.yaml       # 1KB
```

## Monotonic Constraints

- `amount_pct` ↑ → risk ↑
- `device_new=True` → risk ↑
- `acct_age_days` ↑ → risk ↓

## NOT IN MVP

- Ensemble models
- Deep learning
- Online learning
- Embedding features
- AutoML optimization
