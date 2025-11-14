#!/usr/bin/env python3
"""Test script to verify security detection is working"""

import requests
import time
import json

BASE_URL = "http://localhost:8000"

def test_brute_force():
    """Test brute force detection"""
    print("=" * 60)
    print("Testing Brute Force Detection")
    print("=" * 60)

    source_id = f"test_brute_{int(time.time())}"
    print(f"Source ID: {source_id}")

    # Send 10 failed auth attempts
    print("Sending 10 failed authentication attempts...")
    for i in range(10):
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
            }
        )
        print(f"  Attempt {i+1}: {response.status_code}")
        time.sleep(0.1)

    # Check for events
    print(f"\nChecking for security events for {source_id}...")
    response = requests.get(f"{BASE_URL}/v1/security/events?source_id={source_id}&limit=10")
    events = response.json()

    print(f"Events found: {len(events)}")
    for event in events:
        print(f"  - {event['threat_type']} (level {event['threat_level']}): {event['description']}")

    return len(events) > 0

def test_api_abuse():
    """Test API abuse detection"""
    print("\n" + "=" * 60)
    print("Testing API Abuse Detection")
    print("=" * 60)

    source_id = f"test_abuse_{int(time.time())}"
    print(f"Source ID: {source_id}")

    # Send rapid requests
    print("Sending 120 rapid requests...")
    for i in range(120):
        response = requests.post(
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
            }
        )
        if (i + 1) % 20 == 0:
            print(f"  Sent {i+1}/120 (status: {response.status_code})")

    # Check for events
    print(f"\nChecking for security events for {source_id}...")
    response = requests.get(f"{BASE_URL}/v1/security/events?source_id={source_id}&limit=10")
    events = response.json()

    print(f"Events found: {len(events)}")
    for event in events:
        print(f"  - {event['threat_type']} (level {event['threat_level']}): {event['description']}")

    return len(events) > 0

if __name__ == "__main__":
    try:
        print("Security Detection Test Suite\n")

        # Test 1: Brute Force
        bf_works = test_brute_force()

        # Test 2: API Abuse
        abuse_works = test_api_abuse()

        # Summary
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"Brute Force Detection: {'✅ WORKING' if bf_works else '❌ FAILED'}")
        print(f"API Abuse Detection: {'✅ WORKING' if abuse_works else '❌ FAILED'}")

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
