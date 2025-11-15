"""
Rate Limiting Middleware

Protects API endpoints from abuse with:
- Token bucket algorithm for smooth rate limiting
- Configurable limits per endpoint/source
- Automatic blocking of repeat offenders
- Integration with institute security monitoring

Production-ready implementation suitable for banking environments.
"""

import time
from typing import Dict, Optional, Tuple
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum


class RateLimitTier(Enum):
    """Rate limit tiers for different user types"""
    FREE = "free"           # Low limits for unauthenticated
    BASIC = "basic"         # Standard authenticated users
    PREMIUM = "premium"     # Higher limits for premium users
    INTERNAL = "internal"   # Internal systems, high limits
    UNLIMITED = "unlimited" # Admin/monitoring, no limits


@dataclass
class RateLimitConfig:
    """Rate limit configuration"""
    requests_per_minute: int
    burst_capacity: int  # Maximum burst allowed
    block_duration_seconds: int = 300  # 5 minutes default


class TokenBucket:
    """
    Token bucket implementation for rate limiting.

    Allows bursts while enforcing average rate limits.
    """

    def __init__(self, capacity: int, refill_rate: float):
        """
        Initialize token bucket.

        Args:
            capacity: Maximum tokens (burst capacity)
            refill_rate: Tokens added per second
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = capacity
        self.last_refill = time.time()

    def consume(self, tokens: int = 1) -> bool:
        """
        Try to consume tokens.

        Args:
            tokens: Number of tokens to consume

        Returns:
            True if tokens available, False if rate limited
        """
        # Refill tokens based on time elapsed
        now = time.time()
        elapsed = now - self.last_refill
        self.tokens = min(
            self.capacity,
            self.tokens + (elapsed * self.refill_rate)
        )
        self.last_refill = now

        # Check if enough tokens available
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True

        return False

    def get_retry_after(self) -> float:
        """
        Get seconds until next token available.

        Returns:
            Seconds to wait before retry
        """
        if self.tokens >= 1:
            return 0.0

        tokens_needed = 1 - self.tokens
        return tokens_needed / self.refill_rate


class RateLimiter:
    """
    Flexible rate limiting system with multiple tiers and automatic blocking.

    Integrates with institute security engine to detect and prevent API abuse.
    """

    def __init__(self):
        """Initialize rate limiter"""

        # Default rate limit configurations
        self.tier_configs = {
            RateLimitTier.FREE: RateLimitConfig(
                requests_per_minute=20,
                burst_capacity=10,
                block_duration_seconds=300
            ),
            RateLimitTier.BASIC: RateLimitConfig(
                requests_per_minute=100,
                burst_capacity=30,
                block_duration_seconds=300
            ),
            RateLimitTier.PREMIUM: RateLimitConfig(
                requests_per_minute=500,
                burst_capacity=100,
                block_duration_seconds=300
            ),
            RateLimitTier.INTERNAL: RateLimitConfig(
                requests_per_minute=2000,
                burst_capacity=500,
                block_duration_seconds=600
            ),
            RateLimitTier.UNLIMITED: RateLimitConfig(
                requests_per_minute=999999,
                burst_capacity=999999,
                block_duration_seconds=0
            ),
        }

        # Token buckets per source
        self._buckets: Dict[str, TokenBucket] = {}

        # Source tier assignments
        self._source_tiers: Dict[str, RateLimitTier] = defaultdict(
            lambda: RateLimitTier.BASIC
        )

        # Temporary blocks (source_id -> unblock_time)
        self._blocked_until: Dict[str, float] = {}

        # Rate limit violation tracking
        self._violations: Dict[str, list] = defaultdict(list)

    def set_source_tier(self, source_id: str, tier: RateLimitTier):
        """
        Set rate limit tier for a source.

        Args:
            source_id: Source identifier (API key, user ID, IP)
            tier: Rate limit tier to assign
        """
        self._source_tiers[source_id] = tier

        # Clear existing bucket to apply new limits
        if source_id in self._buckets:
            del self._buckets[source_id]

    def check_rate_limit(
        self,
        source_id: str,
        tokens: int = 1
    ) -> Tuple[bool, Optional[Dict[str, any]]]:
        """
        Check if request should be rate limited.

        Args:
            source_id: Source making the request
            tokens: Number of tokens to consume (default 1)

        Returns:
            Tuple of (allowed: bool, metadata: dict or None)
            If not allowed, metadata contains retry_after and reason
        """
        now = time.time()

        # Check if source is temporarily blocked
        if source_id in self._blocked_until:
            unblock_time = self._blocked_until[source_id]

            if now < unblock_time:
                # Still blocked
                retry_after = int(unblock_time - now)
                return False, {
                    "reason": "rate_limit_block",
                    "retry_after_seconds": retry_after,
                    "message": f"Temporarily blocked due to rate limit violations. "
                              f"Try again in {retry_after} seconds."
                }
            else:
                # Block expired, remove it
                del self._blocked_until[source_id]

        # Get or create token bucket
        tier = self._source_tiers[source_id]
        config = self.tier_configs[tier]

        if source_id not in self._buckets:
            refill_rate = config.requests_per_minute / 60.0  # Convert to per-second
            self._buckets[source_id] = TokenBucket(
                capacity=config.burst_capacity,
                refill_rate=refill_rate
            )

        bucket = self._buckets[source_id]

        # Try to consume tokens
        if bucket.consume(tokens):
            # Request allowed
            return True, None

        # Rate limited - record violation
        self._violations[source_id].append(now)

        # Clean old violations (older than 5 minutes)
        self._violations[source_id] = [
            t for t in self._violations[source_id]
            if now - t < 300
        ]

        # Check if should temporarily block (3+ violations in 5 minutes)
        if len(self._violations[source_id]) >= 3:
            # Block the source
            self._blocked_until[source_id] = now + config.block_duration_seconds

            return False, {
                "reason": "rate_limit_block",
                "retry_after_seconds": config.block_duration_seconds,
                "message": f"Blocked for {config.block_duration_seconds}s due to "
                          f"repeated rate limit violations.",
                "violations_count": len(self._violations[source_id])
            }

        # Regular rate limit (not blocked yet)
        retry_after = bucket.get_retry_after()

        return False, {
            "reason": "rate_limit",
            "retry_after_seconds": int(retry_after) + 1,
            "message": f"Rate limit exceeded. Try again in {int(retry_after) + 1} seconds.",
            "limit": config.requests_per_minute,
            "tier": tier.value
        }

    def is_blocked(self, source_id: str) -> bool:
        """
        Check if source is currently blocked.

        Args:
            source_id: Source to check

        Returns:
            True if blocked, False otherwise
        """
        if source_id not in self._blocked_until:
            return False

        now = time.time()
        if now >= self._blocked_until[source_id]:
            # Block expired
            del self._blocked_until[source_id]
            return False

        return True

    def unblock_source(self, source_id: str) -> bool:
        """
        Manually unblock a source.

        Args:
            source_id: Source to unblock

        Returns:
            True if was blocked, False if wasn't blocked
        """
        if source_id in self._blocked_until:
            del self._blocked_until[source_id]
            # Clear violations
            if source_id in self._violations:
                del self._violations[source_id]
            # Reset token bucket to allow immediate requests
            if source_id in self._buckets:
                del self._buckets[source_id]
            return True
        return False

    def get_source_status(self, source_id: str) -> Dict[str, any]:
        """
        Get current rate limit status for a source.

        Args:
            source_id: Source to check

        Returns:
            Status dictionary with limits, usage, and remaining capacity
        """
        tier = self._source_tiers[source_id]
        config = self.tier_configs[tier]

        status = {
            "source_id": source_id,
            "tier": tier.value,
            "limit_per_minute": config.requests_per_minute,
            "burst_capacity": config.burst_capacity,
            "blocked": self.is_blocked(source_id),
        }

        # Add bucket info if exists
        if source_id in self._buckets:
            bucket = self._buckets[source_id]
            status["tokens_available"] = int(bucket.tokens)
            status["tokens_capacity"] = bucket.capacity

        # Add block info if blocked
        if source_id in self._blocked_until:
            now = time.time()
            status["blocked_until"] = self._blocked_until[source_id]
            status["unblock_in_seconds"] = int(self._blocked_until[source_id] - now)

        # Add violation count
        if source_id in self._violations:
            status["violations_last_5min"] = len(self._violations[source_id])

        return status

    def get_statistics(self) -> Dict[str, any]:
        """
        Get overall rate limiting statistics.

        Returns:
            Statistics dictionary
        """
        now = time.time()

        # Count active blocks
        active_blocks = sum(
            1 for unblock_time in self._blocked_until.values()
            if unblock_time > now
        )

        # Count sources by tier
        tier_counts = defaultdict(int)
        for tier in self._source_tiers.values():
            tier_counts[tier.value] += 1

        # Count recent violations
        recent_violations = sum(
            len([t for t in times if now - t < 300])
            for times in self._violations.values()
        )

        return {
            "active_sources": len(self._buckets),
            "blocked_sources": active_blocks,
            "recent_violations": recent_violations,
            "tier_distribution": dict(tier_counts),
        }

    def reset_source(self, source_id: str):
        """
        Reset all state for a source (for testing/admin purposes).

        Args:
            source_id: Source to reset
        """
        if source_id in self._buckets:
            del self._buckets[source_id]
        if source_id in self._blocked_until:
            del self._blocked_until[source_id]
        if source_id in self._violations:
            del self._violations[source_id]
        if source_id in self._source_tiers:
            del self._source_tiers[source_id]
