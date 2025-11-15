# Session 2 Architecture - Session Monitor + Behavioral Scorer

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Fraud Detection API                          │
│                   (api/routes/decision.py)                      │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        │ Optional session_id in request
                        │
                        ▼
        ┌───────────────────────────────────────┐
        │      Session Tracking Layer           │
        │    (Non-blocking, Optional)           │
        └───────────┬───────────────────────────┘
                    │
        ┌───────────┴───────────┐
        │                       │
        ▼                       ▼
┌───────────────────┐   ┌──────────────────────┐
│ SessionMonitor    │   │ BehavioralScorer     │
│                   │   │                      │
│ - CRUD ops        │   │ - 5 signals          │
│ - Lifecycle mgmt  │   │ - Risk calculation   │
│ - Event tracking  │   │ - Anomaly detection  │
│ - Cache (60s TTL) │   │ - Pure computation   │
└─────────┬─────────┘   └──────────────────────┘
          │
          │ Uses existing storage
          │
          ▼
┌─────────────────────────────────────┐
│   SecurityEventStore                │
│   (api/utils/security_storage.py)   │
│                                     │
│   - session_behaviors table         │
│   - session_events table            │
│   - SQLite database                 │
└─────────────────────────────────────┘
```

---

## Component Interaction Flow

### 1. Transaction with Session Tracking

```
Client Request
    │
    │ POST /v1/decision
    │ { user_id, amount, session_id (optional) }
    │
    ▼
┌─────────────────────────────────────┐
│  Fraud Detection Pipeline           │
│                                     │
│  1. Rules Engine                    │
│  2. ML Engine                       │
│  3. Policy Engine                   │
│                                     │
│  Decision: APPROVE/DECLINE/REVIEW   │
└──────────┬──────────────────────────┘
           │
           │ If session_id present
           │
           ▼
┌─────────────────────────────────────┐
│  SessionMonitor.record_transaction  │
│                                     │
│  - Get/create session               │
│  - Update metrics                   │
│  - Store event                      │
└──────────┬──────────────────────────┘
           │
           │ Session retrieved
           │
           ▼
┌─────────────────────────────────────┐
│  BehavioralScorer.calculate_risk    │
│                                     │
│  - Check 5 signals                  │
│  - Calculate score                  │
│  - Identify anomalies               │
└──────────┬──────────────────────────┘
           │
           │ Risk score calculated
           │
           ▼
┌─────────────────────────────────────┐
│  SessionMonitor.update_session      │
│                                     │
│  - Update risk score                │
│  - Add anomalies                    │
│  - Persist to DB                    │
└──────────┬──────────────────────────┘
           │
           │ If risk >= 80 (CRITICAL)
           │
           ▼
┌─────────────────────────────────────┐
│  SessionMonitor.terminate_session   │
│                                     │
│  - Mark terminated                  │
│  - Store termination event          │
└─────────────────────────────────────┘
```

---

## Data Flow

### Session Lifecycle

```
CREATE
  │
  │ SessionMonitor.create_session()
  │
  ├─> session_behaviors table (INSERT)
  │   - session_id, account_id, user_id
  │   - login_time, risk_score=0
  │
  └─> session_events table (INSERT)
      - event_type: "session_start"

ACTIVE
  │
  │ SessionMonitor.record_transaction()
  │
  ├─> session_behaviors table (UPDATE)
  │   - transaction_count++
  │   - total_amount += amount
  │   - last_activity_time = now
  │
  └─> session_events table (INSERT)
      - event_type: "transaction"
      - event_data: {amount, ...}

SCORED
  │
  │ BehavioralScorer.calculate_risk()
  │
  ├─> 5 Signal Checks (in-memory)
  │   1. Transaction Velocity
  │   2. Amount Deviation
  │   3. Beneficiary Changes
  │   4. Time of Day
  │   5. Transaction Pattern
  │
  └─> RiskScore object
      - score: 0-100
      - signals_triggered: [...]
      - anomalies: [...]

UPDATED
  │
  │ SessionMonitor.update_session()
  │
  └─> session_behaviors table (UPDATE)
      - risk_score = calculated_score
      - anomalies_detected = [...]
      - updated_at = now

TERMINATED (if high risk)
  │
  │ SessionMonitor.terminate_session()
  │
  ├─> session_behaviors table (UPDATE)
  │   - is_terminated = true
  │   - termination_reason = "..."
  │
  └─> session_events table (INSERT)
      - event_type: "session_terminated"
