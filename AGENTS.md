# Allianz Fraud Middleware MVP - Agent Instructions

## Quick Context

Building a fraud detection API that makes real-time decisions in <90ms. This is an MVP for a scholarship - focus on working code over perfect code.

## Tech Stack

- Python 3.11 + FastAPI
- LightGBM model (ONNX format)
- SQLite database
- React demo UI
- Docker Compose

## Project Layout

```
api/           → FastAPI app (main.py, routes/, models/)
training/      → Jupyter notebooks for model
models/        → fraud_model.onnx, calibration.pkl
config/        → rules_v1.yaml, policy_v1.yaml
tests/         → Test suite
demo/          → React UI
docs/          → Detailed specifications
```

## Key Files

- `api/main.py` - FastAPI app entry
- `api/routes/decision.py` - /v1/decision endpoint
- `api/models/rules.py` - Stage 1 rules
- `api/models/ml_engine.py` - Stage 2 ML
- `api/models/policy.py` - Decision logic
- `api/utils/features.py` - Feature engineering

## Common Tasks

### Fix a bug:

1. Check relevant test first
2. Make minimal change
3. Verify test passes
4. Check latency not degraded

### Add logging:

```python
from api.utils.logging import get_logger
logger = get_logger(__name__)
logger.info("Processing", extra={"txn_id": txn_id})
```

### Update config:

1. Edit YAML in `config/`
2. Restart API to reload
3. Test with demo scenario

### Run tests:

```bash
pytest tests/test_<module>.py -v
```

## Code Style

- Type hints on functions
- Docstrings for public methods
- f-strings for formatting
- Early returns over nested ifs
- Constants in UPPER_CASE

## What NOT to Do

❌ Don't add complex features not in spec
❌ Don't optimize prematurely
❌ Don't add dependencies without asking
❌ Don't refactor working code unnecessarily
❌ Don't implement "future work" items

## MVP Boundaries

✅ We ARE building: Rules + ML + Policy + API + Demo
❌ We're NOT building: Graph features, Kafka, Kubernetes, Feature Store

## Performance Targets

- Response time: <60ms P95
- Throughput: 100 TPS
- Memory: <500MB
- Startup: <5 seconds

## Testing Checklist

- [ ] Unit test passes
- [ ] Latency <60ms
- [ ] Demo scenario works
- [ ] No new errors in logs

```

```
