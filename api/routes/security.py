"""
Security Operations Center (SOC) API Endpoints

Provides tools for security analysts to:
- Monitor security events and alerts
- Review flagged incidents
- Manage blocked sources
- Access audit trails
- View security dashboards

Designed for integration with SIEM systems and analyst workflows.
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query, Header
from pydantic import BaseModel, Field

from api.models.institute_security import (
    SecurityEvent,
    ThreatLevel,
    ThreatType
)
from api.utils.rate_limiter import RateLimitTier
from api.utils.errors import not_found_error, bad_request_error, internal_error

# Import shared singleton instances (CRITICAL: must use same instances as middleware!)
from api.singletons import security_engine, event_store, rate_limiter


router = APIRouter()


# Request/Response Models

class ReviewRequest(BaseModel):
    """Request to review a security event"""
    event_id: str = Field(..., description="Event ID to review")
    analyst_id: str = Field(..., description="Analyst performing review")
    notes: Optional[str] = Field(None, description="Review notes")
    action: Optional[str] = Field(None, description="Action taken (investigate, dismiss, escalate)")


class UnblockRequest(BaseModel):
    """Request to unblock a source"""
    source_id: str = Field(..., description="Source to unblock")
    analyst_id: str = Field(..., description="Analyst performing unblock")
    reason: Optional[str] = Field(None, description="Reason for unblocking")


class EventResponse(BaseModel):
    """Security event response"""
    event_id: str
    timestamp: str
    threat_type: str
    threat_level: int
    source_identifier: str
    description: str
    metadata: Dict[str, Any]
    requires_review: bool


class ReviewQueueResponse(BaseModel):
    """Review queue response"""
    total_pending: int
    events: List[Dict[str, Any]]


class SourceRiskResponse(BaseModel):
    """Source risk profile response"""
    source_id: str
    risk_score: int
    is_blocked: bool
    recent_events: int
    threat_breakdown: Dict[str, int]
    highest_threat_level: int


class SecurityDashboardResponse(BaseModel):
    """Security dashboard statistics"""
    total_events: int
    pending_reviews: int
    blocked_sources: int
    threat_level_distribution: Dict[str, int]
    threat_type_distribution: Dict[str, int]
    recent_events: List[Dict[str, Any]]


# Endpoints

@router.get("/events", response_model=List[Dict[str, Any]])
async def get_security_events(
    limit: int = Query(100, ge=1, le=1000, description="Maximum events to return"),
    min_threat_level: int = Query(0, ge=0, le=4, description="Minimum threat level"),
    threat_type: Optional[str] = Query(None, description="Filter by threat type"),
    source_id: Optional[str] = Query(None, description="Filter by source"),
):
    """
    Retrieve security events with optional filters.

    Useful for:
    - Security monitoring dashboards
    - Incident investigation
    - Compliance reporting
    """
    try:
        # Get from database for persistence
        events = event_store.get_events(
            limit=limit,
            min_threat_level=min_threat_level,
            threat_type=threat_type,
            source_id=source_id
        )

        return events

    except Exception as e:
        raise internal_error("retrieve events", e)


@router.get("/events/review-queue", response_model=ReviewQueueResponse)
async def get_review_queue(
    limit: int = Query(10000, ge=1, le=50000, description="Maximum events to return")
):
    """
    Get events flagged for SOC analyst review.

    Returns unreviewed high-priority security events that need
    human analysis and decision-making.
    """
    try:
        pending_events = event_store.get_review_queue(limit=limit)

        return ReviewQueueResponse(
            total_pending=len(pending_events),
            events=pending_events
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve review queue: {str(e)}"
        )


@router.post("/events/{event_id}/review")
async def review_event(event_id: str, review: ReviewRequest):
    """
    Mark a security event as reviewed by an analyst.

    Workflow:
    1. Analyst reviews event details
    2. Takes appropriate action (investigate, dismiss, escalate)
    3. Logs review with notes for audit trail
    """
    try:
        success = event_store.mark_reviewed(
            event_id=event_id,
            reviewed_by=review.analyst_id,
            notes=review.notes
        )

        if not success:
            raise not_found_error("event", event_id)

        # Log audit event
        event_store.log_audit_event(
            source_id=review.analyst_id,
            action="review_security_event",
            resource=f"event:{event_id}",
            success=True,
            metadata={
                "action": review.action,
                "notes": review.notes
            }
        )

        return {
            "success": True,
            "event_id": event_id,
            "reviewed_by": review.analyst_id,
            "message": "Event marked as reviewed"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise internal_error("review event", e)


@router.post("/events/review-queue/clear")
async def clear_review_queue(analyst_id: str = Query(..., description="Analyst ID performing bulk clear")):
    """
    Clear all pending reviews (mark all as reviewed).
    
    Bulk operation to mark all unreviewed events as reviewed.
    Useful for clearing backlogs from testing or known false positives.
    
    WARNING: This marks ALL pending reviews as dismissed.
    Use with caution in production environments.
    """
    try:
        # Get count of pending reviews before clearing
        pending_events = event_store.get_review_queue(limit=10000)
        count_before = len(pending_events)
        
        # Clear all pending reviews
        cleared_count = event_store.clear_all_reviews(
            reviewed_by=analyst_id,
            notes="Bulk cleared via SOC Workspace"
        )
        
        # Log audit event
        event_store.log_audit_event(
            source_id=analyst_id,
            action="bulk_clear_review_queue",
            resource="review_queue",
            success=True,
            metadata={
                "cleared_count": cleared_count,
                "reason": "Bulk clear operation"
            }
        )
        
        return {
            "success": True,
            "cleared_count": cleared_count,
            "analyst_id": analyst_id,
            "message": f"Cleared {cleared_count} pending review(s)"
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to clear review queue: {str(e)}"
        )


@router.get("/sources/{source_id}/risk", response_model=SourceRiskResponse)
async def get_source_risk_profile(source_id: str):
    """
    Get comprehensive risk profile for a source.

    Provides:
    - Risk score (0-100)
    - Block status
    - Recent security events
    - Threat type breakdown
    - Historical patterns
    """
    try:
        profile = security_engine.get_source_risk_profile(source_id)

        return SourceRiskResponse(
            source_id=profile["source_id"],
            risk_score=profile["risk_score"],
            is_blocked=profile["is_blocked"],
            recent_events=profile["recent_events"],
            threat_breakdown=profile["threat_breakdown"],
            highest_threat_level=profile["highest_threat_level"]
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve risk profile: {str(e)}"
        )


@router.get("/sources/blocked", response_model=List[Dict[str, Any]])
async def get_blocked_sources():
    """
    Get list of currently blocked sources.

    Returns all sources blocked due to security violations,
    including reason and timestamp.
    """
    try:
        # Query from storage
        with event_store._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT source_id, blocked_at, reason, threat_level, auto_blocked
                FROM blocked_sources
                WHERE unblocked = 0
                ORDER BY blocked_at DESC
            """)

            blocked = [dict(row) for row in cursor.fetchall()]

        return blocked

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve blocked sources: {str(e)}"
        )


