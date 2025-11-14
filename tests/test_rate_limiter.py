"""
Tests for Rate Limiting System

Tests cover:
- Token bucket algorithm
- Rate limit tiers
- Automatic blocking
- Source tier management
"""

import pytest
import time
from api.utils.rate_limiter import (
    RateLimiter,
    RateLimitTier,
    TokenBucket,
    RateLimitConfig
)


@pytest.fixture
def rate_limiter():
    """Create fresh rate limiter for each test"""
    return RateLimiter()


class TestTokenBucket:
    """Test token bucket implementation"""

    def test_initial_capacity(self):
        """Bucket should start at full capacity"""
        bucket = TokenBucket(capacity=10, refill_rate=1.0)

        assert bucket.tokens == 10
        assert bucket.consume(1) is True

    def test_consume_within_capacity(self):
        """Consuming within capacity should succeed"""
        bucket = TokenBucket(capacity=10, refill_rate=1.0)

        # Consume 5 tokens
        for _ in range(5):
            assert bucket.consume(1) is True

        assert bucket.tokens == 5

    def test_consume_exceeds_capacity(self):
        """Consuming beyond capacity should fail"""
        bucket = TokenBucket(capacity=10, refill_rate=1.0)

        # Consume all tokens
        for _ in range(10):
            bucket.consume(1)

        # Next consume should fail
        assert bucket.consume(1) is False

    def test_token_refill(self):
        """Tokens should refill over time"""
        bucket = TokenBucket(capacity=10, refill_rate=10.0)  # 10 tokens/sec

        # Consume all tokens
        for _ in range(10):
            bucket.consume(1)

        assert bucket.consume(1) is False  # Empty

        # Wait for refill (0.2 seconds = 2 tokens)
        time.sleep(0.2)

        # Should have refilled ~2 tokens
        assert bucket.consume(1) is True
        assert bucket.consume(1) is True

    def test_refill_caps_at_capacity(self):
        """Refill should not exceed capacity"""
        bucket = TokenBucket(capacity=10, refill_rate=100.0)

        # Wait for refill
        time.sleep(0.5)

        # Should still be capped at 10
        bucket.consume(10)
        assert bucket.consume(1) is False

    def test_retry_after_calculation(self):
        """get_retry_after should return seconds until next token"""
        bucket = TokenBucket(capacity=10, refill_rate=2.0)  # 2 tokens/sec

        # Drain bucket
        for _ in range(10):
            bucket.consume(1)

        # Retry after should be ~0.5 seconds (1 token / 2 tokens per second)
        retry_after = bucket.get_retry_after()
        assert 0.4 < retry_after < 0.6


class TestRateLimitTiers:
    """Test different rate limit tiers"""

    def test_default_tier_is_basic(self, rate_limiter):
        """New sources should default to BASIC tier"""
        source_id = "new_user"

        # First request should succeed (basic tier = 100/min)
        allowed, _ = rate_limiter.check_rate_limit(source_id)
        assert allowed is True

        # Check tier assignment
        tier = rate_limiter._source_tiers[source_id]
        assert tier == RateLimitTier.BASIC

    def test_set_source_tier(self, rate_limiter):
        """Setting tier should apply new limits"""
        source_id = "premium_user"

        # Set to premium tier
        rate_limiter.set_source_tier(source_id, RateLimitTier.PREMIUM)

        # Verify tier
        assert rate_limiter._source_tiers[source_id] == RateLimitTier.PREMIUM

    def test_unlimited_tier_never_blocks(self, rate_limiter):
        """Unlimited tier should never block"""
        source_id = "admin_user"

        rate_limiter.set_source_tier(source_id, RateLimitTier.UNLIMITED)

        # Make 1000 requests
        for _ in range(1000):
            allowed, _ = rate_limiter.check_rate_limit(source_id)
            assert allowed is True

    def test_free_tier_has_low_limits(self, rate_limiter):
        """Free tier should have restrictive limits"""
        source_id = "free_user"

        rate_limiter.set_source_tier(source_id, RateLimitTier.FREE)

        # Free tier: 20/min, burst 10
        # Should block after ~10 rapid requests
        allowed_count = 0
        for _ in range(20):
            allowed, _ = rate_limiter.check_rate_limit(source_id)
            if allowed:
                allowed_count += 1

        # Should have blocked some requests
        assert allowed_count < 20


