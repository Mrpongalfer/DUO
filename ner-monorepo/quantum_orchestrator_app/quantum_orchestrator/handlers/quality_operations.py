"""
Quality operation handlers for the Quantum Orchestrator.

Provides handlers for running linters and tests to ensure code quality.
"""

import os
from typing import Any, Dict

from quantum_orchestrator.handlers import handler
from quantum_orchestrator.utils.logging_utils import get_logger
from quantum_orchestrator.utils.path_resolver import resolve_path
from quantum_orchestrator.utils.security import sanitize_path
from quantum_orchestrator.services.quality_service import (
    run_linter_service,
    run_tests_service,
)

logger = get_logger(__name__)


@handler(
    name="run_linter",
    description="Runs a linter on the specified code or files",
    parameters={
        "code": {"type": "string", "description": "Code to lint", "default": ""},
        "path": {
            "type": "string",
            "description": "Path to file or directory to lint",
            "default": "",
        },
        "linter": {
            "type": "string",
            "description": "Linter to use (flake8, black)",
            "default": "flake8",
        },
        "fix": {
            "type": "boolean",
            "description": "Whether to automatically fix issues",
            "default": False,
        },
        "config": {
            "type": "object",
            "description": "Linter configuration",
            "default": {},
        },
    },
    returns={
        "success": {
            "type": "boolean",
            "description": "Whether the operation was successful",
        },
        "issues": {"type": "array", "description": "Detected issues"},
        "fixed_code": {
            "type": "string",
            "description": "Fixed code if fix=true and code was provided",
        },
        "summary": {"type": "object", "description": "Summary of linting results"},
        "error": {"type": "string", "description": "Error message if operation failed"},
    },
)
def run_linter(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run a linter on the specified code or files.

    Args:
        params: Dictionary containing code, path, linter, fix, and config

    Returns:
        Dict containing success flag, issues, fixed_code, summary, and error message if any
    """
    try:
        code = params.get("code", "")
        path = params.get("path", "")
        linter = params.get("linter", "flake8").lower()
        fix = params.get("fix", False)
        config = params.get("config", {})

        # Either code or path must be provided
        if not code and not path:
            return {"success": False, "error": "Either code or path must be provided"}

        # If path is provided, resolve and sanitize it
        if path:
            safe_path = sanitize_path(path)
            if not safe_path:
                return {"success": False, "error": f"Invalid or unsafe path: {path}"}
            path = resolve_path(safe_path)

            # Check if path exists
            if not os.path.exists(path):
                return {"success": False, "error": f"Path does not exist: {path}"}

        # Use the quality service to run the linter
        logger.info(f"Running {linter} linter")
        result = run_linter_service(
            code=code, path=path, linter=linter, fix=fix, config=config
        )

        # Process the result
        if result["success"]:
            return result
        else:
            logger.error(f"Linter failed: {result.get('error', 'Unknown error')}")
            return result

    except Exception as e:
        logger.error(f"Error running linter: {str(e)}")
        return {"success": False, "error": f"Error running linter: {str(e)}"}


@handler(
    name="run_tests",
    description="Runs tests for the specified code or in the specified directory",
    parameters={
        "path": {
            "type": "string",
            "description": "Path to file or directory to test",
            "default": "./",
        },
        "pattern": {
            "type": "string",
            "description": "Test file pattern",
            "default": "test_*.py",
        },
        "framework": {
            "type": "string",
            "description": "Test framework to use (pytest, unittest)",
            "default": "pytest",
        },
        "verbosity": {
            "type": "number",
            "description": "Test verbosity level",
            "default": 2,
        },
        "args": {
            "type": "array",
            "description": "Additional test arguments",
            "default": [],
        },
    },
    returns={
        "success": {"type": "boolean", "description": "Whether the tests passed"},
        "results": {"type": "object", "description": "Test results"},
        "summary": {"type": "object", "description": "Summary of test results"},
        "output": {"type": "string", "description": "Raw test output"},
        "error": {"type": "string", "description": "Error message if operation failed"},
    },
)
def run_tests(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run tests for the specified code or in the specified directory.

    Args:
        params: Dictionary containing path, pattern, framework, verbosity, and args

    Returns:
        Dict containing success flag, results, summary, output, and error message if any
    """
    try:
        path = params.get("path", "./")
        pattern = params.get("pattern", "test_*.py")
        framework = params.get("framework", "pytest").lower()
        verbosity = params.get("verbosity", 2)
        args = params.get("args", [])

        # Resolve and sanitize path
        safe_path = sanitize_path(path)
        if not safe_path:
            return {"success": False, "error": f"Invalid or unsafe path: {path}"}
        path = resolve_path(safe_path)

        # Check if path exists
        if not os.path.exists(path):
            return {"success": False, "error": f"Path does not exist: {path}"}

        # Use the quality service to run the tests
        logger.info(f"Running tests with {framework}")
        result = run_tests_service(
            path=path,
            pattern=pattern,
            framework=framework,
            verbosity=verbosity,
            args=args,
        )

        # Process the result
        if result["success"]:
            return result
        else:
            logger.error(f"Tests failed: {result.get('error', 'Unknown error')}")
            return result

    except Exception as e:
        logger.error(f"Error running tests: {str(e)}")
        return {"success": False, "error": f"Error running tests: {str(e)}"}
