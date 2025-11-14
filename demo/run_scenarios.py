#!/usr/bin/env python3
"""
Demo Scenario Runner

Executes demo fraud detection scenarios and displays results.
Validates behavior against expectations in DEMO_SCENARIOS.md.

Usage:
    python demo/run_scenarios.py                    # Run all scenarios
    python demo/run_scenarios.py --scenario normal  # Run specific scenario
    python demo/run_scenarios.py --verbose          # Show detailed output
"""

import sys
import json
import time
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.models.rules import RulesEngine
from api.models.ml_engine import MLEngine
from api.models.policy import PolicyEngine


@dataclass
class ScenarioResult:
    """Result from running a scenario"""
    scenario_name: str
    decision_code: int
    score: float
    ml_score: float
    rule_flags: List[str]
    top_features: List[Dict[str, Any]]
    reasons: List[str]
    latency_ms: float
    passed: bool
    expected_decision: Optional[int] = None
    expected_score_range: Optional[List[float]] = None
    failure_reasons: List[str] = None

    def __post_init__(self):
        if self.failure_reasons is None:
            self.failure_reasons = []


class FraudDemoRunner:
    """Runner for fraud detection demo scenarios"""

    def __init__(self):
        """Initialize engines"""
        self.rules_engine = RulesEngine()
        self.ml_engine = MLEngine()
        self.policy_engine = PolicyEngine()

        # Load scenarios
        scenarios_path = Path(__file__).parent / "scenarios.json"
        with open(scenarios_path, 'r') as f:
            self.scenarios = json.load(f)

    def reset_state(self):
        """Reset feature extraction state for clean scenario runs"""
        from api.utils.features import reset_feature_state
        reset_feature_state()

    def run_transaction(self, transaction: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run a single transaction through the fraud pipeline.

        Args:
            transaction: Transaction data dict

        Returns:
            Result dict with decision, scores, and metadata
        """
        start_time = time.time()

        # Stage 1: Rules
        rules_result = self.rules_engine.evaluate(transaction)

        # If blocked by rules, return immediately
        if rules_result.action.value == "block":
            latency_ms = (time.time() - start_time) * 1000
            return {
                "decision_code": 4,
                "score": 1.0,
                "ml_score": None,
                "rule_flags": rules_result.reasons,
                "top_features": [],
                "reasons": rules_result.reasons,
                "latency_ms": round(latency_ms, 2)
            }

        # Stage 2: ML
        ml_result = self.ml_engine.predict(transaction)

        # Stage 3: Policy
        rules_dict = {
            "action": rules_result.action.value,
            "flags": rules_result.reasons,
            "blocked": False
        }
        decision = self.policy_engine.decide(rules_dict, ml_result)

        latency_ms = (time.time() - start_time) * 1000

        return {
            "decision_code": decision["decision_code"],
            "score": decision["score"],
            "ml_score": ml_result.get("score"),
            "rule_flags": rules_result.reasons,
            "top_features": ml_result.get("top_features", []),
            "reasons": decision["reasons"],
            "latency_ms": round(latency_ms, 2)
        }

    def run_scenario(self, scenario_key: str, verbose: bool = False) -> ScenarioResult:
        """
        Run a specific scenario.

        Args:
            scenario_key: Key identifying the scenario
            verbose: Whether to print detailed output

        Returns:
            ScenarioResult with outcome and validation
        """
        if scenario_key not in self.scenarios:
            raise ValueError(f"Unknown scenario: {scenario_key}")

        # Reset state for clean, reproducible results
        self.reset_state()

        scenario = self.scenarios[scenario_key]

        if verbose:
            print(f"\n{'='*80}")
            print(f"Running: {scenario['name']}")
            print(f"Description: {scenario['description']}")
            print(f"{'='*80}")

        # Handle multi-transaction scenarios (like velocity attack)
        if "transactions" in scenario:
            # Run all transactions in sequence
            results = []
            for txn in scenario["transactions"]:
                result = self.run_transaction(txn)
                results.append(result)

            # Return the last transaction's result
            final_result = results[-1]
        else:
            # Single transaction scenario
            final_result = self.run_transaction(scenario["transaction"])

        # Validate against expectations
        expected = scenario.get("expected", {})
        passed = True
        failure_reasons = []

        # Check decision code
        expected_code = expected.get("decision_code")
        if expected_code is not None and final_result["decision_code"] != expected_code:
            passed = False
            failure_reasons.append(
                f"Decision code mismatch: got {final_result['decision_code']}, "
                f"expected {expected_code}"
            )

        # Check score range
        expected_range = expected.get("score_range")
        if expected_range is not None:
            score = final_result["score"]
            if not (expected_range[0] <= score <= expected_range[1]):
                passed = False
                failure_reasons.append(
                    f"Score {score:.3f} outside expected range "
                    f"[{expected_range[0]}, {expected_range[1]}]"
                )

        # Check latency
        max_latency = expected.get("max_latency_ms")
        if max_latency is not None and final_result["latency_ms"] > max_latency:
            passed = False
            failure_reasons.append(
                f"Latency {final_result['latency_ms']:.2f}ms exceeds "
                f"max {max_latency}ms"
            )

        return ScenarioResult(
            scenario_name=scenario["name"],
            decision_code=final_result["decision_code"],
            score=final_result["score"],
            ml_score=final_result["ml_score"] or 0.0,
            rule_flags=final_result["rule_flags"],
            top_features=final_result["top_features"],
            reasons=final_result["reasons"],
            latency_ms=final_result["latency_ms"],
            passed=passed,
            expected_decision=expected_code,
            expected_score_range=expected_range,
            failure_reasons=failure_reasons
        )

    def print_result(self, result: ScenarioResult, verbose: bool = False):
        """Print scenario result in a formatted way"""

        # Decision code names
        decision_names = {
            0: "ALLOW",
            1: "MONITOR",
            2: "STEP-UP",
            3: "REVIEW",
            4: "BLOCK"
        }

        # Color codes for terminal
        GREEN = '\033[92m'
        YELLOW = '\033[93m'
        RED = '\033[91m'
        BLUE = '\033[94m'
        RESET = '\033[0m'
        BOLD = '\033[1m'

        # Status indicator
        status_icon = f"{GREEN}✓{RESET}" if result.passed else f"{RED}✗{RESET}"

        print(f"\n{BOLD}{result.scenario_name}{RESET} {status_icon}")
        print(f"{'─'*80}")

        # Decision
        decision_name = decision_names.get(result.decision_code, "UNKNOWN")
        decision_color = {
            0: GREEN,
            1: BLUE,
            2: YELLOW,
            3: YELLOW,
            4: RED
        }.get(result.decision_code, RESET)

        print(f"Decision:     {decision_color}{decision_name} ({result.decision_code}){RESET}")

        # Scores
        score_color = GREEN if result.score < 0.35 else YELLOW if result.score < 0.75 else RED
        print(f"Score:        {score_color}{result.score:.3f}{RESET}")

        if result.ml_score:
            print(f"ML Score:     {result.ml_score:.3f}")

        # Latency
        latency_color = GREEN if result.latency_ms < 60 else YELLOW if result.latency_ms < 90 else RED
        print(f"Latency:      {latency_color}{result.latency_ms:.2f}ms{RESET}")

        # Rule flags
        if result.rule_flags:
            print(f"\nRule Flags:   {', '.join(result.rule_flags)}")

        # Top features
        if result.top_features and verbose:
            print(f"\nTop Features:")
            for feat in result.top_features[:3]:
                print(f"  - {feat['name']}: {feat['value']:.3f} "
                      f"(contribution: {feat.get('contribution', 0):.3f})")

        # Reasons (in verbose mode)
        if verbose and result.reasons:
            print(f"\nReasons:")
            for reason in result.reasons[:5]:
                print(f"  - {reason}")

        # Validation info
        if result.expected_decision is not None:
            exp_name = decision_names.get(result.expected_decision, "UNKNOWN")
            print(f"\nExpected:     {exp_name} ({result.expected_decision}), "
                  f"score in {result.expected_score_range}")

        # Failure reasons
        if not result.passed and result.failure_reasons:
            print(f"\n{RED}Validation Failures:{RESET}")
            for reason in result.failure_reasons:
                print(f"  {RED}•{RESET} {reason}")

    def run_all_scenarios(self, verbose: bool = False) -> List[ScenarioResult]:
        """
        Run all scenarios.

        Args:
            verbose: Whether to print detailed output

        Returns:
            List of ScenarioResult objects
        """
        results = []

        print(f"\n{'='*80}")
        print(f"{'FRAUD DETECTION DEMO SCENARIOS':^80}")
        print(f"{'='*80}")

        for scenario_key in self.scenarios.keys():
            result = self.run_scenario(scenario_key, verbose=verbose)
            results.append(result)
            self.print_result(result, verbose=verbose)

        # Summary
        print(f"\n{'='*80}")
        print(f"{'SUMMARY':^80}")
        print(f"{'='*80}")

        passed = sum(1 for r in results if r.passed)
        total = len(results)

        GREEN = '\033[92m'
        RED = '\033[91m'
        RESET = '\033[0m'

        status_color = GREEN if passed == total else RED
        print(f"\nScenarios: {status_color}{passed}/{total} passed{RESET}")

        avg_latency = sum(r.latency_ms for r in results) / len(results)
        print(f"Avg Latency: {avg_latency:.2f}ms")
        print(f"Max Latency: {max(r.latency_ms for r in results):.2f}ms")

        # Score distribution
        print(f"\nScore Distribution:")
        for result in results:
            bar_length = int(result.score * 50)
            bar = '█' * bar_length + '░' * (50 - bar_length)
            print(f"  {result.scenario_name[:30]:<30} {bar} {result.score:.3f}")

        return results


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Run fraud detection demo scenarios")
    parser.add_argument(
        "--scenario",
        type=str,
        help="Run specific scenario (e.g., 'normal_transaction')"
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed output including features and reasons"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all available scenarios"
    )

    args = parser.parse_args()

    runner = FraudDemoRunner()

    # List scenarios
    if args.list:
        print("\nAvailable scenarios:")
        for key, scenario in runner.scenarios.items():
            print(f"  {key:<25} - {scenario['name']}")
        return

    # Run specific scenario
    if args.scenario:
        result = runner.run_scenario(args.scenario, verbose=args.verbose)
        runner.print_result(result, verbose=args.verbose)
        sys.exit(0 if result.passed else 1)

    # Run all scenarios
    results = runner.run_all_scenarios(verbose=args.verbose)

    # Exit with error if any failed
    all_passed = all(r.passed for r in results)
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
