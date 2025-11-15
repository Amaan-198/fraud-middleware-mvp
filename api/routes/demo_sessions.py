"""
Demo Session Scenarios

Simulates normal vs attack sessions using the real /v1/decision pipeline.

**FOR DEMO ONLY** - Not for production use.

Uses:
- /v1/decision endpoint (real fraud detection)
- SessionMonitor (real session tracking)
- BehavioralScorer (real risk calculation)
"""

import asyncio
import logging
import time
import random
from typing import Dict, Any, List
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import httpx

router = APIRouter()
logger = logging.getLogger(__name__)

# Configuration
API_BASE_URL = "http://localhost:8000"
DECISION_ENDPOINT = f"{API_BASE_URL}/v1/decision"


class SessionScenarioRequest(BaseModel):
    """Request to run a session scenario"""
    type: str = Field(..., pattern="^(normal|attack)$", description="normal or attack")


class SessionScenarioResponse(BaseModel):
    """Response from running a session scenario"""
    session_id: str
    type: str
    transactions_sent: int
    final_risk_score: float
    is_terminated: bool
    duration_seconds: float


class SessionComparisonResponse(BaseModel):
    """Response from running both scenarios"""
    normal_session_id: str
    attack_session_id: str
    comparison: Dict[str, Any]


class SessionScenarios:
    """
    Helper class to generate and run session scenarios.
    
    Simulates realistic user behavior for demo purposes.
    """
    
    @staticmethod
    def generate_session_id(scenario_type: str) -> str:
        """Generate a unique session ID"""
        timestamp = int(time.time())
        random_suffix = random.randint(1000, 9999)
        return f"demo_{scenario_type}_{timestamp}_{random_suffix}"
    
    @staticmethod
    async def generate_normal_user_session() -> List[Dict[str, Any]]:
        """
        Generate a normal user session.
        
        Characteristics:
        - Business hours (9 AM - 6 PM simulation)
        - 2-3 transactions
        - 45-60 second delays between actions
        - Small amounts (1000-3000 INR)
        - Existing beneficiaries (is_new_beneficiary=False)
        
        Returns:
            List of transaction payloads
        """
        transactions = []
        base_time = datetime.now(timezone.utc)
        
        # Simulate business hours by setting a daytime timestamp
        business_hour = 14  # 2 PM
        base_time = base_time.replace(hour=business_hour, minute=0, second=0)
        
        num_transactions = random.randint(2, 3)
        
        for i in range(num_transactions):
            # Delay between transactions (45-60 seconds)
            if i > 0:
                await asyncio.sleep(2)  # Speed up for demo (2s instead of 45s)
            
            transactions.append({
                "user_id": "demo_user_normal",
                "device_id": "device_normal_123",
                "amount": round(random.uniform(1000, 3000), 2),
                "timestamp": base_time.isoformat(),
                "location": "19.0760,72.8777",  # Mumbai
                "merchant_id": f"merchant_{random.randint(100, 200)}",
                "ip_address": "203.192.10.50",
                "transaction_type": "transfer",
                "is_new_beneficiary": False,  # Existing beneficiary
            })
        
        return transactions
    
    @staticmethod
    async def generate_attack_session() -> List[Dict[str, Any]]:
        """
        Generate an account takeover attack session.
        
        Characteristics:
        - Off-hours (2:30 AM simulation)
        - 8-10 rapid transactions
        - 2-5 second delays (very rapid)
        - Large amounts (50,000-100,000 INR)
        - Multiple new beneficiaries
        
        Returns:
            List of transaction payloads
        """
        transactions = []
        base_time = datetime.now(timezone.utc)
        
        # Simulate off-hours
        off_hour = 2  # 2:30 AM
        base_time = base_time.replace(hour=off_hour, minute=30, second=0)
        
        num_transactions = random.randint(8, 10)
        
        for i in range(num_transactions):
            # Very short delay between transactions (2-5 seconds)
            if i > 0:
                await asyncio.sleep(random.uniform(0.5, 1.5))  # Speed up for demo
            
            transactions.append({
                "user_id": "demo_user_attack",
                "device_id": "device_attack_999",
                "amount": round(random.uniform(50000, 100000), 2),
                "timestamp": base_time.isoformat(),
                "location": "51.5074,-0.1278",  # London (unusual location)
                "merchant_id": f"merchant_{random.randint(500, 600)}",
                "ip_address": "185.220.101.50",  # Suspicious IP
                "transaction_type": "transfer",
                "is_new_beneficiary": i % 2 == 0,  # Half are new beneficiaries
            })
        
        return transactions
    
    @staticmethod
    async def run_scenario_simulation(scenario_type: str) -> Dict[str, Any]:
        """
        Run a full scenario simulation by calling real /v1/decision endpoint.
        
        Args:
            scenario_type: "normal" or "attack"
            
        Returns:
            Dict with session_id, type, and results
        """
        start_time = time.time()
        session_id = SessionScenarios.generate_session_id(scenario_type)
        
        # Generate transactions
        if scenario_type == "normal":
            transactions = await SessionScenarios.generate_normal_user_session()
        else:
            transactions = await SessionScenarios.generate_attack_session()
        
        # Send transactions to real API
        results = []
        final_risk_score = 0.0
        is_terminated = False
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            for i, txn in enumerate(transactions):
                # Add session_id to transaction
                txn["session_id"] = session_id
                
                try:
                    response = await client.post(DECISION_ENDPOINT, json=txn)
                    response.raise_for_status()
                    result = response.json()
                    
                    # Extract session risk info
                    session_risk = result.get("session_risk")
                    if session_risk:
                        final_risk_score = session_risk.get("risk_score", 0.0)
                        is_terminated = session_risk.get("is_terminated", False)
                        
                        logger.info(
                            f"{scenario_type} session {session_id} - "
                            f"Transaction {i+1}: risk={final_risk_score:.1f}, "
                            f"terminated={is_terminated}"
                        )
                    
                    results.append(result)
                    
                    # If session is terminated, stop sending more transactions
                    if is_terminated:
                        logger.info(f"Session {session_id} terminated, stopping simulation")
                        break
                        
                except Exception as e:
                    logger.error(f"Transaction {i+1} failed: {e}")
                    break
        
        duration = time.time() - start_time
        
        return {
            "session_id": session_id,
            "type": scenario_type,
            "transactions_sent": len(results),
            "transactions_planned": len(transactions),
            "final_risk_score": final_risk_score,
            "is_terminated": is_terminated,
            "duration_seconds": round(duration, 2),
            "results": results,
        }


