# Allianz Fraud Middleware MVP - Agent Instructions

## Quick Context

Building a **three-layer security architecture**:
1. **Customer fraud detection** - Real-time decisions in <1ms (0.46ms avg)
2. **Institute security monitoring** - Threat detection for the organization itself
3. **Behavioral biometrics** - Session-level account takeover detection 🆕

This is an MVP for a scholarship - focus on working, impressive features.

## Tech Stack

- Python 3.11 + FastAPI
- LightGBM model (ONNX format) - 5MB
- SQLite database (events, audit logs, sessions)
- React + Vite demo UI (9 sections)
- Docker Compose

## Project Layout

```
api/                # FastAPI application (5000+ LOC)
├── main.py        # Entry point, middleware, health checks
├── routes/        # API endpoints
│   ├── decision.py          # /v1/decision (fraud detection + session tracking)
│   ├── security.py          # /v1/security/* (security ops)
│   ├── sessions.py          # /v1/sessions/* (session monitoring) 🆕
│   └── demo_sessions.py     # /v1/demo/* (demo scenarios) 🆕
├── models/        # Detection engines
│   ├── rules.py             # Stage 1: Rule-based detection
│   ├── ml_engine.py         # Stage 2: ML inference
│   ├── policy.py            # Decision engine
│   ├── institute_security.py # Institute security monitoring
│   ├── session_monitor.py   # Session tracking & storage 🆕
│   ├── behavioral_scorer.py # Behavioral risk scoring 🆕
│   └── session_behavior.py  # Session data models 🆕
└── utils/         # Utilities
    ├── rate_limiter.py      # Token bucket rate limiting
    ├── security_storage.py  # Event storage & audit
    ├── features.py          # Feature extraction
    └── cache.py             # Redis/in-memory cache

tests/             # Test suite
├── test_security.py                # Basic security tests
├── test_security_comprehensive.py  # Full security test suite
├── test_institute_security.py      # Security engine tests (492 lines)
├── test_rate_limiter.py            # Rate limiting tests (395 lines)
├── test_security_api.py            # Security API tests (428 lines)
├── test_session_monitor.py         # Session monitor tests (428 lines) 🆕
├── test_behavioral_scorer.py       # Behavioral scorer tests (554 lines) 🆕
├── test_session_api.py             # Session API tests (582 lines) 🆕
└── test_session_behavior.py        # Session models tests (27 tests) 🆕

demo/frontend/     # React playground UI (9 sections)
├── src/
│   ├── components/
│   │   ├── Dashboard.jsx
│   │   ├── FraudTester.jsx
│   │   ├── SessionMonitor.jsx         # Live session monitoring 🆕
│   │   ├── SessionDemoComparison.jsx  # Attack vs normal demo 🆕
│   │   ├── SessionCard.jsx            # Session display card 🆕
│   │   ├── SessionDetail.jsx          # Session details modal 🆕
│   │   ├── SecurityMonitor.jsx
│   │   ├── SocWorkspace.jsx
│   │   ├── RateLimitingPlayground.jsx
│   │   ├── SecurityTestPlayground.jsx
│   │   └── AuditTrail.jsx
│   └── services/
│       └── api.js              # API client (with session methods)

training/          # Model training
models/            # Trained models (fraud_model.onnx)
config/            # YAML configurations
docs/              # Detailed specifications
├── BEHAVIORAL_BIOMETRICS.md    # Session monitoring guide 🆕
├── DEMO_CHECKLIST.md           # Demo preparation guide 🆕
├── ARCHITECTURE.md
├── SECURITY.md
└── ... (other docs)
```

## Key Files

**Fraud Detection:**
- `api/routes/decision.py` - /v1/decision endpoint (with session support)
- `api/models/rules.py` - Stage 1 rules engine
- `api/models/ml_engine.py` - Stage 2 ML inference
- `api/models/policy.py` - Decision logic
- `api/utils/features.py` - Feature engineering (15 features)

**Security Monitoring:**
- `api/models/institute_security.py` - Threat detection engine (22KB)
- `api/routes/security.py` - Security API endpoints (15KB)
- `api/utils/rate_limiter.py` - Token bucket rate limiting (11KB)
- `api/utils/security_storage.py` - Event storage & audit (18KB)

**Behavioral Biometrics (NEW):** 🆕
- `api/models/session_monitor.py` - Session tracking & lifecycle
- `api/models/behavioral_scorer.py` - 5 behavioral signals, risk scoring
- `api/models/session_behavior.py` - Session data models
- `api/routes/sessions.py` - Session API endpoints
- `api/routes/demo_sessions.py` - Demo scenarios
- `demo/frontend/src/components/SessionMonitor.jsx` - Live session dashboard
- `demo/frontend/src/components/SessionDemoComparison.jsx` - Attack vs normal demo

## Common Tasks

### Run All Tests

```bash
# Security tests
pytest tests/test_institute_security.py -v
pytest tests/test_rate_limiter.py -v
pytest tests/test_security_api.py -v

# Session tests 🆕
pytest tests/test_session_behavior.py -v
pytest tests/test_session_monitor.py -v
pytest tests/test_behavioral_scorer.py -v
pytest tests/test_session_api.py -v

# Integration tests
python tests/test_security.py
python tests/test_security_comprehensive.py

# Run all at once
pytest tests/ -v
```

### Run Demo

```bash
# Start full stack (backend + frontend)
cd demo/frontend
npm run dev:all

# Access at:
# Frontend: http://localhost:3000
# Backend: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### Test Behavioral Demo

```bash
# Test demo comparison endpoint
curl http://localhost:8000/v1/demo/session-comparison

