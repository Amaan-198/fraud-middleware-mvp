# Allianz Fraud Middleware MVP - Claude Code Instructions

## Project Overview

You're helping build a **dual-purpose real-time fraud detection and security monitoring system** for the Allianz Scholarship. This started as a customer fraud detection MVP and has evolved into **Version 2.0** with comprehensive institute-level security.

**Current Status:** Production-ready MVP with sub-millisecond latency (0.46ms avg) and complete security monitoring.

## Architecture Summary

### Customer Fraud Detection (Original)
```
FastAPI → Rules Engine → ML Engine → Policy Engine → Decision Code (0-4)
         (Stage 1)      (Stage 2)     (Decisions)
```

### Institute Security Monitoring (NEW - Version 2.0)
```
API Request → Rate Limiting → Security Monitoring → Threat Detection → Auto-Block
             (Token Bucket)   (Pattern Analysis)   (ML + Rules)      (if Critical)
                                                           ↓
                                                    SOC Review Queue
```

## Project Structure

```
fraud-middleware-mvp/
├── api/                        # FastAPI application (3412 LOC total)
│   ├── main.py                # App entrypoint, middleware, health checks (257 lines)
│   ├── models/                # Core engines
│   │   ├── rules.py          # Stage 1 - Rule-based detection (15KB)
│   │   ├── ml_engine.py      # Stage 2 - ONNX ML inference (10KB)
│   │   ├── policy.py         # Decision engine (6.5KB)
│   │   └── institute_security.py  # ⭐ NEW: Security monitoring (22KB)
│   ├── routes/                # API endpoints
│   │   ├── decision.py       # /v1/decision endpoint (fraud detection)
│   │   └── security.py       # ⭐ NEW: /v1/security/* endpoints (15KB)
│   └── utils/                 # Utilities
│       ├── features.py       # Feature extraction (15 core features)
│       ├── cache.py          # Redis/in-memory cache
│       ├── logging.py        # Structured JSON logging
│       ├── rate_limiter.py   # ⭐ NEW: Token bucket rate limiting (11KB)
│       └── security_storage.py # ⭐ NEW: Event storage & audit (18KB)
├── training/                  # Model training
│   └── scripts/              # Training, ONNX conversion, calibration
├── models/                    # Trained models
│   ├── fraud_model.onnx      # LightGBM model (5MB)
│   ├── calibration.pkl       # Isotonic calibrator
│   └── training_summary.json # Model metrics
├── config/                    # YAML configurations
│   ├── rules_v1.yaml         # Rule thresholds
│   ├── policy_v1.yaml        # Decision thresholds
│   └── features.yaml         # Feature metadata
├── tests/                     # Test suite
│   ├── test_institute_security.py  # ✅ Implemented (492 lines)
│   ├── test_rate_limiter.py  # ✅ Implemented (395 lines)
│   ├── test_security_api.py  # ✅ Implemented (428 lines)
│   ├── test_security.py      # ✅ Standalone script (132 lines)
│   └── test_security_comprehensive.py  # ✅ Standalone script (242 lines)
├── demo/                      # Demo & testing tools
│   ├── frontend/             # ⭐ NEW: React web playground
│   ├── run_scenarios.py      # Original fraud detection demo
│   └── demo_institute_security.py  # ⭐ NEW: Security demo
├── docs/                      # Documentation
│   ├── ARCHITECTURE.md       # System architecture
│   ├── RULES_ENGINE_SPEC.md  # Rules engine spec
│   ├── ML_ENGINE_SPEC.md     # ML engine spec
│   ├── POLICY_ENGINE_SPEC.md # Policy engine spec
│   ├── FEATURE_CONTRACT.md   # Feature definitions
│   ├── DEMO_SCENARIOS.md     # Demo scenarios
│   ├── SECURITY.md           # ⭐ NEW: Security documentation (16KB)
│   ├── INTEGRATION.md        # ⭐ NEW: Integration guide (24KB)
│   └── FUTURE_WORK.md        # Production roadmap
├── TROUBLESHOOTING.md        # ⭐ NEW: Common issues & fixes
├── PLAYGROUND_GUIDE.md       # ⭐ NEW: Web UI guide
└── README.md                 # Project overview (13KB, updated)
```

## Coding Standards

