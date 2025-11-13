"""
Manual test script for Rules Engine integration
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000/v1"

def test_normal_transaction():
    """Test a normal transaction that should be allowed"""
    print("\n=== Test 1: Normal Transaction ===")
    data = {
        "user_id": "user_normal_123",
        "device_id": "device_123",
        "amount": 100.0,
        "timestamp": datetime.now().isoformat(),
        "location": "New York"
    }

    response = requests.post(f"{BASE_URL}/decision", json=data)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

    result = response.json()
    assert result["decision_code"] != 4, "Normal transaction should not be blocked"
    assert len(result["rule_flags"]) == 0 or "denied" not in str(result["rule_flags"]), \
        "Normal user should not trigger deny list"
    print("✓ PASSED")


def test_denied_user():
    """Test a transaction from a denied user (should be blocked)"""
    print("\n=== Test 2: Denied User ===")
    data = {
        "user_id": "fraud_user_1",  # This is in the deny list
        "device_id": "device_123",
        "amount": 100.0,
        "timestamp": datetime.now().isoformat(),
        "location": "New York"
    }

    response = requests.post(f"{BASE_URL}/decision", json=data)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

    result = response.json()
    assert result["decision_code"] == 4, "Denied user should be blocked"
    assert "denied_user" in result["rule_flags"], "Should have denied_user flag"
    print("✓ PASSED")


def test_denied_device():
    """Test a transaction from a denied device (should be blocked)"""
    print("\n=== Test 3: Denied Device ===")
    data = {
        "user_id": "user_normal_123",
        "device_id": "device_blacklisted_1",  # This is in the deny list
        "amount": 100.0,
        "timestamp": datetime.now().isoformat(),
        "location": "New York"
    }

    response = requests.post(f"{BASE_URL}/decision", json=data)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

    result = response.json()
    assert result["decision_code"] == 4, "Denied device should be blocked"
    assert "denied_device" in result["rule_flags"], "Should have denied_device flag"
    print("✓ PASSED")


def test_denied_ip():
    """Test a transaction from a denied IP (should be blocked)"""
    print("\n=== Test 4: Denied IP ===")
    data = {
        "user_id": "user_normal_123",
        "device_id": "device_123",
        "ip_address": "192.168.1.66",  # This is in the deny list
        "amount": 100.0,
        "timestamp": datetime.now().isoformat(),
        "location": "New York"
    }

    response = requests.post(f"{BASE_URL}/decision", json=data)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

    result = response.json()
    assert result["decision_code"] == 4, "Denied IP should be blocked"
    assert "denied_ip" in result["rule_flags"], "Should have denied_ip flag"
    print("✓ PASSED")


def test_high_amount():
    """Test a large amount transaction (should trigger review)"""
    print("\n=== Test 5: Large Amount ===")
    data = {
        "user_id": "user_large_amount",
        "device_id": "device_456",
        "amount": 15000.0,  # Above review_large_amount threshold
        "timestamp": datetime.now().isoformat(),
        "location": "New York"
    }

    response = requests.post(f"{BASE_URL}/decision", json=data)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

    result = response.json()
    assert "amount_large" in result["rule_flags"], "Large amount should trigger amount_large flag"
    print("✓ PASSED")


def test_velocity_user():
    """Test user velocity limits"""
    print("\n=== Test 6: User Velocity ===")
    user_id = "velocity_test_user"

    # Send 11 transactions in quick succession (limit is 10/hour)
    for i in range(11):
        data = {
            "user_id": user_id,
            "device_id": f"device_{i}",
            "amount": 50.0,
            "timestamp": datetime.now().isoformat(),
            "location": "New York"
        }
        response = requests.post(f"{BASE_URL}/decision", json=data)

        if i < 10:
            print(f"Transaction {i+1}: {response.json()['decision_code']}")
        else:
            # The 11th transaction should be blocked
            print(f"Transaction {i+1} (should be blocked): {response.json()['decision_code']}")
            result = response.json()
            assert result["decision_code"] == 4, "11th transaction should be blocked"
            assert "velocity_user_1h" in result["rule_flags"], "Should have velocity_user_1h flag"

    print("✓ PASSED")


if __name__ == "__main__":
    print("Testing Rules Engine Integration")
    print("=" * 50)

    try:
        # Check if server is running
        response = requests.get("http://localhost:8000/health")
        print(f"Server health: {response.json()}")

        # Run tests
        test_normal_transaction()
        test_denied_user()
        test_denied_device()
        test_denied_ip()
        test_high_amount()
        test_velocity_user()

        print("\n" + "=" * 50)
        print("All tests passed! ✓")

    except requests.exceptions.ConnectionError:
        print("\nERROR: Could not connect to server.")
        print("Please start the server with: uvicorn api.main:app --reload")
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