```

---

## Behavioral Scorer Signal Architecture

### Signal Processing Pipeline

```
Input: SessionBehavior + transaction_data
  │
  ├─> Signal 1: TRANSACTION_VELOCITY
  │   ├─> Check transaction count vs time
  │   └─> Score: (excess_count) * 20
  │
  ├─> Signal 2: AMOUNT_DEVIATION
  │   ├─> Compare to baseline ($2500)
  │   └─> Score: 30 if > 3x baseline
  │
  ├─> Signal 3: BENEFICIARY_CHANGES
  │   ├─> Count new beneficiaries
  │   └─> Score: (new_count) * 25
  │
  ├─> Signal 4: TIME_OF_DAY_ANOMALY
  │   ├─> Check against active hours (9-22)
  │   └─> Score: 15 if off-hours
  │
  └─> Signal 5: TRANSACTION_PATTERN
      ├─> Check transaction count vs typical
      └─> Score: 20 if > 2x typical
  │
  ▼
Total Score (clamped 0-100)
  │
  ├─> 0-30:   LOW
  ├─> 30-60:  MEDIUM
  ├─> 60-80:  HIGH
  └─> 80-100: CRITICAL
```

---

## Database Schema (from Session 1)

### session_behaviors Table

```sql
CREATE TABLE session_behaviors (
    session_id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL,
    user_id TEXT,
    login_time INTEGER NOT NULL,
    transaction_count INTEGER DEFAULT 0,
    total_amount REAL DEFAULT 0.0,
    beneficiaries_added INTEGER DEFAULT 0,
    last_activity_time INTEGER NOT NULL,
    risk_score REAL DEFAULT 0.0,
    is_terminated BOOLEAN DEFAULT 0,
    termination_reason TEXT,
    anomalies_detected TEXT DEFAULT '[]',  -- JSON
    metadata TEXT DEFAULT '{}',            -- JSON
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);

-- Indices
CREATE INDEX idx_session_account ON session_behaviors(account_id);
CREATE INDEX idx_session_risk ON session_behaviors(risk_score DESC);
CREATE INDEX idx_session_active ON session_behaviors(is_terminated);
CREATE INDEX idx_session_time ON session_behaviors(created_at DESC);
```

### session_events Table

```sql
CREATE TABLE session_events (
    event_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    event_time INTEGER NOT NULL,
    risk_delta REAL DEFAULT 0.0,
    event_data TEXT DEFAULT '{}',  -- JSON
    FOREIGN KEY (session_id) REFERENCES session_behaviors(session_id)
);

-- Indices
CREATE INDEX idx_event_session ON session_events(session_id);
CREATE INDEX idx_event_time ON session_events(event_time DESC);
```

---

## Caching Strategy

### In-Memory Cache (SessionMonitor)

```
┌─────────────────────────────────────┐
│        Session Cache                │
│                                     │
│  {                                  │
│    "sess_123": {                    │
│      session_data...                │
│      cache_ts: 1234567890           │
│    },                               │
│    "sess_456": { ... }              │
│  }                                  │
└─────────────────────────────────────┘
         │
         │ TTL: 60 seconds
         │
         ▼
┌─────────────────────────────────────┐
│  Auto-Expiration                    │
│                                     │
│  - Check cache_ts on read           │
│  - If > 60s old, query DB           │
│  - Background cleanup optional      │
└─────────────────────────────────────┘
```

**Benefits:**
- Reduces DB queries for frequently accessed sessions
- 60s TTL balances freshness vs performance
- Optional (can be disabled by removing cache dict)
- Automatic expiration on next access

---

## Error Handling Strategy

### Non-Blocking Session Tracking

```python
try:
    # CRITICAL PATH: Fraud detection (always succeeds)
    decision = policy_engine.decide(...)
    
    # OPTIONAL PATH: Session tracking (may fail)
    if request.session_id:
        try:
            # Session tracking operations
            session_monitor.record_transaction(...)
            risk = behavioral_scorer.calculate_risk(...)
            session_monitor.update_session(...)
        except Exception as e:
            # Log but don't propagate
            logger.warning(f"Session tracking failed: {e}")
    
    # Return fraud decision (always)
    return DecisionResponse(decision)
    
except Exception as e:
    # Only fraud detection errors propagate
    raise HTTPException(...)
