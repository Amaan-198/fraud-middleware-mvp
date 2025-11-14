"""
Tests for Institute Security Engine

Tests cover:
- API abuse detection
- Brute force protection
- Data exfiltration monitoring
- Off-hours access detection
- Source risk profiling
"""

import pytest
import time
from datetime import datetime
from api.models.institute_security import (
    InstituteSecurityEngine,
    ThreatLevel,
    ThreatType,
    SecurityEvent
)


@pytest.fixture
def security_engine():
    """Create fresh security engine for each test"""
    return InstituteSecurityEngine()


class TestAPIAbuseDetection:
    """Test API abuse and rate-based attack detection"""

    def test_normal_request_rate_no_alert(self, security_engine):
        """Normal request rate should not trigger alerts"""
        source_id = "normal_user"

        # Simulate 20 requests (well below warning threshold)
        for _ in range(20):
            event = security_engine.monitor_api_request(
                source_id=source_id,
                endpoint="/v1/decision",
                success=True,
                response_time_ms=45.0
            )
            time.sleep(0.01)  # Spread over short window

        # Should not generate event
        assert event is None

    def test_high_request_rate_warning(self, security_engine):
        """High request rate should trigger warning"""
        source_id = "high_volume_user"

        # Simulate 120 requests in quick succession (>100/min warning)
        event = None
        for _ in range(120):
            event = security_engine.monitor_api_request(
                source_id=source_id,
                endpoint="/v1/decision",
                success=True,
                response_time_ms=45.0
            )

        # Should trigger HIGH level event
        assert event is not None
        assert event.threat_type == ThreatType.API_ABUSE.value
        assert event.threat_level == ThreatLevel.HIGH.value
        assert "requests/minute" in event.description

    def test_rapid_burst_detection(self, security_engine):
        """Rapid bursts below per-minute threshold should still alert"""
        source_id = "burst_user"

        # Make minute thresholds unreachable so only rapid detection triggers
        security_engine.config["api_requests_per_minute_warning"] = 999
        security_engine.config["api_requests_per_minute_critical"] = 1000
        security_engine.config["rapid_requests_threshold"] = 40
        security_engine.config["rapid_requests_window_seconds"] = 30

        event = None
        for _ in range(security_engine.config["rapid_requests_threshold"]):
            event = security_engine.monitor_api_request(
                source_id=source_id,
                endpoint="/v1/decision",
                success=True,
                response_time_ms=45.0
            )

        assert event is not None
        assert event.threat_type == ThreatType.API_ABUSE.value
        assert event.threat_level == ThreatLevel.MEDIUM.value
        assert "rapid burst" in event.description.lower()

    def test_critical_request_rate_blocks_source(self, security_engine):
        """Critical request rate should block source"""
        source_id = "abusive_user"

        # Simulate 550 requests (>500/min critical)
        event = None
        for _ in range(550):
            event = security_engine.monitor_api_request(
                source_id=source_id,
                endpoint="/v1/decision",
                success=True,
                response_time_ms=45.0
            )

        # Should trigger CRITICAL event
        assert event is not None
        assert event.threat_level == ThreatLevel.CRITICAL.value

        # Source should be blocked
        assert security_engine.is_source_blocked(source_id)

    def test_high_error_rate_detection(self, security_engine):
        """High error rate should be detected"""
        source_id = "failing_user"

        # 20 successful requests
        for _ in range(20):
            security_engine.monitor_api_request(
                source_id=source_id,
                endpoint="/v1/decision",
                success=True,
                response_time_ms=45.0
            )

        # 30 failed requests (60% error rate)
        event = None
        for _ in range(30):
            event = security_engine.monitor_api_request(
                source_id=source_id,
                endpoint="/v1/decision",
                success=False,
                response_time_ms=45.0
            )

        # Should trigger HIGH level event for error rate
        assert event is not None
        assert event.threat_type == ThreatType.API_ABUSE.value
        assert "error rate" in event.description.lower()


