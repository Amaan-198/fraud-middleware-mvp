"""
Stage 1: Rules Engine

Fast deterministic checks for fraud detection.
- Deny lists (device_id, user_id, IP)
- Velocity caps (transaction frequency)
- Geo anomalies (distance from usual location)
- Time anomalies (high-risk hours)

Latency budget: <200ms
"""

from typing import Dict, List, Any


class RulesEngine:
    """
    Rules-based fraud detection engine.

    Performs fast, deterministic checks before ML scoring.
    """

    def __init__(self):
        """Initialize rules engine with default configuration."""
        # In full implementation, load from config/rules_v1.yaml
        self.deny_list_devices = set()
        self.deny_list_users = set()
        self.velocity_threshold = 10  # max transactions per hour
        self.geo_distance_threshold = 500  # km from usual location
        self.high_risk_hours = (3, 5)  # 3 AM - 5 AM

    def evaluate(self, transaction: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate transaction against rules.

        Args:
            transaction: Transaction data dict

        Returns:
            Dict with:
                - blocked: bool
                - flags: List[str]
                - risk_score: float (0-1)
        """
        # STUB IMPLEMENTATION
        # In production, implement actual rule checks

        flags = []
        blocked = False
        risk_score = 0.0

        # Stub: Check deny lists (not implemented)
        user_id = transaction.get("user_id")
        device_id = transaction.get("device_id")

        if user_id in self.deny_list_users:
            flags.append("user_deny_list")
            blocked = True
            risk_score = 1.0

        if device_id in self.deny_list_devices:
            flags.append("device_deny_list")
            blocked = True
            risk_score = 1.0

        # Stub: Velocity check (not implemented)
        # Would check transaction count in last hour from cache/DB

        # Stub: Geo anomaly check (not implemented)
        # Would check distance from user's usual location

        # Stub: Time anomaly check (not implemented)
        # Would check if transaction in high-risk hours

        # For stub, return clean result
        return {
            "blocked": blocked,
            "flags": flags,
            "risk_score": risk_score,
            "checks_passed": not blocked
        }

    def add_to_deny_list(self, entity_type: str, entity_id: str) -> None:
        """
        Add entity to deny list.

        Args:
            entity_type: 'user' or 'device'
            entity_id: ID to block
        """
        if entity_type == "user":
            self.deny_list_users.add(entity_id)
        elif entity_type == "device":
            self.deny_list_devices.add(entity_id)

    def get_flags_description(self) -> Dict[str, str]:
        """Return descriptions of all possible rule flags."""
        return {
            "user_deny_list": "User ID is on deny list",
            "device_deny_list": "Device ID is on deny list",
            "velocity_exceeded": "Too many transactions in time window",
            "geo_anomaly": "Unusual location for user",
            "time_anomaly": "Transaction during high-risk hours"
        }
