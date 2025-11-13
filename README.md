# Allianz Fraud Middleware – Optimized MVP

Real-time fraud & risk decisioning **middleware** designed as a scholarship project for the Allianz program.

The system exposes a single `/v1/decision` API that:

- Accepts transaction context (user, device, amount, geo, etc.)
- Runs a **three-stage pipeline**:
  1. Stage 1 – Rules Engine (fast deterministic checks)
  2. Stage 2 – ML Engine (LightGBM → ONNX, calibrated score)
  3. Policy Engine – combines rules + score → Decision Code (0–4)
- Returns a **decision code**, calibrated risk score, latency, and human-readable explanation.

Goal: show **production-style thinking** with a **real working prototype** that a judge can run locally in minutes.

---

## MVP Scope

✅ **In scope (implemented / planned for MVP)**

- Monolithic FastAPI service (`api/`) with `/v1/decision`
- Stage 1 Rules Engine
  - Deny lists (user, device, IP, merchant)
  - Velocity checks (user / device caps)
  - Geo & time rules (impossible travel, risky time windows)
  - Amount-based rules (unusual / very high amounts)
- Stage 2 ML Engine
  - LightGBM model trained on IEEE-CIS fraud dataset
  - Converted to ONNX and served via ONNX Runtime
  - Isotonic calibration for well-behaved probabilities
  - SHAP-based “top feature” explanations
- Policy Engine
  - Decision codes 0–4
  - Cost-based thresholds (FP = friction, FN = fraud loss)
  - Progressive friction (allow → monitor → step-up → hold → block)
- SQLite for logging + simple aggregates
- Optional Redis for hot feature cache / deny lists
- Demo harness + pre-built scenarios to showcase decisions
- Basic test suite + latency checks
- Docker / docker-compose setup for easy local run

❌ **Out of scope for MVP (documented only)**

- Full graph intelligence (Stage 3 – users/devices/merchants graph, GNNs)
- Auto-triage engine and full SOC workflows (Stage 4)
- Kafka / message bus, dedicated feature store, Kubernetes, multi-region, etc.
- Full case management system and SOC UI
- Heavy compliance / governance implementation (kept in docs as roadmap)

For more detail on design vs production roadmap, see `docs/FUTURE_WORK.md`.

---

## Tech Stack

- **Backend:** Python 3.11, FastAPI
- **ML:** LightGBM, ONNX Runtime, scikit-learn, SHAP
- **Storage:** SQLite (required), Redis (optional)
- **Frontend (demo):** React (Vite or similar), TypeScript/JS, Recharts/Tailwind
- **Infra:** Docker + docker-compose for local setup

---

## Project Structure

```text
fraud-middleware-mvp/
├── api/
│   ├── __init__.py
│   ├── main.py              # FastAPI app entrypoint
│   ├── routes/
│   │   └── decision.py      # /v1/decision endpoint
│   ├── models/
│   │   ├── rules.py         # Stage 1 – rules engine
│   │   ├── ml_engine.py     # Stage 2 – ML engine (ONNX runtime wrapper)
│   │   └── policy.py        # Policy engine (decision codes 0–4)
│   └── utils/
│       ├── features.py      # Feature extraction (15 core features)
│       ├── cache.py         # Redis/simple in-memory cache wrapper
│       └── logging.py       # Structured JSON logging helpers
├── training/
│   ├── notebooks/
│   │   ├── 01_eda.ipynb
│   │   ├── 02_training.ipynb
│   │   └── 03_calibration.ipynb
│   └── scripts/
│       ├── train.py         # Training CLI
│       └── convert_onnx.py  # Convert LightGBM → ONNX
├── demo/
│   ├── frontend/            # React demo app
│   │   ├── src/
│   │   ├── public/
│   │   └── package.json
│   └── scenarios/
│       └── scenarios.json   # Pre-built test cases used in demo
├── models/
│   ├── fraud_model.onnx     # Exported LightGBM model
│   ├── calibration.pkl      # Isotonic calibrator
│   └── thresholds.yaml      # Thresholds & policy parameters
├── config/
│   ├── rules_v1.yaml        # Rule configuration & thresholds
│   ├── policy_v1.yaml       # Policy thresholds & overrides
│   └── features.yaml        # Feature metadata / ranges
├── tests/
│   ├── test_api.py          # /v1/decision endpoint tests
│   ├── test_rules.py        # Stage 1 – rule behavior
│   ├── test_ml_engine.py    # Stage 2 – model & calibration
│   └── test_latency.py      # Latency / performance checks
├── docs/
│   ├── README.md            # Docs entrypoint / overview
│   ├── ARCHITECTURE.md      # System-level architecture
│   ├── FEATURE_CONTRACT.md  # 15-feature definition & validation rules
│   ├── RULES_ENGINE_SPEC.md # Stage 1 rules design
│   ├── ML_ENGINE_SPEC.md    # Stage 2 model, training & serving spec
│   ├── POLICY_ENGINE_SPEC.md# Decisioning & thresholds spec
│   ├── DEMO_SCENARIOS.md    # Detailed demo scenarios + expectations
│   └── FUTURE_WORK.md       # Production roadmap & “Stage 3/4” vision
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── AGENTS.md
├── README.md
└── .env.example
```
