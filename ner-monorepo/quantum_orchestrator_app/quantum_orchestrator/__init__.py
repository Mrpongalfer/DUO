# File: ~/Projects/quantum_orchestrator_app/quantum_orchestrator/__init__.py
"""
Quantum Orchestrator Package Initialization.

Exposes key components for easy access.
"""

import logging

# import sys # Removed F401 - Add back if needed elsewhere
# import os # Removed F401 - Add back if needed elsewhere

# Imports moved to top
from .games.nexus_omniengine_v3.core.config import Settings, get_settings  # Import CORRECT class name
from .games.nexus_omniengine_v3.core.agent import Orchestrator

# Only import other core components if they need to be directly accessible via
# `from quantum_orchestrator import X`, otherwise import where used.
# from .core.state_manager import StateManager
# from .core.instruction_parser import InstructionParser
# from .core.self_verification import verify_system # Example

__version__ = "0.1.0"  # Define package version

# Set up default logger for the package.
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())  # Avoids "No handler found" warnings

# Define what 'from quantum_orchestrator import *' exposes
__all__ = ["Orchestrator", "Settings", "get_settings"]  # Example

logger.debug(f"Quantum Orchestrator package {__version__} initialized.")
