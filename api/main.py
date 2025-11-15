"""
Allianz Fraud Middleware - FastAPI Application

Main entry point for the fraud detection API.

Features:
- Real-time fraud detection (customer protection)
- Institute-level security monitoring (breach prevention)
- Rate limiting and API protection
- SOC analyst workflow tools
"""

import time
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from api.routes import decision, security, sessions, demo_sessions
# Import shared singletons
from api.singletons import rate_limiter, security_engine, event_store

app = FastAPI(
    title="Allianz Fraud Middleware",
    description="Real-time fraud detection with sub-100ms latency + Institute Security",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware for demo UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Singletons are imported from api.singletons module (shared across entire app)
# This ensures middleware and routes use the SAME instances


# Security monitoring middleware
@app.middleware("http")
async def security_monitoring_middleware(request: Request, call_next):
    """
    Monitor all API requests for security threats.

    Tracks:
    - Rate limiting
    - API abuse patterns
    - Failed requests
    - Response times
    """
    start_time = time.time()

    # Extract source identifier - prioritize custom header over IP
    # This allows frontend to test specific source IDs without rate-limiting the whole browser
    source_id = request.headers.get("X-Source-ID")
    if not source_id:
        source_id = request.client.host if request.client else "unknown"

    # Check if this is a security test scenario (bypass rate limiting for clean test execution)
    # Security tests use special headers to simulate specific threat patterns
    is_security_test = any([
        request.headers.get("X-Auth-Result"),      # Brute force test
        request.headers.get("X-Records-Accessed"),  # Data exfiltration test
        request.headers.get("X-Access-Time"),      # Insider threat test
    ])

    # Allow certain endpoints to bypass rate limiting (health, docs, security monitoring)
    bypass_paths = [
        "/", "/health", "/docs", "/redoc", "/openapi.json",
        "/v1/security/events", "/v1/security/dashboard", "/v1/security/audit-trail",
        "/v1/security/health", "/v1/decision/health"
    ]
    # Also bypass security endpoint GET requests (monitoring should always work)
    is_security_get = request.url.path.startswith("/v1/security/") and request.method == "GET"
    should_rate_limit = request.url.path not in bypass_paths and not is_security_get and not is_security_test

    # Check rate limit
    if should_rate_limit:
        allowed, metadata = rate_limiter.check_rate_limit(source_id)

        if not allowed:
            # Log blocked request
            event_store.log_api_access(
                source_id=source_id,
                endpoint=request.url.path,
                method=request.method,
                status_code=429,
                response_time_ms=0,
                ip_address=source_id,
                blocked=True,
                metadata=metadata
            )

            # Monitor with security engine and store any events
            security_event = security_engine.monitor_api_request(
                source_id=source_id,
                endpoint=request.url.path,
                success=False,
                response_time_ms=0,
                metadata={"blocked_reason": metadata["reason"]}
            )

            # Store security event if detected
            if security_event:
                event_store.store_event(security_event.to_dict())

                # If event requires blocking (HIGH or CRITICAL), persist block to database
                if security_event.threat_level >= 3:  # HIGH or CRITICAL
                    event_store.block_source(
                        source_id=source_id,
                        reason=security_event.description,
                        threat_level=security_event.threat_level,
                        auto_blocked=True
                    )

            # Return rate limit response
            return JSONResponse(
                status_code=429,
                content={
                    "error": "rate_limit_exceeded",
                    "message": metadata["message"],
                    "retry_after_seconds": metadata["retry_after_seconds"]
                },
                headers={
                    "Retry-After": str(metadata["retry_after_seconds"])
                }
            )

    # Process request
    try:
        response = await call_next(request)
        success = response.status_code < 400

        # Calculate latency
        latency_ms = (time.time() - start_time) * 1000

        # Log API access
        event_store.log_api_access(
            source_id=source_id,
            endpoint=request.url.path,
            method=request.method,
            status_code=response.status_code,
            response_time_ms=latency_ms,
            ip_address=source_id,
            blocked=False
        )

        # Monitor with security engine (skip only for health/docs paths, not security tests)
        should_monitor = request.url.path not in bypass_paths and not is_security_get
        if should_monitor:
            security_event = None

            # Check for authentication attempt (brute force detection)
            # PRIORITY 1: Brute force is most specific
            auth_result = request.headers.get("X-Auth-Result")
            if auth_result:
                auth_event = security_engine.monitor_authentication(
                    source_id=source_id,
                    success=(auth_result.lower() == "success"),
                    metadata={"endpoint": request.url.path}
                )
                if auth_event:
                    security_event = auth_event
                    # Don't continue to API request monitoring - brute force is the specific threat
                    # (API request monitoring would trigger rate limiting on rapid auth attempts)

            # Check for data access (exfiltration detection)
            # PRIORITY 2: Data exfiltration is also specific
            if not security_event:  # Only check if no brute force detected
                records_accessed = request.headers.get("X-Records-Accessed")
                if records_accessed:
                    try:
                        data_event = security_engine.monitor_data_access(
                            source_id=source_id,
                            data_type=request.headers.get("X-Data-Type", "customer_records"),
                            record_count=int(records_accessed),
                            sensitive=True,
                            metadata={"endpoint": request.url.path}
                        )
                        if data_event:
                            security_event = data_event
                            # Don't continue to API request monitoring
                    except ValueError:
                        pass  # Invalid records count

            # Standard API request monitoring (rate limiting, off-hours, etc.)
            # PRIORITY 3: Generic API abuse / insider threat
            # Only check if no specific threat detected above
            if not security_event:
                # Check for simulated off-hours access (for testing)
                metadata = {}
                access_time_header = request.headers.get("X-Access-Time")
                if access_time_header and access_time_header.lower() == "off-hours":
                    metadata["simulate_off_hours"] = True

                # Skip generic API abuse monitoring for specific security tests
                # (brute force and data exfiltration tests shouldn't also trigger api_abuse)
                skip_api_abuse = (
                    request.headers.get("X-Auth-Result") or  # Brute force test
                    request.headers.get("X-Records-Accessed")  # Data exfiltration test
                )

                if not skip_api_abuse:
                    api_event = security_engine.monitor_api_request(
                        source_id=source_id,
                        endpoint=request.url.path,
                        success=success,
                        response_time_ms=latency_ms,
                        metadata=metadata if metadata else None
                    )
                    if api_event:
                        security_event = api_event

            # If security event detected, store it
            if security_event:
                event_store.store_event(security_event.to_dict())

                # If event requires blocking (HIGH or CRITICAL), persist block to database
                if security_event.threat_level >= 3:  # HIGH or CRITICAL
                    event_store.block_source(
                        source_id=source_id,
                        reason=security_event.description,
                        threat_level=security_event.threat_level,
                        auto_blocked=True
                    )

        return response

    except Exception as e:
        # Log failed request
        latency_ms = (time.time() - start_time) * 1000

        event_store.log_api_access(
            source_id=source_id,
            endpoint=request.url.path,
            method=request.method,
            status_code=500,
            response_time_ms=latency_ms,
            ip_address=source_id,
            blocked=False,
            metadata={"error": str(e)}
        )

        raise


# Include routers
app.include_router(decision.router, prefix="/v1", tags=["decisions"])
app.include_router(security.router, prefix="/v1/security", tags=["security"])
app.include_router(sessions.router, prefix="/v1", tags=["sessions"])
app.include_router(demo_sessions.router, prefix="/v1", tags=["demo"])


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "Allianz Fraud Middleware",
        "status": "operational",
        "version": "2.0.0",
        "features": [
            "Customer Fraud Detection",
            "Institute Security Monitoring",
            "Session Behavior Monitoring",
            "Rate Limiting",
            "SOC Analyst Tools"
        ]
    }


@app.get("/health")
async def health():
    """Detailed health check"""
    try:
        # Get security stats
        security_stats = security_engine.get_statistics()
        rate_stats = rate_limiter.get_statistics()

        return {
            "status": "healthy",
            "components": {
                "api": "up",
                "rules_engine": "up",
                "ml_engine": "up",
                "policy_engine": "up",
                "security_engine": "up",
                "rate_limiter": "up",
                "event_store": "up"
            },
            "metrics": {
                "security_events": security_stats["total_events"],
                "blocked_sources": security_stats["blocked_sources"],
                "monitored_sources": security_stats["monitored_sources"],
                "rate_limited_sources": rate_stats["active_sources"]
            }
        }
    except Exception as e:
        return {
            "status": "degraded",
            "error": str(e)
        }
