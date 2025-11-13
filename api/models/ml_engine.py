"""
Stage 2: ML Engine

Probabilistic fraud scoring using machine learning.
- Feature extraction (15 core features)
- ONNX model inference
- Probability calibration
- SHAP explanations

Latency budget: <40ms
"""

from typing import Dict, List, Any, Optional
import random


class MLEngine:
    """
    Machine learning fraud detection engine.

    Uses LightGBM model (ONNX) with calibrated probabilities.
    """

    def __init__(self, model_path: Optional[str] = None, calibration_path: Optional[str] = None):
        """
        Initialize ML engine.

        Args:
            model_path: Path to ONNX model (default: models/fraud_model.onnx)
            calibration_path: Path to calibration model (default: models/calibration.pkl)
        """
        # STUB IMPLEMENTATION
        # In production:
        # - Load ONNX model with onnxruntime
        # - Load calibration model with pickle
        # - Precompute SHAP values

        self.model_path = model_path or "models/fraud_model.onnx"
        self.calibration_path = calibration_path or "models/calibration.pkl"

        # Stub: Model and calibrator not loaded
        self.model = None
        self.calibrator = None
        self.feature_names = [
            "amount_pct",
            "device_new",
            "acct_age_days",
            "txn_count_1h",
            "txn_count_24h",
            "avg_amount_30d",
            "geo_distance_km",
            "time_since_last_txn_min",
            "card_age_days",
            "merchant_risk_score",
            "ip_risk_score",
            "email_domain_age_days",
            "billing_shipping_match",
            "device_count_30d",
            "failed_txn_count_7d"
        ]

    def predict(self, transaction: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate fraud score for transaction.

        Args:
            transaction: Transaction data dict

        Returns:
            Dict with:
                - score: float (calibrated probability)
                - top_features: List[Dict] (SHAP explanations)
                - blocked: bool
        """
        # STUB IMPLEMENTATION
        # In production:
        # 1. Extract features from transaction
        # 2. Run ONNX inference
        # 3. Apply calibration
        # 4. Compute SHAP values

        # For stub, return random score
        raw_score = random.uniform(0.1, 0.5)  # Low scores for testing

        # Stub top features (would be from SHAP)
        top_features = [
            {
                "name": "amount_pct",
                "value": transaction.get("amount", 0) / 1000,
                "contribution": 0.15
            },
            {
                "name": "device_new",
                "value": 0,
                "contribution": 0.05
            },
            {
                "name": "txn_count_1h",
                "value": 1,
                "contribution": 0.02
            }
        ]

        return {
            "score": round(raw_score, 3),
            "top_features": top_features,
            "blocked": False,
            "model_version": "stub_v1"
        }

    def extract_features(self, transaction: Dict[str, Any]) -> List[float]:
        """
        Extract 15 features from transaction.

        Args:
            transaction: Raw transaction data

        Returns:
            List of 15 feature values
        """
        # STUB IMPLEMENTATION
        # In production: implement full feature extraction
        # See api/utils/features.py

        # Return dummy features
        return [0.0] * 15

    def calibrate_score(self, raw_score: float) -> float:
        """
        Apply calibration to raw model score.

        Args:
            raw_score: Uncalibrated probability

        Returns:
            Calibrated probability
        """
        # STUB IMPLEMENTATION
        # In production: use isotonic regression calibrator
        return raw_score

    def explain(self, features: List[float], top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Generate SHAP explanations for prediction.

        Args:
            features: Feature values
            top_k: Number of top features to return

        Returns:
            List of top contributing features
        """
        # STUB IMPLEMENTATION
        # In production: compute SHAP values using TreeSHAP

        return [
            {"name": self.feature_names[i], "value": features[i], "contribution": 0.0}
            for i in range(min(top_k, len(features)))
        ]

    def get_model_info(self) -> Dict[str, Any]:
        """Return model metadata."""
        return {
            "model_path": self.model_path,
            "calibration_path": self.calibration_path,
            "num_features": 15,
            "model_type": "LightGBM (ONNX)",
            "status": "stub"
        }
