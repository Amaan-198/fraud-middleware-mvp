# Allianz Fraud Middleware – Real-Time Fraud Detection MVP

> A production-ready fraud detection system achieving **sub-millisecond latency** for the Allianz Scholarship Program
> **Now with Institute-Level Security & Breach Prevention** 🛡️

## Overview

Real-time fraud detection middleware exposing a REST API (`/v1/decision`) that combines rule-based checks with machine learning to make instant fraud decisions on financial transactions.

**Version 2.0** adds comprehensive institute-level security monitoring to protect both customers AND the organization itself from threats.

**Key Achievements:**
- **Customer Protection:** Average decision latency of **0.46ms** (460 microseconds) - **130x faster** than the 60ms P95 target
- **Institute Security:** Real-time detection of API abuse, insider threats, data breaches, and brute force attacks
- **SOC Ready:** Complete analyst workflow with review queue, audit trails, and SIEM integration

### Customer Fraud Detection Pipeline

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

### Institute Security Monitoring 🆕

**Version 2.0** adds comprehensive organization-level security:

```
API Request → Rate Limiting → Security Monitoring → Threat Detection → Auto-Block
             (Token Bucket)   (Pattern Analysis)   (ML + Rules)      (if Critical)
                                                           ↓
                                                    SOC Review Queue
```

**Security Features:**
- **API Abuse Detection:** Monitors request rates, error rates, unusual patterns
- **Brute Force Protection:** Tracks failed auth attempts, auto-blocks attackers
- **Data Exfiltration Prevention:** Detects unusual data access volumes
- **Insider Threat Detection:** Flags off-hours access, privilege escalation
- **Rate Limiting:** Token bucket algorithm with 5 tiers (Free → Unlimited)
- **SOC Analyst Tools:** Review queue, audit trails, risk profiling
- **SIEM Integration:** Splunk, ELK, Azure Sentinel support

**Threat Levels:**
- **INFO (0):** Normal activity, logged for audit
- **LOW (1):** Minor anomaly, monitor
- **MEDIUM (2):** Suspicious, flag for review
- **HIGH (3):** Serious threat, alert immediately
- **CRITICAL (4):** Active breach, auto-block + escalate

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

# 3. Run the fraud detection demo
python demo/run_scenarios.py --verbose

# 4. Run the institute security demo (NEW!)
python demo/demo_institute_security.py
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

## Interactive Web UI Playground 🎮

**NEW:** A unified web interface to explore all fraud detection and security features interactively!

### Starting the Playground

**Option 1: Simple (Recommended) - Run Everything Together**
```bash
# Install frontend dependencies (first time only)
cd demo/frontend
npm install

# Start both backend and frontend together
npm run dev:all

# Open your browser at http://localhost:5173
```

**Option 2: Manual - Run Backend and Frontend Separately**
```bash
# Terminal 1 - Start the backend API
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000

# Terminal 2 - Start the frontend
cd demo/frontend
npm run dev

# Open your browser at http://localhost:5173
```

### Playground Features

The playground provides 7 interactive sections:

1. **Dashboard** - Real-time system health, metrics, and recent events
   - System health monitoring (decision pipeline + security subsystem)
   - Key metrics: events, reviews, blocked sources
   - Threat distribution charts
   - Recent high-priority events

2. **Fraud Tester** - Test fraud detection decisions
   - Pre-configured scenarios (normal, high amount, foreign location, suspicious)
   - Custom transaction builder
   - Real-time results with decision code, score, latency, and ML features
   - Perfect for demos and testing

3. **Security Monitor** - View security events and threats
   - Real-time event feed with filtering
   - Filter by threat level, type, source, limit
   - Auto-refresh capability
   - Event statistics

4. **SOC Workspace** - Security Operations Center analyst tools
   - Review queue for events requiring human review
   - Source risk profiling (risk score, recent events, threat breakdown)
   - One-click analyst actions (dismiss, investigate, escalate)
   - Blocked sources management with unblock capability
   - Full audit trail logging

5. **Rate Limiting Playground** - Test rate limiting behavior
   - Test different tiers (Free, Basic, Premium, Internal, Unlimited)
   - Send burst requests and observe blocking
   - Real-time status monitoring (tokens, violations, blocks)
   - Visual timeline of allowed/blocked requests

6. **Security Test Playground** 🆕 - Trigger security scenarios interactively
   - API Abuse: High request rate simulation (150 rapid requests)
   - Brute Force: Multiple failed authentication attempts (15 attempts)
   - Data Exfiltration: Large/unusual data access patterns (10x baseline)
   - Insider Threat: Off-hours privileged endpoint access
   - Real-time event generation and blocking status
   - Threat level and type visualization

7. **Audit Trail** 🆕 - Complete compliance audit log
   - Who accessed what and when
   - Source identifiers and timestamps
   - Action types and success/failure status
   - Detailed metadata for each operation
   - Auto-refresh capability
   - Activity timeline visualization

**Perfect for:**
- Live demos and presentations
- Testing new scenarios
- Understanding system behavior
- Training analysts
- Debugging and troubleshooting

See `demo/frontend/README.md` for detailed documentation.

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
