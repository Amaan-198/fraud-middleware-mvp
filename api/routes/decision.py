"""
Decision endpoint for fraud detection.

Handles incoming transaction requests and returns fraud decisions.
"""

import time
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.models.rules import RulesEngine, RuleAction
from api.models.ml_engine import MLEngine
from api.models.policy import PolicyEngine

router = APIRouter()

# Initialize engines (singleton instances)
rules_engine = RulesEngine()
ml_engine = MLEngine()
policy_engine = PolicyEngine()


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
    location: Location

    # Optional fields
    merchant_id: Optional[str] = None
    card_last4: Optional[str] = None
    transaction_type: Optional[str] = "purchase"


class DecisionResponse(BaseModel):
    """Fraud decision response"""
    decision_code: int = Field(..., ge=0, le=4, description="0=Allow, 1=Monitor, 2=Step-up, 3=Review, 4=Block")
    score: float = Field(..., ge=0, le=1, description="Fraud probability")
    reasons: List[str] = Field(..., description="Explanation for decision")
    latency_ms: float = Field(..., description="Total processing time")

    # Additional metadata
    rule_flags: List[str] = Field(default_factory=list)
    ml_score: Optional[float] = None
    top_features: Optional[List[Dict[str, Any]]] = None


@router.post("/decision", response_model=DecisionResponse)
async def make_decision(request: TransactionRequest) -> DecisionResponse:
    """
    Evaluate a transaction for fraud.

    Pipeline: Rules Engine -> ML Engine -> Policy Engine -> Decision

    Returns decision with explanation and latency metrics.
    """
    start_time = time.time()

    try:
        # Stage 1: Rules Engine
        rules_result = rules_engine.evaluate(request.model_dump())

        # If blocked by rules, return immediately with decision_code=4
        if rules_result.action == RuleAction.BLOCK:
            latency_ms = (time.time() - start_time) * 1000
            return DecisionResponse(
                decision_code=4,  # Block
                score=1.0,  # High fraud score
                reasons=rules_result.reasons,
                latency_ms=round(latency_ms, 2),
                rule_flags=rules_result.reasons,
                ml_score=None,  # ML not evaluated
                top_features=None
            )

        # Stage 2: ML Engine (only if not blocked by rules)
        ml_result = ml_engine.predict(request.model_dump())

        # Stage 3: Policy Engine (combine results)
        # Convert RuleResult to dict format for policy engine
        rules_dict = {
            "action": rules_result.action.value,
            "flags": rules_result.reasons,
            "blocked": False
        }
        decision = policy_engine.decide(rules_dict, ml_result)

        # Calculate latency
        latency_ms = (time.time() - start_time) * 1000

        # Build response
        response = DecisionResponse(
            decision_code=decision["decision_code"],
            score=decision["score"],
            reasons=decision["reasons"],
            latency_ms=round(latency_ms, 2),
            rule_flags=rules_result.reasons,
            ml_score=ml_result.get("score"),
            top_features=ml_result.get("top_features", [])
        )

        return response

    except Exception as e:
        # Log error and return safe default (block transaction)
        raise HTTPException(
            status_code=500,
            detail=f"Decision pipeline failed: {str(e)}"
        )


@router.get("/decision/health")
async def decision_health():
    """Check health of decision pipeline"""
    return {
        "status": "healthy",
        "engines": {
            "rules": "ready",
            "ml": "ready",
            "policy": "ready"
        }
    }
