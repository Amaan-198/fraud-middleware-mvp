#!/usr/bin/env python3
"""
FIXED Test Script - Security Detection with Proper Timing

This version includes proper delays between requests to allow
the security monitoring system to track request rates correctly.
"""

import requests
import time
import sys

BASE_URL = "http://localhost:8000"

def test_brute_force():
    """Test brute force detection"""
    print("=" * 70)
    print("TEST 1: Brute Force Detection")
    print("=" * 70)

    source_id = f"test_brute_{int(time.time())}"
    print(f"Source ID: {source_id}")
    print(f"Sending 10 failed authentication attempts...\n")

    for i in range(10):
        try:
            response = requests.post(
                f"{BASE_URL}/v1/decision",
                headers={
                    "Content-Type": "application/json",
                    "X-Source-ID": source_id,
                    "X-Auth-Result": "failed",
                },
                json={
                    "user_id": "test",
                    "device_id": "test_device",
                    "amount": 100,
                    "timestamp": "2024-01-01T00:00:00Z",
                    "location": "Test"
                },
                timeout=5
            )
            print(f"  [{i+1}/10] Status: {response.status_code}")
            time.sleep(0.1)
        except Exception as e:
            print(f"  [{i+1}/10] ERROR: {e}")
            assert False, f"Request failed: {e}"

    # Check for events
    print(f"\nQuerying security events for {source_id}...")
    try:
        response = requests.get(
            f"{BASE_URL}/v1/security/events",
            params={"source_id": source_id, "limit": 20},
            timeout=5
        )
        events = response.json()

        print(f"✓ Found {len(events)} event(s)")
        brute_force_events = [e for e in events if e['threat_type'] == 'brute_force']

        if brute_force_events:
            print(f"\n✅ PASS: Detected {len(brute_force_events)} brute force event(s)")
            for event in brute_force_events[:3]:  # Show first 3
                print(f"   - Level {event['threat_level']}: {event['description']}")
        else:
            print(f"\n❌ FAIL: No brute force events detected")
            assert False, "No brute force events detected"

    except AssertionError:
        raise
    except Exception as e:
        print(f"\n❌ ERROR querying events: {e}")
        assert False, f"Error querying events: {e}"


def test_api_abuse():
    """Test API abuse detection with proper timing"""
    print("\n" + "=" * 70)
    print("TEST 2: API Abuse Detection")
    print("=" * 70)

    source_id = f"test_abuse_{int(time.time())}"
    print(f"Source ID: {source_id}")
    print(f"Sending 110 requests rapidly (using connection pooling)...")
    print(f"Expected: Trigger at 100 requests/minute threshold\n")

    start_time = time.time()
    success_count = 0

    # Create a session for connection pooling (MUCH faster on Windows!)
    session = requests.Session()

    for i in range(110):
        try:
            response = session.post(
                f"{BASE_URL}/v1/decision",
                headers={
                    "Content-Type": "application/json",
                    "X-Source-ID": source_id,
                },
                json={
                    "user_id": "test",
                    "device_id": "test_device",
                    "amount": 10,
                    "timestamp": "2024-01-01T00:00:00Z",
                    "location": "Test"
                },
                timeout=5
            )

            if response.status_code == 200:
                success_count += 1

            # Progress indicator
            if (i + 1) % 25 == 0:
                elapsed = time.time() - start_time
                rate = (i + 1) / (elapsed / 60) if elapsed > 0 else 0
                print(f"  [{i+1}/110] Rate: {rate:.0f} req/min | Successful: {success_count}")

            # Small delay to avoid overwhelming the server
            # On Windows, time.sleep is slow, so we use a tiny value
            time.sleep(0.01)

        except Exception as e:
            print(f"  [{i+1}/110] ERROR: {e}")
            # Continue even on error

    # Close session
    session.close()

    elapsed_time = time.time() - start_time
    actual_rate = 110 / (elapsed_time / 60) if elapsed_time > 0 else 0

    print(f"\n✓ Completed: {success_count}/{110} successful")
    print(f"✓ Total time: {elapsed_time:.2f}s")
    print(f"✓ Actual rate: {actual_rate:.0f} req/min")

    # Wait for events to be processed and stored
    print(f"\nWaiting 2 seconds for event processing...")
    time.sleep(2)

    # Query for events
    print(f"Querying security events for {source_id}...")
    try:
        response = requests.get(
            f"{BASE_URL}/v1/security/events",
            params={"source_id": source_id, "limit": 20},
            timeout=5
        )
        events = response.json()

        print(f"✓ Found {len(events)} event(s)")
        api_abuse_events = [e for e in events if e['threat_type'] == 'api_abuse']

        if api_abuse_events:
            print(f"\n✅ PASS: Detected {len(api_abuse_events)} API abuse event(s)")
            for event in api_abuse_events[:5]:  # Show first 5
                print(f"   - Level {event['threat_level']}: {event['description']}")
        else:
            print(f"\n❌ FAIL: No API abuse events detected")
            if events:
                print(f"   Found other event types: {set(e['threat_type'] for e in events)}")
            assert False, "No API abuse events detected"

    except AssertionError:
        raise
    except Exception as e:
        print(f"\n❌ ERROR querying events: {e}")
        assert False, f"Error querying events: {e}"


def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("FRAUD MIDDLEWARE - SECURITY DETECTION TEST SUITE (FIXED)")
    print("=" * 70)
    print(f"Backend URL: {BASE_URL}")
    print(f"Start time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70 + "\n")

    # Check if backend is running
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✓ Backend is running\n")
        else:
            print(f"⚠ Backend returned status {response.status_code}\n")
    except Exception as e:
        print(f"❌ ERROR: Cannot connect to backend at {BASE_URL}")
        print(f"   {e}")
        print(f"\nMake sure the backend is running:")
        print(f"   python -m uvicorn api.main:app --host 0.0.0.0 --port 8000\n")
        return False

    # Run tests
    results = {}

    try:
        test_brute_force()
        results['brute_force'] = True
    except Exception as e:
        print(f"\n❌ Brute force test crashed: {e}")
        results['brute_force'] = False

    try:
        test_api_abuse()
        results['api_abuse'] = True
    except Exception as e:
        print(f"\n❌ API abuse test crashed: {e}")
        results['api_abuse'] = False

    # Summary
    print("\n" + "=" * 70)
    print("TEST RESULTS SUMMARY")
    print("=" * 70)
    print(f"Brute Force Detection: {'✅ PASS' if results.get('brute_force') else '❌ FAIL'}")
    print(f"API Abuse Detection:   {'✅ PASS' if results.get('api_abuse') else '❌ FAIL'}")
    print("=" * 70)

    all_passed = all(results.values())
    if all_passed:
        print("\n🎉 ALL TESTS PASSED! Security detection is working correctly.")
    else:
        print("\n⚠ SOME TESTS FAILED - Review output above for details")

    print()
    return all_passed


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠ Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
