# Integration Guide

## Overview

This guide explains how to integrate the Allianz Fraud Middleware into your banking infrastructure. The system provides real-time fraud detection and institute-level security monitoring with minimal integration effort.

---

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Integration Patterns](#integration-patterns)
- [API Integration](#api-integration)
- [Decision Consumption](#decision-consumption)
- [Security Integration](#security-integration)
- [SIEM Integration](#siem-integration)
- [Deployment Models](#deployment-models)
- [Versioning & Upgrades](#versioning--upgrades)
- [Testing & Validation](#testing--validation)
- [Troubleshooting](#troubleshooting)

---

## Architecture Overview

### System Components

```
┌─────────────────────────────────────────────────────────────────┐
│                     Your Banking Systems                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Payment    │  │   Mobile     │  │     Web      │          │
│  │   Gateway    │  │   Banking    │  │   Banking    │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         │                  │                  │                  │
│         └──────────────────┼──────────────────┘                  │
│                            │                                     │
│                            ▼                                     │
│         ┌──────────────────────────────────────┐                │
│         │  Fraud Middleware API Gateway        │                │
│         │  (Rate Limiting, Auth, Routing)      │                │
│         └──────────────────┬───────────────────┘                │
│                            │                                     │
│         ┌──────────────────┼───────────────────┐                │
│         │                  │                   │                │
│         ▼                  ▼                   ▼                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │   Fraud     │  │  Security   │  │     SOC     │            │
│  │  Detection  │  │  Monitoring │  │   Console   │            │
│  │   Engine    │  │   Engine    │  │             │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
│         │                  │                   │                │
│         └──────────────────┼───────────────────┘                │
│                            │                                     │
│         ┌──────────────────▼───────────────────┐                │
│         │     Event Store & Audit Logs         │                │
│         │  (PostgreSQL / SQLite)                │                │
│         └──────────────────────────────────────┘                │
│                            │                                     │
│                            ▼                                     │
│         ┌──────────────────────────────────────┐                │
│         │         SIEM / Analytics              │                │
│         │  (Splunk, ELK, Azure Sentinel)       │                │
│         └──────────────────────────────────────┘                │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Transaction Request** → Your system sends transaction to `/v1/decision`
2. **Fraud Analysis** → Rules + ML engines evaluate in <90ms
3. **Security Check** → Institute security monitors API usage
4. **Decision Response** → Returns decision code (0-4) with reasoning
5. **Action** → Your system takes appropriate action
6. **Logging** → All events logged for audit and SIEM

---

## Integration Patterns

### Pattern 1: Synchronous Decision (Recommended)

**Use Case:** Real-time transaction approval at POS/checkout

```python
# Your payment processing code
async def process_payment(transaction: Transaction):
    # 1. Call fraud middleware BEFORE processing payment
    fraud_response = await fraud_middleware.check_transaction(transaction)

    # 2. Take action based on decision code
    if fraud_response.decision_code == 4:  # Block
        return reject_transaction(reason="Suspected fraud")

    elif fraud_response.decision_code == 3:  # Review
        queue_for_manual_review(transaction, fraud_response)
        return hold_transaction(message="Under review")

    elif fraud_response.decision_code == 2:  # Step-up
        return request_additional_auth(transaction)

    elif fraud_response.decision_code == 1:  # Monitor
        log_for_monitoring(transaction, fraud_response)
        # Continue processing...

    # 3. Process payment
    result = await payment_gateway.charge(transaction)
    return result
```

**Latency:** <90ms P99
**Throughput:** 2000+ TPS per instance

### Pattern 2: Asynchronous Review Queue

**Use Case:** Batch processing, background screening

```python
# Your batch processor
async def process_batch(transactions: List[Transaction]):
    for txn in transactions:
        fraud_response = await fraud_middleware.check_transaction(txn)

        # Queue high-risk transactions for review
        if fraud_response.decision_code >= 3:
            review_queue.add(txn, fraud_response)
        else:
            # Auto-approve low risk
            await approve_transaction(txn)
```

### Pattern 3: Webhook Notifications

**Use Case:** Async notification of security events

```python
# Configure webhook endpoint
fraud_middleware.configure_webhook(
    url="https://yourbank.com/fraud-webhook",
    events=["critical_threat", "decision_code_4"]
)

# Your webhook handler
@app.post("/fraud-webhook")
async def handle_fraud_event(event: FraudEvent):
    if event.type == "critical_threat":
        alert_security_team(event)
    elif event.type == "decision_code_4":
        auto_block_card(event.card_id)
```

---

## API Integration

### Authentication

**Production Setup:**

```python
import requests

# 1. Obtain API credentials from admin
API_KEY = os.getenv("FRAUD_MIDDLEWARE_API_KEY")
BASE_URL = "https://fraud-middleware.yourbank.com"

# 2. Make authenticated requests
headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

response = requests.post(
    f"{BASE_URL}/v1/decision",
    headers=headers,
    json=transaction_data
)
```

### Making Fraud Decisions

**Endpoint:** `POST /v1/decision`

**Request:**

```json
{
  "user_id": "user_12345",
  "device_id": "device_abc123",
  "amount": 500.00,
  "timestamp": "2024-01-15T14:30:00Z",
  "location": "New York, USA",
  "merchant_id": "merchant_xyz",
  "ip_address": "203.0.113.42",
  "card_last4": "1234",
  "transaction_type": "purchase"
}
```

**Response:**

```json
{
  "decision_code": 1,
  "score": 0.42,
  "reasons": [
    "Fraud probability: 42.0%",
    "Risk factor: velocity_1h = 3.00"
  ],
  "latency_ms": 45.2,
  "rule_flags": ["velocity_check"],
  "ml_score": 0.42,
  "top_features": [
    {"name": "velocity_1h", "value": 3.0, "importance": 0.23},
    {"name": "amount_pct", "value": 0.85, "importance": 0.18}
  ]
}
```

### Decision Code Mapping

| Code | Name | Action | Implementation |
|------|------|--------|----------------|
| **0** | Allow | Approve transaction | Process normally |
| **1** | Monitor | Approve + log | Process + flag for review |
| **2** | Step-up | Request 2FA | Prompt for OTP/biometric |
| **3** | Review | Hold for analyst | Queue for manual review |
| **4** | Block | Decline transaction | Reject with fraud message |

**Sample Implementation:**

```python
def handle_decision(decision_code: int, transaction: Transaction):
    handlers = {
        0: lambda: approve_transaction(transaction),
        1: lambda: approve_and_monitor(transaction),
        2: lambda: request_stepup_auth(transaction),
        3: lambda: queue_for_review(transaction),
        4: lambda: decline_transaction(transaction, reason="fraud")
    }

    handler = handlers.get(decision_code)
    return handler()
```

### Error Handling

```python
try:
    response = fraud_api.check_transaction(txn)

except requests.exceptions.Timeout:
    # Timeout (>2s) - fail open or safe
    logger.error("Fraud API timeout")
    # Option A: Allow transaction (fail open)
    return approve_transaction(txn)
    # Option B: Block transaction (fail safe)
    return decline_transaction(txn, reason="system_unavailable")

except requests.exceptions.HTTPError as e:
    if e.response.status_code == 429:  # Rate limited
        # Implement exponential backoff
        time.sleep(retry_after)
        return fraud_api.check_transaction(txn)  # Retry

    elif e.response.status_code == 500:
        # Server error - use fallback
        return use_rule_based_fallback(txn)
```

---

## Decision Consumption

### Option 1: REST API (Primary)

**Best for:** Real-time synchronous decisions

```bash
curl -X POST https://fraud-api.yourbank.com/v1/decision \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_123",
    "amount": 500,
    "timestamp": "2024-01-15T10:30:00Z",
    "location": "San Francisco"
  }'
```

### Option 2: Webhooks (Events)

**Best for:** Asynchronous notifications, security alerts

**Configure:**

```python
# Register webhook
fraud_api.register_webhook(
    url="https://yourbank.com/webhooks/fraud",
    events=["security_event", "high_risk_transaction"],
    secret="webhook_secret_xyz"
)
```

**Receive:**

```python
@app.post("/webhooks/fraud")
async def fraud_webhook(request: Request):
    # 1. Verify signature
    signature = request.headers.get("X-Fraud-Signature")
    payload = await request.body()

    if not verify_signature(payload, signature, webhook_secret):
        raise HTTPException(status_code=401)

    # 2. Process event
    event = await request.json()

    if event["type"] == "security_event":
        handle_security_event(event)
    elif event["type"] == "high_risk_transaction":
        flag_for_review(event)

    return {"status": "received"}
```

### Option 3: Message Queue (High Volume)

**Best for:** High-throughput batch processing

**Architecture:**

```
Your System → Kafka/RabbitMQ → Fraud Middleware → Response Queue → Your System
```

**Example with Kafka:**

```python
from kafka import KafkaProducer, KafkaConsumer

# Producer: Send transactions
producer = KafkaProducer(bootstrap_servers='kafka:9092')

producer.send('fraud-requests', value=transaction_json)

# Consumer: Receive decisions
consumer = KafkaConsumer('fraud-decisions', bootstrap_servers='kafka:9092')

for message in consumer:
    decision = json.loads(message.value)
    handle_decision(decision)
```

### Option 4: Batch API (Scheduled Jobs)

**Best for:** Daily screening, retrospective analysis

```python
# Submit batch for analysis
batch_response = fraud_api.submit_batch(
    transactions=daily_transactions,
    priority="low",
    callback_url="https://yourbank.com/batch-complete"
)

# Poll for results
results = fraud_api.get_batch_results(batch_response.batch_id)
```

---

## Security Integration

### SOC Analyst Workflow

**Dashboard Access:**

```bash
# Get security events
GET /v1/security/dashboard

# Response
{
  "total_events": 1250,
  "pending_reviews": 8,
  "blocked_sources": 3,
  "threat_level_distribution": {
    "1": 800,  # Low
    "2": 350,  # Medium
    "3": 85,   # High
    "4": 15    # Critical
  }
}
```

**Review Queue:**

```bash
# Get events requiring review
GET /v1/security/events/review-queue?limit=50

# Review an event
POST /v1/security/events/{event_id}/review
{
  "analyst_id": "analyst_smith",
  "action": "investigate",
  "notes": "Escalating to tier 2 - possible insider threat"
}
```

**Unblock Sources:**

```bash
# Unblock a false positive
POST /v1/security/sources/api_key_abc/unblock
{
  "analyst_id": "analyst_smith",
  "reason": "Legitimate batch job, whitelisted"
}
```

### Audit Trail Integration

**Export audit logs:**

```python
# Get audit trail for compliance
audit_logs = fraud_api.get_audit_trail(
    start_date="2024-01-01",
    end_date="2024-01-31",
    source_id="user_12345"  # Optional filter
)

# Export to CSV for compliance team
export_to_csv(audit_logs, "audit_january_2024.csv")
```

**Compliance Queries:**

```sql
-- Who accessed customer X's data?
SELECT source_id, action, timestamp
FROM audit_logs
WHERE resource = 'user:customer_123'
ORDER BY timestamp DESC;

-- What did analyst Y do today?
SELECT action, resource, success, timestamp
FROM audit_logs
WHERE source_id = 'analyst_smith'
  AND DATE(timestamp) = CURRENT_DATE;
```

---

## SIEM Integration

### Supported SIEM Platforms

- **Splunk** (via HEC - HTTP Event Collector)
- **Elastic Stack** (via Logstash/Beats)
- **Azure Sentinel** (via Azure Monitor)
- **IBM QRadar** (via Syslog)

### Splunk Integration

**Setup:**

```python
# Configure Splunk HEC
fraud_api.configure_siem(
    type="splunk",
    endpoint="https://splunk.yourbank.com:8088/services/collector",
    token="YOUR_HEC_TOKEN",
    index="fraud_middleware"
)
```

**Query in Splunk:**

```spl
index=fraud_middleware
| where threat_level >= 3
| stats count by threat_type, source_identifier
| sort -count
```

### ELK Stack Integration

**Logstash Configuration:**

```ruby
input {
  http {
    port => 5044
    codec => json
  }
}

filter {
  if [event_type] == "security_event" {
    mutate {
      add_tag => ["security", "fraud_middleware"]
    }
  }
}

output {
  elasticsearch {
    hosts => ["elasticsearch:9200"]
    index => "fraud-middleware-%{+YYYY.MM.dd}"
  }
}
```

**Kibana Dashboard:**

Create visualizations for:
- Security events over time
- Threat level distribution
- Top blocked sources
- API usage patterns

### Azure Sentinel

**Data Connector:**

```python
# Forward to Azure Sentinel
fraud_api.configure_siem(
    type="azure_sentinel",
    workspace_id="YOUR_WORKSPACE_ID",
    shared_key="YOUR_SHARED_KEY"
)
```

**KQL Query:**

```kql
FraudMiddlewareEvents
| where ThreatLevel >= 3
| summarize Count=count() by ThreatType, bin(TimeGenerated, 1h)
| render timechart
```

---

## Deployment Models

### Model 1: On-Premise (Private Cloud)

**Architecture:**
- Deploy in your data center
- Full control over data
- Lower latency to core systems

**Setup:**

```yaml
# docker-compose.yml
version: '3.8'
services:
  fraud-api:
    image: fraud-middleware:2.0.0
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/fraud
      - SIEM_ENDPOINT=https://splunk.internal:8088
    volumes:
      - ./models:/app/models
      - ./config:/app/config

  database:
    image: postgres:15
    volumes:
      - fraud_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    # For caching and rate limiting
```

**Deploy:**

```bash
docker-compose up -d
```

### Model 2: Hybrid Cloud

**Architecture:**
- API layer in cloud (Azure/AWS)
- Data remains on-premise
- Secure VPN/ExpressRoute connection

**Benefits:**
- Scalability of cloud
- Data residency compliance
- Failover capabilities

### Model 3: SaaS (Multi-Tenant)

**Architecture:**
- Fully managed service
- Shared infrastructure
- Per-transaction pricing

**Integration:**

```python
# SaaS client library
from fraud_middleware_client import FraudClient

client = FraudClient(
    api_key="your_api_key",
    region="us-east-1"
)

decision = client.check_transaction(transaction)
```

---

## Versioning & Upgrades

### API Versioning

**Current:** `v1` (2.0.0)

**URL Structure:**
- `/v1/decision` - Current stable API
- `/v2/decision` - Future version (when released)

**Version Header:**

```http
GET /v1/decision
X-API-Version: 2.0.0
```

### Upgrade Process

**Minor Versions (2.0.x → 2.1.x):**
- Backward compatible
- No code changes required
- Deploy during maintenance window

**Major Versions (2.x → 3.x):**
- May have breaking changes
- Deprecation notices 6 months in advance
- Parallel running supported (v1 + v2)

**Upgrade Steps:**

1. **Read Release Notes** - Check breaking changes
2. **Test in Staging** - Validate with test transactions
3. **Gradual Rollout** - 10% → 50% → 100% traffic
4. **Monitor Metrics** - Latency, error rates, decision distribution
5. **Rollback Plan** - Keep previous version ready

**Zero-Downtime Upgrade:**

```bash
# Blue-Green Deployment
# 1. Deploy new version (green)
docker-compose -f docker-compose.green.yml up -d

# 2. Run health checks
curl http://green:8000/health

# 3. Switch load balancer
haproxy_switch_backend blue green

# 4. Monitor for 1 hour

# 5. If stable, decommission blue
docker-compose -f docker-compose.blue.yml down
```

### Backwards Compatibility

**Guaranteed for 1 year:**
- Request/response schemas
- Decision codes (0-4)
- Core endpoints

**Deprecation Policy:**
- 6 months notice via API header
- Email notifications to registered contacts
- Detailed migration guide

---

## Testing & Validation

### Pre-Production Testing

**1. Functional Tests:**

```python
def test_fraud_decision():
    # Test known fraud pattern
    response = fraud_api.check_transaction({
        "user_id": "test_fraud_user",
        "amount": 10000,
        "location": "Nigeria",  # High-risk location in test config
        "device_id": "new_device"
    })

    assert response.decision_code == 4  # Should block
    assert response.score > 0.9
```

**2. Load Testing:**

```bash
# Use k6 or Locust
k6 run --vus 100 --duration 5m fraud_load_test.js

# Expected: <90ms P99, <1% errors
```

**3. Security Testing:**

```bash
# Test rate limiting
for i in {1..200}; do
  curl -X POST http://fraud-api/v1/decision
done
# Should receive 429 after limit

# Test authentication
curl -X POST http://fraud-api/v1/decision  # No auth
# Should receive 401 Unauthorized
```

### Production Validation

**Canary Testing:**

```yaml
# Route 5% of production traffic to new version
canary:
  version: "2.1.0"
  weight: 5%
  success_criteria:
    - latency_p99 < 100ms
    - error_rate < 0.5%
    - decision_code_distribution_variance < 10%
```

**Monitoring Metrics:**

```python
# Key metrics to watch post-deployment
metrics = {
    "latency_p50": "<50ms",
    "latency_p99": "<90ms",
    "error_rate": "<0.1%",
    "decision_codes": {
        0: "60-70%",  # Allow
        1: "15-20%",  # Monitor
        2: "5-10%",   # Step-up
        3: "3-5%",    # Review
        4: "1-2%"     # Block
    }
}
```

---

## Troubleshooting

### Common Issues

#### Issue: High Latency (>100ms)

**Diagnosis:**
```bash
# Check component latency
GET /v1/decision/health

# Response shows breakdown
{
  "rules_engine": "12ms",
  "ml_engine": "85ms",  # ← Bottleneck
  "policy_engine": "3ms"
}
```

**Solutions:**
- Scale ML engine instances
- Optimize ONNX model
- Increase CPU allocation
- Enable GPU inference (if available)

#### Issue: Rate Limit False Positives

**Diagnosis:**
```bash
# Check source status
GET /v1/security/rate-limits/{source_id}

{
  "tier": "basic",  # ← May need upgrade
  "limit_per_minute": 100,
  "tokens_available": 0,
  "blocked": false
}
```

**Solutions:**
```bash
# Upgrade tier
POST /v1/security/rate-limits/{source_id}/tier?tier=premium
```

#### Issue: Unexpected Blocks

**Diagnosis:**
```bash
# Get risk profile
GET /v1/security/sources/{source_id}/risk

# Get recent events
GET /v1/security/events?source_id={source_id}
```

**Solutions:**
- Review security events
- Whitelist if legitimate
- Adjust thresholds in config

### Debug Mode

**Enable verbose logging:**

```bash
# Set environment variable
FRAUD_MIDDLEWARE_DEBUG=true

# Logs will include:
# - Full request/response bodies
# - Feature values
# - Rule evaluation steps
# - ML model predictions
```

### Support Escalation

1. **Self-Service:** Check `/docs`, `/health`, logs
2. **Tier 1:** Email support@fraud-middleware.com
3. **Tier 2:** Slack channel #fraud-middleware-support
4. **Emergency:** Phone +1-XXX-XXX-XXXX (24/7 on-call)

**Include in support request:**
- Transaction ID or timestamp
- Error message / status code
- Logs from `/health` endpoint
- Expected vs actual behavior

---

## Best Practices

### Performance Optimization

1. **Use Connection Pooling**
   ```python
   session = requests.Session()
   adapter = HTTPAdapter(pool_connections=100, pool_maxsize=100)
   session.mount('https://', adapter)
   ```

2. **Implement Caching** (for batch lookups)
   ```python
   from cachetools import TTLCache
   decision_cache = TTLCache(maxsize=10000, ttl=60)
   ```

3. **Async Calls** (if possible)
   ```python
   import asyncio
   decisions = await asyncio.gather(*[
       fraud_api.check_transaction(txn) for txn in batch
   ])
   ```

### Reliability

1. **Circuit Breaker Pattern**
   ```python
   from pybreaker import CircuitBreaker

   breaker = CircuitBreaker(fail_max=5, timeout_duration=60)

   @breaker
   def call_fraud_api(txn):
       return fraud_api.check_transaction(txn)
   ```

2. **Retry with Exponential Backoff**
   ```python
   from tenacity import retry, wait_exponential

   @retry(wait=wait_exponential(multiplier=1, min=1, max=10))
   def call_with_retry(txn):
       return fraud_api.check_transaction(txn)
   ```

3. **Health Checks**
   ```python
   # Poll health endpoint every 30s
   health = fraud_api.get_health()
   if health["status"] != "healthy":
       alert_ops_team()
   ```

---

## Appendix

### Sample Code Libraries

**Python:**
```bash
pip install fraud-middleware-client
```

**Java:**
```xml
<dependency>
    <groupId>com.fraud</groupId>
    <artifactId>fraud-middleware-client</artifactId>
    <version>2.0.0</version>
</dependency>
```

**Node.js:**
```bash
npm install @fraud-middleware/client
```

### Configuration Examples

See `/config` directory for:
- `rules_v1.yaml` - Rule engine configuration
- `policy_v1.yaml` - Decision thresholds
- `rate_limits.yaml` - Rate limiting tiers

---

**Last Updated:** 2024-01-15
**Maintained By:** Integration Team
**Support:** integration-support@fraud-middleware.com
