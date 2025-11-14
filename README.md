# Allianz Fraud Middleware – Real-Time Fraud Detection MVP

> A production-ready fraud detection system achieving **sub-millisecond latency** for the Allianz Scholarship Program

## Overview

Real-time fraud detection middleware exposing a REST API (`/v1/decision`) that combines rule-based checks with machine learning to make instant fraud decisions on financial transactions.

**Key Achievement:** Average decision latency of **0.46ms** (460 microseconds) - **130x faster** than the 60ms P95 target.

### Decision Pipeline

```
Transaction → Rules Engine → ML Engine → Policy Engine → Decision Code (0-4)
              (<1ms)         (<1ms)      (<0.1ms)
```

**Decision Codes:**
- **0 (Allow)**: Low risk, approve instantly
- **1 (Monitor)**: Approve with logging for pattern analysis
- **2 (Step-up)**: Request additional authentication (OTP/2FA)
- **3 (Review)**: Hold for manual analyst review
- **4 (Block)**: High risk, deny transaction

---

## Quick Start

### Prerequisites

- Python 3.11+
- pip

### Installation & Running

```bash
# 1. Clone the repository
git clone <repo-url>
cd fraud-middleware-mvp

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the demo scenarios
python demo/run_scenarios.py --verbose
```

### Expected Output

```
================================================================================
                         FRAUD DETECTION DEMO SCENARIOS
================================================================================

Normal Transaction ✓
────────────────────────────────────────────────────────────────────────────────
Decision:     ALLOW (0)
Score:        0.018
ML Score:     0.018
Latency:      1.34ms

...

================================================================================
                                    SUMMARY
================================================================================

Scenarios: 5/5 passed
Avg Latency: 0.46ms
Max Latency: 1.34ms
```

---

## Key Features & Technical Highlights

### Performance
- **Sub-millisecond latency**: 0.46ms average (130x faster than target)
- **Early exit optimization**: Rules-only blocks complete in <0.1ms
- **ONNX Runtime**: 5x faster than native Python ML inference
- **Lightweight**: 15 core features for fast computation (<10ms feature extraction)

### Fraud Detection Capabilities
- **Multi-stage pipeline**: Rules → ML → Policy for balanced precision/recall
- **Real-time velocity tracking**: Detects burst patterns (>10 txns/hour)
- **Behavioral scoring**: Account age, device history, spending patterns
- **Time/geo anomalies**: Night window (3-5 AM), impossible travel detection
- **Calibrated probabilities**: Isotonic regression for interpretable scores

### ML Model
- **Algorithm**: LightGBM (100 trees, depth 13) → ONNX format
- **Training data**: IEEE-CIS Fraud Detection dataset (~500k transactions)
- **Performance**: AUC-ROC 0.903, Precision@1%FPR 0.821
- **Explainability**: Top-3 contributing features for every decision

### Production-Ready Design
- **Config-driven**: YAML-based rules and thresholds (no code changes to tune)
- **Version control**: All configs and models tracked with versioning
- **Structured logging**: JSON logs for monitoring and analysis
- **Cost-optimized thresholds**: Balances $5 FP cost vs $200 FN cost

### Uniqueness & Innovation
This MVP demonstrates:
1. **Hybrid approach**: Combines deterministic rules (precision) with ML (recall)
2. **Real-world performance**: Achieves production-grade latency on commodity hardware
3. **Explainability**: Every decision includes human-readable reasons
4. **Scalability mindset**: Architecture designed for horizontal scaling (Stage 3/4 in docs)
5. **Business alignment**: Thresholds optimized for actual fraud economics

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
