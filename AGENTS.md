# Allianz Fraud Middleware MVP - Agent Instructions

## Quick Context

Building a **dual-purpose** fraud detection + security monitoring system:
1. **Customer fraud detection** - Real-time decisions in <1ms (0.46ms avg)
2. **Institute security monitoring** - Threat detection for the organization itself

This is an MVP for a scholarship - focus on working, impressive features.

## Tech Stack

- Python 3.11 + FastAPI
- LightGBM model (ONNX format) - 5MB
- SQLite database (events, audit logs)
- React + Vite demo UI
- Docker Compose

## Project Layout

```
api/                # FastAPI application (3412 LOC)
├── main.py        # Entry point, middleware, health checks
├── routes/        # API endpoints
│   ├── decision.py          # /v1/decision (fraud detection)
│   └── security.py          # /v1/security/* (security ops)
├── models/        # Detection engines
│   ├── rules.py             # Stage 1: Rule-based detection
│   ├── ml_engine.py         # Stage 2: ML inference
│   ├── policy.py            # Decision engine
│   └── institute_security.py # NEW: Security monitoring
└── utils/         # Utilities
    ├── rate_limiter.py      # NEW: Token bucket rate limiting
    ├── security_storage.py  # NEW: Event storage & audit
    ├── features.py          # Feature extraction
    └── cache.py             # Redis/in-memory cache

tests/             # Test suite
├── test_security.py                # Basic security tests
├── test_security_comprehensive.py  # Full security test suite
├── test_institute_security.py      # Security engine tests (492 lines)
├── test_rate_limiter.py            # Rate limiting tests (395 lines)
└── test_security_api.py            # Security API tests (428 lines)

training/          # Model training
models/            # Trained models (fraud_model.onnx)
config/            # YAML configurations
demo/              # React playground UI
docs/              # Detailed specifications
```

## Key Files

**Fraud Detection:**
- `api/routes/decision.py` - /v1/decision endpoint
- `api/models/rules.py` - Stage 1 rules engine
- `api/models/ml_engine.py` - Stage 2 ML inference
- `api/models/policy.py` - Decision logic
- `api/utils/features.py` - Feature engineering (15 features)

**Security Monitoring (NEW):**
- `api/models/institute_security.py` - Threat detection engine (22KB)
- `api/routes/security.py` - Security API endpoints (15KB)
- `api/utils/rate_limiter.py` - Token bucket rate limiting (11KB)
- `api/utils/security_storage.py` - Event storage & audit (18KB)

## Common Tasks

### Run Security Tests

```bash
# Quick test
python tests/test_security.py

# Comprehensive test with metrics
python tests/test_security_comprehensive.py

# Unit tests
pytest tests/test_institute_security.py -v
pytest tests/test_rate_limiter.py -v
pytest tests/test_security_api.py -v
```

### Fix a Bug

1. Check relevant test first
2. Make minimal change
3. Verify test passes
4. Check latency not degraded (should be <1ms)

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
- Rate limiting (5 tiers)
- SOC analyst tools (review queue, audit trail)
- Interactive demo UI

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

## Testing Checklist

- [ ] Security tests pass (`python tests/test_security_comprehensive.py`)
- [ ] Unit tests pass (`pytest tests/ -v`)
- [ ] Latency <1ms for fraud detection
- [ ] Demo scenarios work
- [ ] No errors in logs

## Recent Fixes

**2025-11-14:** Fixed API abuse detection test
- Issue: Windows HTTP connection overhead (2+ seconds per request)
- Solution: Added `requests.Session()` for connection pooling
- Result: 350 req/min achieved (vs 28 req/min before)
- See: `docs/TEST_FIXES.md` and `docs/CHANGES_SUMMARY.md`

## Documentation

- `.claude/CLAUDE.md` - Detailed Claude Code instructions
- `docs/SECURITY.md` - Security monitoring documentation
- `docs/INTEGRATION.md` - Integration guide
- `docs/TEST_FIXES.md` - Test fixes and troubleshooting
- `docs/CHANGES_SUMMARY.md` - Recent changes log

## Quick Reference

```bash
# Start backend
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000

# Start frontend
cd demo/frontend && npm run dev

# Run all tests
pytest tests/ -v

# Run security test
python tests/test_security_comprehensive.py

# Check health
curl http://localhost:8000/health
```

---

**Last Updated:** 2025-11-14 (Version 2.0 - All Tests Passing)
