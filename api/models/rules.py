"""
Stage 1: Rules Engine

Fast deterministic checks for fraud detection.
- Deny lists (device_id, user_id, IP)
- Velocity caps (transaction frequency)
- Geo anomalies (distance from usual location)
- Time anomalies (high-risk hours)

Latency budget: <200ms
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Set
from enum import Enum
from datetime import datetime, timedelta
from collections import defaultdict
import yaml
from pathlib import Path


class RuleAction(str, Enum):
    """Possible rule actions"""
    ALLOW = "allow"
    REVIEW = "review"
    STEP_UP = "step_up"
    BLOCK = "block"


@dataclass
class RuleResult:
    """
    Result from rules engine evaluation.

    Attributes:
        action: The action to take (allow, review, step_up, block)
        reasons: List of rule IDs that fired
    """
    action: RuleAction
    reasons: List[str] = field(default_factory=list)


class RulesEngine:
    """
    Rules-based fraud detection engine.

    Performs fast, deterministic checks before ML scoring.
    """

    def __init__(self, config_path: str = "config/rules_v1.yaml"):
        """
        Initialize rules engine with configuration from YAML.

        Args:
            config_path: Path to rules configuration file
        """
        # Load configuration
        self.config = self._load_config(config_path)

        # Deny lists (in-memory sets for MVP)
        # Load from config if available
        deny_lists = self.config.get("deny_lists", {})
        self.denied_devices: Set[str] = set(deny_lists.get("devices", []))
        self.denied_users: Set[str] = set(deny_lists.get("users", []))
        self.denied_ips: Set[str] = set(deny_lists.get("ips", []))
        self.denied_merchants: Set[str] = set(deny_lists.get("merchants", []))

        # Velocity tracking (in-memory for MVP)
        # Key format: "user:{user_id}" or "device:{device_id}"
        # Value: list of timestamps
        self.velocity_tracker: Dict[str, List[datetime]] = defaultdict(list)

        # User transaction tracking for first-time and amount checks
        self.user_transaction_count: Dict[str, int] = defaultdict(int)
        self.user_amounts: Dict[str, List[float]] = defaultdict(list)

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load rules configuration from YAML file."""
        try:
            path = Path(config_path)
            with open(path, 'r') as f:
                config = yaml.safe_load(f)
            return config
        except FileNotFoundError:
            # Return default config if file not found
            return {
                "version": "1.0.0",
                "deny_lists": {
                    "users": [],
                    "devices": [],
                    "ips": [],
                    "merchants": []
                },
                "velocity": {
                    "user_hourly": 10,
                    "user_daily": 50,
                    "device_hourly": 5,
                    "high_value_amount": 1000,
                    "high_value_daily": 3
                },
                "geo_time": {
                    "review_distance_km": 500,
                    "block_impossible_travel_km": 1000,
                    "impossible_travel_min_hours": 2,
                    "night_start_hour": 3,
                    "night_end_hour": 5
                },
                "amount": {
                    "first_txn_step_up": 500,
                    "review_large_amount": 10000,
                    "review_amount_multiplier": 100
                }
            }

    def evaluate(self, transaction: Dict[str, Any]) -> RuleResult:
        """
        Evaluate transaction against rules.

        Args:
            transaction: Transaction data dict with keys:
                - user_id: str
                - device_id: str
                - amount: float
                - timestamp: str (ISO 8601)
                - location: dict with latitude, longitude
                - ip_address: str (optional)

        Returns:
            RuleResult with action and list of triggered rule reasons
        """
        reasons = []
        action = RuleAction.ALLOW

        # Extract transaction data
        user_id = transaction.get("user_id")
        device_id = transaction.get("device_id")
        amount = transaction.get("amount", 0)
        timestamp_str = transaction.get("timestamp")
        ip_address = transaction.get("ip_address")
        merchant_id = transaction.get("merchant_id")

        # Parse timestamp
        try:
            txn_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            txn_time = datetime.now()

        # 1. Check deny lists (highest priority - instant block)
        deny_result = self._check_denylists(user_id, device_id, ip_address, merchant_id)
        if deny_result:
            return RuleResult(action=RuleAction.BLOCK, reasons=deny_result)

        # 2. Check velocity caps
        velocity_result = self._check_velocity(user_id, device_id, amount, txn_time)
        if velocity_result:
            reasons.extend(velocity_result["reasons"])
            if velocity_result["action"] == RuleAction.BLOCK:
                return RuleResult(action=RuleAction.BLOCK, reasons=reasons)
            elif velocity_result["action"] == RuleAction.REVIEW:
                action = RuleAction.REVIEW

        # 3. Check time anomalies
        time_result = self._check_time_anomaly(txn_time)
        if time_result:
            reasons.append(time_result)
            # Time anomaly increases risk but doesn't block
            if action == RuleAction.ALLOW:
                action = RuleAction.REVIEW

        # 4. Check amount rules
        amount_result = self._check_amount_rules(user_id, amount)
        if amount_result:
            reasons.extend(amount_result["reasons"])
            # Upgrade action if needed
            if amount_result["action"] == RuleAction.STEP_UP and action == RuleAction.ALLOW:
                action = RuleAction.STEP_UP
            elif amount_result["action"] == RuleAction.REVIEW and action in [RuleAction.ALLOW, RuleAction.STEP_UP]:
                action = RuleAction.REVIEW

        # Track this transaction for future velocity/amount checks
        self._track_transaction(user_id, device_id, amount, txn_time)

        return RuleResult(action=action, reasons=reasons)

    def _check_denylists(self, user_id: str, device_id: str, ip_address: str = None, merchant_id: str = None) -> List[str]:
        """
        Check if user, device, IP, or merchant is on deny list.

        Returns:
            List of triggered deny list rules (empty if none)
        """
        reasons = []

        if user_id and user_id in self.denied_users:
            reasons.append("denied_user")

        if device_id and device_id in self.denied_devices:
            reasons.append("denied_device")

        if ip_address and ip_address in self.denied_ips:
            reasons.append("denied_ip")

        if merchant_id and merchant_id in self.denied_merchants:
            reasons.append("denied_merchant")

        return reasons

    def _check_velocity(self, user_id: str, device_id: str, amount: float, txn_time: datetime) -> Dict[str, Any]:
        """
        Check velocity caps for user and device.

        Returns:
            Dict with action and reasons, or None if no violations
        """
        reasons = []
        action = RuleAction.ALLOW

        # Get thresholds from config
        user_hourly = self.config["velocity"]["user_hourly"]
        user_daily = self.config["velocity"]["user_daily"]
        device_hourly = self.config["velocity"]["device_hourly"]
        high_value_amount = self.config["velocity"]["high_value_amount"]
        high_value_daily = self.config["velocity"]["high_value_daily"]

        # Check user velocity (1 hour)
        user_key = f"user:{user_id}"
        user_txns_1h = self._count_recent_transactions(user_key, txn_time, hours=1)
        if user_txns_1h >= user_hourly:
            reasons.append("velocity_user_1h")
            action = RuleAction.BLOCK

        # Check user velocity (24 hours)
        user_txns_1d = self._count_recent_transactions(user_key, txn_time, hours=24)
        if user_txns_1d >= user_daily:
            reasons.append("velocity_user_1d")
            action = RuleAction.BLOCK

        # Check device velocity (1 hour)
        device_key = f"device:{device_id}"
        device_txns_1h = self._count_recent_transactions(device_key, txn_time, hours=1)
        if device_txns_1h >= device_hourly:
            reasons.append("velocity_device_1h")
            action = RuleAction.BLOCK

        # Check high-value transaction velocity
        if amount > high_value_amount:
            high_value_key = f"high_value:{user_id}"
            high_value_txns = self._count_recent_transactions(high_value_key, txn_time, hours=24)
            if high_value_txns >= high_value_daily:
                reasons.append("velocity_high_value")
                action = RuleAction.REVIEW

        if reasons:
            return {"action": action, "reasons": reasons}
        return None

    def _count_recent_transactions(self, key: str, current_time: datetime, hours: int) -> int:
        """
        Count transactions in the last N hours for a given key.

        Args:
            key: Tracking key (e.g., "user:123" or "device:abc")
            current_time: Current transaction time
            hours: Number of hours to look back

        Returns:
            Count of recent transactions
        """
        if key not in self.velocity_tracker:
            return 0

        cutoff_time = current_time - timedelta(hours=hours)

        # Filter transactions within time window
        recent_txns = [t for t in self.velocity_tracker[key] if t > cutoff_time]

        # Update tracker (remove old entries)
        self.velocity_tracker[key] = recent_txns

        return len(recent_txns)

    def _check_time_anomaly(self, txn_time: datetime) -> str:
        """
        Check if transaction occurs during high-risk hours.

        Returns:
            Rule ID if anomaly detected, None otherwise
        """
        hour = txn_time.hour

        # Get night window from config
        night_start = self.config.get("geo_time", {}).get("night_start_hour", 3)
        night_end = self.config.get("geo_time", {}).get("night_end_hour", 5)

        # Check if transaction is in night window
        if night_start <= hour < night_end:
            return "time_night_window"

        return None

    def _check_amount_rules(self, user_id: str, amount: float) -> Dict[str, Any]:
        """
        Check amount-based rules.

        Returns:
            Dict with action and reasons, or None if no violations
        """
        reasons = []
        action = RuleAction.ALLOW

        # Get thresholds from config
        first_txn_threshold = self.config["amount"]["first_txn_step_up"]
        large_amount_threshold = self.config["amount"]["review_large_amount"]
        amount_multiplier = self.config["amount"]["review_amount_multiplier"]

        # Check if first transaction
        txn_count = self.user_transaction_count.get(user_id, 0)
        if txn_count == 0 and amount > first_txn_threshold:
            reasons.append("amount_first_txn_high")
            action = RuleAction.STEP_UP

        # Check large amount
        if amount > large_amount_threshold:
            reasons.append("amount_large")
            action = RuleAction.REVIEW

        # Check amount vs user average
        if user_id in self.user_amounts and len(self.user_amounts[user_id]) > 0:
            user_avg = sum(self.user_amounts[user_id]) / len(self.user_amounts[user_id])
            if amount > user_avg * amount_multiplier:
                reasons.append("amount_unusual")
                action = RuleAction.REVIEW

        if reasons:
            return {"action": action, "reasons": reasons}
        return None

    def _track_transaction(self, user_id: str, device_id: str, amount: float, txn_time: datetime) -> None:
        """
        Track transaction for future velocity and amount checks.

        Args:
            user_id: User ID
            device_id: Device ID
            amount: Transaction amount
            txn_time: Transaction timestamp
        """
        # Track for velocity
        self.velocity_tracker[f"user:{user_id}"].append(txn_time)
        self.velocity_tracker[f"device:{device_id}"].append(txn_time)

        # Track high-value transactions separately
        high_value_amount = self.config["velocity"]["high_value_amount"]
        if amount > high_value_amount:
            self.velocity_tracker[f"high_value:{user_id}"].append(txn_time)

        # Track for amount rules
        self.user_transaction_count[user_id] += 1
        self.user_amounts[user_id].append(amount)

        # Keep only last 30 amounts for average calculation
        if len(self.user_amounts[user_id]) > 30:
            self.user_amounts[user_id] = self.user_amounts[user_id][-30:]

    def add_to_deny_list(self, entity_type: str, entity_id: str) -> None:
        """
        Add entity to deny list.

        Args:
            entity_type: 'user', 'device', 'ip', or 'merchant'
            entity_id: ID to block
        """
        if entity_type == "user":
            self.denied_users.add(entity_id)
        elif entity_type == "device":
            self.denied_devices.add(entity_id)
        elif entity_type == "ip":
            self.denied_ips.add(entity_id)
        elif entity_type == "merchant":
            self.denied_merchants.add(entity_id)

    def remove_from_deny_list(self, entity_type: str, entity_id: str) -> None:
        """
        Remove entity from deny list.

        Args:
            entity_type: 'user', 'device', 'ip', or 'merchant'
            entity_id: ID to unblock
        """
        if entity_type == "user":
            self.denied_users.discard(entity_id)
        elif entity_type == "device":
            self.denied_devices.discard(entity_id)
        elif entity_type == "ip":
            self.denied_ips.discard(entity_id)
        elif entity_type == "merchant":
            self.denied_merchants.discard(entity_id)

    def get_flags_description(self) -> Dict[str, str]:
        """Return descriptions of all possible rule flags."""
        return {
            "denied_user": "User ID is on deny list",
            "denied_device": "Device ID is on deny list",
            "denied_ip": "IP address is on deny list",
            "denied_merchant": "Merchant ID is on deny list",
            "velocity_user_1h": "Too many user transactions in 1 hour",
            "velocity_user_1d": "Too many user transactions in 24 hours",
            "velocity_device_1h": "Too many device transactions in 1 hour",
            "velocity_high_value": "Too many high-value transactions",
            "time_night_window": "Transaction during high-risk hours (3-5 AM)",
            "amount_first_txn_high": "First transaction amount is high",
            "amount_large": "Transaction amount exceeds large threshold",
            "amount_unusual": "Amount is unusually high for user"
        }
