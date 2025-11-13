"""
Feature extraction for fraud detection.

Computes the 15 core features defined in FEATURE_CONTRACT.md.
All features computed in <10ms total.
"""

import math
import hashlib
from datetime import datetime
from typing import Dict, Any, List
from collections import defaultdict, deque

# In-memory state for MVP (would be Redis/SQLite in production)
_device_registry = set()  # Set of seen device_ids
_velocity_1h = defaultdict(lambda: deque())  # user_id -> deque of timestamps (1h window)
_velocity_1d = defaultdict(lambda: deque())  # user_id -> deque of timestamps (1d window)


def extract_features(transaction: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compute the 15 core features defined in FEATURE_CONTRACT.md.

    Args:
        transaction: Raw transaction data dict with fields:
            - user_id: str
            - device_id: str
            - amount: float
            - timestamp: str (ISO 8601)
            - location: str
            - ip_address: str (optional)
            - merchant_id: str (optional)

    Returns:
        Dict mapping feature name -> value (15 features total)
    """
    features = {}

    # Parse timestamp
    try:
        dt = datetime.fromisoformat(transaction["timestamp"].replace("Z", "+00:00"))
    except (ValueError, KeyError):
        dt = datetime.utcnow()

    # === Transaction Features (4) ===

    # amount: log-normalized
    amount_raw = transaction.get("amount", 0.0)
    features["amount"] = math.log1p(amount_raw)  # log(1 + amount) to handle 0

    # amount_pct: percentile vs user's 30d history [0,1]
    # MVP: Use mock default, assume 50th percentile unless very high/low
    spend_avg = 100.0  # Default from contract
    if amount_raw > spend_avg * 3:
        features["amount_pct"] = 0.95
    elif amount_raw < spend_avg * 0.1:
        features["amount_pct"] = 0.05
    else:
        features["amount_pct"] = 0.5

    # tod: hour of day [0-23]
    features["tod"] = dt.hour

    # dow: day of week [0-6], 0=Monday
    features["dow"] = dt.weekday()

    # === Device/Location Features (3) ===

    # device_new: First seen in 30d (bool -> int for ML)
    device_id = transaction.get("device_id", "unknown")
    if device_id in _device_registry:
        features["device_new"] = 0
    else:
        _device_registry.add(device_id)
        features["device_new"] = 1

    # km_dist: Distance from mode location, capped at 10000
    # MVP: Use simple hash-based distance (deterministic for testing)
    location = transaction.get("location", "")
    location_hash = int(hashlib.md5(location.encode()).hexdigest(), 16)
    features["km_dist"] = min((location_hash % 5000), 10000)

    # ip_asn_risk: IP reputation score [0,1]
    # MVP: Default to 0.5, unless IP present then use hash-based mock
    ip_address = transaction.get("ip_address")
    if ip_address:
        ip_hash = int(hashlib.md5(ip_address.encode()).hexdigest(), 16)
        features["ip_asn_risk"] = (ip_hash % 100) / 100.0  # [0, 1]
    else:
        features["ip_asn_risk"] = 0.5

    # === Velocity Features (2) ===

    user_id = transaction.get("user_id", "unknown")
    current_time = dt.timestamp()

    # velocity_1h: Transaction count last hour, capped at 50
    # Clean old entries (> 1 hour)
    hour_window = _velocity_1h[user_id]
    while hour_window and current_time - hour_window[0] > 3600:
        hour_window.popleft()
    hour_window.append(current_time)
    features["velocity_1h"] = min(len(hour_window), 50)

    # velocity_1d: Transaction count last day, capped at 500
    # Clean old entries (> 24 hours)
    day_window = _velocity_1d[user_id]
    while day_window and current_time - day_window[0] > 86400:
        day_window.popleft()
    day_window.append(current_time)
    features["velocity_1d"] = min(len(day_window), 500)

    # === Account Features (2) ===

    # acct_age_days: Days since account creation, capped at 3650
    # MVP: Use mock value based on user_id hash (deterministic)
    user_hash = int(hashlib.md5(user_id.encode()).hexdigest(), 16)
    features["acct_age_days"] = min((user_hash % 1000) + 30, 3650)  # At least 30 days

    # failed_logins_15m: Failed auth attempts, capped at 10
    # MVP: Mock value (always 0 for clean users)
    features["failed_logins_15m"] = 0

    # === Historical Features (2) ===

    # spend_avg_30d: 30-day average spend, log-normalized
    # MVP: Use default from contract
    features["spend_avg_30d"] = math.log1p(100.0)  # Default avg=100

    # spend_std_30d: 30-day std deviation, log-normalized
    # MVP: Use default from contract
    features["spend_std_30d"] = math.log1p(50.0)  # Default std=50

    # === Graph-lite Features (2) ===

    # nbr_risky_30d: Fraction risky neighbors [0,1], mocked as 0.1
    features["nbr_risky_30d"] = 0.1

    # device_reuse_cnt: Unique users on device, mocked from device_id hash
    device_hash = int(hashlib.md5(device_id.encode()).hexdigest(), 16)
    features["device_reuse_cnt"] = (device_hash % 5) + 1  # [1, 5]

    return features


def features_to_vector(features: Dict[str, Any], feature_order: List[str]) -> List[float]:
    """
    Convert feature dict into a list aligned with `feature_order`.

    Args:
        features: Dict mapping feature name -> value
        feature_order: List of feature names in expected order

    Returns:
        List of feature values in the specified order
    """
    return [float(features.get(name, 0.0)) for name in feature_order]


def validate_features(features: Dict[str, Any]) -> bool:
    """
    Validate that all features meet contract requirements.

    Args:
        features: Feature dict to validate

    Returns:
        True if valid, raises ValueError otherwise
    """
    required_features = [
        "amount", "amount_pct", "tod", "dow",
        "device_new", "km_dist", "ip_asn_risk",
        "velocity_1h", "velocity_1d",
        "acct_age_days", "failed_logins_15m",
        "spend_avg_30d", "spend_std_30d",
        "nbr_risky_30d", "device_reuse_cnt"
    ]

    # Check all features present
    for name in required_features:
        if name not in features:
            raise ValueError(f"Missing required feature: {name}")

        # Check for NaN/None
        value = features[name]
        if value is None or (isinstance(value, float) and math.isnan(value)):
            raise ValueError(f"Feature {name} has invalid value: {value}")

    # Range checks
    if not 0 <= features["amount_pct"] <= 1:
        raise ValueError(f"amount_pct out of range: {features['amount_pct']}")

    if not 0 <= features["tod"] <= 23:
        raise ValueError(f"tod out of range: {features['tod']}")

    if not 0 <= features["dow"] <= 6:
        raise ValueError(f"dow out of range: {features['dow']}")

    if features["km_dist"] > 10000:
        raise ValueError(f"km_dist exceeds cap: {features['km_dist']}")

    if not 0 <= features["ip_asn_risk"] <= 1:
        raise ValueError(f"ip_asn_risk out of range: {features['ip_asn_risk']}")

    if features["velocity_1h"] > 50:
        raise ValueError(f"velocity_1h exceeds cap: {features['velocity_1h']}")

    if features["velocity_1d"] > 500:
        raise ValueError(f"velocity_1d exceeds cap: {features['velocity_1d']}")

    if features["acct_age_days"] > 3650:
        raise ValueError(f"acct_age_days exceeds cap: {features['acct_age_days']}")

    if features["failed_logins_15m"] > 10:
        raise ValueError(f"failed_logins_15m exceeds cap: {features['failed_logins_15m']}")

    if not 0 <= features["nbr_risky_30d"] <= 1:
        raise ValueError(f"nbr_risky_30d out of range: {features['nbr_risky_30d']}")

    return True
