"""
Institute Security Demo Scenarios

Demonstrates the new security features:
1. API abuse detection
2. Brute force protection
3. Data exfiltration monitoring
4. SOC analyst workflow
5. Rate limiting
"""

import sys
import time
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.models.institute_security import InstituteSecurityEngine, ThreatLevel, ThreatType
from api.utils.rate_limiter import RateLimiter, RateLimitTier
from api.utils.security_storage import SecurityEventStore


def print_header(title: str):
    """Print formatted header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_event(event):
    """Pretty print security event"""
    if event:
        print(f"\n🚨 SECURITY EVENT DETECTED:")
        print(f"   Type: {event.threat_type}")
        print(f"   Level: {event.threat_level} ({ThreatLevel(event.threat_level).name})")
        print(f"   Source: {event.source_identifier}")
        print(f"   Description: {event.description}")
        print(f"   Requires Review: {event.requires_review}")
    else:
        print("   ✓ No threat detected")


def scenario_1_api_abuse():
    """Scenario 1: API Abuse Detection"""
    print_header("Scenario 1: API Abuse Detection")
    print("\nSimulating high-volume API requests from a single source...")

    engine = InstituteSecurityEngine()
    source_id = "abusive_api_client"

    # Normal requests (no alert)
    print("\n1. Normal usage (50 requests in 1 minute):")
    for _ in range(50):
        event = engine.monitor_api_request(
            source_id=source_id,
            endpoint="/v1/decision",
            success=True,
            response_time_ms=45.0
        )
    print_event(event)

    # High volume (warning)
    print("\n2. High volume (120 requests - WARNING threshold):")
    event = None
    for _ in range(120):
        event = engine.monitor_api_request(
            source_id=source_id,
            endpoint="/v1/decision",
            success=True,
            response_time_ms=45.0
        )
    print_event(event)

    # Critical volume (auto-block)
    print("\n3. Critical volume (550 requests - AUTO-BLOCK):")
    event = None
    for _ in range(550):
        event = engine.monitor_api_request(
            source_id=source_id,
            endpoint="/v1/decision",
            success=True,
            response_time_ms=45.0
        )
    print_event(event)
    print(f"\n   Source blocked: {engine.is_source_blocked(source_id)}")


def scenario_2_brute_force():
    """Scenario 2: Brute Force Attack Detection"""
    print_header("Scenario 2: Brute Force Attack Detection")
    print("\nSimulating multiple failed authentication attempts...")

    engine = InstituteSecurityEngine()
    attacker_ip = "203.0.113.42"

    # 3 failed attempts (no alert yet)
    print("\n1. First 3 failed login attempts:")
    for i in range(3):
        event = engine.monitor_authentication(
            source_id=attacker_ip,
            success=False,
            auth_method="password"
        )
    print_event(event)

    # 6 failed attempts (warning)
    print("\n2. 6 failed attempts (WARNING):")
    event = None
    for i in range(6):
        event = engine.monitor_authentication(
            source_id=attacker_ip,
            success=False,
            auth_method="password"
        )
    print_event(event)

    # 12 failed attempts (critical + block)
    print("\n3. 12 failed attempts (CRITICAL + AUTO-BLOCK):")
    event = None
    for i in range(12):
        event = engine.monitor_authentication(
            source_id=attacker_ip,
            success=False,
            auth_method="password"
        )
    print_event(event)
    print(f"\n   Attacker blocked: {engine.is_source_blocked(attacker_ip)}")

    # Successful login clears counter
    print("\n4. Demonstrating successful login clears counter:")
    legitimate_user = "user_12345"
    for _ in range(3):
        engine.monitor_authentication(legitimate_user, success=False)
    print("   - 3 failed attempts recorded")

    event = engine.monitor_authentication(legitimate_user, success=True)
    print("   - Successful authentication")
    print_event(event)

    # Next failure starts fresh
    event = engine.monitor_authentication(legitimate_user, success=False)
    print("   - Next failure starts fresh count")
    print_event(event)


def scenario_3_data_exfiltration():
    """Scenario 3: Data Exfiltration Detection"""
    print_header("Scenario 3: Data Exfiltration Monitoring")
    print("\nSimulating unusual data access patterns...")

    engine = InstituteSecurityEngine()
    insider_threat = "analyst_smith"

    # Establish normal baseline
    print("\n1. Establishing normal access pattern (10 records, 10 times):")
    for _ in range(10):
        engine.monitor_data_access(
            source_id=insider_threat,
            data_type="customer_records",
            record_count=10,
            sensitive=False
        )
    print("   ✓ Baseline established: ~10 records per access")

    # Unusual volume
    print("\n2. Sudden spike to 100 records (10x normal):")
    event = engine.monitor_data_access(
        source_id=insider_threat,
        data_type="customer_records",
        record_count=100,
        sensitive=False
    )
    print_event(event)

    # Sensitive data exfiltration (critical)
    print("\n3. Large sensitive data access:")
    event = engine.monitor_data_access(
        source_id=insider_threat,
        data_type="pii_data",
        record_count=150,
        sensitive=True
    )
    print_event(event)


def scenario_4_rate_limiting():
    """Scenario 4: Rate Limiting in Action"""
    print_header("Scenario 4: Rate Limiting Demonstration")
    print("\nTesting different rate limit tiers...")

    limiter = RateLimiter()

    # Test FREE tier
    print("\n1. FREE tier (20/min, burst 10):")
    free_user = "free_tier_user"
    limiter.set_source_tier(free_user, RateLimitTier.FREE)

    allowed_count = 0
    for i in range(25):
        allowed, metadata = limiter.check_rate_limit(free_user)
        if allowed:
            allowed_count += 1

    print(f"   Allowed: {allowed_count}/25 requests")
    print(f"   Status: {limiter.get_source_status(free_user)['tokens_available']} tokens remaining")

    # Test PREMIUM tier
    print("\n2. PREMIUM tier (500/min, burst 100):")
    premium_user = "premium_user"
    limiter.set_source_tier(premium_user, RateLimitTier.PREMIUM)

    allowed_count = 0
    for i in range(100):
        allowed, metadata = limiter.check_rate_limit(premium_user)
        if allowed:
            allowed_count += 1

    print(f"   Allowed: {allowed_count}/100 requests")

    # Demonstrate blocking
    print("\n3. Rate limit violations trigger temporary block:")
    violator = "repeat_violator"

    # Trigger 3 violations
    for violation in range(3):
        for _ in range(50):
            limiter.check_rate_limit(violator)
        time.sleep(0.01)

    allowed, metadata = limiter.check_rate_limit(violator)
    print(f"   Blocked: {not allowed}")
    if not allowed:
        print(f"   Retry after: {metadata['retry_after_seconds']} seconds")
        print(f"   Reason: {metadata['message']}")


def scenario_5_soc_workflow():
    """Scenario 5: SOC Analyst Workflow"""
    print_header("Scenario 5: SOC Analyst Workflow")
    print("\nDemonstrating security operations workflow...")

    engine = InstituteSecurityEngine()
    store = SecurityEventStore()

    # Generate various security events
    print("\n1. Generating security events...")

    # Brute force
    for _ in range(7):
        engine.monitor_authentication("attacker_1", success=False)

    # API abuse
    for _ in range(150):
        engine.monitor_api_request("abuser_1", "/v1/decision", True, 45.0)

    # Data access
    for _ in range(10):
        engine.monitor_data_access("insider_1", "records", 10, False)
    engine.monitor_data_access("insider_1", "records", 100, True)

    # Get events requiring review
    print("\n2. Events requiring SOC review:")
    review_events = engine.get_events_requiring_review()
    print(f"   Total events flagged: {len(review_events)}")

    for i, event in enumerate(review_events[:5], 1):
        print(f"\n   Event {i}:")
        print(f"     Type: {event['threat_type']}")
        print(f"     Level: {ThreatLevel(event['threat_level']).name}")
        print(f"     Source: {event['source_identifier']}")
        print(f"     Description: {event['description']}")

    # Get statistics
    print("\n3. Security Dashboard Statistics:")
    stats = engine.get_statistics()
    print(f"   Total Events: {stats['total_events']}")
    print(f"   Blocked Sources: {stats['blocked_sources']}")
    print(f"   Events Requiring Review: {stats['events_requiring_review']}")
    print(f"   Monitored Sources: {stats['monitored_sources']}")

    # Risk profiling
    print("\n4. Source Risk Profiles:")
    for source_id in ["attacker_1", "abuser_1", "insider_1"]:
        profile = engine.get_source_risk_profile(source_id)
        print(f"\n   {source_id}:")
        print(f"     Risk Score: {profile['risk_score']}/100")
        print(f"     Blocked: {profile['is_blocked']}")
        print(f"     Recent Events: {profile['recent_events']}")
        print(f"     Threats: {profile['threat_breakdown']}")


def scenario_6_integration():
    """Scenario 6: Full Stack Integration"""
    print_header("Scenario 6: Complete Integration Example")
    print("\nSimulating real-world security monitoring...")

    engine = InstituteSecurityEngine()
    limiter = RateLimiter()
    store = SecurityEventStore()

    # Simulate various users/systems
    users = {
        "legitimate_user": {"tier": RateLimitTier.BASIC, "behavior": "normal"},
        "power_user": {"tier": RateLimitTier.PREMIUM, "behavior": "high_volume"},
        "suspicious_user": {"tier": RateLimitTier.BASIC, "behavior": "suspicious"},
        "attacker": {"tier": RateLimitTier.FREE, "behavior": "malicious"},
    }

    print("\n1. Simulating mixed traffic pattern...")

    for user_id, config in users.items():
        limiter.set_source_tier(user_id, config["tier"])

        if config["behavior"] == "normal":
            # Normal usage
            for _ in range(10):
                allowed, _ = limiter.check_rate_limit(user_id)
                if allowed:
                    engine.monitor_api_request(user_id, "/v1/decision", True, 45.0)

        elif config["behavior"] == "high_volume":
            # High but legitimate volume
            for _ in range(100):
                allowed, _ = limiter.check_rate_limit(user_id)
                if allowed:
                    engine.monitor_api_request(user_id, "/v1/decision", True, 42.0)

        elif config["behavior"] == "suspicious":
            # Off-hours data access
            engine._user_access_patterns[user_id]["hourly_distribution"][14] = 50
            for _ in range(20):
                engine.monitor_api_request(user_id, "/admin/export", True, 120.0)

        elif config["behavior"] == "malicious":
            # Brute force
            for _ in range(15):
                engine.monitor_authentication(user_id, success=False)

    # Summary
    print("\n2. Security Summary:")
    print(f"\n   Total Events: {engine.get_statistics()['total_events']}")
    print(f"   Blocked Sources: {engine.get_statistics()['blocked_sources']}")

    print("\n3. High-Risk Sources:")
    for user_id in users.keys():
        profile = engine.get_source_risk_profile(user_id)
        if profile['risk_score'] > 20:
            print(f"\n   {user_id}:")
            print(f"     Risk Score: {profile['risk_score']}")
            print(f"     Status: {'BLOCKED' if profile['is_blocked'] else 'ACTIVE'}")

    print("\n4. Rate Limit Status:")
    for user_id in users.keys():
        status = limiter.get_source_status(user_id)
        print(f"\n   {user_id}:")
        print(f"     Tier: {status['tier']}")
        print(f"     Blocked: {status['blocked']}")


def main():
    """Run all demo scenarios"""
    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 10 + "INSTITUTE SECURITY DEMONSTRATION" + " " * 26 + "║")
    print("║" + " " * 15 + "Allianz Fraud Middleware v2.0" + " " * 24 + "║")
    print("╚" + "═" * 68 + "╝")

    scenarios = [
        ("API Abuse Detection", scenario_1_api_abuse),
        ("Brute Force Protection", scenario_2_brute_force),
        ("Data Exfiltration Monitoring", scenario_3_data_exfiltration),
        ("Rate Limiting", scenario_4_rate_limiting),
        ("SOC Analyst Workflow", scenario_5_soc_workflow),
        ("Full Integration", scenario_6_integration),
    ]

    print("\nAvailable Scenarios:")
    for i, (name, _) in enumerate(scenarios, 1):
        print(f"  {i}. {name}")

    print("\nRunning all scenarios...\n")

    for name, scenario_func in scenarios:
        try:
            scenario_func()
            time.sleep(0.5)  # Pause between scenarios
        except Exception as e:
            print(f"\n❌ Error in {name}: {str(e)}")

    print("\n")
    print("=" * 70)
    print("  ✅ DEMO COMPLETE")
    print("=" * 70)
    print("\nKey Takeaways:")
    print("  • Institute-level security protects the organization itself")
    print("  • Automatic threat detection and blocking")
    print("  • Comprehensive audit trail for compliance")
    print("  • SOC analyst tools for investigation and response")
    print("  • Rate limiting prevents API abuse")
    print("\nFor production deployment, see docs/INTEGRATION.md")
    print()


if __name__ == "__main__":
    main()
