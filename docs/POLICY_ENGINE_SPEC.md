# Policy Engine Specification

## Overview

Combines Stage 1 rules + Stage 2 ML scores into final decision codes.
Location: `api/models/policy.py`

## Decision Framework

### Decision Codes

| Code | Name          | Action                  | Customer Experience |
| ---- | ------------- | ----------------------- | ------------------- |
| 0    | Allow         | Approve instantly       | Seamless            |
| 1    | Allow+Monitor | Approve with logging    | Seamless            |
| 2    | Step-up       | Request OTP/challenge   | Minor friction      |
| 3    | Hold & Review | Queue for manual review | Major friction      |
| 4    | Block         | Reject transaction      | Transaction failed  |

### Decision Logic

```python
def compute_decision(rule_result, ml_score, context):
    # Hard blocks from rules
    if rule_result.action == BLOCK:
        return DecisionCode.BLOCK

    # Score-based decisions
    if ml_score < T1:  # T1=0.35
        return DecisionCode.ALLOW
    elif ml_score < T2:  # T2=0.55
        return DecisionCode.ALLOW_MONITOR
    elif ml_score < T3:  # T3=0.75
        return DecisionCode.STEP_UP

    # High risk handling
    if context.amount > 5000 and ml_score > 0.7:
        return DecisionCode.HOLD_REVIEW

    if ml_score > 0.90:
        return DecisionCode.BLOCK

    return DecisionCode.HOLD_REVIEW
```

## Threshold Optimization

Cost function: `minimize(FP_cost * FPR + FN_cost * FNR)`

- False Positive cost: $5 (customer friction)
- False Negative cost: $200 (fraud loss)

Optimized thresholds:

```yaml
thresholds:
  T1: 0.35 # 70% of transactions
  T2: 0.55 # 20% of transactions
  T3: 0.75 # 8% of transactions
  T_block: 0.90 # 2% of transactions
```

## Progressive Friction

Based on cumulative risk signals:

1. New device + high amount → Step-up minimum
2. Failed logins + unusual location → Review
3. Multiple velocity violations → Block

## Trust Score (Simplified MVP)

```python
trust_score = (
    0.3 * (1 - ml_score) +
    0.3 * min(acct_age_days/365, 1) +
    0.2 * (1 - velocity_1d/10) +
    0.2 * (0 if device_new else 1)
)
```

## Policy Versioning

Stored in `config/policy_v1.yaml`:

```yaml
version: "1.0.0"
effective_date: "2025-01-15"
thresholds:
  allow: 0.35
  monitor: 0.55
  challenge: 0.75
  block: 0.90
overrides:
  high_amount: 5000
  trust_bypass: 0.8
```

## NOT IN MVP

- A/B testing policies
- User preference overrides
- Dynamic threshold adjustment
- Merchant-specific policies
- Regulatory overrides by region
