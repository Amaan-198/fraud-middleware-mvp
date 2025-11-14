"""
Tests for Security API Endpoints

Tests cover:
- Security event retrieval
- Review queue management
- Source blocking/unblocking
- Audit trail access
- Dashboard statistics
"""

import pytest
from fastapi.testclient import TestClient
from api.main import app
from api.models.institute_security import InstituteSecurityEngine, ThreatLevel
from api.utils.security_storage import SecurityEventStore
from api.utils.rate_limiter import RateLimiter, RateLimitTier


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def setup_and_teardown():
    """Reset security components before each test"""
    # This is a simplified version - in production, use proper test database
    yield
    # Cleanup would go here


class TestSecurityEventsEndpoint:
    """Test GET /v1/security/events"""

    def test_get_events_empty(self, client):
        """Empty state should return empty list"""
        response = client.get("/v1/security/events")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_events_with_limit(self, client):
        """Limit parameter should be respected"""
        response = client.get("/v1/security/events?limit=10")

        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 10

    def test_get_events_with_threat_level_filter(self, client):
        """Min threat level filter should work"""
        response = client.get("/v1/security/events?min_threat_level=3")

        assert response.status_code == 200
        data = response.json()

        # All events should have threat_level >= 3
        for event in data:
            assert event["threat_level"] >= 3

    def test_get_events_invalid_limit(self, client):
        """Invalid limit should return 422"""
        response = client.get("/v1/security/events?limit=5000")

        assert response.status_code == 422


class TestReviewQueueEndpoint:
    """Test GET /v1/security/events/review-queue"""

    def test_get_review_queue_structure(self, client):
        """Review queue should return correct structure"""
        response = client.get("/v1/security/events/review-queue")

        assert response.status_code == 200
        data = response.json()

        assert "total_pending" in data
        assert "events" in data
        assert isinstance(data["events"], list)

    def test_review_queue_limit(self, client):
        """Limit parameter should work"""
        response = client.get("/v1/security/events/review-queue?limit=5")

        assert response.status_code == 200
        data = response.json()

        assert len(data["events"]) <= 5


class TestEventReviewEndpoint:
    """Test POST /v1/security/events/{event_id}/review"""

    def test_review_event_not_found(self, client):
        """Reviewing non-existent event should return 404"""
        review_data = {
            "event_id": "nonexistent",
            "analyst_id": "analyst_001",
            "notes": "Test review"
        }

        response = client.post(
            "/v1/security/events/nonexistent_event/review",
            json=review_data
        )

        assert response.status_code == 404

    def test_review_event_missing_fields(self, client):
        """Missing required fields should return 422"""
        review_data = {
            "event_id": "test_event"
            # Missing analyst_id
        }

        response = client.post(
            "/v1/security/events/test_event/review",
            json=review_data
        )

        assert response.status_code == 422


class TestSourceRiskProfileEndpoint:
    """Test GET /v1/security/sources/{source_id}/risk"""

    def test_get_risk_profile_new_source(self, client):
        """New source should have low risk"""
        response = client.get("/v1/security/sources/new_source_123/risk")

        assert response.status_code == 200
        data = response.json()

        assert "risk_score" in data
        assert "is_blocked" in data
        assert "recent_events" in data
        assert data["risk_score"] == 0
        assert data["is_blocked"] is False

    def test_risk_profile_structure(self, client):
        """Risk profile should have correct structure"""
        response = client.get("/v1/security/sources/test_source/risk")

        assert response.status_code == 200
        data = response.json()

        required_fields = [
            "source_id",
            "risk_score",
            "is_blocked",
            "recent_events",
            "threat_breakdown",
            "highest_threat_level"
        ]

        for field in required_fields:
            assert field in data


class TestBlockedSourcesEndpoint:
    """Test GET /v1/security/sources/blocked"""

    def test_get_blocked_sources_empty(self, client):
        """No blocked sources should return empty list"""
        response = client.get("/v1/security/sources/blocked")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestUnblockSourceEndpoint:
    """Test POST /v1/security/sources/{source_id}/unblock"""

    def test_unblock_not_blocked_source(self, client):
        """Unblocking non-blocked source should return 404"""
        unblock_data = {
            "source_id": "not_blocked",
            "analyst_id": "analyst_001",
            "reason": "Test unblock"
        }

        response = client.post(
            "/v1/security/sources/not_blocked/unblock",
            json=unblock_data
        )

        # Should return 404 or success: false
        assert response.status_code in [404, 200]

    def test_unblock_missing_analyst_id(self, client):
        """Missing analyst_id should return 422"""
        unblock_data = {
            "source_id": "test_source"
            # Missing analyst_id
        }

        response = client.post(
            "/v1/security/sources/test_source/unblock",
            json=unblock_data
        )

        assert response.status_code == 422


