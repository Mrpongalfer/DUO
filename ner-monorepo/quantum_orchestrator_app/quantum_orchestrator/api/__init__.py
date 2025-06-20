"""
API Service for the Quantum Orchestrator.

This module provides API access to the Quantum Orchestrator functionality.
"""

import threading
import logging
from typing import Any

logger = logging.getLogger(__name__)


def init_api_service(orchestrator_instance: Any = None) -> bool:
    """
    Initialize the API service.

    This function starts a separate thread running the API service,
    providing access to the Quantum Orchestrator functionality.

    Args:
        orchestrator_instance: The orchestrator instance to use

    Returns:
        True if the API service was started successfully, False otherwise
    """
    logger.info("Initializing API service")

    # If no orchestrator instance was provided, try to get the global one
    if orchestrator_instance is None:
        from quantum_orchestrator import get_orchestrator

        orchestrator_instance = get_orchestrator()

    if orchestrator_instance is None:
        logger.error("No orchestrator instance available for API service")
        return False

    # Start API service in a separate thread
    try:
        from .api_server import start_api_server

        api_thread = threading.Thread(
            target=start_api_server, args=(orchestrator_instance,), daemon=True
        )

        api_thread.start()
        logger.info("API service started in background thread")

        return True

    except Exception as e:
        logger.error(f"Failed to start API service: {str(e)}")
        return False
