"""
Shared Constants for Fraud Middleware

This module centralizes all magic numbers and strings used throughout the
application to improve maintainability and reduce errors.
"""

from enum import IntEnum


class DecisionCode(IntEnum):
    """
    Fraud decision codes returned to clients.

    These codes indicate the recommended action for a transaction.
    """
    ALLOW = 0       # Transaction approved - low/no fraud risk
    MONITOR = 1     # Allow but log for review - slight risk
    STEP_UP = 2     # Require additional authentication
    REVIEW = 3      # Hold for manual review - high risk
    BLOCK = 4       # Reject transaction - fraud detected


# Decision code descriptions for API responses
DECISION_CODE_DESCRIPTIONS = {
    DecisionCode.ALLOW: "Transaction approved",
    DecisionCode.MONITOR: "Transaction allowed with monitoring",
    DecisionCode.STEP_UP: "Additional authentication required",
    DecisionCode.REVIEW: "Transaction flagged for manual review",
    DecisionCode.BLOCK: "Transaction blocked due to fraud risk",
}


# HTTP Status Codes (for clarity in error handling)
HTTP_OK = 200
HTTP_BAD_REQUEST = 400
HTTP_UNAUTHORIZED = 401
HTTP_FORBIDDEN = 403
HTTP_NOT_FOUND = 404
HTTP_TOO_MANY_REQUESTS = 429
HTTP_INTERNAL_ERROR = 500
HTTP_SERVICE_UNAVAILABLE = 503


# API Version
API_VERSION = "2.0.0"


# Performance Targets (for monitoring and alerts)
TARGET_LATENCY_MS = 60.0  # P95 target for fraud decision pipeline
TARGET_RULES_LATENCY_MS = 200.0
TARGET_ML_LATENCY_MS = 40.0
TARGET_POLICY_LATENCY_MS = 10.0
