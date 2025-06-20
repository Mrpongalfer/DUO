"""
Logging Utilities for the Quantum Orchestrator.

Provides a consistent logging interface across the system.
"""

import os
import logging
import sys
from typing import Optional

# Configure logging format
DEFAULT_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


def setup_logging(
    log_level: Optional[int] = None, log_format: Optional[str] = None
) -> None:
    """
    Set up logging for the entire application.

    Args:
        log_level: Optional log level to set
        log_format: Optional log format string
    """
    # Use the configure_root_logger function to avoid duplication
    configure_root_logger(log_level=log_level, log_format=log_format)

    # Set up additional loggers for external libraries
    for logger_name in ["urllib3", "watchdog", "asyncio", "requests"]:
        logging.getLogger(logger_name).setLevel(logging.WARNING)


def get_logger(name: str, log_level: Optional[int] = None) -> logging.Logger:
    """
    Get a configured logger instance.

    Args:
        name: Name of the logger, typically __name__
        log_level: Optional log level to set

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Set log level from environment variable or parameter or default to INFO
    if log_level is None:
        env_level = os.environ.get("LOG_LEVEL", "INFO").upper()
        try:
            log_level = getattr(logging, env_level)
        except AttributeError:
            log_level = logging.INFO

    logger.setLevel(log_level)

    # Add handler if not already present
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(DEFAULT_LOG_FORMAT)
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


def configure_root_logger(
    log_level: Optional[int] = None, log_format: Optional[str] = None
) -> None:
    """
    Configure the root logger for the application.

    Args:
        log_level: Optional log level to set
        log_format: Optional log format string
    """
    if log_level is None:
        env_level = os.environ.get("LOG_LEVEL", "INFO").upper()
        try:
            log_level = getattr(logging, env_level)
        except AttributeError:
            log_level = logging.INFO

    if log_format is None:
        log_format = DEFAULT_LOG_FORMAT

    # Configure the root logger
    logging.basicConfig(level=log_level, format=log_format, stream=sys.stdout)


def get_request_logger(request_id: str) -> logging.Logger:
    """
    Get a logger for tracking a specific request.

    Args:
        request_id: Unique identifier for the request

    Returns:
        Logger with request context
    """
    logger = get_logger(f"request.{request_id}")

    # Add request ID to all log messages
    class RequestAdapter(logging.LoggerAdapter):
        def process(self, msg, kwargs):
            return f"[Request: {request_id}] {msg}", kwargs

    return RequestAdapter(logger, {})
