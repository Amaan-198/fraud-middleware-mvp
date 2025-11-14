"""
Shared Singleton Instances

This module provides single instances of security components that are shared
across the entire application (middleware, routes, background tasks).

IMPORTANT: All modules must import from here to ensure state consistency.
"""

from api.utils.rate_limiter import RateLimiter
from api.utils.security_storage import SecurityEventStore
from api.models.institute_security import InstituteSecurityEngine

# Create singleton instances once
rate_limiter = RateLimiter()
security_engine = InstituteSecurityEngine()
event_store = SecurityEventStore()
