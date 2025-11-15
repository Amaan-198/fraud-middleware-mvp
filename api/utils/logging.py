"""
Logging configuration for the Fraud Middleware API.

Provides structured logging with proper formatting and thread-safety
to prevent log interleaving in multi-worker environments.
"""

import logging
import sys
from typing import Optional


def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """
    Configure logging for the application.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    
    Returns:
        Configured logger instance
    """
    # Get root logger
    logger = logging.getLogger("fraud_middleware")
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove any existing handlers
    logger.handlers.clear()
    
    # Create console handler with structured formatting
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(getattr(logging, log_level.upper()))
    
    # Format: [LEVEL] message
    # Using simple format to match existing log style
    formatter = logging.Formatter('[%(levelname)s] %(message)s')
    handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(handler)
    
    # Prevent propagation to root logger
    logger.propagate = False
    
    return logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Get a logger instance.
    
    Args:
        name: Optional logger name (defaults to fraud_middleware)
    
    Returns:
        Logger instance
    """
    if name:
        return logging.getLogger(f"fraud_middleware.{name}")
    return logging.getLogger("fraud_middleware")


# Initialize default logger
default_logger = setup_logging()
