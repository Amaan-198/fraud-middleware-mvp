"""
Stage 3: Policy Engine

Combines rules and ML scores to make final fraud decisions.

Decision codes:
- 0: Allow (score < 0.35)
- 1: Allow + Monitor (0.35 ≤ score < 0.55)
- 2: Step-up Auth (0.55 ≤ score < 0.75)
- 3: Hold & Review (0.75 ≤ score < 0.90)
- 4: Block (score ≥ 0.90 OR hard rule violations)

Latency budget: <10ms
"""

from typing import Dict, List, Any, Optional
from pathlib import Path
import yaml


class PolicyEngine:
    """
    Policy engine for fraud decision making.

    Combines rules and ML scores into actionable decisions.
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize policy engine.

        Args:
            config_path: Path to policy config (default: config/policy_v1.yaml)
        """
        self.config_path = config_path or "config/policy_v1.yaml"
        self.config = self._load_config(self.config_path)

        # Decision thresholds loaded from config
        self.thresholds = self.config.get("thresholds", {
            "allow": 0.35,
            "monitor": 0.55,
            "stepup": 0.75,
            "review": 0.90
        })

        # Cost parameters for threshold optimization
        costs = self.config.get("costs", {})
        self.false_positive_cost = costs.get("false_positive", 5.0)
        self.false_negative_cost = costs.get("false_negative", 200.0)

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load policy configuration from YAML file."""
        try:
            path = Path(config_path)
            with open(path, "r") as f:
                config = yaml.safe_load(f)
            return config if config else {}
        except FileNotFoundError:
            # Return default config if file not found
            return {
                "version": "1.0.0",
                "thresholds": {
                    "allow": 0.35,
                    "monitor": 0.55,
                    "stepup": 0.75,
                    "review": 0.90
                },
                "costs": {
                    "false_positive": 5.0,
                    "false_negative": 200.0
                }
            }

    def decide(self, rules_result: Dict[str, Any], ml_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make final fraud decision.

        Args:
            rules_result: Output from RulesEngine
            ml_result: Output from MLEngine

        Returns:
            Dict with:
                - decision_code: int (0-4)
                - score: float
                - reasons: List[str]
        """
        # If blocked by rules, immediately return block decision
        if rules_result.get("blocked", False):
            return {
                "decision_code": 4,  # Block
                "score": 1.0,
                "reasons": self._build_reasons(rules_result, ml_result, blocked=True)
            }

        # Get ML score
        ml_score = ml_result.get("score", 0.0)

        # Apply thresholds to determine decision code
        if ml_score < self.thresholds["allow"]:
            decision_code = 0  # Allow
            decision_name = "Allow"
        elif ml_score < self.thresholds["monitor"]:
            decision_code = 1  # Allow + Monitor
            decision_name = "Allow with Monitoring"
        elif ml_score < self.thresholds["stepup"]:
            decision_code = 2  # Step-up Auth
            decision_name = "Step-up Authentication Required"
        elif ml_score < self.thresholds["review"]:
            decision_code = 3  # Hold & Review
            decision_name = "Hold for Review"
        else:
            decision_code = 4  # Block
            decision_name = "Block"

        # Build reasons
        reasons = self._build_reasons(rules_result, ml_result, blocked=False)

        return {
            "decision_code": decision_code,
            "score": ml_score,
            "reasons": reasons,
            "decision_name": decision_name
        }

    def _build_reasons(
        self,
        rules_result: Dict[str, Any],
        ml_result: Dict[str, Any],
        blocked: bool
    ) -> List[str]:
        """
        Build human-readable reasons for decision.

        Args:
            rules_result: Rules engine output
            ml_result: ML engine output
            blocked: Whether transaction was blocked

        Returns:
            List of reason strings
        """
        reasons = []

        # Add rule flags if any
        flags = rules_result.get("flags", [])
        if flags:
            reasons.extend([f"Rule triggered: {flag}" for flag in flags])

        # Add ML score reason
        ml_score = ml_result.get("score", 0.0)
        if ml_score > 0:
            reasons.append(f"Fraud probability: {ml_score:.1%}")

        # Add top ML features
        top_features = ml_result.get("top_features", [])
        if top_features:
            for feature in top_features[:2]:  # Top 2 features
                reasons.append(
                    f"Risk factor: {feature['name']} = {feature['value']:.2f}"
                )

        # Default reason if none found
        if not reasons:
            if blocked:
                reasons.append("Transaction blocked by security rules")
            else:
                reasons.append("Low fraud risk detected")

        return reasons

    def get_decision_description(self, decision_code: int) -> str:
        """
        Get human-readable description of decision code.

        Args:
            decision_code: Decision code (0-4)

        Returns:
            Description string
        """
        descriptions = {
            0: "Allow - Transaction appears legitimate",
            1: "Allow with Monitoring - Low fraud risk, monitor for patterns",
            2: "Step-up Authentication - Request additional verification",
            3: "Hold for Review - Manual review required before processing",
            4: "Block - High fraud risk, transaction denied"
        }
        return descriptions.get(decision_code, "Unknown decision code")

    def get_thresholds(self) -> Dict[str, float]:
        """Return current decision thresholds."""
        return self.thresholds.copy()

    def update_threshold(self, threshold_name: str, value: float) -> None:
        """
        Update a decision threshold.

        Args:
            threshold_name: Name of threshold (allow, monitor, stepup, review)
            value: New threshold value (0-1)
        """
        if threshold_name in self.thresholds and 0 <= value <= 1:
            self.thresholds[threshold_name] = value