class TestRateLimitEnforcement:
    """Test rate limit enforcement"""

    def test_within_limit_allowed(self, rate_limiter):
        """Requests within limit should be allowed"""
        source_id = "normal_user"

        # BASIC tier: 100/min, burst 30
        # 20 requests should all succeed
        for _ in range(20):
            allowed, _ = rate_limiter.check_rate_limit(source_id)
            assert allowed is True

    def test_burst_capacity_exceeded(self, rate_limiter):
        """Exceeding burst capacity should rate limit"""
        source_id = "burst_user"

        # BASIC tier: burst capacity = 30
        # Rapid 40 requests should hit limit
        blocked_count = 0
        for _ in range(40):
            allowed, metadata = rate_limiter.check_rate_limit(source_id)
            if not allowed:
                blocked_count += 1

        # Should have blocked at least a few
        assert blocked_count > 0

    def test_rate_limit_response_metadata(self, rate_limiter):
        """Rate limit response should include metadata"""
        source_id = "limited_user"

        # Drain tokens
        for _ in range(50):
            rate_limiter.check_rate_limit(source_id)

        # Next request should be limited with metadata
        allowed, metadata = rate_limiter.check_rate_limit(source_id)

        if not allowed:
            assert metadata is not None
            assert "retry_after_seconds" in metadata
            assert "message" in metadata
            assert metadata["reason"] in ["rate_limit", "rate_limit_block"]


class TestAutomaticBlocking:
    """Test automatic blocking on repeated violations"""

    def test_single_violation_no_block(self, rate_limiter):
        """Single rate limit violation should not block"""
        source_id = "occasional_spiker"

        # Exceed limit once
        for _ in range(50):
            rate_limiter.check_rate_limit(source_id)

        # Should not be blocked yet
        assert not rate_limiter.is_blocked(source_id)

    def test_repeated_violations_trigger_block(self, rate_limiter):
        """3+ violations in 5 minutes should block"""
        source_id = "repeat_offender"

        # Trigger 3 violations
        for violation in range(3):
            # Drain tokens to trigger violation
            for _ in range(50):
                rate_limiter.check_rate_limit(source_id)

            # Small delay between violations
            time.sleep(0.1)

        # Should be blocked after 3rd violation
        allowed, metadata = rate_limiter.check_rate_limit(source_id)

        assert allowed is False
        assert metadata["reason"] == "rate_limit_block"
        assert "blocked" in metadata["message"].lower()

    def test_blocked_source_stays_blocked(self, rate_limiter):
        """Blocked source should remain blocked"""
        source_id = "blocked_user"

        # Trigger block
        for _ in range(3):
            for _ in range(50):
                rate_limiter.check_rate_limit(source_id)

        # Multiple subsequent requests should still be blocked
        for _ in range(5):
            allowed, _ = rate_limiter.check_rate_limit(source_id)
            assert allowed is False

    def test_manual_unblock(self, rate_limiter):
        """Manual unblock should work"""
        source_id = "falsely_blocked"

        # Trigger block
        for _ in range(3):
            for _ in range(50):
                rate_limiter.check_rate_limit(source_id)

        assert rate_limiter.is_blocked(source_id)

        # Unblock
        result = rate_limiter.unblock_source(source_id)
        assert result is True
        assert not rate_limiter.is_blocked(source_id)

        # Should be able to make requests again
        allowed, _ = rate_limiter.check_rate_limit(source_id)
        assert allowed is True


