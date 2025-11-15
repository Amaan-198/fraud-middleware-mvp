# Allianz Fraud Middleware - Architecture (Version 2.0)

## System Overview

Dual-purpose real-time fraud detection and security monitoring system with sub-millisecond latency.

**Version 2.0** adds comprehensive institute-level security monitoring alongside customer fraud detection.

## Dual Architecture

### Customer Fraud Detection Pipeline

```
Transaction → Rules → ML → Policy → Decision (0-4)
              <1ms    <1ms  <0.1ms
```

**Measured Performance:**
- Average latency: **0.46ms** (130x better than 60ms target)
- Maximum latency: **1.34ms** (67x better than 90ms target)
- Rule-only blocks: **<0.1ms** (early exit optimization)

### Institute Security Monitoring Pipeline (NEW)

```
API Request → Rate Limiting → Security Monitoring → Threat Detection → Auto-Block
             (Token Bucket)   (Pattern Analysis)   (7 Threat Types)  (Critical)
                                                           ↓
                                                    SOC Review Queue
```

**Security Performance:**
- Event detection: **<5ms** overhead per request
- Rate limiting: **<1ms** overhead
- Event storage: **<10ms** write latency
- Dashboard queries: **<50ms**

## Components

### Stage 1: Rules Engine

- **Purpose:** Fast deterministic checks
- **Location:** `api/models/rules.py`
- **Checks:**
  - Deny list (device_id, user_id, ip_address)
  - Velocity caps (max 10 txn/hour per user)
  - Geo anomalies (>500km from usual location)
  - Time anomalies (3-5 AM high-risk window)
- **Early exit:** Block immediately on hard violations
- **Version control:** Rules loaded from `config/rules_v1.yaml`

### Stage 2: ML Engine

- **Purpose:** Probabilistic fraud scoring
- **Location:** `api/models/ml_engine.py`
- **Model:** LightGBM → ONNX (models/fraud_model.onnx)
- **Features:** 15 core features (see FEATURE_CONTRACT.md)
- **Calibration:** Isotonic regression (models/calibration.pkl)
- **Explanations:** SHAP top-3 features
- **Performance:** <1ms actual measured latency with ONNX Runtime

### Policy Engine

- **Purpose:** Combine rules + ML score → decision code
- **Location:** `api/models/policy.py`
- **Decision codes:**
  - 0: Allow (score < 0.35)
  - 1: Allow + Monitor (0.35 ≤ score < 0.55)
  - 2: Step-up (0.55 ≤ score < 0.75)
  - 3: Hold & Review (0.75 ≤ score, OR specific rule triggers)
  - 4: Block (hard rules OR score > 0.90)
- **Thresholds:** Loaded from `config/policy_v1.yaml`
- **Cost optimization:** FP=$5, FN=$200

### API Layer

- **Framework:** FastAPI
- **Endpoint:** POST /v1/decision
- **Location:** `api/main.py`, `api/routes/decision.py`
- **Response time:** Actual P95 ~1ms, well below 60ms target (P99 < 2ms vs 90ms target)
- **Logging:** Structured JSON to SQLite

### Institute Security Engine (NEW - Version 2.0)

- **Purpose:** Organization-level threat detection and prevention
- **Location:** `api/models/institute_security.py`
- **Threat Types:**
  1. API Abuse (high request rates, error patterns)
  2. Brute Force (failed authentication attempts)
  3. Data Exfiltration (unusual data access volumes)
  4. Insider Threats (off-hours access, privilege escalation)
  5. Privilege Escalation (unauthorized endpoint access)
  6. Unusual Access Patterns (geographic, temporal anomalies)
  7. System Anomalies (configuration changes, errors)
- **Threat Levels:** INFO (0) → LOW (1) → MEDIUM (2) → HIGH (3) → CRITICAL (4)
- **Auto-blocking:** Critical (level 4) threats trigger immediate source block
- **Pattern Analysis:** Sliding windows, statistical thresholds, ML-based detection

### Rate Limiter (NEW - Version 2.0)