@router.post("/sources/{source_id}/unblock")
async def unblock_source(source_id: str, request: UnblockRequest):
    """
    Unblock a previously blocked source.

    Requires analyst approval. Logs action for audit trail.
    """
    try:
        # Unblock in storage
        success = event_store.unblock_source(
            source_id=source_id,
            unblocked_by=request.analyst_id
        )

        if not success:
            raise not_found_error("blocked source", source_id)

        # Unblock in security engine and rate limiter
        security_engine.unblock_source(source_id)
        rate_limiter.unblock_source(source_id)

        # Log audit event
        event_store.log_audit_event(
            source_id=request.analyst_id,
            action="unblock_source",
            resource=f"source:{source_id}",
            success=True,
            metadata={"reason": request.reason}
        )

        return {
            "success": True,
            "source_id": source_id,
            "unblocked_by": request.analyst_id,
            "message": "Source successfully unblocked"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to unblock source: {str(e)}"
        )


@router.get("/audit-trail", response_model=List[Dict[str, Any]])
async def get_audit_trail(
    source_id: Optional[str] = Query(None, description="Filter by source"),
    resource: Optional[str] = Query(None, description="Filter by resource"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum entries")
):
    """
    Get audit trail for compliance and investigation.

    Provides complete log of:
    - Who accessed what
    - When actions occurred
    - Success/failure status
    - Additional context

    Critical for compliance (GDPR, PCI-DSS, DPDP).
    """
    try:
        logs = event_store.get_audit_trail(
            source_id=source_id,
            resource=resource,
            limit=limit
        )

        return logs

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve audit trail: {str(e)}"
        )


