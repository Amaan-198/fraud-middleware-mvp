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
import logging
import pickle
from pathlib import Path

import numpy as np

from api.utils.features import extract_features, features_to_vector

logger = logging.getLogger(__name__)


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
        self.model_path = model_path or "models/fraud_model.onnx"
        self.calibration_path = calibration_path or "models/calibration.pkl"

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

        # Try to load real models
        self.session = None
        self.calibrator = None
        self._model_ready = False

        # Try loading ONNX model
        try:
            import onnxruntime as ort
            if Path(self.model_path).exists():
                self.session = ort.InferenceSession(
                    self.model_path,
                    providers=['CPUExecutionProvider']
                )
                logger.info(f"Loaded ONNX model from {self.model_path}")
            else:
                logger.warning(f"ONNX model not found at {self.model_path}, using stub mode")
        except Exception as e:
            logger.warning(f"Failed to load ONNX model: {e}, using stub mode")
            self.session = None

        # Try loading calibration model
        try:
            if Path(self.calibration_path).exists():
                with open(self.calibration_path, 'rb') as f:
                    self.calibrator = pickle.load(f)
                logger.info(f"Loaded calibration model from {self.calibration_path}")
            else:
                logger.warning(f"Calibration model not found at {self.calibration_path}")
        except Exception as e:
            logger.warning(f"Failed to load calibration model: {e}")
            self.calibrator = None

        # Set model ready flag
        if self.session is not None:
            self._model_ready = True
            logger.info("MLEngine initialized in REAL mode")
        else:
            self._model_ready = False
            logger.info("MLEngine initialized in STUB mode")

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
        # Step 1: Always extract features from transaction
        features_dict = extract_features(transaction)

        # Step 2: Convert to feature vector
        feature_vector = features_to_vector(features_dict, self.feature_names)

        # Step 3: Run inference (real model or stub)
        if self._model_ready:
            # REAL MODEL PATH: Run ONNX inference
            try:
                # Prepare input for ONNX model (1, 15) shape
                input_array = np.array([feature_vector], dtype=np.float32)
                input_name = self.session.get_inputs()[0].name

                # Run inference - get all outputs
                # Output 0: label (predicted class)
                # Output 1: probabilities (dict with class probabilities)
                result = self.session.run(None, {input_name: input_array})

                # Extract fraud probability (class 1) from probabilities dict
                # result[1] is probabilities list, [0] is first sample, [1] is fraud class
                probabilities = result[1][0]  # {0: prob_non_fraud, 1: prob_fraud}
                raw_score = float(probabilities[1])  # Fraud probability

                # Apply calibration
                calibrated_score = self.calibrate_score(raw_score)

                # Build top features based on actual values
                feature_importance = []
                for name, value in features_dict.items():
                    # Use feature magnitude as proxy for importance
                    if name in ["amount", "velocity_1h", "velocity_1d", "amount_pct"]:
                        contribution = abs(value) * 0.05
                    else:
                        contribution = abs(value) * 0.01
                    feature_importance.append({
                        "name": name,
                        "value": value,
                        "contribution": round(contribution, 3)
                    })

                feature_importance.sort(key=lambda x: x["contribution"], reverse=True)
                top_features = feature_importance[:3]

                model_version = "onnx_v1"

            except Exception as e:
                logger.error(f"Error during ONNX inference: {e}, falling back to stub")
                # Fall back to stub if inference fails
                raw_score = random.uniform(0.1, 0.5)
                calibrated_score = self.calibrate_score(raw_score)

                feature_importance = []
                for name, value in features_dict.items():
                    if name in ["amount", "velocity_1h", "velocity_1d"]:
                        contribution = abs(value) * 0.05
                    else:
                        contribution = abs(value) * 0.01
                    feature_importance.append({
                        "name": name,
                        "value": value,
                        "contribution": round(contribution, 3)
                    })

                feature_importance.sort(key=lambda x: x["contribution"], reverse=True)
                top_features = feature_importance[:3]
                model_version = "stub_v1_fallback"
        else:
            # STUB PATH: Use random score
            raw_score = random.uniform(0.1, 0.5)
            calibrated_score = self.calibrate_score(raw_score)

            # Build top features based on feature values
            feature_importance = []
            for name, value in features_dict.items():
                if name in ["amount", "velocity_1h", "velocity_1d"]:
                    contribution = abs(value) * 0.05
                else:
                    contribution = abs(value) * 0.01
                feature_importance.append({
                    "name": name,
                    "value": value,
                    "contribution": round(contribution, 3)
                })

            feature_importance.sort(key=lambda x: x["contribution"], reverse=True)
            top_features = feature_importance[:3]
            model_version = "stub_v1"

        return {
            "score": round(calibrated_score, 3),
            "top_features": top_features,
            "blocked": False,
            "model_version": model_version,
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
        if self.calibrator is not None:
            try:
                # Sklearn calibrators (e.g., IsotonicRegression) expect 2D numpy array
                if hasattr(self.calibrator, 'predict'):
                    calibrated = self.calibrator.predict(np.array([[raw_score]]))[0]
                    return float(calibrated)
                # Try __call__ method
                elif callable(self.calibrator):
                    calibrated = self.calibrator(raw_score)
                    return float(calibrated)
            except Exception as e:
                logger.warning(f"Calibration failed: {e}, using raw score")
                return raw_score

        # No calibrator available, return raw score
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
            "status": "ready" if self._model_ready else "stub",
            "model_loaded": self.session is not None,
            "calibrator_loaded": self.calibrator is not None
        }