- **Purpose:** Request rate control and abuse prevention
- **Location:** `api/utils/rate_limiter.py`
- **Algorithm:** Token bucket with configurable refill rates
- **Tiers:**
  - Free: 10 req/min (30 burst)
  - Basic: 60 req/min (120 burst)
  - Premium: 300 req/min (500 burst)
  - Internal: 1000 req/min (2000 burst)
  - Unlimited: No limits
- **Auto-blocking:** 3 violations within window → temporary block
- **Performance:** <1ms overhead per request

### Security Storage (NEW - Version 2.0)

- **Purpose:** Security event persistence and audit logging
- **Location:** `api/utils/security_storage.py`
- **Database:** SQLite with 3 tables:
  - `security_events` - Threat detections
  - `api_access_log` - All API requests
  - `audit_trail` - Analyst actions for compliance
- **Features:**
  - Event querying with filters
  - Source risk profiling
  - Audit trail for SOC actions
  - Compliance logging

### Data Layer

- **SQLite:** Transaction logs, security events, audit trail
- **Redis (optional):** Feature cache, deny lists
- **Files:** Model artifacts, configs
- **In-memory:** Rate limiter state, security patterns (production would use Redis)

## API Endpoints

### Fraud Detection
- `POST /v1/decision` - Get fraud decision for transaction
- `GET /health` - System health check

### Security Monitoring (NEW)
- `GET /v1/security/events` - Query security events
- `GET /v1/security/dashboard` - SOC dashboard stats
- `GET /v1/security/review-queue` - Events requiring review
- `GET /v1/security/source-profile/{id}` - Source risk profile
- `POST /v1/security/analyst-action` - Review/dismiss/escalate
- `GET /v1/security/blocked-sources` - List blocked sources
- `POST /v1/security/blocked-sources/unblock` - Unblock source
- `GET /v1/security/audit-trail` - Compliance audit log
- `GET /v1/security/rate-limits/{id}/status` - Rate limit status
- `POST /v1/security/rate-limits/{id}/tier` - Update rate tier
- `GET /v1/security/health` - Security subsystem health

## Implemented vs Future Work

### ✅ Fully Implemented (Version 2.0)

**Customer Fraud Detection:**
- Rules engine with early exit optimization
- ML engine with ONNX Runtime (5x faster)
- Policy engine with cost-optimized thresholds
- 15-feature extraction pipeline
- SHAP explanations

**Institute Security:**
- 7 threat types with auto-blocking
- 5 rate limit tiers
- SOC analyst workspace
- Event storage & audit trail
- Source risk profiling
- Real-time monitoring

**Demos & UI:**
- Interactive web playground
- Command-line demos
- Comprehensive test suite (75 tests)

### ❌ Out of Scope (Documented Only)

- Graph Intelligence (Stage 3 - mocked with static values)
- Full SOC case management UI (basic workflow implemented)
- Kafka/RabbitMQ messaging
- Full Feature Store (Feast)
- Kubernetes orchestration
- Multi-region deployment

## Key Design Decisions

### Version 1.0 (Fraud Detection)
1. **Monolithic FastAPI** vs microservices → Simplicity wins for MVP
2. **SQLite** vs PostgreSQL → Good enough for demo scale
3. **ONNX Runtime** vs Python inference → 5x faster, production-ready
4. **15 features** vs 100+ → Covers core patterns, fast computation
5. **Simple caching** vs feature store → Redis/dict sufficient for MVP

### Version 2.0 (Security Monitoring)
6. **In-memory state** vs Redis → Fast for MVP, easy migration path
7. **Token bucket** vs leaky bucket → Better burst handling
8. **SQLite** vs time-series DB → Sufficient for MVP scale
9. **7 threat types** vs specialized tools → Demonstrates breadth
10. **Auto-blocking** vs manual only → Shows production thinking

## Scalability Considerations

While the MVP uses simplified components, the architecture supports production scaling:

- **Rate Limiter:** In-memory → Redis (distributed state)
- **Security Events:** SQLite → TimescaleDB/ClickHouse (time-series)
- **API Layer:** Single instance → Kubernetes with horizontal scaling
- **Fraud Detection:** Synchronous → Async with message queue
- **Feature Store:** Dict/Redis → Feast/Tecton
- **Monitoring:** Logs → Prometheus/Grafana/ELK
