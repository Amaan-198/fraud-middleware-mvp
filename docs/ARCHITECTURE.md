# Allianz Fraud Middleware - Architecture

## System Overview

Real-time fraud detection middleware with sub-100ms latency serving decisions via REST API.

## Core Pipeline

```
REQUEST → Stage 1 (Rules) → Stage 2 (ML) → Policy Engine → RESPONSE
           <1ms              <1ms           <0.1ms
```

**Measured Performance (from demo scenarios):**
- Average latency: **0.46ms** (well below 60ms P95 target)
- Maximum latency: **1.34ms** (well below 90ms P99 target)
- Rule-only blocks: **<0.1ms** (velocity checks exit early)

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

### Data Layer (Simplified for MVP)

- **SQLite:** Transaction logs, historical aggregates
- **Redis (optional):** Feature cache, deny lists
- **Files:** Model artifacts, configs

## NOT IN MVP (Future Work)

- ❌ Graph Intelligence (Stage 3)
- ❌ Auto-Triage Engine (Stage 4.1)
- ❌ SOC Integration (Stage 4.2+)
- ❌ Full Feature Store (Feast)
- ❌ Message Queue (Kafka)
- ❌ Kubernetes orchestration
- ❌ Multi-region deployment

## Key Design Decisions

1. **Monolithic FastAPI** vs microservices → Simplicity wins for MVP
2. **SQLite** vs PostgreSQL → Good enough for demo scale
3. **ONNX Runtime** vs Python inference → 5x faster, production-ready
4. **15 features** vs 100+ → Covers core patterns, fast computation
5. **Simple caching** vs feature store → Redis/dict sufficient for MVP
