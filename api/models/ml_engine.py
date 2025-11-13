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

from api.utils.features import extract_features, features_to_vector


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
        # Feature names from FEATURE_CONTRACT.md (exact order for ML model)
        self.feature_names = [
            "amount",
            "amount_pct",
            "tod",
            "dow",
            "device_new",
            "km_dist",
            "ip_asn_risk",
            "velocity_1h",
            "velocity_1d",
            "acct_age_days",
            "failed_logins_15m",
            "spend_avg_30d",
            "spend_std_30d",
            "nbr_risky_30d",
            "device_reuse_cnt"
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
                - model_version: str
                - features: dict (for debugging, optional)
        """
        # Step 1: Extract features from transaction
        features_dict = extract_features(transaction)

        # Step 2: Convert to feature vector
        feature_vector = features_to_vector(features_dict, self.feature_names)

        # Step 3: Run ONNX inference (STUB: use random score for now)
        # TODO: Replace with actual ONNX model inference
        raw_score = random.uniform(0.1, 0.5)  # Low scores for testing

        # Step 4: Apply calibration (STUB: pass through for now)
        calibrated_score = self.calibrate_score(raw_score)

        # Step 5: Compute SHAP explanations (STUB: use top 3 features by value)
        # TODO: Replace with actual SHAP computation
        # For now, pick features with highest values (normalized)
        feature_importance = []
        for name, value in features_dict.items():
            # Simple heuristic: use feature value as proxy for importance
            if name in ["amount", "velocity_1h", "velocity_1d"]:
                contribution = abs(value) * 0.05  # Scale for demo
            else:
                contribution = abs(value) * 0.01
            feature_importance.append({
                "name": name,
                "value": value,
                "contribution": round(contribution, 3)
            })

        # Sort by contribution and take top 3
        feature_importance.sort(key=lambda x: x["contribution"], reverse=True)
        top_features = feature_importance[:3]

        return {
            "score": round(calibrated_score, 3),
            "top_features": top_features,
            "blocked": False,
            "model_version": "stub_v2_features",
            "features": features_dict  # Include for debugging (can remove later)
        }

    def extract_features(self, transaction: Dict[str, Any]) -> List[float]:
        """
        Extract 15 features from transaction.

        Args:
            transaction: Raw transaction data

        Returns:
            List of 15 feature values
        """
        # Use the feature extraction module
        features_dict = extract_features(transaction)
        return features_to_vector(features_dict, self.feature_names)

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