class TestBruteForceProtection:
    """Test brute force and authentication attack detection"""

    def test_successful_auth_clears_failures(self, security_engine):
        """Successful auth should clear failed attempts"""
        source_id = "good_user"

        # 3 failed attempts
        for _ in range(3):
            security_engine.monitor_authentication(
                source_id=source_id,
                success=False
            )

        # Successful auth
        event = security_engine.monitor_authentication(
            source_id=source_id,
            success=True
        )

        # Should not generate event
        assert event is None

        # Next failure should start fresh count
        event = security_engine.monitor_authentication(
            source_id=source_id,
            success=False
        )
        assert event is None  # Only 1 failure

    def test_warning_level_failed_auths(self, security_engine):
        """5+ failed auths should trigger warning"""
        source_id = "suspicious_user"

        event = None
        # 6 failed attempts (>5 warning threshold)
        for _ in range(6):
            event = security_engine.monitor_authentication(
                source_id=source_id,
                success=False
            )

        # Should trigger HIGH level event
        assert event is not None
        assert event.threat_type == ThreatType.BRUTE_FORCE.value
        assert event.threat_level == ThreatLevel.HIGH.value
        assert "failed auth" in event.description.lower()

    def test_critical_level_failed_auths_blocks(self, security_engine):
        """10+ failed auths should block source"""
        source_id = "attacker"

        event = None
        # 12 failed attempts (>10 critical threshold)
        for _ in range(12):
            event = security_engine.monitor_authentication(
                source_id=source_id,
                success=False
            )

        # Should trigger CRITICAL event and block
        assert event is not None
        assert event.threat_level == ThreatLevel.CRITICAL.value
        assert security_engine.is_source_blocked(source_id)


class TestDataExfiltrationDetection:
    """Test detection of unusual data access patterns"""

    def test_normal_data_access_no_alert(self, security_engine):
        """Normal data access should not trigger alerts"""
        source_id = "analyst"

        # Simulate normal access pattern (10 records each time)
        for _ in range(10):
            event = security_engine.monitor_data_access(
                source_id=source_id,
                data_type="customer_records",
                record_count=10,
                sensitive=False
            )

        # Should not generate event
        assert event is None

    def test_unusual_volume_triggers_alert(self, security_engine):
        """Accessing 3x normal volume should trigger alert"""
        source_id = "insider_threat"

        # Establish baseline (10 records per access, 10 times)
        for _ in range(10):
            security_engine.monitor_data_access(
                source_id=source_id,
                data_type="customer_records",
                record_count=10,
                sensitive=False
            )

        # Sudden spike to 100 records (10x baseline, >3x threshold)
        event = security_engine.monitor_data_access(
            source_id=source_id,
            data_type="customer_records",
            record_count=100,
            sensitive=False
        )

        # Should trigger event
        assert event is not None
        assert event.threat_type == ThreatType.DATA_EXFILTRATION.value
        assert "unusual data access" in event.description.lower()

    def test_sensitive_data_triggers_critical(self, security_engine):
        """Unusual access to sensitive data should be CRITICAL"""
        source_id = "risky_user"

        # Establish baseline
        for _ in range(10):
            security_engine.monitor_data_access(
                source_id=source_id,
                data_type="pii_data",
                record_count=5,
                sensitive=True
            )

        # Large sensitive data access
        event = security_engine.monitor_data_access(
            source_id=source_id,
            data_type="pii_data",
            record_count=50,
            sensitive=True
        )

        # Should be CRITICAL due to sensitive flag
        assert event is not None
        assert event.threat_level == ThreatLevel.CRITICAL.value


class TestOffHoursAccess:
    """Test detection of unusual off-hours access"""

    def test_normal_hours_access_no_alert(self, security_engine):
        """Access during normal hours should not trigger"""
        source_id = "day_worker"

        # Simulate daytime access (10 AM)
        # Build usage pattern first
        for _ in range(25):
            security_engine._user_access_patterns[source_id]["hourly_distribution"][10] += 1

        # Access at 10 AM
        event = security_engine._check_off_hours_access(
            source_id=source_id,
            hour=10,
            endpoint="/v1/decision"
        )

        assert event is None

    def test_off_hours_access_with_pattern_no_alert(self, security_engine):
        """User with off-hours pattern should not trigger"""
        source_id = "night_shift"

        # Build off-hours pattern (user works at night)
        for hour in range(22, 24):  # 10 PM - midnight
            for _ in range(10):
                security_engine._user_access_patterns[source_id]["hourly_distribution"][hour] += 1

        for hour in range(0, 6):  # midnight - 6 AM
            for _ in range(10):
                security_engine._user_access_patterns[source_id]["hourly_distribution"][hour] += 1

        # Access at 2 AM should be normal for this user
        event = security_engine._check_off_hours_access(
            source_id=source_id,
            hour=2,
            endpoint="/v1/decision"
        )

        assert event is None

    def test_unusual_off_hours_triggers_alert(self, security_engine):
        """Day worker accessing at night should trigger"""
        source_id = "suspicious_daytime_user"

        # Build daytime pattern only
        for hour in range(9, 17):  # 9 AM - 5 PM
            for _ in range(5):
                security_engine._user_access_patterns[source_id]["hourly_distribution"][hour] += 1

        # Access at 2 AM (unusual for this user)
        event = security_engine._check_off_hours_access(
            source_id=source_id,
            hour=2,
            endpoint="/v1/decision"
        )

        # Should trigger event
        assert event is not None
        assert event.threat_type == ThreatType.UNUSUAL_ACCESS.value
        assert "off-hours" in event.description.lower()