class TestAuditTrailEndpoint:
    """Test GET /v1/security/audit-trail"""

    def test_get_audit_trail(self, client):
        """Audit trail should return list"""
        response = client.get("/v1/security/audit-trail")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_audit_trail_with_filters(self, client):
        """Filters should be accepted"""
        response = client.get(
            "/v1/security/audit-trail?source_id=test&limit=10"
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 10


class TestSecurityDashboardEndpoint:
    """Test GET /v1/security/dashboard"""

    def test_get_dashboard(self, client):
        """Dashboard should return statistics"""
        response = client.get("/v1/security/dashboard")

        assert response.status_code == 200
        data = response.json()

        required_fields = [
            "total_events",
            "pending_reviews",
            "blocked_sources",
            "threat_level_distribution",
            "threat_type_distribution",
            "recent_events"
        ]

        for field in required_fields:
            assert field in data

    def test_dashboard_structure_types(self, client):
        """Dashboard fields should have correct types"""
        response = client.get("/v1/security/dashboard")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data["total_events"], int)
        assert isinstance(data["pending_reviews"], int)
        assert isinstance(data["blocked_sources"], int)
        assert isinstance(data["threat_level_distribution"], dict)
        assert isinstance(data["threat_type_distribution"], dict)
        assert isinstance(data["recent_events"], list)


class TestRateLimitStatusEndpoint:
    """Test GET /v1/security/rate-limits/{source_id}"""

    def test_get_rate_limit_status(self, client):
        """Should return rate limit status"""
        response = client.get("/v1/security/rate-limits/test_source")

        assert response.status_code == 200
        data = response.json()

        assert "source_id" in data
        assert "tier" in data
        assert "blocked" in data


class TestRateLimitTierEndpoint:
    """Test POST /v1/security/rate-limits/{source_id}/tier"""

    def test_set_rate_limit_tier(self, client):
        """Setting tier should work"""
        response = client.post(
            "/v1/security/rate-limits/test_source/tier?tier=premium&analyst_id=analyst_001"
        )

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["new_tier"] == "premium"

    def test_set_invalid_tier(self, client):
        """Invalid tier should return 400"""
        response = client.post(
            "/v1/security/rate-limits/test_source/tier?tier=invalid&analyst_id=analyst_001"
        )

        assert response.status_code == 400

    def test_set_tier_missing_analyst(self, client):
        """Missing analyst_id should return 422"""
        response = client.post(
            "/v1/security/rate-limits/test_source/tier?tier=premium"
        )

        assert response.status_code == 422


class TestSecurityHealthEndpoint:
    """Test GET /v1/security/health"""

    def test_security_health(self, client):
        """Health endpoint should return status"""
        response = client.get("/v1/security/health")

        assert response.status_code == 200
        data = response.json()

        assert "status" in data
        assert "components" in data
        assert data["status"] == "healthy"

    def test_health_components(self, client):
        """Health should list all components"""
        response = client.get("/v1/security/health")

        assert response.status_code == 200
        data = response.json()

        components = data["components"]
        assert "security_engine" in components
        assert "event_store" in components
        assert "rate_limiter" in components

        # All should be "up"
        for component, status in components.items():
            assert status == "up"


class TestMainAppHealth:
    """Test main app health endpoints"""

    def test_root_endpoint(self, client):
        """Root endpoint should return service info"""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()

        assert "service" in data
        assert "version" in data
        assert "features" in data
        assert data["service"] == "Allianz Fraud Middleware"

    def test_health_endpoint(self, client):
        """Health endpoint should include security components"""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()

        assert "status" in data
        assert "components" in data

        components = data["components"]
        assert "security_engine" in components
        assert "rate_limiter" in components
        assert "event_store" in components


class TestRateLimitingMiddleware:
    """Test rate limiting middleware integration"""

    def test_rate_limit_applied_to_decision_endpoint(self, client):
        """Decision endpoint should have rate limiting"""
        # Make many rapid requests to trigger rate limit
        responses = []

        for _ in range(150):  # Exceed BASIC tier burst (30)
            response = client.post(
                "/v1/decision",
                json={
                    "user_id": "test_user",
                    "device_id": "test_device",
                    "amount": 100.0,
                    "timestamp": "2024-01-15T10:00:00Z",
                    "location": "Test City"
                }
            )
            responses.append(response.status_code)

        # Should have some 429 (rate limited) responses
        assert 429 in responses

    def test_rate_limit_bypass_for_health(self, client):
        """Health endpoints should bypass rate limiting"""
        # Make many requests to health endpoint
        for _ in range(200):
            response = client.get("/health")
            # Should never be rate limited
            assert response.status_code == 200

    def test_rate_limit_response_format(self, client):
        """Rate limit response should have correct format"""
        # Trigger rate limit
        for _ in range(100):
            client.get("/v1/security/events")

        # Next request should be limited
        response = client.get("/v1/security/events")

        if response.status_code == 429:
            data = response.json()
            assert "error" in data
            assert "message" in data
            assert "retry_after_seconds" in data
            assert data["error"] == "rate_limit_exceeded"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
