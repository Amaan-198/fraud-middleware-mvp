# Allianz Fraud Middleware – Optimized MVP

Real-time fraud & risk decisioning **middleware** designed as a scholarship project for the Allianz program.

The system exposes a single `/v1/decision` API that:

- Accepts transaction context (user, device, amount, geo, etc.)
- Runs a **three-stage pipeline**:
  1. Stage 1 – Rules Engine (fast deterministic checks)
  2. Stage 2 – ML Engine (LightGBM → ONNX, calibrated score)
  3. Policy Engine – combines rules + score → Decision Code (0–4)
- Returns a **decision code**, calibrated risk score, latency, and explanation.

The goal is to show **production-style thinking** with a **real working prototype** that a judge can run locally in minutes.

---

## MVP Scope

✅ **In scope (implemented)**

- Monolithic FastAPI service (`api/`) with `/v1/decision`
- Stage 1 Rules Engine (deny lists, velocity, geo/time, amount)
- Stage 2 ML Engine
  - LightGBM model trained on IEEE-CIS
  - Converted to ONNX and served via ONNX Runtime
  - Isotonic calibration
  - SHAP-based top feature explanations
- Policy Engine with Decision Codes 0–4 and cost-based thresholds
- SQLite for logging + simple aggregates, optional Redis for caching
- Demo harness + scenarios to showcase decisions
- Basic test suite + latency checks
- Docker / docker-compose setup for easy local run

❌ **Out of scope for MVP (documented only)**

- Full graph intelligence (Stage 3)
- Auto-triage engine and SOC workflows (Stage 4)
- Kafka/message bus, feature store, Kubernetes, multi-region, etc.
- Complex case management and full SOC UI

See `docs/PRODUCTION_ROADMAP.md` and `docs/DEMO_GUIDE.md` for more on roadmap and demo story.

---

## Tech Stack

- **Backend:** Python 3.11, FastAPI
- **ML:** LightGBM, ONNX Runtime, scikit-learn, SHAP
- **Storage:** SQLite (required), Redis (optional)
- **Frontend (demo):** React (Vite or similar), TypeScript/JS, Recharts
- **Environment:** Docker + docker-compose for local setup

---

## Project Structure

```text
fraud-middleware-mvp/
├── api/
│   ├── __init__.py
│   ├── main.py              # FastAPI app
│   ├── routes/
│   │   └── decision.py      # /v1/decision endpoint
│   ├── models/
│   │   ├── rules.py         # Stage 1 – rules engine
│   │   ├── ml_engine.py     # Stage 2 – ML engine
│   │   └── policy.py        # Policy engine
│   └── utils/
│       ├── features.py      # Feature extraction (15 core features)
│       ├── cache.py         # Redis/simple cache wrapper
│       └── logging.py       # Structured logging helpers
├── training/
│   ├── notebooks/
│   │   ├── 01_eda.ipynb
│   │   ├── 02_training.ipynb
│   │   └── 03_calibration.ipynb
│   └── scripts/
│       ├── train.py
│       └── convert_onnx.py
├── demo/
│   ├── frontend/            # React app
│   │   ├── src/
│   │   ├── public/
│   │   └── package.json
│   └── scenarios/           # Pre-built test cases
│       └── scenarios.json
├── models/
│   ├── fraud_model.onnx
│   ├── calibration.pkl
│   └── thresholds.yaml
├── config/
│   ├── rules_v1.yaml
│   ├── policy_v1.yaml
│   └── features.yaml
├── tests/
│   ├── test_api.py
│   ├── test_rules.py
│   ├── test_ml_engine.py
│   └── test_latency.py
├── docs/
│   ├── README.md            # Docs entrypoint / overview
│   ├── ARCHITECTURE.md      # System-level architecture
│   ├── API_REFERENCE.md     # /v1/decision API contract & examples
│   ├── MODEL_CARD.md        # Model details, training, metrics
│   ├── PRODUCTION_ROADMAP.md# Future stages & hardening plan
│   └── DEMO_GUIDE.md        # How to run and narrate the demo
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── .env.example
```
