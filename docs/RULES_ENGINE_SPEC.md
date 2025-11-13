# Stage 1: Rules Engine Specification

## Overview

Fast, deterministic fraud checks that can block transactions immediately.
Target: <200ms execution, covers 20% of fraud with 99.9% precision.

## Rule Categories

### 1. Deny Lists (Instant Block)

**File:** `config/denylists.yaml` or Redis key `deny:*`

- `deny:device` - Blacklisted device IDs
- `deny:user` - Banned user accounts
- `deny:ip` - Malicious IP addresses
- `deny:merchant` - Fraudulent merchants

**Implementation:**

```python
def check_denylists(txn):
    if txn.device_id in denied_devices:
        return RuleResult(action=BLOCK, reason="denied_device")
```

### 2. Velocity Caps

**Thresholds:**

- 10 transactions/hour per user
- 50 transactions/day per user
- 5 transactions/hour per device
- 3 high-value (>$1000) per day

**Implementation:**

```python
def check_velocity(user_id, device_id):
    user_1h = count_transactions(user_id, hours=1)
    if user_1h > 10:
        return RuleResult(action=BLOCK, reason="velocity_user_1h")
```

### 3. Geo/Time Anomalies

**Rules:**

- Distance >500km from usual location → Review
- Transaction 3-5 AM local time → Increase risk
- Impossible travel (<2hr, >1000km) → Block

### 4. Amount Rules

**Thresholds:**

- First transaction >$500 → Step-up
- Amount >$10,000 → Review
- Amount >100x user average → Review

## Rule Versioning

Each rule set tagged with version in `config/rules_v1.yaml`:

```yaml
version: "1.0.0"
effective_date: "2025-01-15"
rules:
  velocity:
    user_hourly: 10
    user_daily: 50
```

## Rule Hit Logging

Every evaluation logged to SQLite:

```json
{
  "txn_id": "abc123",
  "rules_evaluated": ["velocity", "geo", "amount"],
  "rules_triggered": ["amount_high"],
  "execution_ms": 12
}
```

## Performance Requirements

- P99 latency: <200ms
- Throughput: 1000 TPS
- Memory: <100MB for all lists

## NOT IN MVP

- Complex behavioral rules
- ML-based rule thresholds
- Real-time rule learning
- A/B testing framework
