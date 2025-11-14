#!/usr/bin/env python3
"""
Comprehensive Playground Test Suite
Tests all major features to ensure everything works
"""

import asyncio
import aiohttp
import json
from datetime import datetime

API_BASE = "http://localhost:8000"

class PlaygroundTester:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.results = []

    def test_result(self, name, passed, details=""):
        status = "✓ PASS" if passed else "✗ FAIL"
        self.results.append({
            "name": name,
            "passed": passed,
            "details": details
        })
        if passed:
            self.passed += 1
            print(f"  {status} - {name}")
        else:
            self.failed += 1
            print(f"  {status} - {name}: {details}")

    async def test_health(self, session):
        """Test basic health check"""
        try:
            async with session.get(f"{API_BASE}/health") as response:
                data = await response.json()
                self.test_result(
                    "Health Check",
                    response.status == 200 and data.get("status") == "healthy",
                    f"Status: {data.get('status')}"
                )
                return True
        except Exception as e:
            self.test_result("Health Check", False, str(e))
            return False

    async def test_fraud_decision(self, session):
        """Test fraud decision endpoint"""
        try:
            transaction = {
                "user_id": "test_user_playground",
                "device_id": "test_device",
                "amount": 100.0,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "location": "Test Location"
            }

            async with session.post(
                f"{API_BASE}/v1/decision",
                json=transaction,
                headers={"X-Source-ID": "playground_test"}
            ) as response:
                data = await response.json()
                self.test_result(
                    "Fraud Decision",
                    response.status == 200 and "decision" in data,
                    f"Decision: {data.get('decision')}, Score: {data.get('fraud_score')}"
                )
        except Exception as e:
            self.test_result("Fraud Decision", False, str(e))

    async def test_security_events(self, session):
        """Test security events endpoint"""
        try:
            async with session.get(
                f"{API_BASE}/v1/security/events",
                headers={"X-Source-ID": "playground_test"}
            ) as response:
                data = await response.json()
                self.test_result(
                    "Security Events",
                    response.status == 200 and isinstance(data, list),
                    f"Retrieved {len(data)} events"
                )
        except Exception as e:
            self.test_result("Security Events", False, str(e))

    async def test_security_dashboard(self, session):
        """Test security dashboard"""
        try:
            async with session.get(
                f"{API_BASE}/v1/security/dashboard",
                headers={"X-Source-ID": "playground_test"}
            ) as response:
                data = await response.json()
                self.test_result(
                    "Security Dashboard",
                    response.status == 200 and "total_events" in data,
                    f"Events: {data.get('total_events')}"
                )
        except Exception as e:
            self.test_result("Security Dashboard", False, str(e))

    async def test_review_queue(self, session):
        """Test review queue"""
        try:
            async with session.get(
                f"{API_BASE}/v1/security/events/review-queue",
                headers={"X-Source-ID": "playground_test"}
            ) as response:
                data = await response.json()
                self.test_result(
                    "Review Queue",
                    response.status == 200 and "total_pending" in data,
                    f"Pending: {data.get('total_pending')}"
                )
        except Exception as e:
            self.test_result("Review Queue", False, str(e))

    async def test_rate_limit_status(self, session):
        """Test rate limit status"""
        try:
            source_id = "playground_test"
            async with session.get(
                f"{API_BASE}/v1/security/rate-limits/{source_id}",
                headers={"X-Source-ID": source_id}
            ) as response:
                data = await response.json()
                self.test_result(
                    "Rate Limit Status",
                    response.status == 200 and "tier" in data,
                    f"Tier: {data.get('tier')}"
                )
        except Exception as e:
            self.test_result("Rate Limit Status", False, str(e))

    async def test_rate_limit_resilience(self, session):
        """Test rate limiting with burst"""
        try:
            source_id = "burst_resilience_test"
            results = []

            # Send 50 requests
            for i in range(50):
                try:
                    txn = {
                        "user_id": f"user_{i}",
                        "device_id": "test_device",
                        "amount": 10.0,
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                        "location": "Test"
                    }

                    async with session.post(
                        f"{API_BASE}/v1/decision",
                        json=txn,
                        headers={"X-Source-ID": source_id},
                        timeout=aiohttp.ClientTimeout(total=5)
                    ) as response:
                        results.append(response.status)
                except Exception:
                    results.append(0)

            allowed = results.count(200)
            rate_limited = results.count(429)

            self.test_result(
                "Rate Limit Resilience (50 requests)",
                allowed > 0 and rate_limited > 0,
                f"Allowed: {allowed}, Rate Limited: {rate_limited}, Total: {len(results)}"
            )

        except Exception as e:
            self.test_result("Rate Limit Resilience", False, str(e))

    async def test_blocked_sources(self, session):
        """Test blocked sources endpoint"""
        try:
            async with session.get(
                f"{API_BASE}/v1/security/sources/blocked",
                headers={"X-Source-ID": "playground_test"}
            ) as response:
                data = await response.json()
                self.test_result(
                    "Blocked Sources",
                    response.status == 200 and isinstance(data, list),
                    f"Blocked: {len(data)} sources"
                )
        except Exception as e:
            self.test_result("Blocked Sources", False, str(e))

    async def run_all_tests(self):
        """Run all tests"""
        print("\n" + "="*60)
        print("  Security & Fraud Playground - Test Suite")
        print("="*60 + "\n")

        async with aiohttp.ClientSession() as session:
            # Core functionality tests
            print("🔍 Testing Core Functionality...")
            await self.test_health(session)
            await self.test_fraud_decision(session)

            # Security tests
            print("\n🛡️  Testing Security Features...")
            await self.test_security_events(session)
            await self.test_security_dashboard(session)
            await self.test_review_queue(session)
            await self.test_blocked_sources(session)

            # Rate limiting tests
            print("\n⏱️  Testing Rate Limiting...")
            await self.test_rate_limit_status(session)
            await self.test_rate_limit_resilience(session)

        # Summary
        print("\n" + "="*60)
        print(f"  Test Results: {self.passed} passed, {self.failed} failed")
        print("="*60 + "\n")

        if self.failed == 0:
            print("🎉 All tests passed! Playground is ready for demo.\n")
            return True
        else:
            print(f"⚠️  {self.failed} test(s) failed. Review issues above.\n")
            return False


async def main():
    tester = PlaygroundTester()
    success = await tester.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
