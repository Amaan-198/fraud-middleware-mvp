# Demo Scenarios

## Quick Start

```bash
python demo/run_scenarios.py              # Run all scenarios
python demo/run_scenarios.py --verbose    # Show detailed output
python demo/run_scenarios.py --scenario normal_transaction  # Run specific scenario
python demo/run_scenarios.py --list       # List available scenarios
```

## Understanding Model Behavior

The trained LightGBM model exhibits **non-linear response** to transaction amounts:
- **Small amounts** ($0-100): Low fraud risk (score ~0.2-0.3)
- **Medium amounts** ($500-1000): **Peak fraud risk** (score ~0.7-0.8)
- **Large amounts** ($5000+): Moderate risk (score ~0.5)

This reflects real-world patterns where fraudsters target the "sweet spot" - large enough to profit, but small enough to avoid automatic review.

## Scenario Details

### 1. Normal Transaction ✅

```json
{
  "user_id": "alice_regular",
  "device_id": "iphone_abc123",
  "amount": 45.99,
  "merchant_id": "starbucks_001",
  "location": "home",
  "timestamp": "2024-01-15T14:30:00Z"
}
```

**Result:** Code 0 (Allow), Score 0.018, Latency 1.34ms
**Demonstrates:** Fast approval for normal patterns with established users

### 2. Unusual Amount (Established User) 💰

```json
{
  "user_id": "alice_regular",
  "device_id": "iphone_abc123",
  "amount": 899.99,
  "merchant_id": "bestbuy_002",
  "location": "home",
  "timestamp": "2024-01-15T14:35:00Z"
}
```

**Result:** Code 0 (Allow), Score 0.049, Latency 0.54ms
**Demonstrates:** Established user patterns keep score low despite higher amount

### 3. New Device + High Risk 🚨

```json
{
  "user_id": "bob_victim",
  "device_id": "android_new_xyz",
  "amount": 749.99,
  "merchant_id": "electronics_999",
  "location": "unusual_city_far_away",
  "timestamp": "2024-01-15T03:00:00Z"
}
```

**Result:** Code 3 (Review), Score 0.769, Latency 0.28ms
**Reasons:** New device + night window (3am) + first transaction high amount
**Demonstrates:** Combination of risk factors triggering manual review

### 4. Velocity Attack 🛑

```json
{
  "user_id": "charlie_compromised",
  "transactions": 11,
  "timeframe": "10 minutes"
}
```

**Result:** Code 4 (Block), Score 1.0, Latency <0.1ms
**Reason:** "velocity_device_1h" rule violation (>10 txns/hour)
**Demonstrates:** Fast rule-based blocking before ML evaluation

### 5. High Velocity Pattern ⚠️

```json
{
  "user_id": "emma_shopper",
  "transactions": 5,
  "timeframe": "20 minutes",
  "total_amount": 900.48
}
```

**Result:** Code 0 (Allow), Score 0.338, Latency 0.15ms
**Demonstrates:** Moderate velocity (5 txns) increases risk but stays below monitoring threshold (0.35)

## Output Example

```
================================================================================
                         FRAUD DETECTION DEMO SCENARIOS
================================================================================

Normal Transaction ✓
────────────────────────────────────────────────────────────────────────────────
Decision:     ALLOW (0)
Score:        0.018
ML Score:     0.018
Latency:      1.60ms

Expected:     ALLOW (0), score in [0.0, 0.35]

...

================================================================================
                                    SUMMARY
================================================================================

Scenarios: 5/5 passed
Avg Latency: 0.53ms
Max Latency: 1.60ms

Score Distribution:
  Normal Transaction             ░... 0.018
  Unusual Amount                 █... 0.049
  New Device + High Risk         ████████... 0.769
  Velocity Attack                ██████████ 1.000
  High Velocity Pattern          ████... 0.338
```

## Decision Code Reference

- **0 (Allow)**: Transaction approved, low risk (score < 0.35)
- **1 (Monitor)**: Approved with monitoring (0.35 ≤ score < 0.55)
- **2 (Step-up)**: Require additional authentication (0.55 ≤ score < 0.75)
- **3 (Review)**: Hold for manual review (0.75 ≤ score < 0.90)
- **4 (Block)**: Transaction denied (score ≥ 0.90 OR hard rule violation)

## Performance Metrics

All scenarios demonstrate:
- **Latency**: 0.46ms average, 1.34ms max (well below 60ms P95 and 90ms P99 targets)
- **Accuracy**: 5/5 scenarios behave as expected
- **Consistency**: State reset ensures reproducible results
