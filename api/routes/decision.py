"""
Decision endpoint for fraud detection.

Handles incoming transaction requests and returns fraud decisions.
"""

import time
import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Request as FastAPIRequest
from pydantic import BaseModel, Field, model_validator

from api.models.rules import RulesEngine, RuleAction
from api.models.ml_engine import MLEngine
from api.models.policy import PolicyEngine
from api.constants import DecisionCode
from api.models.session_monitor import SessionMonitor
from api.models.behavioral_scorer import BehavioralScorer
from api.utils.security_storage import SecurityEventStore

router = APIRouter()
logger = logging.getLogger(__name__)

# Initialize engines (singleton instances)
rules_engine = RulesEngine()
ml_engine = MLEngine()
policy_engine = PolicyEngine()

# Session monitoring components (initialized on first use)
_session_monitor: Optional[SessionMonitor] = None
_behavioral_scorer: Optional[BehavioralScorer] = None

def get_session_monitor() -> SessionMonitor:
    """Get or create SessionMonitor singleton"""
    global _session_monitor
    if _session_monitor is None:
        _session_monitor = SessionMonitor(storage=SecurityEventStore())
    return _session_monitor

def get_behavioral_scorer() -> BehavioralScorer:
    """Get or create BehavioralScorer singleton"""
    global _behavioral_scorer
    if _behavioral_scorer is None:
        _behavioral_scorer = BehavioralScorer()
    return _behavioral_scorer


class Location(BaseModel):
    """Geographic location"""

    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    country: Optional[str] = None
    city: Optional[str] = None


class TransactionRequest(BaseModel):
    """Incoming transaction request"""

    user_id: str = Field(..., min_length=1, max_length=100)
    device_id: str = Field(..., min_length=1, max_length=100)
    amount: float = Field(..., gt=0)
    timestamp: str = Field(..., description="ISO 8601 timestamp")
    location: str

    # Optional fields
    merchant_id: Optional[str] = None
    ip_address: Optional[str] = None
    card_last4: Optional[str] = None
    transaction_type: Optional[str] = "purchase"
    
    # Session monitoring fields (optional, backward compatible)
    session_id: Optional[str] = None
    is_new_beneficiary: Optional[bool] = False
    session_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class DecisionResponse(BaseModel):
    """Fraud decision response"""

    decision_code: int = Field(
        ..., ge=0, le=4, description="0=Allow, 1=Monitor, 2=Step-up, 3=Review, 4=Block"
    )
    score: float = Field(..., ge=0, le=1, description="Fraud probability")
    reasons: List[str] = Field(..., description="Explanation for decision")
    latency_ms: float = Field(..., description="Total processing time")

    # Additional metadata
    rule_flags: List[str] = Field(default_factory=list)
    ml_score: Optional[float] = None
    top_features: Optional[List[Dict[str, Any]]] = None
    
    # Session risk info (optional, backward compatible)
    session_risk: Optional[Dict[str, Any]] = None

    # Backward compatibility aliases for playground
    decision: Optional[int] = Field(None, description="Alias for decision_code")
    fraud_score: Optional[float] = Field(None, description="Alias for score")

    @model_validator(mode='after')
    def set_aliases(self):
        """Automatically set backward compatibility aliases"""
        if self.decision is None:
            self.decision = self.decision_code
        if self.fraud_score is None:
            self.fraud_score = self.score
        return self