@router.get("/dashboard", response_model=SecurityDashboardResponse)
async def get_security_dashboard():
    """
    Get comprehensive security dashboard data.

    Provides overview for SOC analysts:
    - Total events by severity
    - Pending review count
    - Blocked sources
    - Recent high-priority events
    - Threat distribution
    """
    try:
        # Get statistics from both engine and storage
        engine_stats = security_engine.get_statistics()
        storage_stats = event_store.get_statistics()

        # Get recent high-priority events
        recent_events = event_store.get_events(
            limit=20,
            min_threat_level=ThreatLevel.MEDIUM.value
        )

        # Combine stats
        threat_level_dist = {
            str(k): v for k, v in storage_stats["threat_level_distribution"].items()
        }

        threat_type_dist = {
            k: v for k, v in storage_stats["threat_type_distribution"].items()
        }

        return SecurityDashboardResponse(
            total_events=storage_stats["total_events"],
            pending_reviews=storage_stats["pending_reviews"],
            blocked_sources=storage_stats["blocked_sources"],
            threat_level_distribution=threat_level_dist,
            threat_type_distribution=threat_type_dist,
            recent_events=recent_events
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve dashboard data: {str(e)}"
        )


@router.get("/rate-limits/{source_id}")
async def get_rate_limit_status(source_id: str):
    """
    Get current rate limit status for a source.

    Useful for debugging and monitoring API usage.
    """
    try:
        status = rate_limiter.get_source_status(source_id)
        return status

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve rate limit status: {str(e)}"
        )


@router.post("/rate-limits/{source_id}/tier")
async def set_rate_limit_tier(
    source_id: str,
    tier: str = Query(..., description="Tier: free, basic, premium, internal, unlimited"),
    analyst_id: str = Query(..., description="Analyst making the change")
):
    """
    Update rate limit tier for a source.

    Allows manual adjustment of limits for VIP users or internal systems.
    """
    try:
        # Validate tier
        try:
            tier_enum = RateLimitTier(tier)
        except ValueError:
            valid_tiers = [t.value for t in RateLimitTier]
            raise bad_request_error(f"Invalid tier. Must be one of: {valid_tiers}")

        # Update tier
        rate_limiter.set_source_tier(source_id, tier_enum)

        # Log audit event
        event_store.log_audit_event(
            source_id=analyst_id,
            action="update_rate_limit_tier",
            resource=f"source:{source_id}",
            success=True,
            metadata={"new_tier": tier}
        )

        return {
            "success": True,
            "source_id": source_id,
            "new_tier": tier,
            "message": f"Rate limit tier updated to {tier}"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update tier: {str(e)}"
        )


@router.post("/sources/{source_id}/reset")
async def reset_source(
    source_id: str,
    analyst_id: str = Query("admin", description="Analyst performing reset")
):
    """
    Reset all rate limiting and security state for a source.

    Useful for testing and resolving false positives.
    """
    try:
        # Reset in rate limiter
        rate_limiter.reset_source(source_id)

        # Unblock in security engine
        security_engine.unblock_source(source_id)

        # Log audit event
        event_store.log_audit_event(
            source_id=analyst_id,
            action="reset_source",
            resource=f"source:{source_id}",
            success=True,
            metadata={"action": "reset all state"}
        )

        return {
            "success": True,
            "source_id": source_id,
            "message": "Source reset successfully - all blocks and violations cleared"
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to reset source: {str(e)}"
        )


@router.get("/health")
async def security_health():
    """Health check for security subsystem"""
    try:
        # Check components are working
        engine_stats = security_engine.get_statistics()
        rate_stats = rate_limiter.get_statistics()

        return {
            "status": "healthy",
            "components": {
                "security_engine": "up",
                "event_store": "up",
                "rate_limiter": "up"
            },
            "metrics": {
                "monitored_sources": engine_stats["monitored_sources"],
                "active_rate_limits": rate_stats["active_sources"],
                "total_events": engine_stats["total_events"]
            }
        }

    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Security subsystem unhealthy: {str(e)}"
        )
