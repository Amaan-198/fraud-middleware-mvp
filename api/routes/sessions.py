"""
Session API Endpoints

Provides API access to session monitoring data and operations:
- View active sessions
- Get session details and risk scores
- Terminate sessions
- Query suspicious sessions
"""

import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.models.session_monitor import SessionMonitor
from api.models.behavioral_scorer import BehavioralScorer
from api.utils.security_storage import SecurityEventStore

router = APIRouter()
logger = logging.getLogger(__name__)

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


# Request/Response Models

class TerminateSessionRequest(BaseModel):
    """Request to terminate a session"""
    termination_reason: str = Field(..., min_length=1, max_length=500)


class SessionSummary(BaseModel):
    """Summary info for a session"""
    session_id: str
    account_id: str
    transaction_count: int
    total_amount: float
    risk_score: float
    is_terminated: bool
    anomalies_count: int  # Changed from anomalies_detected
    login_time: int
    last_activity_time: int


class SessionDetail(BaseModel):
    """Full session details"""
    session_id: str
    account_id: str
    user_id: Optional[str]
    transaction_count: int
    total_amount: float
    beneficiaries_added: int
    risk_score: float
    anomalies_count: int  # Changed from anomalies_detected
    is_terminated: bool
    termination_reason: Optional[str]
    login_time: int
    last_activity_time: int
    created_at: int
    updated_at: int


class SessionRiskInfo(BaseModel):
    """Risk-focused session info"""
    session_id: str
    risk_score: float
    risk_level: str
    anomalies_detected: int
    signals_triggered: List[str]
    anomalies: List[str]
    is_terminated: bool
    explanation: Optional[str] = None


# API Endpoints

@router.get("/sessions/active", response_model=List[SessionSummary])
async def get_active_sessions(limit: int = 100):
    """
    Get list of active sessions.
    
    Returns summary info for all non-terminated sessions.
    """
    try:
        session_monitor = get_session_monitor()
        sessions = session_monitor.get_active_sessions(limit=limit)
        
        return [
            SessionSummary(
                session_id=s.session_id,
                account_id=s.account_id,
                transaction_count=s.transaction_count,
                total_amount=s.total_amount,
                risk_score=s.risk_score,
                is_terminated=s.is_terminated,
                anomalies_count=len(s.anomalies_detected) if isinstance(s.anomalies_detected, list) else 0,
                login_time=s.login_time,
                last_activity_time=s.last_activity_time,
            )
            for s in sessions
        ]
    except Exception as e:
        logger.error(f"Failed to get active sessions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}", response_model=SessionDetail)
async def get_session(session_id: str):
    """
    Get full details for a specific session.
    """
    try:
        session_monitor = get_session_monitor()
        session = session_monitor.get_session(session_id)
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return SessionDetail(
            session_id=session.session_id,
            account_id=session.account_id,
            user_id=session.user_id,
            transaction_count=session.transaction_count,
            total_amount=session.total_amount,
            beneficiaries_added=session.beneficiaries_added,
            risk_score=session.risk_score,
            anomalies_count=len(session.anomalies_detected) if isinstance(session.anomalies_detected, list) else 0,
            is_terminated=session.is_terminated,
            termination_reason=session.termination_reason,
            login_time=session.login_time,
            last_activity_time=session.last_activity_time,
            created_at=session.created_at,
            updated_at=session.updated_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get session {session_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}/risk", response_model=SessionRiskInfo)
async def get_session_risk(session_id: str):
    """
    Get risk-focused information for a session.
    
    Includes current risk score, signals triggered, and anomaly details.
    """
    try:
        session_monitor = get_session_monitor()
        behavioral_scorer = get_behavioral_scorer()
        
        session = session_monitor.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Calculate current risk
        risk = behavioral_scorer.calculate_risk(session, transaction_data={})
        
        # Get explanation
        explanation = behavioral_scorer.get_risk_explanation(session)
        
        return SessionRiskInfo(
            session_id=session.session_id,
            risk_score=risk.score,
            risk_level=risk.details.get("risk_level", "UNKNOWN"),
            anomalies_detected=len(risk.anomalies),
            signals_triggered=risk.signals_triggered,
            anomalies=risk.anomalies,
            is_terminated=session.is_terminated,
            explanation=explanation,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get session risk {session_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sessions/{session_id}/terminate", response_model=SessionDetail)
async def terminate_session(session_id: str, request: TerminateSessionRequest):
    """
    Terminate a session.
    
    Marks the session as terminated with the provided reason.
    """
    try:
        session_monitor = get_session_monitor()
        
        # Check if session exists
        session = session_monitor.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Terminate session
        session_monitor.terminate_session(session_id, request.termination_reason)
        
        # Get updated session
        session = session_monitor.get_session(session_id)
        
        return SessionDetail(
            session_id=session.session_id,
            account_id=session.account_id,
            user_id=session.user_id,
            transaction_count=session.transaction_count,
            total_amount=session.total_amount,
            beneficiaries_added=session.beneficiaries_added,
            risk_score=session.risk_score,
            anomalies_count=len(session.anomalies_detected) if isinstance(session.anomalies_detected, list) else 0,
            is_terminated=session.is_terminated,
            termination_reason=session.termination_reason,
            login_time=session.login_time,
            last_activity_time=session.last_activity_time,
            created_at=session.created_at,
            updated_at=session.updated_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to terminate session {session_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/suspicious", response_model=List[SessionSummary])
async def get_suspicious_sessions(min_risk_score: float = 60.0, limit: int = 100):
    """
    Get list of suspicious sessions.
    
    Returns sessions with high risk scores or terminated status.
    """
    try:
        session_monitor = get_session_monitor()
        
        # Get active sessions and filter by risk
        sessions = session_monitor.get_active_sessions(limit=limit * 2)  # Get more to filter
        
        # Filter for suspicious sessions
        suspicious = [
            s for s in sessions
            if s.risk_score >= min_risk_score or s.is_terminated
        ][:limit]
        
        return [
            SessionSummary(
                session_id=s.session_id,
                account_id=s.account_id,
                transaction_count=s.transaction_count,
                total_amount=s.total_amount,
                risk_score=s.risk_score,
                is_terminated=s.is_terminated,
                anomalies_count=len(s.anomalies_detected) if isinstance(s.anomalies_detected, list) else 0,
                login_time=s.login_time,
                last_activity_time=s.last_activity_time,
            )
            for s in suspicious
        ]
    except Exception as e:
        logger.error(f"Failed to get suspicious sessions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/health")
async def sessions_health():
    """Check health of session monitoring system"""
    try:
        session_monitor = get_session_monitor()
        behavioral_scorer = get_behavioral_scorer()
        
        # Try to get active sessions count
        sessions = session_monitor.get_active_sessions(limit=1)
        
        return {
            "status": "healthy",
            "components": {
                "session_monitor": "ready",
                "behavioral_scorer": "ready",
            },
            "active_sessions_available": len(sessions) > 0,
        }
    except Exception as e:
        logger.error(f"Session health check failed: {e}", exc_info=True)
        return {
            "status": "degraded",
            "error": str(e),
        }
