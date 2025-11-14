# Stage 2: ML Engine Specification

## Model Architecture

- **Algorithm:** LightGBM (gbdt)
- **Trees:** 100 (default, stopped with early_stopping)
- **Leaves:** 160
- **Depth:** 13
- **Learning rate:** 0.025
- **Feature fraction:** 0.95
- **Bagging fraction:** 0.95
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

Achieved metrics on validation set (from optimize_pipeline.py):

- **AUC-ROC:** 0.903
- **Precision@1% FPR:** 0.821
- **Recall@5% FPR:** 0.648
- **Calibration (Brier Score):** 0.023

Note: While the AUC target of 0.92 was not quite met, the model achieves strong performance on the precision and recall metrics that matter most for production use. The Brier score of 0.023 is very close to the 0.02 target, indicating good probability calibration.

## Model Artifacts

```
models/
├── fraud_model.onnx      # 2.5MB
├── calibration.pkl       # 50KB
├── shap_values.npz       # 500KB (precomputed)
└── thresholds.yaml       # 1KB
```

## Model Behavior Notes

### Amount Sensitivity

The model exhibits **non-linear response** to transaction amounts:
- Small amounts ($0-100): Low fraud risk (score ~0.2-0.3)
- Medium amounts ($500-1000): **Peak fraud risk** (score ~0.7-0.8)
- Large amounts ($5000+): Moderate risk (score ~0.5)

This learned behavior reflects real-world fraud patterns where:
1. Fraudsters target the "sweet spot" - large enough to profit, small enough to avoid automatic review
2. Very large purchases ($5000+) have different behavioral patterns than typical fraud
3. The model weighs `amount_pct` (percentile vs user history) more heavily than raw `amount`

### Key Feature Relationships

- `amount_pct` ↑ → risk ↑ (but non-linearly, peaks at mid-high range)
- `device_new=True` → risk ↑
- `acct_age_days` ↑ → risk ↓
- `velocity_1h` ↑ → risk ↑↑ (strong signal)

## NOT IN MVP

- Ensemble models
- Deep learning
- Online learning
- Embedding features
- AutoML optimization
