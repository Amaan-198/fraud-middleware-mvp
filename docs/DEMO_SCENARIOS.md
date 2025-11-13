# Demo Scenarios

## Quick Start

```bash
cd demo
python run_scenarios.py --scenario all
```

## Scenario Details

### 1. Normal Transaction ✅

```json
{
  "user_id": "alice_regular",
  "device_id": "iphone_abc123",
  "amount": 45.99,
  "merchant": "Starbucks",
  "location": "home"
}
```

**Expected:** Code 0 (Allow), Score ~0.02, Latency <55ms
**Demonstrates:** Fast approval for normal patterns

### 2. Unusual Amount ⚠️

```json
{
  "user_id": "alice_regular",
  "device_id": "iphone_abc123",
  "amount": 5000.0,
  "merchant": "BestBuy",
  "location": "home"
}
```

**Expected:** Code 2 (Step-up), Score ~0.42
**Reason:** "Amount is 99th percentile for your history"

### 3. New Device + High Risk 🚨

```json
{
  "user_id": "bob_victim",
  "device_id": "android_new_xyz",
  "amount": 3000.0,
  "timestamp": "03:00:00",
  "location": "unusual_city"
}
```

**Expected:** Code 3 (Hold), Score ~0.76
**Reasons:** New device, unusual time, high amount

### 4. Velocity Attack 🛑

```json
{
  "user_id": "charlie_compromised",
  "transactions": 15,
  "timeframe": "10min"
}
```

**Expected:** Code 4 (Block)
**Reason:** "Velocity exceeded (max 10/hour)"
**Latency:** <12ms (rule engine only)

### 5. Device Farm Detection 🏭

```json
{
  "user_id": "david_mule",
  "device_id": "shared_device_001",
  "device_users": 50,
  "amount": 2000.0
}
```

**Expected:** Code 3 (Hold), Score ~0.81
**Reason:** "Device associated with 50+ accounts"

## Running Scenarios

### Individual Test

```python
from demo.runner import run_scenario
result = run_scenario("normal_transaction")
print(f"Decision: {result.decision_code}")
print(f"Score: {result.score:.2f}")
print(f"Latency: {result.latency_ms}ms")
```

### Batch Testing

```python
results = run_all_scenarios()
for name, result in results.items():
    assert result.decision_code == expected[name]
    assert result.latency_ms < 90
```

## Demo UI Integration

1. Select scenario from dropdown
2. Click "Submit Transaction"
3. View real-time decision + explanation
4. Check metrics dashboard update
