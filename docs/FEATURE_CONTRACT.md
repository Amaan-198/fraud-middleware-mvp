# Feature Contract v1.0

## Core Features (15 total)

All features must be computed in <10ms total.

### Transaction Features

```python
{
    # Basic (4)
    "amount": float,           # USD amount, log-normalized
    "amount_pct": float,       # Percentile vs user's 30d history [0,1]
    "tod": int,                # Hour of day [0-23]
    "dow": int,                # Day of week [0-6], 0=Monday

    # Device/Location (3)
    "device_new": bool,        # First seen in 30d
    "km_dist": float,          # Distance from mode location, capped at 10000
    "ip_asn_risk": float,      # IP reputation score [0,1]

    # Velocity (2)
    "velocity_1h": int,        # Transaction count last hour, capped at 50
    "velocity_1d": int,        # Transaction count last day, capped at 500

    # Account (2)
    "acct_age_days": int,      # Days since account creation, capped at 3650
    "failed_logins_15m": int,  # Failed auth attempts, capped at 10

    # Historical (2)
    "spend_avg_30d": float,    # 30-day average spend, log-normalized
    "spend_std_30d": float,    # 30-day std deviation, log-normalized

    # Graph-lite (2) - Pre-computed/mocked for MVP
    "nbr_risky_30d": float,    # Fraction risky neighbors [0,1], mocked as 0.1
    "device_reuse_cnt": int    # Unique users on device, mocked from device_id hash
}
```

## Feature Engineering Pipeline

Location: `api/utils/features.py`

### Required Lookups

1. **User history** (SQLite): Last 30d transactions for aggregates
2. **Device registry** (SQLite/Redis): First-seen timestamps
3. **IP reputation** (Redis/mock): ASN risk scores

### Computation Order (Optimized)

1. Extract raw fields from request
2. Lookup user history (parallel with #3)
3. Lookup device/IP data (parallel with #2)
4. Compute derived features
5. Apply caps and normalizations

### Missing Data Handling

- Historical features → Use defaults (avg=100, std=50)
- Device features → Assume new device
- IP features → Default risk=0.5

## Feature Validation

All features must pass these checks:

- No NaN/null values
- Within expected ranges
- Computation time <10ms
- Match training distribution (monitored, not enforced)

## NOT IN MVP

- Real-time graph features (use mocked values)
- Complex behavioral sequences
- NLP on merchant names
- Image/document features
