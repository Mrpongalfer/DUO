# File: ~/Projects/quantum_orchestrator_app/quantum_orchestrator/handlers/__init__.py
"""
Initialization for the handlers package and definition of the @handler decorator.
"""

import inspect
from typing import Callable, Dict, Any, Optional

DEFAULT_HANDLER_METADATA_KEY = "_handler_metadata"


def handler(
    name: Optional[str] = None,
    description: Optional[str] = None,
    parameters: Optional[Dict[str, Any]] = None,
    returns: Optional[Dict[str, Any]] = None,
) -> Callable:
    """
    Decorator to register a function as an action handler.

    Attaches metadata to the function object which is used by the
    Orchestrator's dynamic registration process.

    Args:
        name: The unique name (action type) for this handler. If None,
              uses the function name.
        description: A brief description of what the handler does.
        parameters: A dictionary describing the expected input parameters
                    (e.g., using JSON schema-like definitions).
        returns: A dictionary describing the expected return value structure.

    Returns:
        The decorated function with metadata attached.
    """

    def decorator(func: Callable) -> Callable:
        actual_name = name or func.__name__
        # Use inspect here
        func_doc = inspect.getdoc(func) or "No description provided."
        meta = {
            "name": actual_name,
            "description": description or func_doc,
            "parameters": parameters or {},
            "returns": returns or {},
            "is_handler": True,  # Flag for discovery
            "function_name": func.__name__,
            "module_name": func.__module__,
        }
        setattr(func, DEFAULT_HANDLER_METADATA_KEY, meta)
        setattr(func, "is_handler", True)  # Add flag directly too
        # functools.update_wrapper(decorator, func) # Causes issues sometimes
        return func

    return decorator