class TestSensitiveEndpointAccess:
    """Test detection of unusual endpoint access patterns"""

    def test_normal_endpoint_no_alert(self, security_engine):
        """Normal endpoint access should not trigger"""
        source_id = "regular_user"

        # Access normal endpoint
        event = security_engine._check_unusual_endpoint_access(
            source_id=source_id,
            endpoint="/v1/decision"
        )

        assert event is None

    def test_first_time_sensitive_endpoint_triggers(self, security_engine):
        """First access to sensitive endpoint should trigger"""
        source_id = "escalating_user"

        # First access to admin endpoint
        event = security_engine._check_unusual_endpoint_access(
            source_id=source_id,
            endpoint="/admin/config"
        )

        # Should trigger HIGH level event
        assert event is not None
        assert event.threat_type == ThreatType.PRIVILEGE_ESCALATION.value
        assert event.threat_level == ThreatLevel.HIGH.value


class TestRiskProfiling:
    """Test source risk profile generation"""

    def test_clean_source_low_risk(self, security_engine):
        """Source with no events should have low risk"""
        source_id = "clean_user"

        profile = security_engine.get_source_risk_profile(source_id)

        assert profile["risk_score"] == 0
        assert not profile["is_blocked"]
        assert profile["recent_events"] == 0

    def test_multiple_events_increase_risk(self, security_engine):
        """Multiple security events should increase risk score"""
        source_id = "risky_user"

        # Trigger multiple events
        # Failed auths
        for _ in range(6):
            security_engine.monitor_authentication(source_id=source_id, success=False)

        # High request rate
        for _ in range(120):
            security_engine.monitor_api_request(
                source_id=source_id,
                endpoint="/v1/decision",
                success=True,
                response_time_ms=45.0
            )

        profile = security_engine.get_source_risk_profile(source_id)

        # Risk score should be elevated
        assert profile["risk_score"] > 0
        assert profile["recent_events"] > 0
        assert len(profile["threat_breakdown"]) > 0

    def test_blocked_source_in_profile(self, security_engine):
        """Blocked status should appear in profile"""
        source_id = "blocked_user"

        # Trigger critical event that blocks
        for _ in range(15):
            security_engine.monitor_authentication(source_id=source_id, success=False)

        profile = security_engine.get_source_risk_profile(source_id)

        assert profile["is_blocked"]
        assert profile["highest_threat_level"] == ThreatLevel.CRITICAL.value


class TestSourceBlocking:
    """Test source blocking and unblocking"""

    def test_block_and_unblock_source(self, security_engine):
        """Test manual blocking and unblocking"""
        source_id = "test_user"

        # Initially not blocked
        assert not security_engine.is_source_blocked(source_id)

        # Trigger event that blocks
        for _ in range(600):
            security_engine.monitor_api_request(
                source_id=source_id,
                endpoint="/v1/decision",
                success=True,
                response_time_ms=45.0
            )

        # Should be blocked
        assert security_engine.is_source_blocked(source_id)

        # Unblock
        result = security_engine.unblock_source(source_id)
        assert result is True
        assert not security_engine.is_source_blocked(source_id)

    def test_unblock_non_blocked_source(self, security_engine):
        """Unblocking non-blocked source should return False"""
        source_id = "never_blocked"

        result = security_engine.unblock_source(source_id)
        assert result is False


class TestStatistics:
    """Test security statistics generation"""

    def test_statistics_empty_state(self, security_engine):
        """Statistics for clean state should be zero"""
        stats = security_engine.get_statistics()

        assert stats["total_events"] == 0
        assert stats["blocked_sources"] == 0
        assert stats["events_requiring_review"] == 0

    def test_statistics_with_events(self, security_engine):
        """Statistics should reflect generated events"""
        # Generate various events
        security_engine.monitor_authentication("user1", success=False)
        for _ in range(6):
            security_engine.monitor_authentication("user1", success=False)

        for _ in range(150):
            security_engine.monitor_api_request("user2", "/v1/decision", True, 45.0)

        stats = security_engine.get_statistics()

        assert stats["total_events"] > 0
        assert stats["monitored_sources"] >= 2
        assert len(stats["threat_types"]) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