class TestSourceStatus:
    """Test source status reporting"""

    def test_get_source_status(self, rate_limiter):
        """Should return comprehensive status"""
        source_id = "status_user"

        # Make a few requests
        for _ in range(5):
            rate_limiter.check_rate_limit(source_id)

        status = rate_limiter.get_source_status(source_id)

        assert status["source_id"] == source_id
        assert status["tier"] == RateLimitTier.BASIC.value
        assert "tokens_available" in status
        assert "blocked" in status
        assert status["blocked"] is False

    def test_blocked_status_shows_unblock_time(self, rate_limiter):
        """Blocked status should show when unblock occurs"""
        source_id = "temp_blocked"

        # Trigger block
        for _ in range(3):
            for _ in range(50):
                rate_limiter.check_rate_limit(source_id)

        status = rate_limiter.get_source_status(source_id)

        assert status["blocked"] is True
        assert "unblock_in_seconds" in status
        assert status["unblock_in_seconds"] > 0


class TestStatistics:
    """Test rate limiter statistics"""

    def test_statistics_initial_state(self, rate_limiter):
        """Initial statistics should be empty"""
        stats = rate_limiter.get_statistics()

        assert stats["active_sources"] == 0
        assert stats["blocked_sources"] == 0
        assert stats["recent_violations"] == 0

    def test_statistics_with_activity(self, rate_limiter):
        """Statistics should reflect activity"""
        # Create activity with multiple sources
        for i in range(5):
            source_id = f"user_{i}"
            for _ in range(10):
                rate_limiter.check_rate_limit(source_id)

        stats = rate_limiter.get_statistics()

        assert stats["active_sources"] == 5

    def test_statistics_with_blocks(self, rate_limiter):
        """Statistics should count blocked sources"""
        # Block two sources
        for i in range(2):
            source_id = f"blocked_{i}"
            for _ in range(3):
                for _ in range(50):
                    rate_limiter.check_rate_limit(source_id)

        stats = rate_limiter.get_statistics()

        assert stats["blocked_sources"] == 2


class TestSourceReset:
    """Test resetting source state"""

    def test_reset_clears_all_state(self, rate_limiter):
        """Reset should clear all tracking"""
        source_id = "reset_user"

        # Create some state
        rate_limiter.set_source_tier(source_id, RateLimitTier.PREMIUM)
        for _ in range(20):
            rate_limiter.check_rate_limit(source_id)

        # Block the source
        for _ in range(3):
            for _ in range(100):
                rate_limiter.check_rate_limit(source_id)

        # Verify state exists
        assert source_id in rate_limiter._buckets
        assert source_id in rate_limiter._source_tiers

        # Reset
        rate_limiter.reset_source(source_id)

        # All state should be cleared
        assert source_id not in rate_limiter._buckets
        assert source_id not in rate_limiter._source_tiers
        assert source_id not in rate_limiter._blocked_until


class TestRateLimitTierConfigs:
    """Test tier configuration values"""

    def test_tier_limits_correct(self, rate_limiter):
        """Verify tier limits match specification"""
        configs = rate_limiter.tier_configs

        # FREE: 20/min
        assert configs[RateLimitTier.FREE].requests_per_minute == 20
        assert configs[RateLimitTier.FREE].burst_capacity == 10

        # BASIC: 100/min
        assert configs[RateLimitTier.BASIC].requests_per_minute == 100
        assert configs[RateLimitTier.BASIC].burst_capacity == 30

        # PREMIUM: 500/min
        assert configs[RateLimitTier.PREMIUM].requests_per_minute == 500
        assert configs[RateLimitTier.PREMIUM].burst_capacity == 100

        # INTERNAL: 2000/min
        assert configs[RateLimitTier.INTERNAL].requests_per_minute == 2000
        assert configs[RateLimitTier.INTERNAL].burst_capacity == 500


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