```

**Principle:** Session monitoring is telemetry, not critical path.

---

## Performance Characteristics

### Operation Latencies

| Operation | DB Queries | Cache Hit | Cache Miss | Total Time |
|-----------|-----------|-----------|-----------|------------|
| `create_session()` | 2 | N/A | N/A | 2-5ms |
| `get_session()` | 0-1 | <0.1ms | 1-2ms | 0.1-2ms |
| `update_session()` | 1 | N/A | N/A | 1-2ms |
| `record_transaction()` | 2 | N/A | N/A | 2-4ms |
| `calculate_risk()` | 0 | N/A | N/A | <1ms |
| `terminate_session()` | 2 | N/A | N/A | 2-4ms |

### Typical Transaction Flow

```
/v1/decision request with session_id
  │
  ├─> Fraud detection: 0.46ms (unchanged)
  │
  └─> Session tracking: 2-5ms
      ├─> get_session(): 0.1-2ms (cached)
      ├─> record_transaction(): 2-4ms
      ├─> calculate_risk(): <1ms
      ├─> update_session(): 1-2ms
      └─> Total: ~3-9ms

TOTAL: 3.5-9.5ms (fraud + session)

Note: Session tracking can be made async (future optimization)
```

---

## Configuration & Tuning

### Risk Thresholds (RISK_THRESHOLDS)

```python
{
    # Velocity
    "velocity_normal_max": 3,
    "velocity_anomaly_count": 5,
    "velocity_score_per_excess": 20,
    
    # Amount
    "amount_deviation_multiplier": 3.0,
    "amount_deviation_score": 30,
    
    # Beneficiaries
    "beneficiary_score_per_new": 25,
    
    # Time
    "time_anomaly_score": 15,
    
    # Pattern
    "pattern_deviation_multiplier": 2.0,
    "pattern_deviation_score": 20,
    
    # Risk levels
    "risk_low": 30,
    "risk_medium": 60,
    "risk_high": 80,
}
```

### User Baselines (USER_BASELINES)

```python
{
    "default": {
        "avg_transaction_amount": 2500.0,
        "active_hours_range": (9, 22),
        "avg_transactions_per_session": 2,
        "typical_beneficiaries": 2,
        "avg_time_between_transactions": 60,
    }
}
```

---

## Integration with Existing Systems

### Singletons Pattern (api/singletons.py)

```python
from api.utils.rate_limiter import RateLimiter
from api.utils.security_storage import SecurityEventStore
from api.models.institute_security import InstituteSecurityEngine
from api.models.session_monitor import SessionMonitor  # NEW
from api.models.behavioral_scorer import BehavioralScorer  # NEW

# Existing singletons
rate_limiter = RateLimiter()
security_engine = InstituteSecurityEngine()
event_store = SecurityEventStore()

# NEW: Session tracking singletons
session_monitor = SessionMonitor(storage=event_store)
behavioral_scorer = BehavioralScorer()
```

### Middleware Integration (api/main.py)

```python
from api.singletons import (
    rate_limiter,
    security_engine,
    event_store,
    session_monitor,      # NEW
    behavioral_scorer     # NEW
)

# Existing middleware unchanged
# Session tracking called from routes, not middleware
```

---

## Testing Strategy

### Unit Tests (Session 4)

1. **SessionMonitor Tests**
   - Session creation
   - Session retrieval (cache hit/miss)
   - Transaction recording
   - Session update
   - Session termination
   - Query operations
   - Cleanup operations

2. **BehavioralScorer Tests**
   - Normal session scoring
   - Attack session scoring
   - Individual signal tests
   - Risk level classification
   - Custom threshold tests
   - Edge cases (missing data)

3. **Integration Tests**
   - Full lifecycle test
   - Database persistence
   - Cache behavior
   - Error handling
   - Concurrent access

---

## Future Enhancements (Post-MVP)

### Phase 1: User Profiles
- Per-user baselines in database
- Learn from user history
- Dynamic threshold adjustment

### Phase 2: ML-Enhanced Scoring
- Train ML model on session data
- Replace rule-based signals with ML
- Ensemble with fraud detection model

### Phase 3: Real-Time Streaming
- Kafka/RabbitMQ integration
- Stream session events
- Real-time analytics dashboard

### Phase 4: Advanced Analytics
- Session clustering
- Behavior pattern discovery
- Anomaly visualization
- Temporal analysis

---

## Summary

**Session 2 delivers:**
- ✅ Core session monitoring (SessionMonitor)
- ✅ Behavioral risk scoring (BehavioralScorer)
- ✅ 5-signal anomaly detection
- ✅ Database integration via SecurityEventStore
- ✅ In-memory caching for performance
- ✅ Non-blocking, graceful degradation
- ✅ Comprehensive documentation

**Ready for Session 3:**
- API endpoint creation (`/v1/sessions/*`)
- Integration with `/v1/decision`
- Frontend UI components
- End-to-end testing

---

**Document Version:** 1.0  
**Date:** 2025-11-15  
**Status:** Architecture Complete