# API Endpoints

@router.post("/demo/session-scenario", response_model=SessionScenarioResponse)
async def run_session_scenario(request: SessionScenarioRequest):
    """
    Run a single session scenario (normal or attack).
    
    **DEMO ONLY** - Simulates user behavior for demonstration purposes.
    
    Args:
        request: Scenario type (normal or attack)
        
    Returns:
        Session ID and results
    """
    try:
        result = await SessionScenarios.run_scenario_simulation(request.type)
        
        return SessionScenarioResponse(
            session_id=result["session_id"],
            type=result["type"],
            transactions_sent=result["transactions_sent"],
            final_risk_score=result["final_risk_score"],
            is_terminated=result["is_terminated"],
            duration_seconds=result["duration_seconds"],
        )
    except Exception as e:
        logger.error(f"Failed to run {request.type} scenario: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/demo/session-comparison", response_model=SessionComparisonResponse)
async def run_session_comparison():
    """
    Run both normal and attack scenarios for comparison.
    
    **DEMO ONLY** - Demonstrates the difference between normal and attack sessions.
    
    Runs:
    1. Normal user session (2-3 transactions, business hours, small amounts)
    2. Attack session (8-10 rapid transactions, off-hours, large amounts)
    
    Returns:
        Both session IDs and comparison data
    """
    try:
        # Run both scenarios in parallel for speed
        normal_task = SessionScenarios.run_scenario_simulation("normal")
        attack_task = SessionScenarios.run_scenario_simulation("attack")
        
        normal_result, attack_result = await asyncio.gather(normal_task, attack_task)
        
        # Build comparison
        comparison = {
            "normal": {
                "session_id": normal_result["session_id"],
                "transactions_sent": normal_result["transactions_sent"],
                "final_risk_score": normal_result["final_risk_score"],
                "is_terminated": normal_result["is_terminated"],
                "duration_seconds": normal_result["duration_seconds"],
            },
            "attack": {
                "session_id": attack_result["session_id"],
                "transactions_sent": attack_result["transactions_sent"],
                "final_risk_score": attack_result["final_risk_score"],
                "is_terminated": attack_result["is_terminated"],
                "duration_seconds": attack_result["duration_seconds"],
            },
            "difference": {
                "risk_score_delta": attack_result["final_risk_score"] - normal_result["final_risk_score"],
                "attack_detected": attack_result["is_terminated"],
                "normal_not_blocked": not normal_result["is_terminated"],
            }
        }
        
        return SessionComparisonResponse(
            normal_session_id=normal_result["session_id"],
            attack_session_id=attack_result["session_id"],
            comparison=comparison,
        )
    except Exception as e:
        logger.error(f"Failed to run comparison: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/demo/health")
async def demo_health():
    """Check health of demo endpoints"""
    return {
        "status": "healthy",
        "endpoints": {
            "session_scenario": "ready",
            "session_comparison": "ready",
        },
        "note": "Demo endpoints call real /v1/decision API",
    }