- **Python 3.11** with type hints everywhere
- **FastAPI** best practices (Pydantic models, dependency injection)
- **Async where beneficial**, sync where simpler (don't over-async)
- **Error handling** with proper HTTP status codes (400, 429, 500)
- **Structured logging** (JSON format for production parsing)
- **Test coverage** goal: >80% for critical paths (currently gaps in core tests)

## Implementation Status

### ✅ FULLY IMPLEMENTED (Version 2.0)

#### Customer Fraud Detection
1. `/v1/decision` endpoint with **0.46ms average latency** (130x faster than 60ms target)
2. Stage 1 rules (denylists, velocity, geo, time-based)
3. Stage 2 ML (ONNX inference, SHAP explanations)
4. Policy engine (5 decision codes: 0=Allow, 1=Monitor, 2=Step-up, 3=Review, 4=Block)
5. Demo scenarios with expected outcomes

#### Institute Security (NEW)
6. **Rate limiting** with 5 tiers (Free, Basic, Premium, Internal, Unlimited)
7. **Security monitoring** for 7 threat types:
   - API abuse
   - Brute force attacks
   - Data exfiltration
   - Insider threats
   - Privilege escalation
   - Unusual access patterns
   - System anomalies
8. **Threat detection** with 5 levels (INFO, LOW, MEDIUM, HIGH, CRITICAL)
9. **Auto-blocking** for critical threats
10. **SOC analyst workspace** (review queue, audit trail, source profiling)
11. **Security event storage** with SQLite backend
12. **API endpoints** for security operations:
    - `/v1/security/events` - Query security events
    - `/v1/security/events/review-queue` - Events requiring review
    - `/v1/security/events/{event_id}/review` - Review event
    - `/v1/security/events/review-queue/clear` - Bulk clear reviews
    - `/v1/security/dashboard` - SOC dashboard stats
    - `/v1/security/sources/{source_id}/risk` - Source risk profiling
    - `/v1/security/sources/blocked` - List blocked sources
    - `/v1/security/sources/{source_id}/unblock` - Unblock source
    - `/v1/security/sources/{source_id}/reset` - Reset source
    - `/v1/security/rate-limits/{source_id}` - Get rate limit status
    - `/v1/security/rate-limits/{source_id}/tier` - Set rate tier
    - `/v1/security/audit-trail` - Compliance audit log
    - `/v1/security/health` - Security subsystem health

#### Demo & Testing
13. **Interactive web playground** (React + Vite)
    - Dashboard with real-time metrics
    - Fraud detection tester
    - Security event monitor
    - SOC analyst workspace
    - Rate limiting playground
    - Security test scenarios
    - Audit trail viewer
14. Python demo scripts for both fraud and security

### ⚠️ PARTIALLY IMPLEMENTED (Gaps)

1. **Core test suite** - Security tests are comprehensive (✅), fraud detection tests needed (❌):
   - ✅ `tests/test_security.py` - Basic security detection tests (working)
   - ✅ `tests/test_security_comprehensive.py` - Full test suite with metrics (working)
   - ✅ `tests/test_institute_security.py` - Security engine unit tests (492 lines)
   - ✅ `tests/test_rate_limiter.py` - Rate limiting tests (395 lines)
   - ✅ `tests/test_security_api.py` - Security API endpoint tests (428 lines)
   - ❌ Fraud detection tests (rules, ML, policy engines) - Not yet implemented

2. **Production deployment** - Docker configs exist but need validation

### ❌ NOT IN SCOPE (Documented Only)

- Graph features (Stage 3 - mock with static values)
- Full SOC case management UI (basic workflow implemented)
- Kafka/RabbitMQ (use Python queue/in-memory)
- Kubernetes orchestration (Docker Compose only)
- Multi-region deployment
- Synthetic data generation beyond demos

## File-by-File Guidance

### When editing `api/main.py`:
- **Purpose:** FastAPI app initialization, CORS, middleware, health checks
- **Key components:**
  - Security monitoring middleware (monitors ALL requests)
  - Rate limiting enforcement
  - Event logging and threat detection
  - Component initialization (singletons)
- **Important:** The middleware handles both rate limiting AND security event detection
- **Headers recognized:**
  - `X-Source-ID` - Source identifier (bypasses IP-based tracking)
  - `X-Auth-Result` - Authentication result for brute force detection
  - `X-Records-Accessed` - Data access count for exfiltration detection
  - `X-Access-Time` - Simulate off-hours access for testing

### When editing `api/models/rules.py`:
- **Purpose:** Stage 1 rule-based fraud detection
- Keep rules simple and fast (<200ms total)
- Use early exit patterns for efficiency
- Version rules in `config/rules_v1.yaml`
- Return `RuleResult` with triggered rules + metadata
- See `docs/RULES_ENGINE_SPEC.md`

### When editing `api/models/ml_engine.py`:
- **Purpose:** Stage 2 ML-based fraud scoring
- Use ONNX Runtime for inference (5x faster than native)
- Cache feature computations to avoid recomputation
- Return calibrated probabilities (0.0-1.0)
- Include SHAP-based feature importance (top 3)
- See `docs/ML_ENGINE_SPEC.md`

### When editing `api/models/policy.py`:
- **Purpose:** Final decision engine (combines rules + ML)
- Combine rules + scores deterministically
- Use thresholds from `config/policy_v1.yaml`
- Log all decisions with reasoning
- Return decision code (0-4) with explanation
- See `docs/POLICY_ENGINE_SPEC.md`

### When editing `api/models/institute_security.py`:
- **Purpose:** Organization-level security monitoring (NEW in v2.0)
- **Key methods:**
  - `monitor_api_request()` - Track API usage patterns
  - `monitor_authentication()` - Detect brute force
  - `monitor_data_access()` - Detect exfiltration
  - `detect_insider_threat()` - Off-hours access, privilege abuse
  - `should_block_source()` - Auto-blocking logic
- **Thresholds:** All configurable in `self.config` dict
- **Returns:** `SecurityEvent` objects with threat type/level
- **Auto-blocking:** Critical (level 4) events trigger immediate block
- Thread-safe using `defaultdict` and `deque`

### When editing `api/routes/decision.py`:
- **Purpose:** Main fraud detection endpoint
- Single endpoint: `POST /v1/decision`
- Accept transaction payload (Pydantic model)
- Run through Rules → ML → Policy pipeline
- Return decision code + metadata + latency
- **Performance target:** <60ms P95 (currently 0.46ms avg!)

### When editing `api/routes/security.py`:
- **Purpose:** Security monitoring API endpoints (NEW)
- **All endpoints:**
  - `GET /events` - Query security events with filtering
  - `GET /events/review-queue` - Events requiring analyst review
  - `POST /events/{event_id}/review` - Review event
  - `POST /events/review-queue/clear` - Bulk clear reviews
  - `GET /dashboard` - SOC dashboard statistics
  - `GET /sources/{source_id}/risk` - Source risk profile
  - `GET /sources/blocked` - List blocked sources
  - `POST /sources/{source_id}/unblock` - Unblock source
  - `POST /sources/{source_id}/reset` - Reset source
  - `GET /rate-limits/{source_id}` - Get rate limit status
  - `POST /rate-limits/{source_id}/tier` - Set rate tier
  - `GET /audit-trail` - Compliance audit log
  - `GET /health` - Security subsystem health
- Uses `SecurityEventStore` for persistence
- Uses `InstituteSecurityEngine` for threat detection

### When editing `api/utils/features.py`:
- **Purpose:** Feature extraction for ML model
- Compute exactly **15 features** (defined in `docs/FEATURE_CONTRACT.md`)
- Handle missing data gracefully (use defaults/imputation)
- Keep computation <10ms total
- Return dict with feature names matching training data

### When editing `api/utils/rate_limiter.py`:
- **Purpose:** Token bucket rate limiting (NEW)
- **5 tiers:** Free (10/min), Basic (60/min), Premium (300/min), Internal (1000/min), Unlimited
- Uses in-memory tracking (would be Redis in production)
- Returns tuple: `(allowed: bool, metadata: dict)`
- Metadata includes: tokens remaining, reset time, retry delay
- Thread-safe with `defaultdict`

### When editing `api/utils/security_storage.py`:
- **Purpose:** Security event storage and audit logging (NEW)
- **SQLite schema:**
  - `security_events` table (event_id, timestamp, threat_type, threat_level, etc.)
  - `api_access_log` table (source_id, endpoint, status_code, latency, etc.)
  - `audit_trail` table (who, what, when for compliance)
- **Key methods:**
  - `store_event()` - Store security event
  - `get_events()` - Query with filtering
  - `log_api_access()` - Log all API requests
  - `log_analyst_action()` - Audit analyst actions
- Auto-creates DB and tables if missing

## Testing Strategy

### Current Test Status

**✅ Fully Implemented:**
1. `pytest tests/test_institute_security.py` - Security engine tests (492 lines)
2. `pytest tests/test_rate_limiter.py` - Rate limiting tests (395 lines)
3. `pytest tests/test_security_api.py` - Security API tests (428 lines)
4. `python tests/test_security.py` - Basic security detection tests (working, 3.8KB)
5. `python tests/test_security_comprehensive.py` - Full security test suite (working, 8KB)

**❌ Not Implemented (Lower Priority):**
6. Fraud detection unit tests (rules, ML, policy engines) - Not needed for MVP

**Demo scripts (working):**
7. `python demo/run_scenarios.py` - Fraud detection scenarios
8. `python demo/demo_institute_security.py` - Security scenarios

### When Adding Tests

**For fraud detection tests (not implemented):**
Fraud detection unit tests for rules, ML, and policy engines are not currently implemented. Focus remains on security monitoring tests which are comprehensive.

**For security tests (follow existing patterns):**
- See `tests/test_institute_security.py` for examples
- Use pytest fixtures for engine initialization
- Test each threat type separately
- Verify threat levels and auto-blocking

## Common Tasks

### Add a new fraud detection rule:
1. Update `config/rules_v1.yaml` with new rule config
2. Add logic to `api/models/rules.py` (in `check_transaction()` method)
3. Document in `docs/RULES_ENGINE_SPEC.md`
4. Add to demo scenario in `demo/scenarios.json` if relevant
5. Test manually with playground or demo scripts

### Add a new security threat type:
1. Add to `ThreatType` enum in `api/models/institute_security.py`
2. Implement detection method (e.g., `def detect_new_threat()`)
3. Call from appropriate monitoring method
4. Add test to `tests/test_institute_security.py`
5. Update `docs/SECURITY.md` documentation

### Update ML model:
1. Train in `training/scripts/` (use existing scripts as templates)
2. Convert to ONNX format using `training/scripts/convert_to_onnx.py`
3. Replace `models/fraud_model.onnx`
4. Update calibration using `training/scripts/calibrate_model.py`
5. Update `models/training_summary.json` with new metrics
6. Test inference latency (should be <40ms)

### Add demo scenario:
1. Define in `demo/scenarios/scenarios.json` (or create new JSON)
2. Add to UI dropdown in `demo/frontend/src/components/FraudTester.tsx`
3. Test expected outcome with `python demo/run_scenarios.py`
4. Document in `docs/DEMO_SCENARIOS.md`

### Deploy the web playground:
```bash
# Install frontend dependencies (first time)
cd demo/frontend
npm install

# Start everything together
npm run dev:all

# Or manually in separate terminals:
# Terminal 1: python -m uvicorn api.main:app --host 0.0.0.0 --port 8000
# Terminal 2: cd demo/frontend && npm run dev

# Access at http://localhost:3000
```

## API Endpoints Reference

### Fraud Detection
- `POST /v1/decision` - Get fraud decision for transaction
- `GET /v1/decision/health` - Decision pipeline health check

### Security Monitoring (NEW)
- `GET /v1/security/events` - Query security events
- `GET /v1/security/events/review-queue` - Events requiring review
- `POST /v1/security/events/{event_id}/review` - Review event
- `POST /v1/security/events/review-queue/clear` - Bulk clear reviews
- `GET /v1/security/dashboard` - SOC dashboard stats
- `GET /v1/security/sources/{source_id}/risk` - Source risk profile
- `GET /v1/security/sources/blocked` - List blocked sources
- `POST /v1/security/sources/{source_id}/unblock` - Unblock source
- `POST /v1/security/sources/{source_id}/reset` - Reset source
- `GET /v1/security/rate-limits/{source_id}` - Get rate limit status
- `POST /v1/security/rate-limits/{source_id}/tier` - Set rate tier
- `GET /v1/security/audit-trail` - Compliance audit log
- `GET /v1/security/health` - Security subsystem health

### System
- `GET /` - Root health check
- `GET /health` - Detailed health with metrics
- `GET /docs` - Auto-generated OpenAPI docs
- `GET /redoc` - ReDoc documentation

## Performance Targets & Achievements

### Fraud Detection
- ✅ **API response:** <60ms P95 target → **0.46ms average** (130x better!)
- ✅ **Rules engine:** <200ms → **<1ms actual**
- ✅ **ML inference:** <40ms → **<1ms actual**
- ✅ **Policy engine:** <10ms → **<0.1ms actual**

### Security Monitoring
- ✅ **Event detection:** <5ms per request
- ✅ **Rate limiting:** <1ms overhead
- ✅ **Event storage:** <10ms write latency
- ✅ **Dashboard queries:** <50ms

## Configuration Files

### `config/rules_v1.yaml`
- Denylist configurations
- Velocity thresholds
- Geo-based rules
- Time-based rules
- Amount thresholds

### `config/policy_v1.yaml`
- Decision code thresholds
- Score cutoffs for each decision (0-4)
- Rule override policies
- Cost-based tuning parameters

### `config/features.yaml`
- Feature metadata (currently minimal/empty)
- Feature ranges and defaults

## Important Design Patterns

### 1. Early Exit Pattern (Performance)
```python
# In rules.py - exit early if high-confidence decision
if user_id in denylist:
    return RuleResult(triggered=True, should_block=True)
    # Don't continue to ML if rule-based block
```

### 2. Singleton Pattern (Shared State)
```python
# In main.py - shared instances across requests
rate_limiter = RateLimiter()  # Singleton
security_engine = InstituteSecurityEngine()  # Singleton
event_store = SecurityEventStore()  # Singleton
```

### 3. Middleware Pattern (Security)
```python
# In main.py - all requests go through security middleware
@app.middleware("http")
async def security_monitoring_middleware(request: Request, call_next):
    # Rate limiting
    # Security monitoring
    # Event logging
    # Threat detection
```

### 4. Threshold-Based Decision (Deterministic)
```python
# In policy.py - clear, auditable thresholds
if risk_score >= 0.8:
    return Decision.BLOCK
elif risk_score >= 0.6:
    return Decision.REVIEW
# ... etc
```

## Troubleshooting Common Issues

See `TROUBLESHOOTING.md` for detailed solutions. Quick fixes:

### Backend won't start:
```bash
# Check dependencies
pip install -r requirements.txt

# Check if port 8000 is in use
lsof -i :8000  # Mac/Linux
netstat -ano | findstr :8000  # Windows

# Test backend directly
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000
```

### Frontend won't build:
```bash
cd demo/frontend
rm -rf node_modules package-lock.json
npm install
npm run dev
```

### Tests failing:
```bash
# Many core tests are not implemented yet - this is expected
# Security tests should pass:
pytest tests/test_institute_security.py -v
pytest tests/test_rate_limiter.py -v
pytest tests/test_security_api.py -v
```

### Rate limiting blocking everything:
```bash
# Use X-Source-ID header to avoid IP-based rate limiting
curl -H "X-Source-ID: test-unique-id" http://localhost:8000/v1/decision
```

## Git Workflow

### Current Branch
- Main development: `main` branch
- Feature branches: `claude/*` pattern
- Always create descriptive commits

### Before Committing
1. Run implemented tests: `pytest tests/test_institute_security.py tests/test_rate_limiter.py tests/test_security_api.py`
2. Check code formatting (if tools configured)
3. Update documentation if adding features
4. Test manually with playground or demo scripts

## Documentation Standards

When updating docs:
- Keep `README.md` as the main entry point
- Technical specs go in `docs/*.md`
- API changes → update OpenAPI docs (FastAPI auto-generates)
- Security features → update `docs/SECURITY.md`
- New scenarios → update `docs/DEMO_SCENARIOS.md`
- Integration guides → `docs/INTEGRATION.md`

## Remember: MVP Priorities

This is a **scholarship MVP**, not production code. Priorities:

1. ✅ **Make it work** - Both fraud detection and security monitoring work
2. ✅ **Make it fast** - Sub-millisecond latency achieved
3. ✅ **Make it impressive** - Interactive playground, comprehensive features
4. ⚠️ **Make it tested** - Security tests done, fraud tests missing
5. ✅ **Make it documented** - Extensive docs and guides

**What matters most:**
- Live demos work perfectly (playground is impressive!)
- Performance is measurable and excellent
- Security features show depth and thought
- Documentation explains everything clearly

**What matters less:**
- Perfect test coverage (good enough for MVP)
- Production scalability (architecture shows it's possible)
- Every edge case (demo scenarios cover main paths)

## Key Differentiators

This MVP stands out because:

1. **Dual-purpose design:** Customer fraud + Institute security (most just do one)
2. **Extreme performance:** 0.46ms average (most are 50-100ms+)
3. **Production-ready patterns:** Config-driven, observable, scalable
4. **Complete SOC workflow:** Not just detection, but analyst tools
5. **Beautiful demo:** Interactive playground vs. CLI-only demos
6. **Real ML model:** Trained on real fraud data, not synthetic/mocked
7. **Explainability:** SHAP features + rule reasoning for every decision

## Quick Reference Card

```bash
# Start everything
cd demo/frontend && npm run dev:all

# Run fraud demo
python demo/run_scenarios.py

# Run security demo
python demo/demo_institute_security.py

# Run tests (implemented ones)
pytest tests/test_institute_security.py -v
pytest tests/test_rate_limiter.py -v

# Check system health
curl http://localhost:8000/health

# View API docs
open http://localhost:8000/docs

# Access playground
open http://localhost:3000
```

---

**Last Updated:** 2025-11-14 (Version 2.0 - Institute Security Edition)
