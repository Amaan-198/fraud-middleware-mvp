"""
Shared Error Response Utilities

Provides consistent error response formatting across all API endpoints.
"""

from typing import Optional, Dict, Any
from fastapi import HTTPException
from api.constants import (
    HTTP_BAD_REQUEST,
    HTTP_NOT_FOUND,
    HTTP_TOO_MANY_REQUESTS,
    HTTP_INTERNAL_ERROR,
)


def not_found_error(resource: str, resource_id: str) -> HTTPException:
    """
    Standard 404 Not Found error.

    Args:
        resource: Type of resource (e.g., "event", "source")
        resource_id: ID of the resource

    Returns:
        HTTPException with 404 status
    """
    return HTTPException(
        status_code=HTTP_NOT_FOUND,
        detail=f"{resource.capitalize()} '{resource_id}' not found",
    )


def bad_request_error(message: str) -> HTTPException:
    """
    Standard 400 Bad Request error.

    Args:
        message: Error message describing what was invalid

    Returns:
        HTTPException with 400 status
    """
    return HTTPException(
        status_code=HTTP_BAD_REQUEST,
        detail=message,
    )


def internal_error(operation: str, error: Exception) -> HTTPException:
    """
    Standard 500 Internal Server Error.

    Args:
        operation: Description of operation that failed
        error: The underlying exception

    Returns:
        HTTPException with 500 status
    """
    return HTTPException(
        status_code=HTTP_INTERNAL_ERROR,
        detail=f"Failed to {operation}: {str(error)}",
    )


def rate_limit_error(retry_after_seconds: int, message: Optional[str] = None) -> Dict[str, Any]:
    """
    Standard 429 Rate Limit response.

    Note: Returns a dict for use with JSONResponse, not HTTPException,
    because rate limiting needs custom headers.

    Args:
        retry_after_seconds: Seconds until rate limit resets
        message: Optional custom message

    Returns:
        Dict for JSONResponse content
    """
    return {
        "error": "rate_limit_exceeded",
        "message": message or "Rate limit exceeded. Please try again later.",
        "retry_after_seconds": retry_after_seconds,
    }