def check_session_behavior(request: TransactionRequest) -> Dict[str, Any]:
    """
    Check session behavioral risk for the given transaction request.
    
    Uses SessionMonitor + BehavioralScorer to detect anomalies.
    Must NOT raise exceptions; on failure, logs and returns error dict.
    
    Args:
        request: Transaction request with session_id
        
    Returns:
        Dict containing session risk info or error details
    """
    try:
        session_monitor = get_session_monitor()
        behavioral_scorer = get_behavioral_scorer()
        
        # Get or create session
        session = session_monitor.get_session(request.session_id)
        if not session:
            session = session_monitor.create_session(
                session_id=request.session_id,
                account_id=request.user_id,
                user_id=request.user_id
            )
        
        # Record transaction event
        session_monitor.record_transaction(
            session_id=request.session_id,
            transaction_amount=request.amount,
            new_beneficiary=request.is_new_beneficiary,
            transaction_data={
                "amount": request.amount,
                "timestamp": request.timestamp,
                "is_new_beneficiary": request.is_new_beneficiary,
                "location": request.location,
                "device_id": request.device_id,
                "merchant_id": request.merchant_id,
            }
        )
        
        # Refresh session after recording transaction
        session = session_monitor.get_session(request.session_id)
        
        # Calculate risk score
        transaction_data = {
            "amount": request.amount,
            "is_new_beneficiary": request.is_new_beneficiary,
            "timestamp": request.timestamp,
        }
        risk = behavioral_scorer.calculate_risk(session, transaction_data)
        
        # Update session with risk score
        session.risk_score = risk.score
        session.anomalies_detected = len(risk.anomalies)
        session_monitor.update_session(session)
        
        # Check for termination threshold (configurable, default 80)
        termination_threshold = 80.0
        if risk.score >= termination_threshold and not session.is_terminated:
            session_monitor.terminate_session(
                session_id=request.session_id,
                reason=f"Critical risk score: {risk.score:.1f}"
            )
            session = session_monitor.get_session(request.session_id)
        
        # Build response
        return {
            "session_id": session.session_id,
            "risk_score": risk.score,
            "risk_level": risk.details.get("risk_level", "UNKNOWN"),
            "anomalies_detected": len(risk.anomalies),
            "signals_triggered": risk.signals_triggered,
            "anomalies": risk.anomalies,
            "is_terminated": session.is_terminated,
            "termination_reason": session.termination_reason,
            "transaction_count": session.transaction_count,
            "total_amount": session.total_amount,
        }
        
    except Exception as e:
        logger.warning(f"Session behavior check failed: {e}", exc_info=True)
        return {
            "error": "session_check_failed",
            "details": str(e),
        }


@router.post("/decision", response_model=DecisionResponse)
async def make_decision(raw_request: FastAPIRequest, request: TransactionRequest) -> DecisionResponse:
    """
    Evaluate a transaction for fraud.

    Pipeline: Rules Engine -> ML Engine -> Policy Engine -> Decision
    Optional: Session Behavior Monitoring (if session_id provided)

    Returns decision with explanation and latency metrics.
    """
    start_time = time.time()

    try:
        # Stage 1: Rules Engine
        rules_result = rules_engine.evaluate(request.model_dump())

        # If blocked by rules, return immediately
        if rules_result.action == RuleAction.BLOCK:
            latency_ms = (time.time() - start_time) * 1000
            return DecisionResponse(
                decision_code=DecisionCode.BLOCK,
                score=1.0,  # High fraud score
                reasons=rules_result.reasons,
                latency_ms=round(latency_ms, 2),
                rule_flags=rules_result.reasons,
                ml_score=None,  # ML not evaluated
                top_features=None,
            )

        # Stage 2: ML Engine (only if not blocked by rules)
        ml_result = ml_engine.predict(request.model_dump())

        # Stage 3: Policy Engine (combine results)
        # Convert RuleResult to dict format for policy engine
        rules_dict = {
            "action": rules_result.action.value,
            "flags": rules_result.reasons,
            "blocked": False,
        }
        decision = policy_engine.decide(rules_dict, ml_result)

        # Stage 4 (Optional): Session Behavior Check
        session_risk_info = None
        if request.session_id:
            session_risk_info = check_session_behavior(request)
            
            # If session is terminated, override decision to BLOCK
            if session_risk_info.get("is_terminated"):
                decision["decision_code"] = DecisionCode.BLOCK
                decision["score"] = 1.0
                termination_reason = session_risk_info.get("termination_reason", "Session terminated")
                decision["reasons"] = [f"Session terminated: {termination_reason}"] + decision.get("reasons", [])

        # Calculate latency
        latency_ms = (time.time() - start_time) * 1000

        # Build and return response (aliases set automatically by model validator)
        return DecisionResponse(
            decision_code=decision["decision_code"],
            score=decision["score"],
            reasons=decision["reasons"],
            latency_ms=round(latency_ms, 2),
            rule_flags=rules_result.reasons,
            ml_score=ml_result.get("score"),
            top_features=ml_result.get("top_features", []),
            session_risk=session_risk_info,
        )

    except Exception as e:
        # Log error and return safe default (block transaction)
        raise HTTPException(
            status_code=500, detail=f"Decision pipeline failed: {str(e)}"
        )


@router.get("/decision/health")
async def decision_health():
    """Check health of decision pipeline"""
    return {
        "status": "healthy",
        "engines": {"rules": "ready", "ml": "ready", "policy": "ready"},
    }