# Expected: Returns normal_session_id and attack_session_id
# Attack session should be terminated (risk_score >= 80)
```

### Fix a Bug

1. Check relevant test first
2. Make minimal change
3. Verify test passes
4. Check latency not degraded (should be <1ms for fraud, <5ms for sessions)

### Add Behavioral Signal

1. Add to `BehavioralScorer` in `api/models/behavioral_scorer.py`
2. Implement detection method (returns weight if triggered)
3. Add to `calculate_risk()` logic
4. Add test to `tests/test_behavioral_scorer.py`
5. Update `docs/BEHAVIORAL_BIOMETRICS.md`

### Add Security Threat Type

1. Add to `ThreatType` enum in `api/models/institute_security.py`
2. Implement detection method
3. Call from appropriate monitoring method
4. Add test to `tests/test_institute_security.py`
5. Update `docs/SECURITY.md`

### Update Config

1. Edit YAML in `config/`
2. Restart API to reload
3. Test with demo scenario

## Code Style

- Type hints on functions
- Docstrings for public methods
- f-strings for formatting
- Early returns over nested ifs
- Constants in UPPER_CASE
- Use `requests.Session()` for HTTP connection pooling (Windows performance)

## What NOT to Do

❌ Don't add complex features not in spec
❌ Don't optimize prematurely (already 130x faster than target!)
❌ Don't add dependencies without asking
❌ Don't refactor working code unnecessarily
❌ Don't implement "future work" items

## MVP Boundaries

✅ We ARE building:
- Customer fraud detection (Rules + ML + Policy)
- Institute security monitoring (7 threat types)
- Behavioral biometrics session monitoring (5 signals) 🆕
- Rate limiting (5 tiers)
- SOC analyst tools (review queue, audit trail)
- Interactive demo UI (9 sections)
- Real-time session monitoring dashboard 🆕
- Live attack vs normal comparison demo 🆕

❌ We're NOT building:
- Graph features (Stage 3 - mocked)
- Full case management UI
- Kafka/RabbitMQ integration
- Kubernetes orchestration
- Multi-region deployment

## Performance Targets

**Fraud Detection:**
- ✅ Response time: **0.46ms avg** (target was <60ms P95)
- ✅ Throughput: 100+ TPS
- ✅ Memory: <500MB
- ✅ Startup: <5 seconds

**Security Monitoring:**
- ✅ Event detection: <5ms per request
- ✅ Rate limiting: <1ms overhead
- ✅ Event storage: <10ms write latency

**Behavioral Biometrics:** 🆕
- ✅ Session detection: <5ms per transaction
- ✅ Risk calculation: <1ms
- ✅ Database updates: <3ms
- ✅ Total overhead: ~4ms (still <60ms target)

## Testing Checklist

- [ ] All unit tests pass (`pytest tests/ -v`)
- [ ] Session tests pass (`pytest tests/test_session*.py -v`) 🆕
- [ ] Security tests pass (`python tests/test_security_comprehensive.py`)
- [ ] Latency <1ms for fraud detection
- [ ] Session monitoring <5ms overhead 🆕
- [ ] Demo scenarios work
- [ ] Frontend loads all 9 tabs 🆕
- [ ] Session demo comparison works 🆕
- [ ] No errors in logs

## Recent Updates

**2025-11-15 (Session 4):** Behavioral Biometrics Complete 🆕
- Added session-level behavioral monitoring
- 5 behavioral signals (amount, beneficiary, time, velocity, geolocation)
- Real-time session risk scoring with auto-termination
- Frontend UI: Session Monitor + Session Demo Comparison
- Comprehensive documentation: BEHAVIORAL_BIOMETRICS.md, DEMO_CHECKLIST.md
- 120+ new test cases
- See: `SESSION_4_COMPLETE.md`

**2025-11-14:** Fixed API abuse detection test
- Issue: Windows HTTP connection overhead (2+ seconds per request)
- Solution: Added `requests.Session()` for connection pooling
- Result: 350 req/min achieved (vs 28 req/min before)
- See: `docs/TEST_FIXES.md` and `docs/CHANGES_SUMMARY.md`

## Documentation

- `.claude/CLAUDE.md` - Detailed Claude Code instructions
- `docs/BEHAVIORAL_BIOMETRICS.md` - Session monitoring guide 🆕
- `docs/DEMO_CHECKLIST.md` - Demo preparation guide 🆕
- `docs/SECURITY.md` - Security monitoring documentation
- `docs/INTEGRATION.md` - Integration guide
- `docs/TEST_FIXES.md` - Test fixes and troubleshooting
- `docs/CHANGES_SUMMARY.md` - Recent changes log

## Quick Reference

```bash
# Start full stack (backend + frontend)
cd demo/frontend && npm run dev:all

# Or start separately:
# Backend
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000

# Frontend
cd demo/frontend && npm run dev

# Run all tests
pytest tests/ -v

# Run session tests 🆕
pytest tests/test_session*.py -v

# Run security test
python tests/test_security_comprehensive.py

# Test demo comparison 🆕
curl http://localhost:8000/v1/demo/session-comparison

# Check health
curl http://localhost:8000/health

# Access UI
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

---

**Last Updated:** 2025-11-15 (Session 4 Complete)
**Version:** 3.0 - Three-Layer Security Architecture
**Status:** All Systems Operational ✅

**System Components:**
- ✅ Fraud Detection (Rules + ML + Policy) - 0.46ms avg
- ✅ Institute Security (7 threat types) - <5ms
- ✅ Behavioral Biometrics (5 signals) - <5ms overhead 🆕
- ✅ Interactive Playground (9 sections) - Full UI 🆕
- ✅ Comprehensive Tests (150+ test cases) - All passing
- ✅ Complete Documentation - Production-ready
