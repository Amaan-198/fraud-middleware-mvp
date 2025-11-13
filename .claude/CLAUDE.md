# Allianz Fraud Middleware MVP - Claude Code Instructions

## Project Overview

You're helping build a real-time fraud detection system for the Allianz Scholarship. This is an **optimized MVP** - we're building 30% of features to demonstrate 90% of the capability in 2-3 weeks.

## Architecture Summary

```
FastAPI → Rules Engine → ML Engine → Policy Engine → Response
         (Stage 1)      (Stage 2)     (Decisions)
```

## Project Structure

```
fraud-middleware-mvp/
├── api/                 # FastAPI application
│   ├── models/         # Rules, ML, Policy engines
│   ├── routes/         # API endpoints
│   └── utils/          # Features, cache, logging
├── training/           # Model training notebooks
├── models/             # ONNX model, calibration
├── config/             # Rules, policy configs
├── tests/              # Test suite
├── demo/               # React demo UI
└── docs/               # Documentation
```

## Coding Standards

- Python 3.11 with type hints
- FastAPI best practices (Pydantic models, dependencies)
- Async where beneficial, sync where simpler
- Error handling with proper status codes
- Structured logging (JSON format)
- Test coverage >80% for critical paths

## Implementation Priorities

### ✅ IN SCOPE (MVP)

1. `/v1/decision` endpoint with <90ms P99
2. Stage 1 rules (denylists, velocity, geo)
3. Stage 2 ML (ONNX inference, SHAP)
4. Policy engine (5 decision codes)
5. 5 demo scenarios that work perfectly
6. Simple React dashboard
7. SQLite for storage (good enough)

### ❌ NOT IN SCOPE (Don't Build)

- Graph features (mock with static values)
- Complex SOC integration (just log events)
- Feature store (use simple dict cache)
- Kafka/RabbitMQ (use Python queue)
- Kubernetes (Docker Compose only)
- Synthetic data generation
- Multiple models or ensembles

## File-by-File Guidance

### When editing `api/models/rules.py`:

- Keep rules simple and fast (<200ms)
- Use early exit patterns
- Version rules in YAML config
- See `docs/RULES_ENGINE_SPEC.md`

### When editing `api/models/ml_engine.py`:

- Use ONNX Runtime for inference
- Cache feature computations
- Return calibrated probabilities
- See `docs/ML_ENGINE_SPEC.md`

### When editing `api/models/policy.py`:

- Combine rules + scores deterministically
- Use thresholds from config
- Log all decisions
- See `docs/POLICY_ENGINE_SPEC.md`

### When editing `api/utils/features.py`:

- Compute exactly 15 features
- Handle missing data gracefully
- Keep computation <10ms
- See `docs/FEATURE_CONTRACT.md`

## Testing Strategy

Run tests in this order:

1. `pytest tests/test_rules.py` - Rules work
2. `pytest tests/test_ml_engine.py` - ML inference works
3. `pytest tests/test_api.py` - Endpoint works
4. `pytest tests/test_latency.py` - Performance met
5. `python demo/run_scenarios.py` - Scenarios work

## Common Tasks

### Add a new rule:

1. Update `config/rules_v1.yaml`
2. Add logic to `api/models/rules.py`
3. Add test to `tests/test_rules.py`
4. Document in `docs/RULES_ENGINE_SPEC.md`

### Update model:

1. Train in `training/notebooks/`
2. Convert to ONNX
3. Replace `models/fraud_model.onnx`
4. Update calibration
5. Test inference latency

### Add demo scenario:

1. Define in `demo/scenarios/scenarios.json`
2. Add to UI dropdown
3. Test expected outcome
4. Document in `docs/DEMO_SCENARIOS.md`

## Performance Checklist

- [ ] API responds in <60ms P95
- [ ] Rules complete in <200ms
- [ ] ML inference <40ms
- [ ] All 5 scenarios work
- [ ] Demo UI loads smoothly
- [ ] 1000 requests don't crash

## Remember

This is an MVP to win a scholarship, not production code. Make it work, make it fast, make it impressive. Documentation and demo matter as much as code.
