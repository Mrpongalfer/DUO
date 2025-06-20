#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# File: scripts/scribe_agent.py (within Omnitide Nexus)
# Project Scribe: Apex Automated Validation Agent v1.1
# Augmented by NAA under Core Team Review - Manifested under Drake Protocol v5.0 Apex
# For The Supreme Master Architect Alix Feronti
# Session Timestamp: 2025-05-10 05:09 AM CDT

"""
Project Scribe: Apex Automated Code Validation & Integration Agent (v1.1)

Executes a validation gauntlet on provided Python code artifacts.
Handles venv, dependencies, audit, format, lint, type check, AI test gen/exec,
AI review, pre-commit hooks, conditional Git commit, and JSON reporting.

V1.1 Augmentations (based on Architect's directives & Core Team review):
- ScribeConfig: Rigorous validation of all critical config settings. Stricter default
  allowed_target_bases for NAI TUI context. Optional tool_paths config.
- ToolRunner: Refactored to return CompletedProcess. Calling steps now parse output.
  Added configurable timeout. Logs more summarized debug info.
- LLMClient: Added retry mechanism for API calls. Enhanced code extraction from
  LLM response with warnings for multiple blocks.
- WorkflowSteps: Updated tool-invoking steps to process CompletedProcess.
  More specific OSError handling in apply_code.
- Reporting: Emphasized human review for LLM outputs in logs/reports.
  Standardized 'details' field in JSON StepResult for better machine parsing.
"""

import argparse
import ast
import inspect  # Not strictly used in V1.1 but good for future introspection
import json
import logging
import os
import re
import shlex
import shutil
import subprocess
import sys
import time  # V1.1: Added for LLM retries
import traceback
from datetime import datetime, timezone
from functools import \
    lru_cache  # Not used in V1.1, consider removal if not planned
from pathlib import Path
from typing import (Any, Callable, Dict, List, Optional, Sequence, Tuple,
                    TypedDict, Union, cast)
from urllib.parse import urlparse  # V1.1: Added for URL validation

# --- Dependency Check ---
try:
    import httpx
    HTTP_LIB: Optional[str] = "httpx"
except ImportError:
    try:
        import requests
        HTTP_LIB = "requests"
    except ImportError:
        HTTP_LIB = None

try:
    import tomllib # Python 3.11+
except ImportError:
    try:
        import tomli as tomllib # Fallback for Python < 3.11
        print("INFO: Scribe is using 'tomli' as 'tomllib' (for Python < 3.11).", file=sys.stderr)
    except ImportError:
        print("FATAL ERROR: Could not import 'tomllib' (Python 3.11+) or 'tomli' (fallback). "
              "Project Scribe requires one of these. For Python < 3.11, please run: pip install tomli on your host and ensure it's in requirements.txt for Docker.", file=sys.stderr)
        sys.exit(1)

# --- Constants ---
APP_NAME: str = "Project Scribe"
APP_VERSION: str = "1.1.0" # V1.1: Version bump
LOG_FORMAT: str = '%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s'
DEFAULT_LOG_LEVEL: str = "INFO"
LOG_LEVELS: List[str] = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
DEFAULT_CONFIG_FILENAME: str = ".scribe.toml"
VENV_DIR_NAME: str = ".venv"
DEFAULT_PYTHON_VERSION: str = "3.11" # Scribe itself needs 3.11+
DEFAULT_REPORT_FORMAT: str = "json"
REPORT_FORMATS: List[str] = ["json", "text"]
DEFAULT_OLLAMA_MODEL: str = "mistral-nemo:12b-instruct-2407-q4_k_m" # Example
DEFAULT_OLLAMA_BASE_URL: str = "http://localhost:11434"
SCRIBE_TEST_DIR: str = "tests/scribe_generated" # Relative to target_dir
DEFAULT_TOOL_TIMEOUT: float = 180.0 # V1.1: Increased default timeout for external tools

# Step Status Constants
STATUS_SUCCESS = "SUCCESS"
STATUS_FAILURE = "FAILURE"
STATUS_WARNING = "WARNING"
STATUS_SKIPPED = "SKIPPED"
STATUS_ADVISORY = "ADVISORY"
STATUS_PENDING = "PENDING"


# Type Definitions for Reporting Clarity
class StepOutputDetails(TypedDict, total=False): # V1.1: More structured details
    tool_name: Optional[str]
    return_code: Optional[int]
    message: Optional[str]
    stdout_summary: Optional[str] # Truncated stdout
    stderr_summary: Optional[str] # Truncated stderr
    # For LLM steps
    llm_model: Optional[str]
    prompt_type: Optional[str]
    response_summary: Optional[str] # e.g., snippet of generated code, or count of review items
    generated_content_path: Optional[str] # e.g., path to saved test file
    # For audit_deps
    vulnerability_count: Optional[int]
    vulnerabilities: Optional[List[Dict]] # Snippet or summary, full data in top-level report
    highest_severity: Optional[str]
    configured_fail_severity: Optional[str]
    # Generic fields
    raw_output: Optional[str] # For steps where primary output is a simple string (e.g. extracted signatures, generated report string)
    issues_found: Optional[List[Dict]] # e.g., for AI review findings
    notes: Optional[List[str]] # e.g., "Human review recommended"

class StepResult(TypedDict):
    name: str
    status: str # From STATUS_ constants
    start_time: str # ISO format UTC
    end_time: str   # ISO format UTC
    duration_seconds: float
    details: Union[str, StepOutputDetails, Dict[str, Any], List[Any], None]
    error_message: Optional[str] # If status is FAILURE, a concise error message

class FinalReport(TypedDict):
    scribe_version: str
    run_id: str
    start_time: str # ISO format UTC
    end_time: str   # ISO format UTC
    total_duration_seconds: float
    overall_status: str # From STATUS_ constants
    target_project_dir: str
    target_file_relative: str
    language: str
    python_version: str
    commit_attempted: bool
    commit_sha: Optional[str]
    steps: List[StepResult]
    # Top-level summaries (can be more detailed here than in individual step details if needed)
    audit_findings: Optional[List[Dict[str, Any]]] # Full audit details
    ai_review_findings: Optional[List[Dict[str, Any]]] # Full AI review details
    test_results_summary: Optional[Dict[str, Any]] # E.g., pytest summary object or full stdout/stderr

# --- Custom Exceptions ---
class ScribeError(Exception):
    """Base exception for Scribe-specific errors."""
    pass

class ScribeConfigurationError(ScribeError):
    """Error related to Scribe configuration."""
    pass

class ScribeInputError(ScribeError):
    """Error related to invalid user inputs."""
    pass

class ScribeEnvironmentError(ScribeError):
    """Error related to environment setup (venv, dependencies)."""
    pass

class ScribeToolError(ScribeError):
    """Error related to external tool execution."""
    pass

class ScribeApiError(ScribeError):
    """Error related to LLM API communication."""
    pass

class ScribeFileSystemError(ScribeError):
    """Error related to file system operations."""
    pass

# --- Logging Setup Function ---
def setup_logging(log_level_str: str, log_file: Optional[str] = None) -> logging.Logger:
    """Configures the Python logging system for console and optional file output."""
    log_level = getattr(logging, log_level_str.upper(), logging.INFO)
    root_logger = logging.getLogger() # Get root logger
    root_logger.setLevel(logging.DEBUG) # Set root to DEBUG to allow handlers to filter

    # Remove any existing handlers to prevent duplicate logs if re-initialized
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
        handler.close()

    logging.Formatter.converter = time.gmtime # Use UTC for log timestamps
    formatter = logging.Formatter(LOG_FORMAT + " (UTC)")

    # Console Handler
    console_handler = logging.StreamHandler(sys.stderr) # Log to stderr by convention
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level) # Console handler respects user-defined log level
    root_logger.addHandler(console_handler)

    # File Handler (optional)
    app_logger_name = APP_NAME # Use the global app name for the logger
    if log_file:
        try:
            log_file_path = Path(log_file).resolve()
            log_file_path.parent.mkdir(parents=True, exist_ok=True) # Ensure log directory exists
            file_handler = logging.FileHandler(log_file_path, mode='a', encoding='utf-8')
            file_handler.setFormatter(formatter)
            file_handler.setLevel(logging.DEBUG) # File handler logs at DEBUG level for maximum detail
            root_logger.addHandler(file_handler)
            # Log initial message to both if file logging is setup
            logging.getLogger(app_logger_name).info(
                f"Console logging level: {log_level_str}. Detailed (DEBUG) log file active: {log_file_path}"
            )
        except Exception as e:
            # If file logging fails, log error to console (if possible) and continue without it
            logging.getLogger(app_logger_name).error(
                f"Failed to initialize file logging to '{log_file}': {e}. Continuing with console logging only.",
                exc_info=False # Keep console clean from this specific traceback unless DEBUG for console
            )
    else:
        logging.getLogger(app_logger_name).info(
            f"Console logging level: {log_level_str}. No log file configured."
        )

    return logging.getLogger(app_logger_name)


# --- Configuration Manager ---
class ScribeConfig:
    """Handles loading, validation, and access to Scribe configuration data."""
    def __init__(self, config_path_override: Optional[str] = None, is_nai_context: bool = False): # V1.1: Added is_nai_context
        self._logger = logging.getLogger(f"{APP_NAME}.ScribeConfig")
        self._is_nai_context = is_nai_context
        self._config_path: Optional[Path] = self._find_config_file(config_path_override)
        self._config: Dict[str, Any] = self._load_and_validate_config() # Loads defaults, then file, then validates

    def _find_config_file(self, path_override: Optional[str]) -> Optional[Path]:
        """Finds the Scribe configuration file based on override or default locations."""
        potential_paths: List[Path] = []
        if path_override:
            p = Path(path_override).resolve()
            if p.is_file():
                potential_paths.append(p) # Explicit path override is tried first if valid
            else:
                self._logger.warning(
                    f"Explicit config path override '{path_override}' provided but not found or not a file. "
                    "Will search default locations."
                )

        # Default search locations (e.g., current working directory)
        potential_paths.append(Path.cwd() / DEFAULT_CONFIG_FILENAME)
        # Add other potential paths if needed (e.g., user's home config directory)
        # potential_paths.append(Path.home() / ".config" / "scribe" / DEFAULT_CONFIG_FILENAME)

        for path in potential_paths:
            try:
                if path.is_file():
                    self._logger.info(f"Using Scribe configuration file: {path}")
                    return path
            except OSError as e: # Catch potential permission errors, etc.
                self._logger.warning(f"Cannot access potential config file {path}: {e}")
        
        # No config file found in specified or default locations
        self._logger.info(
            f"No '{DEFAULT_CONFIG_FILENAME}' found in override path or standard locations. "
            "Scribe will operate using internal default configurations."
        )
        return None

    def _get_default_config(self) -> Dict[str, Any]: # V1.1: Centralized defaults
        """Provides the hardcoded default configuration for Scribe."""
        # V1.1: NAI context specific default for allowed_target_bases
        allowed_bases = ["/workspace"] if self._is_nai_context else [str(Path.home()), "/tmp", str(Path.cwd())] # Added cwd for standalone
        if self._is_nai_context:
            self._logger.info(
                "NAI TUI context inferred (or specified): Restricting 'allowed_target_bases' default to '/workspace'."
            )
        else:
            self._logger.info(
                f"Standard context: 'allowed_target_bases' default includes home, /tmp, and current working dir: {allowed_bases}"
            )


        return {
            "allowed_target_bases": allowed_bases,
            "fail_on_audit_severity": "high", # Options: None (cast to str if read from TOML), "critical", "high", "moderate", "low"
            "fail_on_lint_critical": True,
            "fail_on_mypy_error": True,
            "fail_on_test_failure": True,
            "ollama_base_url": os.environ.get("OLLAMA_API_BASE", DEFAULT_OLLAMA_BASE_URL),
            "ollama_model": os.environ.get("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL),
            "ollama_request_timeout": 180.0, # Increased default
            "ollama_api_retries": 2,
            "ollama_api_retry_delay": 5.0,
            "default_tool_timeout": DEFAULT_TOOL_TIMEOUT,
            "commit_message_template": "feat(Scribe): Apply v1.1 validated changes to {target_file}",
            "test_generation_prompt_template": (
                "You are an expert Python test generation assistant. Generate concise and effective pytest unit tests for the provided code. "
                "Focus on testing the public API based on the function and class signatures. "
                "Ensure all generated test code is syntactically correct Python and follows pytest conventions. "
                "Provide ONLY the Python code for the tests, enclosed in a single ```python ... ``` block.\n\n"
                "Target File: {target_file_path}\n"
                "Code Snippet (may be truncated for brevity in prompt):\n```python\n{code_content}\n```\n"
                "Key Signatures for Test Focus:\n{signatures}\n\n"
                "Generated Pytest Code (ensure it is a single, complete Python code block):"
            ),
            "review_prompt_template": (
                "You are an expert Python code reviewer. Perform a thorough review of the following code. "
                "Identify potential bugs, style issues, security vulnerabilities, and areas for improvement. "
                "Provide your findings as a JSON list of objects. Each object MUST have 'severity' (string: 'critical', 'high', 'moderate', 'low', or 'info'), "
                "'description' (string: a clear explanation of the issue), and 'location' (string: e.g., function name, class name, or specific line number if applicable, otherwise 'general' or file name). "
                "Return ONLY the raw JSON list of these objects, without any surrounding text or markdown.\n\n"
                "Target File: {target_file_path}\n"
                "Code:\n```python\n{code_content}\n```\n\n"
                "Review Findings (as a raw JSON list of objects):"
            ),
            "validation_steps": [ # Default execution order
                "validate_inputs", "setup_environment", "install_deps", "audit_deps", "apply_code",
                "format_code", "lint_code", "type_check", "extract_signatures", "generate_tests",
                "save_tests", "execute_tests", "review_code", "run_precommit", "commit_changes",
                "generate_report"
            ],
            "tool_paths": {} # Example: {"ruff": "/usr/local/bin/ruff"}
        }
        # --- Configuration Manager (Continuation) ---
# class ScribeConfig:
#     ... (__init__, _find_config_file, _get_default_config from Part 1) ...

    def _load_and_validate_config(self) -> Dict[str, Any]:
        """Loads configuration from file (if found) and merges with defaults, then validates."""
        defaults = self._get_default_config()
        config_data: Dict[str, Any]

        if not self._config_path:
            self._logger.info("No Scribe configuration file found. Using internal default settings.")
            config_data = defaults
        else:
            try:
                with open(self._config_path, "rb") as f: # TOML must be read in binary mode
                    loaded_config_from_file = tomllib.load(f)
                # Merge loaded config with defaults; settings from file override defaults.
                config_data = self._merge_configs(defaults, loaded_config_from_file)
                self._logger.info(f"Successfully loaded and merged configuration from: {self._config_path}")
            except (tomllib.TOMLDecodeError, OSError) as e:
                self._logger.error(
                    f"Error reading or parsing TOML configuration file '{self._config_path}': {e}. "
                    "Scribe will proceed with internal default configurations."
                )
                config_data = defaults # Fallback to defaults if file is corrupt or unreadable

        # V1.1: Perform rigorous validation after loading and merging.
        try:
            self._validate_loaded_config(config_data)
            self._logger.debug("Scribe configuration successfully validated.")
        except ScribeConfigurationError as e:
            # Log the specific configuration error and re-raise to halt Scribe execution
            # if the configuration is critically flawed.
            self._logger.critical(f"Scribe configuration validation failed: {e}. Cannot continue.")
            raise
        
        return config_data

    def _merge_configs(self, base_config: Dict, updating_config: Dict) -> Dict:
        """
        Recursively merges the updating_config into the base_config.
        Keys from updating_config will overwrite keys in base_config.
        If both values are dictionaries, they are merged recursively.
        """
        merged = base_config.copy()
        for key, value in updating_config.items():
            if isinstance(value, dict) and isinstance(merged.get(key), dict):
                merged[key] = self._merge_configs(merged[key], value)
            else:
                merged[key] = value # Value from updates_config takes precedence
        return merged

    def _validate_loaded_config(self, config: Dict[str, Any]): # V1.1: Significantly enhanced validation
        """Performs comprehensive validation of the loaded Scribe configuration."""
        self._logger.debug("Performing detailed validation of Scribe configuration settings...")

        # Validate 'allowed_target_bases'
        bases = config.get("allowed_target_bases")
        if not isinstance(bases, list) or not all(isinstance(b_item, str) for b_item in bases):
            raise ScribeConfigurationError("'allowed_target_bases' must be a list of strings in .scribe.toml.")
        try:
            # Resolve paths to ensure they are absolute and normalized.
            config["allowed_target_bases"] = [str(Path(p_str).expanduser().resolve()) for p_str in bases]
        except Exception as e:
            raise ScribeConfigurationError(f"Error resolving one or more paths in 'allowed_target_bases': {e}")

        # Validate 'fail_on_audit_severity'
        allowed_severities = [None, "critical", "high", "moderate", "low"] # None means do not fail on any audit
        # TOML files might load 'null' as a string "None" or an actual None type depending on parser/how it's written
        # ScribeConfig's get_str will handle type conversion, but validation should check against expected values.
        # For this, we allow the string "null" or actual None.
        audit_sev = config.get("fail_on_audit_severity")
        if audit_sev is not None and not isinstance(audit_sev, str): # if not None, must be string from TOML
            raise ScribeConfigurationError(f"'fail_on_audit_severity' must be a string (e.g., 'high', 'critical') or null.")
        if audit_sev is not None and str(audit_sev).lower() not in [str(s).lower() if s is not None else "null" for s in allowed_severities] + ["null"]:
             # Add "null" to the list of valid string representations from TOML
            raise ScribeConfigurationError(f"'fail_on_audit_severity' ('{audit_sev}') must be one of {allowed_severities} (or 'null').")


        # Validate boolean flags
        for bool_key_str in ["fail_on_lint_critical", "fail_on_mypy_error", "fail_on_test_failure"]:
            if not isinstance(config.get(bool_key_str), bool):
                raise ScribeConfigurationError(f"Config option '{bool_key_str}' must be a boolean (true/false).")

        # Validate Ollama URL
        ollama_url_str = config.get("ollama_base_url")
        if not isinstance(ollama_url_str, str) or not ollama_url_str:
            raise ScribeConfigurationError("'ollama_base_url' must be a non-empty string.")
        try:
            parsed_url_obj = urlparse(ollama_url_str)
            if not all([parsed_url_obj.scheme, parsed_url_obj.netloc]) or parsed_url_obj.scheme not in ['http', 'https']:
                raise ValueError("URL must include a valid scheme (http/https) and netloc (hostname/IP).")
        except ValueError as e:
            raise ScribeConfigurationError(f"'ollama_base_url' ('{ollama_url_str}') is not a valid HTTP/HTTPS URL: {e}")

        # Validate Ollama Model
        if not isinstance(config.get("ollama_model"), str) or not config.get("ollama_model"):
            raise ScribeConfigurationError("'ollama_model' must be a non-empty string.")

        # Validate numeric settings (timeouts, retries)
        for num_key_str, is_positive_only, is_float_allowed in [
            ("ollama_request_timeout", True, True),
            ("ollama_api_retries", False, False), # Retries can be 0, must be int
            ("ollama_api_retry_delay", True, True),
            ("default_tool_timeout", True, True)
        ]:
            val_num = config.get(num_key_str)
            expected_type_msg = "a number (integer or float)" if is_float_allowed else "an integer"
            if not isinstance(val_num, (int, float) if is_float_allowed else int):
                raise ScribeConfigurationError(f"Config option '{num_key_str}' must be {expected_type_msg}.")
            if is_positive_only and val_num <= 0:
                raise ScribeConfigurationError(f"Config option '{num_key_str}' must be a positive value.")
            if not is_positive_only and val_num < 0: # e.g. retries can be 0 but not negative
                raise ScribeConfigurationError(f"Config option '{num_key_str}' must be a non-negative value.")

        # Validate prompt templates
        for tmpl_key_str in ["test_generation_prompt_template", "review_prompt_template", "commit_message_template"]:
            if not isinstance(config.get(tmpl_key_str), str) or not config.get(tmpl_key_str):
                raise ScribeConfigurationError(f"Config option '{tmpl_key_str}' must be a non-empty string.")

        # Validate 'validation_steps' (list of strings; actual key validity checked in ScribeAgent.run)
        steps_list = config.get("validation_steps")
        if not isinstance(steps_list, list) or not all(isinstance(s_item, str) for s_item in steps_list):
            raise ScribeConfigurationError("'validation_steps' must be a list of strings.")
        if not steps_list:
            raise ScribeConfigurationError("'validation_steps' cannot be empty; at least one step must be defined (e.g., 'generate_report').")


        # Validate 'tool_paths' (optional, but if present, must be a dict of str:str)
        tool_paths_config = config.get("tool_paths")
        if tool_paths_config is not None: # It's optional
            if not isinstance(tool_paths_config, dict):
                raise ScribeConfigurationError("'tool_paths' must be a dictionary (table in TOML) if provided.")
            for tool_name_key, tool_path_val in tool_paths_config.items():
                if not isinstance(tool_name_key, str) or not isinstance(tool_path_val, str):
                    raise ScribeConfigurationError(
                        "Each entry in 'tool_paths' must map a string tool name to a string path. "
                        f"Found invalid entry: {tool_name_key}: {tool_path_val}"
                    )
                # Further validation could check if Path(tool_path_val) looks like a valid path, but ToolRunner will handle actual existence.

        self._logger.debug("Scribe configuration validation passed for all checked settings.")

    # Getter methods for accessing configuration values
    def get(self, key: str, default: Any = None) -> Any:
        return self._config.get(key, default)

    def get_list(self, key: str, default: Optional[List[Any]] = None) -> List[Any]:
        value = self._config.get(key, default if default is not None else [])
        return value if isinstance(value, list) else (default if default is not None else [])

    def get_str(self, key: str, default: str = "") -> str:
        value = self._config.get(key, default)
        return str(value) if value is not None else default

    def get_bool(self, key: str, default: bool = False) -> bool:
        value = self._config.get(key, default)
        # Handle string "true"/"false" from TOML if not parsed as bool directly
        if isinstance(value, str):
            if value.lower() == 'true': return True
            if value.lower() == 'false': return False
        return value if isinstance(value, bool) else default

    def get_float(self, key: str, default: float = 0.0) -> float:
        value = self._config.get(key, default)
        try:
            return float(value)
        except (ValueError, TypeError):
            self._logger.warning(f"Could not parse config value for '{key}' ('{value}') as float. Using default: {default}.")
            return default

    def get_int(self, key: str, default: int = 0) -> int:
        value = self._config.get(key, default)
        try:
            return int(float(value)) # Allow float string to be parsed as int after conversion
        except (ValueError, TypeError):
            self._logger.warning(f"Could not parse config value for '{key}' ('{value}') as int. Using default: {default}.")
            return default

    @property
    def config_path(self) -> Optional[Path]:
        """The path to the loaded configuration file, if any."""
        return self._config_path

    @property
    def is_nai_context(self) -> bool: # V1.1 Helper
        """Indicates if Scribe is operating in a context suggesting NAI TUI (e.g., for specific defaults)."""
        return self._is_nai_context


# --- Tool Runner ---
class ToolRunner:
    """Executes external command-line tools securely and captures their output."""
    def __init__(self, config: ScribeConfig): # V1.1: Takes ScribeConfig for tool_paths & default_tool_timeout
        self._logger = logging.getLogger(f"{APP_NAME}.ToolRunner")
        self._config = config

    def _find_executable(self, executable_name: str, venv_path: Optional[Path] = None) -> Path:
        """
        Finds an executable using configured tool_paths, then venv, then system PATH.
        Raises FileNotFoundError if the executable cannot be located.
        """
        # 1. Check configured tool_paths from ScribeConfig
        configured_tool_paths = self._config.get("tool_paths", {})
        if isinstance(configured_tool_paths, dict) and executable_name in configured_tool_paths:
            custom_path_str = configured_tool_paths[executable_name]
            if isinstance(custom_path_str, str) and custom_path_str.strip():
                custom_path = Path(custom_path_str).expanduser() # Expand ~
                if custom_path.is_file() and os.access(custom_path, os.X_OK):
                    self._logger.debug(f"Using configured path for '{executable_name}': {custom_path}")
                    return custom_path.resolve()
                else:
                    self._logger.warning(
                        f"Configured path for '{executable_name}' ('{custom_path_str}') is not a file or not executable. "
                        "Falling back to venv/PATH search."
                    )
            else: # Should be caught by ScribeConfig validation, but defensive here
                self._logger.warning(
                    f"Invalid path type or empty path for '{executable_name}' in 'tool_paths' config. Expected non-empty string. "
                    "Falling back to venv/PATH search."
                )

        # 2. Check venv bin directory (if venv_path is provided)
        if venv_path:
            resolved_venv_path = venv_path.resolve()
            if resolved_venv_path.is_dir(): # Ensure venv_path itself is a directory
                bin_dir = resolved_venv_path / ("Scripts" if sys.platform == "win32" else "bin")
                # Check common executable names (e.g., with and without .exe on Windows)
                for suffix in ["", ".exe"] if sys.platform == "win32" else [""]:
                    venv_exec_candidate = bin_dir / f"{executable_name}{suffix}"
                    if venv_exec_candidate.is_file() and os.access(venv_exec_candidate, os.X_OK):
                        self._logger.debug(f"Found '{executable_name}' in venv '{resolved_venv_path}': {venv_exec_candidate}")
                        return venv_exec_candidate.resolve()
            else:
                self._logger.warning(f"Provided venv_path '{venv_path}' is not a directory. Skipping venv search for '{executable_name}'.")


        # 3. Fallback to system PATH using shutil.which
        system_exec_path_str = shutil.which(executable_name)
        if system_exec_path_str:
            self._logger.debug(f"Found '{executable_name}' in system PATH: {system_exec_path_str}")
            return Path(system_exec_path_str).resolve()

        # If not found in any location
        err_msg = (
            f"Executable '{executable_name}' not found. Searched in: "
            f"1. Scribe config 'tool_paths'. "
            f"2. Virtual environment bin ('{venv_path}/bin' or '{venv_path}/Scripts' if venv_path was provided). "
            f"3. System PATH."
        )
        self._logger.error(err_msg)
        raise FileNotFoundError(err_msg)
    # --- Tool Runner (Continuation) ---
# class ToolRunner:
#     ... (__init__, _find_executable from Part 2) ...

    def run_tool(self,
                 command_args: List[str],
                 cwd: Path,
                 venv_path: Optional[Path] = None,
                 env_vars: Optional[Dict[str, str]] = None,
                 timeout: Optional[float] = None
                 ) -> subprocess.CompletedProcess: # V1.1: Returns CompletedProcess
        """
        Runs an external tool using the found executable path.
        V1.1: Returns the CompletedProcess object. Caller interprets output & RC.
              Logs only a brief summary. Uses configurable timeout.
        """
        if not command_args:
            self._logger.critical("ToolRunner.run_tool called with empty command_args.")
            # This is an internal error, should not happen with proper Scribe logic.
            # Return a failed CompletedProcess to allow callers to handle it.
            return subprocess.CompletedProcess(args=[], returncode=127, stdout="", stderr="Internal Scribe Error: run_tool called with no command.")


        executable_name = command_args[0]
        try:
            # _find_executable raises FileNotFoundError if not found, caught by caller
            executable_path = self._find_executable(executable_name, venv_path)
        except FileNotFoundError as e:
            # This exception will be caught by the WorkflowStep method calling run_tool,
            # allowing it to mark the step as SKIPPED or FAILED appropriately.
            # Re-raise it as a ScribeToolError for consistent handling if needed,
            # but FileNotFoundError is often specific enough.
            self._logger.error(f"ToolRunner prerequisite error for '{executable_name}': {e}")
            raise ScribeToolError(f"Executable '{executable_name}' could not be found by ToolRunner.") from e

        full_command_list = [str(executable_path)] + command_args[1:]
        # Use shlex.quote for logging to handle spaces in paths or arguments safely
        quoted_command_str = ' '.join(shlex.quote(str(arg)) for arg in full_command_list)
        self._logger.info(f"Executing via ToolRunner: {quoted_command_str} (in CWD: {cwd})")

        # Prepare the environment for the subprocess
        process_env = os.environ.copy()
        if venv_path: # If a virtual environment is specified, activate it for the subprocess
            resolved_venv_path = venv_path.resolve()
            process_env['VIRTUAL_ENV'] = str(resolved_venv_path)
            venv_bin_dir = resolved_venv_path / ('Scripts' if sys.platform == 'win32' else 'bin')
            process_env['PATH'] = f"{str(venv_bin_dir)}{os.pathsep}{process_env.get('PATH', '')}"
            # It's good practice to remove these if a venv is being activated,
            # to prevent conflicts with the venv's Python interpreter.
            process_env.pop('PYTHONHOME', None)
            process_env.pop('PYTHONPATH', None) # Let the venv define its own PYTHONPATH if necessary

        if env_vars: # Allow overriding or adding specific environment variables
            process_env.update(env_vars)

        # Determine the timeout for the tool execution
        effective_timeout = timeout if timeout is not None else self._config.get_float("default_tool_timeout", DEFAULT_TOOL_TIMEOUT)
        if effective_timeout <= 0: # Ensure timeout is positive, or None if 0 or negative
            self._logger.warning(
                f"Configured/provided tool timeout for '{executable_name}' is {effective_timeout}s. "
                "Using no timeout (None) instead as timeout must be positive."
            )
            effective_timeout = None # subprocess.run uses None for no timeout

        try:
            result = subprocess.run(
                full_command_list,
                cwd=cwd,
                env=process_env,
                capture_output=True, # Capture stdout and stderr
                check=False,         # V1.1: Caller (WorkflowStep) is responsible for checking returncode
                text=True,           # Decode stdout/stderr as text
                encoding='utf-8',    # Specify UTF-8 encoding
                errors='replace',    # Replace problematic characters rather than erroring
                timeout=effective_timeout # Apply the configured timeout
            )
            # V1.1: ToolRunner provides minimal, summarized logging.
            # The calling WorkflowStep method will parse result.stdout/stderr for detailed reporting.
            self._logger.debug(
                f"Tool '{executable_name}' finished. RC={result.returncode}. "
                f"Timeout was {effective_timeout or 'None'}s."
            )
            if result.stdout and self._logger.isEnabledFor(logging.DEBUG): # Only log snippets if DEBUG
                self._logger.debug(f"Tool '{executable_name}' STDOUT (first ~100 chars): {result.stdout[:100].strip().replace(os.linesep, ' ')}")
            if result.stderr and self._logger.isEnabledFor(logging.DEBUG):
                self._logger.debug(f"Tool '{executable_name}' STDERR (first ~100 chars): {result.stderr[:100].strip().replace(os.linesep, ' ')}")

            return result # V1.1: Return the full subprocess.CompletedProcess object

        except subprocess.TimeoutExpired as e:
            self._logger.error(
                f"Tool '{executable_name}' (command: {quoted_command_str}) timed out after {effective_timeout} seconds."
            )
            # Construct a CompletedProcess object to signify timeout for consistent handling by caller
            # stdout/stderr from e might be bytes or None
            stdout_decoded = e.stdout.decode('utf-8', errors='replace') if isinstance(e.stdout, bytes) else (e.stdout or "")
            stderr_decoded = e.stderr.decode('utf-8', errors='replace') if isinstance(e.stderr, bytes) else (e.stderr or "")
            
            # Append timeout message to stderr if it's empty or doesn't already indicate timeout
            timeout_msg = f"TimeoutExpired: Command '{quoted_command_str}' timed out after {effective_timeout} seconds."
            if not stderr_decoded or "TimeoutExpired" not in stderr_decoded :
                stderr_decoded = f"{stderr_decoded}\n{timeout_msg}".strip()
            else: # Already contains timeout info, likely from subprocess itself.
                 stderr_decoded = f"{timeout_msg}\n{stderr_decoded}".strip()


            return subprocess.CompletedProcess(
                args=e.cmd or full_command_list, # e.cmd might be None depending on Python version
                returncode=-1, # Use a specific return code to indicate Scribe-detected timeout
                stdout=stdout_decoded,
                stderr=stderr_decoded
            )
        except Exception as e: # Catch other unexpected errors during subprocess.run
            self._logger.error(f"Unexpected OS error running tool '{executable_name}': {e}", exc_info=True)
            # Raise a ScribeToolError for consistent error handling in workflow steps
            raise ScribeToolError(f"Unexpected OS error while executing '{executable_name}': {e}") from e


# --- Environment Manager ---
class EnvironmentManager:
    """Manages the target project's virtual environment and dependencies."""
    def __init__(self, target_dir: Path, python_version_str: str, tool_runner: ToolRunner, config: ScribeConfig): # V1.1 Added config
        self._logger = logging.getLogger(f"{APP_NAME}.EnvironmentManager")
        self._target_dir = target_dir.resolve() # Ensure it's absolute
        # python_version_str is informational for now, venv uses Scribe's Python.
        self._python_version_str = python_version_str
        self._tool_runner = tool_runner
        self._config = config # V1.1: Needed for default_tool_timeout
        self._venv_path = self._target_dir / VENV_DIR_NAME # .venv directory within the target project

        # These are populated by setup_venv()
        self._venv_python_path: Optional[Path] = None
        self._pip_path: Optional[Path] = None

    @property
    def venv_path(self) -> Path:
        return self._venv_path

    @property
    def python_executable(self) -> Optional[Path]:
        """Path to the Python interpreter within the created/managed venv."""
        return self._venv_python_path

    @property
    def pip_executable(self) -> Optional[Path]:
        """Path to the pip executable within the created/managed venv."""
        return self._pip_path

    def find_venv_executable(self, name: str) -> Optional[Path]:
        """
        Finds an executable (e.g., 'python', 'pip', 'ruff') within the managed venv's bin directory.
        Returns the resolved Path or None if not found or venv doesn't exist.
        """
        if not self._venv_path.is_dir():
            self._logger.debug(f"Venv path '{self._venv_path}' does not exist or is not a directory. Cannot find '{name}'.")
            return None
        
        bin_dir = self._venv_path / ("Scripts" if sys.platform == "win32" else "bin")
        for suffix in ["", ".exe"] if sys.platform == "win32" else [""]:
            exec_path_candidate = bin_dir / f"{name}{suffix}"
            if exec_path_candidate.is_file() and os.access(exec_path_candidate, os.X_OK):
                return exec_path_candidate.resolve()
        self._logger.debug(f"Executable '{name}' not found in venv bin directory: {bin_dir}")
        return None

    def setup_venv(self) -> None: # V1.1: Error handling improved by ToolRunner returning CompletedProcess
        """
        Ensures a virtual environment exists at the target location.
        Creates one if not present and upgrades pip, setuptools, wheel.
        Raises ScribeEnvironmentError on failure.
        """
        self._logger.info(f"Ensuring virtual environment exists in: {self._venv_path}")
        venv_creation_timeout = self._config.get_float("default_tool_timeout", DEFAULT_TOOL_TIMEOUT)

        if not self._venv_path.exists():
            self._logger.info(f"Virtual environment not found at '{self._venv_path}'. Creating new venv...")
            # Use the Python interpreter running Scribe to create the venv.
            # This is generally fine for the NAI Docker context where Scribe's Python is the primary one.
            python_exe_for_venv = sys.executable
            try:
                # ToolRunner will find python_exe_for_venv from system PATH (or Scribe's own venv if Scribe is run in one)
                result = self._tool_runner.run_tool(
                    [python_exe_for_venv, "-m", "venv", str(self._venv_path)],
                    cwd=self._target_dir, # Create venv in context of target project's root
                    timeout=venv_creation_timeout
                )
                if result.returncode != 0:
                    err_msg = f"Failed to create virtual environment (RC={result.returncode}). Stderr: {result.stderr.strip()}"
                    self._logger.error(err_msg)
                    raise ScribeEnvironmentError(err_msg)
                self._logger.info(f"Virtual environment successfully created at {self._venv_path}")
            except ScribeToolError as e: # Catch errors from ToolRunner itself (e.g., python not found, timeout)
                raise ScribeEnvironmentError(f"Failed during venv creation command: {e}") from e
        elif not self._venv_path.is_dir():
            raise ScribeEnvironmentError(f"Path '{self._venv_path}' exists but is not a directory. Cannot use as venv.")
        else:
            self._logger.info(f"Existing virtual environment found at {self._venv_path}.")

        # Confirm python and pip executables exist within the venv
        self._venv_python_path = self.find_venv_executable("python")
        self._pip_path = self.find_venv_executable("pip")

        if not self._venv_python_path or not self._pip_path:
            err_msg = (f"Essential executables (python/pip) not found in venv bin: {self._venv_path}. "
                       "The venv might be corrupted or improperly created.")
            self._logger.error(err_msg)
            raise ScribeEnvironmentError(err_msg)
        self._logger.info(f"Venv Python executable: {self._venv_python_path}")
        self._logger.info(f"Venv Pip executable: {self._pip_path}")

        # Upgrade pip, setuptools, wheel in the venv
        try:
            self._logger.info("Upgrading pip, setuptools, and wheel in the virtual environment...")
            upgrade_cmd_list = [str(self._pip_path), "install", "--disable-pip-version-check", "--upgrade", "pip", "setuptools", "wheel"]
            result = self._tool_runner.run_tool(
                upgrade_cmd_list,
                cwd=self._target_dir, # CWD for pip should generally be project root
                venv_path=self._venv_path, # Ensure pip from venv is used
                timeout=venv_creation_timeout
            )
            if result.returncode != 0:
                # Log as warning, as Scribe might still function if core tools are okay.
                self._logger.warning(
                    f"Failed to upgrade pip/setuptools/wheel in venv (RC={result.returncode}). "
                    f"This may not be critical. Stderr: {result.stderr.strip()}"
                )
            else:
                self._logger.info("pip, setuptools, and wheel upgraded successfully in venv.")
        except ScribeToolError as e:
            self._logger.warning(f"ScribeToolError during pip upgrade in venv (might be non-critical): {e}")


    def install_dependencies(self) -> None: # V1.1: Relies on caller (WorkflowStep) to interpret and report.
        """
        Installs project dependencies using pip from pyproject.toml or requirements.txt.
        Raises ScribeEnvironmentError on critical failure.
        """
        if not self._pip_path:
            raise ScribeEnvironmentError("Pip executable path in venv not set. Cannot install dependencies. Ensure setup_venv ran successfully.")
        
        self._logger.info("Attempting to install project dependencies into venv...")
        dep_install_timeout = self._config.get_float("default_tool_timeout", DEFAULT_TOOL_TIMEOUT)
        pyproject_path = self._target_dir / "pyproject.toml"
        requirements_path = self._target_dir / "requirements.txt"
        install_command_used: Optional[List[str]] = None
        installed_successfully = False

        if pyproject_path.is_file():
            self._logger.info(f"Found 'pyproject.toml'. Attempting editable install with common optional dependency groups.")
            # Try common optional dependency groups for development (e.g., [dev,test,lint])
            # Scribe itself needs tools like Ruff, MyPy, Pytest. If a project uses them via pyproject.toml, this helps.
            dev_groups_to_try = ["[dev,test,lint,format]", "[dev,test,lint]", "[dev,test]", "[dev]", ""] # "" for base install
            install_cmd_base = [str(self._pip_path), "install", "--disable-pip-version-check", "-e"] # Editable install

            for group_suffix_str in dev_groups_to_try:
                current_install_target = f".{group_suffix_str}" # e.g. ".[dev]" or "."
                potential_cmd = install_cmd_base + [current_install_target]
                self._logger.debug(f"Attempting 'pip install' with: {' '.join(shlex.quote(s) for s in potential_cmd)}")
                try:
                    result = self._tool_runner.run_tool(
                        potential_cmd,
                        cwd=self._target_dir,
                        venv_path=self._venv_path,
                        timeout=dep_install_timeout
                    )
                    if result.returncode == 0:
                        install_command_used = potential_cmd
                        installed_successfully = True
                        self._logger.info(f"Successfully installed dependencies using: {' '.join(shlex.quote(s) for s in install_command_used)}")
                        break # Success, no need to try other groups
                    else:
                        self._logger.warning(
                            f"'pip install -e {current_install_target}' failed (RC={result.returncode}). "
                            f"Stderr: {result.stderr.strip()[:300]}... Trying next option if available."
                        )
                except ScribeToolError as e: # Error from ToolRunner itself
                    self._logger.warning(f"Tool error during 'pip install -e {current_install_target}': {e}. Trying next option.")
            
            if not installed_successfully:
                err_msg = "All attempts to install dependencies from 'pyproject.toml' (with/without common dev groups) failed."
                self._logger.error(err_msg)
                raise ScribeEnvironmentError(err_msg)

        elif requirements_path.is_file():
            self._logger.info(f"Found 'requirements.txt'. Installing dependencies from it.")
            install_command_used = [str(self._pip_path), "install", "--disable-pip-version-check", "-r", str(requirements_path)]
            try:
                result = self._tool_runner.run_tool(
                    install_command_used,
                    cwd=self._target_dir,
                    venv_path=self._venv_path,
                    timeout=dep_install_timeout
                )
                if result.returncode != 0:
                    err_msg = f"Failed to install dependencies from 'requirements.txt' (RC={result.returncode}). Stderr: {result.stderr.strip()}"
                    self._logger.error(err_msg)
                    raise ScribeEnvironmentError(err_msg)
                installed_successfully = True
                self._logger.info(f"Successfully installed dependencies using: {' '.join(shlex.quote(s) for s in install_command_used)}")
            except ScribeToolError as e:
                raise ScribeEnvironmentError(f"Tool error during 'pip install -r requirements.txt': {e}") from e
        else:
            self._logger.info(
                "No 'pyproject.toml' or 'requirements.txt' found in target directory. "
                "Skipping project-specific dependency installation step."
            )
            # This is not an error condition; many simple projects or scripts may not have these files.
            return # Successfully skipped

        if not installed_successfully and (pyproject_path.is_file() or requirements_path.is_file()):
            # This state should ideally not be reached if errors above raise ScribeEnvironmentError
            final_err_msg = "Dependency installation was attempted but did not complete successfully."
            self._logger.error(final_err_msg)
            raise ScribeEnvironmentError(final_err_msg)


    def run_pip_audit(self) -> subprocess.CompletedProcess: # V1.1: Returns CompletedProcess
        """
        Runs 'pip audit' in the project's venv to check for vulnerabilities.
        Attempts to install 'pip-audit' if not present.
        Returns the CompletedProcess object; caller interprets results.
        Raises ScribeEnvironmentError on critical setup failure before tool run.
        """
        if not self._pip_path:
            raise ScribeEnvironmentError("Pip executable path in venv not set. Cannot run pip audit.")
        
        self._logger.info("Running 'pip audit' to check for known vulnerabilities in dependencies...")
        audit_timeout = self._config.get_float("default_tool_timeout", DEFAULT_TOOL_TIMEOUT)

        # Attempt to ensure pip-audit is installed in the venv, as it's not always default.
        # Scribe could also list pip-audit in its own requirements for a global version,
        # but installing in project venv is cleaner if it picks up that venv's specific dependencies.
        # However, pip audit typically analyzes the current environment it's run from.
        # For simplicity and to ensure it's available, try installing it.
        install_pip_audit_cmd = [str(self._pip_path), "install", "pip-audit"]
        try:
            self._logger.debug("Ensuring 'pip-audit' is installed in the venv...")
            install_result = self._tool_runner.run_tool(
                install_pip_audit_cmd,
                cwd=self._target_dir, # Context for pip
                venv_path=self._venv_path,
                timeout=audit_timeout # Use same timeout for this preparatory step
            )
            if install_result.returncode != 0:
                self._logger.warning(
                    f"Could not install/confirm 'pip-audit' (RC={install_result.returncode}). "
                    "Audit may fail if tool is not already present. Stderr: {install_result.stderr.strip()[:200]}..."
                )
            else:
                 self._logger.info("'pip-audit' tool is available.")
        except ScribeToolError as e: # ToolRunner error during pip-audit install attempt
            self._logger.warning(f"Error trying to install 'pip-audit': {e}. Audit may fail.")


        # Now run pip audit
        # Using --json format for machine-readable output.
        # --progress-spinner off for cleaner logs when capturing output.
        pip_audit_command = [str(self._pip_path), "audit", "--format", "json", "--progress-spinner", "off"]
        
        # ToolRunner.run_tool will raise ScribeToolError for execution issues (e.g., pip not found, OS error).
        # It does not raise for non-zero exit codes of the tool itself (check=False by default in Scribe's use).
        # The calling WorkflowStep (audit_deps) will interpret the CompletedProcess.
        return self._tool_runner.run_tool(
            pip_audit_command,
            cwd=self._target_dir, # Run in project context
            venv_path=self._venv_path, # Ensure it uses the venv's pip and environment
            timeout=audit_timeout
        )
        # --- LLM Client ---
class LLMClient:
    """Handles communication with the configured Ollama LLM API for AI-assisted tasks."""
    def __init__(self, config: ScribeConfig, cli_args: argparse.Namespace):
        self._logger = logging.getLogger(f"{APP_NAME}.LLMClient")
        self._config = config

        # Prioritize CLI args for Ollama settings, then ScribeConfig, then defaults
        self._base_url = cli_args.ollama_base_url or config.get_str("ollama_base_url", DEFAULT_OLLAMA_BASE_URL)
        self._model = cli_args.ollama_model or config.get_str("ollama_model", DEFAULT_OLLAMA_MODEL)
        
        self._timeout = config.get_float("ollama_request_timeout", 180.0) # Default from ScribeConfig
        self._retries = config.get_int("ollama_api_retries", 2) # V1.1: From ScribeConfig
        self._retry_delay = config.get_float("ollama_api_retry_delay", 5.0) # V1.1: From ScribeConfig

        self._http_client: Optional[httpx.Client] = None # For httpx
        if HTTP_LIB == "httpx":
            try:
                # httpx.Client should be configured here. Ensure base_url doesn't have trailing slashes if endpoint is absolute.
                # For httpx.Client, endpoint in post() is usually relative to base_url.
                self._http_client = httpx.Client(base_url=self._base_url.rstrip('/'), timeout=self._timeout, follow_redirects=True)
                self._logger.info(
                    f"LLMClient (httpx) initialized: URL='{self._base_url}', Model='{self._model}', "
                    f"Timeout={self._timeout}s, Retries={self._retries}, RetryDelay={self._retry_delay}s"
                )
            except Exception as e:
                self._logger.error(f"Failed to initialize httpx client for Ollama: {e}", exc_info=True)
                # If httpx init fails, _call_api will raise ScribeApiError if it's the selected lib.
        elif HTTP_LIB == "requests":
            self._logger.info(
                f"LLMClient (requests) configured: URL='{self._base_url}', Model='{self._model}', "
                f"Timeout={self._timeout}s, Retries={self._retries}, RetryDelay={self._retry_delay}s"
            )
        else: # HTTP_LIB is None
            self._logger.error(
                "CRITICAL: No suitable HTTP library (httpx or requests) found. "
                "LLM-dependent features (test generation, AI review) will be unavailable."
            )
            # Scribe should ideally not start or should disable LLM steps if this happens.
            # Main() function has an early exit for this.


    def _call_api(self, prompt_text: str, output_format_type: Optional[str] = None) -> Dict[str, Any]: # V1.1: Added retries
        """
        Calls the Ollama /api/generate endpoint with the given prompt and model.
        Includes retry logic for transient network errors.
        Raises ScribeApiError on persistent failure or non-transient errors.
        """
        if not HTTP_LIB:
            raise ScribeApiError("No HTTP library (httpx/requests) available to call Ollama API.")
        if HTTP_LIB == "httpx" and not self._http_client: # Check if httpx client was initialized
             raise ScribeApiError("httpx library was selected, but its client failed to initialize. Cannot call Ollama API.")

        # For httpx, endpoint is relative. For requests, we construct full URL.
        api_endpoint_path = "/api/generate"
        full_api_url_for_requests = f"{self._base_url.rstrip('/')}{api_endpoint_path}"

        payload: Dict[str, Any] = {
            "model": self._model,
            "prompt": prompt_text,
            "stream": False # Scribe currently expects a single complete response
        }
        if output_format_type: # e.g., "json" if LLM is asked to output JSON
            payload["format"] = output_format_type

        self._logger.info(
            f"Calling Ollama API: Model='{self._model}', Format='{output_format_type or 'text'}'. "
            f"Prompt Length: ~{len(prompt_text)} chars."
        )
        # Log a snippet of the payload for debugging, being careful with prompt length
        debug_payload = {**payload, 'prompt': payload['prompt'][:200] + ('...' if len(payload['prompt']) > 200 else '')}
        self._logger.debug(f"Ollama API Payload (prompt truncated for log): {json.dumps(debug_payload)}")

        last_seen_exception: Optional[Exception] = None
        for attempt_num in range(self._retries + 1): # Max attempts = retries + 1 initial attempt
            try:
                api_response_json: Dict[str, Any]
                if self._http_client: # Using httpx (preferred)
                    http_response = self._http_client.post(api_endpoint_path, json=payload) # endpoint is relative for httpx.Client
                    http_response.raise_for_status() # Raises HTTPStatusError for 4xx/5xx
                    api_response_json = http_response.json()
                elif HTTP_LIB == "requests": # Using requests as fallback
                    http_response = requests.post(full_api_url_for_requests, json=payload, timeout=self._timeout)
                    http_response.raise_for_status()
                    api_response_json = http_response.json()
                else: # Should have been caught by the check at the start of the function
                    raise ScribeApiError("Internal Scribe Error: HTTP_LIB is unexpectedly None during API call.")

                # Check for Ollama-specific error in the JSON response
                if api_response_json.get("error"):
                    ollama_error_msg = api_response_json['error']
                    self._logger.error(f"Ollama API returned an error in its JSON response: {ollama_error_msg}")
                    raise ScribeApiError(f"Ollama API Error: {ollama_error_msg}")
                
                # Ensure the expected 'response' field is present
                if "response" not in api_response_json:
                    self._logger.error("Ollama API JSON response is missing the required 'response' field.")
                    raise ScribeApiError("Ollama API response format error: 'response' field missing.")

                self._logger.info(f"Ollama API call successful on attempt {attempt_num + 1}.")
                return api_response_json # Success

            except (httpx.ConnectError, requests.exceptions.ConnectionError,
                    httpx.TimeoutException, requests.exceptions.Timeout,
                    httpx.NetworkError, requests.exceptions.ChunkedEncodingError, # ChunkedEncodingError can be transient
                    httpx.ReadTimeout, requests.exceptions.ReadTimeout) as e: # Common transient network/timeout errors
                last_seen_exception = e
                self._logger.warning(
                    f"Ollama API call attempt {attempt_num + 1}/{self._retries + 1} failed (Connect/Timeout/Network error): {type(e).__name__} - {e}"
                )
                if attempt_num < self._retries:
                    self._logger.info(f"Retrying in {self._retry_delay} seconds...")
                    time.sleep(self._retry_delay)
                else:
                    self._logger.error(f"Ollama API call failed after all {self._retries + 1} attempts due to Connect/Timeout/Network error.")
                    # Fall through to raise ScribeApiError with the last exception
            except (httpx.HTTPStatusError, requests.exceptions.HTTPError) as e: # Non-transient HTTP errors (e.g., 400, 401, 404, 500 from Ollama server)
                last_seen_exception = e
                # Try to get more info from response if available
                error_response_text = e.response.text[:500] if hasattr(e, 'response') and hasattr(e.response, 'text') else str(e)
                self._logger.error(
                    f"Ollama API call failed with HTTP status {e.response.status_code if hasattr(e, 'response') else 'Unknown'}: {error_response_text}",
                    exc_info=False # exc_info=False as the status code and text are usually enough
                )
                break # Do not retry on HTTP status errors unless specifically handled (e.g. 503 could be retried)
            except json.JSONDecodeError as e: # If Ollama returns non-JSON response when JSON was expected (e.g. for review step)
                last_seen_exception = e
                self._logger.error(f"Failed to decode JSON response from Ollama API: {e}. This might occur if the LLM did not adhere to format instructions.", exc_info=False)
                # Log a snippet of what was received if possible (response object might not be available on httpx.Client if it wasn't a successful HTTP status)
                # This is usually a non-retryable error for the current prompt.
                break
            except Exception as e: # Catch-all for other unexpected errors from HTTP libs or within this try block
                last_seen_exception = e
                self._logger.error(f"An unexpected error occurred during Ollama API call attempt {attempt_num + 1}: {type(e).__name__} - {e}", exc_info=True)
                break # Do not retry on general unexpected exceptions

        # If loop finished due to exhausting retries or breaking on non-retryable error
        if last_seen_exception: # Ensure we have an exception to raise
            raise ScribeApiError(f"Ollama API call ultimately failed after {attempt_num + 1} attempt(s): {last_seen_exception}") from last_seen_exception
        else: # Should not happen if logic is correct (loop must either succeed or set last_exception)
            raise ScribeApiError("Ollama API call failed due to an unknown reason after exhausting retries or encountering an issue.")


    def _extract_code_from_response(self, llm_response_text: str) -> str:
        """
        Extracts Python code from LLM response text.
        Prioritizes ```python ... ``` blocks, then generic ``` ... ``` blocks.
        V1.1: Handles multiple python blocks by concatenating, with a warning.
        """
        self._logger.debug("Attempting to extract Python code block(s) from LLM response...")
        
        # 1. Try to find ```python ... ``` blocks
        # Using re.IGNORECASE for 'python' and re.DOTALL for multiline content
        python_specific_blocks = re.findall(r"```python\n(.*?)\n```", llm_response_text, re.DOTALL | re.IGNORECASE)

        if python_specific_blocks:
            if len(python_specific_blocks) > 1:
                self._logger.warning(
                    f"LLM response contained {len(python_specific_blocks)} '```python ... ```' code blocks. "
                    "Scribe V1.1 will concatenate these. For best results, ensure prompts request a single, consolidated code output."
                )
                # Concatenate all found Python blocks, separated by a clear marker.
                # Also add newlines to ensure they are parsed as separate statements if needed.
                concatenated_code = "\n\n# --- Scribe: Concatenated Python Block ---\n\n".join(block.strip() for block in python_specific_blocks)
                self._logger.debug(f"Concatenated {len(python_specific_blocks)} Python code blocks.")
                return concatenated_code.strip()
            else: # Exactly one python-specific block found
                self._logger.debug("Found a single '```python ... ```' block.")
                return python_specific_blocks[0].strip()

        # 2. If no python-specific blocks, try generic ``` ... ``` blocks
        # This regex tries to capture content within any triple backticks, optionally allowing a language hint on the first line.
        generic_blocks = re.findall(r"```(?:[a-zA-Z0-9_.-]*)?\n(.*?)\n```", llm_response_text, re.DOTALL)
        if generic_blocks:
            self._logger.warning(
                "No '```python ... ```' blocks found. Falling back to generic '``` ... ```' blocks. "
                f"Found {len(generic_blocks)} generic block(s). Using the first one found."
            )
            # Could also try to infer if it's Python (e.g. starts with 'def'/'class'/'import') but that's more complex.
            return generic_blocks[0].strip()

        # 3. If no fenced code blocks at all, assume the entire response is code (last resort)
        self._logger.warning(
            "No markdown code fences (```python...``` or ```...```) found in LLM response. "
            "Assuming the entire response is code. This may lead to errors if the response contains explanatory text."
        )
        return llm_response_text.strip()


    def generate_tests(self, code_content_to_test: str, target_file_display_name: str, function_class_signatures: str) -> Optional[str]:
        """
        Generates unit tests for the given code content using the configured LLM.
        Returns the generated test code as a string, or None on failure.
        """
        self._logger.info(f"Requesting AI test generation for target file context: '{target_file_display_name}'")
        prompt_template_str = self._config.get_str("test_generation_prompt_template")
        
        # Truncate code_content and signatures if they are excessively long to keep prompts manageable
        max_code_len_for_prompt = 7000  # Characters
        max_sigs_len_for_prompt = 1000 # Characters

        truncated_code_content = code_content_to_test[:max_code_len_for_prompt] + \
                                 ("\n# ... (code truncated by Scribe for prompt brevity) ..." if len(code_content_to_test) > max_code_len_for_prompt else "")
        truncated_signatures = function_class_signatures[:max_sigs_len_for_prompt] + \
                               ("\n... (signatures truncated by Scribe for prompt brevity) ..." if len(function_class_signatures) > max_sigs_len_for_prompt else "")

        try:
            prompt = prompt_template_str.format(
                code_content=truncated_code_content,
                target_file_path=target_file_display_name, # Use display name in prompt
                signatures=truncated_signatures
            )
        except KeyError as e:
            self._logger.error(f"Prompt template for 'test_generation' is missing a required key: {e}. Check .scribe.toml.")
            raise ScribeConfigurationError(f"Invalid 'test_generation_prompt_template': Missing key {e}")

        try:
            api_response = self._call_api(prompt_text=prompt) # output_format_type defaults to text
            raw_llm_text_response = api_response.get("response", "")

            if not raw_llm_text_response.strip():
                self._logger.warning("LLM returned an empty response during test generation.")
                return None

            extracted_test_code_str = self._extract_code_from_response(raw_llm_text_response)
            if not extracted_test_code_str:
                self._logger.warning("Failed to extract any usable test code from the LLM's response.")
                return None

            # Basic syntax validation of the extracted test code
            try:
                ast.parse(extracted_test_code_str)
                self._logger.info("Successfully generated test code. Syntax appears valid.")
                self._logger.info("REMINDER (Scribe V1.1): AI-generated tests require thorough human review and validation for correctness, completeness, and effective coverage.")
                return extracted_test_code_str
            except SyntaxError as e:
                self._logger.error(f"Generated test code contains a Python syntax error: {e}")
                self._logger.debug(f"Problematic AI-generated test code (first 500 chars):\n{extracted_test_code_str[:500]}")
                return None # Indicate failure due to syntax error in generated code
        
        except ScribeApiError as e: # Catch API errors from _call_api
            self._logger.error(f"ScribeApiError during test generation: {e}")
            return None # Propagate as None, error already logged by _call_api
        except Exception as e: # Catch any other unexpected errors
            self._logger.error(f"Unexpected error during AI test generation: {e}", exc_info=True)
            return None


    def generate_review(self, code_content_to_review: str, target_file_display_name: str) -> Optional[List[Dict[str, str]]]:
        """
        Generates AI code review findings for the given code content.
        Returns a list of finding dictionaries, or None on failure.
        """
        self._logger.info(f"Requesting AI code review for target file context: '{target_file_display_name}'")
        prompt_template_str = self._config.get_str("review_prompt_template")

        max_code_len_for_prompt = 8000 # Characters
        truncated_code_content = code_content_to_review[:max_code_len_for_prompt] + \
                                 ("\n# ... (code truncated by Scribe for prompt brevity) ..." if len(code_content_to_review) > max_code_len_for_prompt else "")
        try:
            prompt = prompt_template_str.format(
                code_content=truncated_code_content,
                target_file_path=target_file_display_name
            )
        except KeyError as e:
            self._logger.error(f"Prompt template for 'review' is missing a required key: {e}. Check .scribe.toml.")
            raise ScribeConfigurationError(f"Invalid 'review_prompt_template': Missing key {e}")

        try:
            # Expecting JSON output from the LLM for reviews
            api_response = self._call_api(prompt_text=prompt, output_format_type="json")
            raw_llm_json_str_response = api_response.get("response", "")

            if not raw_llm_json_str_response.strip():
                self._logger.warning("LLM returned an empty response string for code review when JSON was expected.")
                return [] # Return empty list to differentiate from API/parsing failure vs. no findings

            try:
                # The prompt asks for a JSON list of objects.
                parsed_findings_list = json.loads(raw_llm_json_str_response)
                
                if not isinstance(parsed_findings_list, list):
                    self._logger.error(
                        f"LLM review response was valid JSON but not a list as expected. Got type: {type(parsed_findings_list)}. "
                        f"Response snippet: {raw_llm_json_str_response[:300]}"
                    )
                    # Attempt to gracefully handle if LLM mistakenly returned a single dict not in a list
                    if isinstance(parsed_findings_list, dict) and all(k_ in parsed_findings_list for k_ in ['severity', 'description', 'location']):
                         self._logger.warning("LLM review response was a single dictionary; wrapping it in a list for processing.")
                         parsed_findings_list = [parsed_findings_list]
                    else:
                         return None # Indicate parsing failure if structure is significantly off

                # Validate and normalize the structure of each finding dictionary
                validated_findings_list: List[Dict[str, str]] = []
                for item_dict in parsed_findings_list:
                    if isinstance(item_dict, dict) and \
                       'severity' in item_dict and \
                       'description' in item_dict and \
                       'location' in item_dict:
                        validated_findings_list.append({
                            "severity": str(item_dict.get('severity', 'info')).strip().lower(),
                            "description": str(item_dict.get('description', 'N/A')).strip(),
                            "location": str(item_dict.get('location', 'N/A')).strip()
                        })
                    else:
                        self._logger.warning(f"Skipping malformed review finding item from LLM due to missing keys or wrong type: {item_dict}")
                
                log_msg = f"Successfully parsed {len(validated_findings_list)} review findings from LLM."
                if not validated_findings_list and raw_llm_json_str_response.strip() != "[]": # Log if empty list but response wasn't just "[]"
                    log_msg += f" (Original LLM response was not an empty list: '{raw_llm_json_str_response[:100]}...')"

                self._logger.info(log_msg)
                self._logger.info("REMINDER (Scribe V1.1): AI-generated review findings are advisory and require human interpretation and validation.")
                return validated_findings_list
            
            except json.JSONDecodeError as e:
                self._logger.error(f"Failed to decode JSON response from LLM for code review: {e}")
                self._logger.debug(f"LLM review response that failed JSON parsing (first 500 chars):\n{raw_llm_json_str_response[:500]}")
                return None # Indicate JSON parsing failure

        except ScribeApiError as e:
            self._logger.error(f"ScribeApiError during code review generation: {e}")
            return None
        except Exception as e:
            self._logger.error(f"Unexpected error during AI code review: {e}", exc_info=True)
            return None

# End of LLMClient class
# --- Workflow Steps Logic ---
class WorkflowSteps:
    """
    Encapsulates the logic for individual Scribe workflow steps.
    Each method corresponds to a step in the validation pipeline and
    is designed to be called by ScribeAgent._execute_step.

    V1.1: Many methods updated to process CompletedProcess from ToolRunner
          and to return more structured StepOutputDetails for the report.
    """
    def __init__(self, agent: 'ScribeAgent'): # Forward reference ScribeAgent for type hinting
        self.agent = agent # Allows access to ScribeAgent's config, tool_runner, env_manager, etc.
        self._logger = logging.getLogger(f"{APP_NAME}.WorkflowSteps")

    def _truncate_output(self, output_str: Optional[str], max_len: int = 500, head_len: int = 200, tail_len: int = 200) -> str:
        """
        Helper to intelligently truncate long strings (like stdout/stderr) for summaries.
        Shows beginning and end if truncated.
        """
        if not output_str:
            return ""
        
        output_str = output_str.strip() # Remove leading/trailing whitespace before length check
        if len(output_str) > max_len:
            if head_len + tail_len >= max_len: # Avoid overlap if max_len is too small
                head_len = max_len // 2
                tail_len = max_len - head_len
            
            return (
                f"{output_str[:head_len]}\n"
                f"... (truncated - {len(output_str)} chars total) ...\n"
                f"{output_str[-tail_len:]}"
            )
        return output_str

    def validate_inputs(self) -> Tuple[str, StepOutputDetails]:
        """
        Validates crucial inputs: target_dir, target_file (relative to target_dir),
        and code_file (source of new code).
        Ensures paths are valid, within allowed bases, and accessible.
        Populates self.agent._target_file_path and self.agent._temp_code_path.
        """
        self._logger.info("Validating Scribe input parameters...")
        details: StepOutputDetails = {}
        try:
            # self.agent._target_dir is already validated during ScribeAgent.__init__ against allowed_target_bases.
            # This step focuses on target_file and code_file relative to that validated context.

            # Validate --target-file (relative path where code will be applied)
            if not self.agent._args.target_file: # Should be caught by argparse if required
                raise ScribeInputError("--target-file argument is mandatory and was not provided.")
            
            target_file_relative_path = Path(self.agent._args.target_file)
            if target_file_relative_path.is_absolute() or ".." in target_file_relative_path.parts:
                raise ScribeInputError(
                    f"Invalid relative path for --target-file: '{target_file_relative_path}'. "
                    "It must be a relative path and must not attempt to traverse upwards (e.g., using '..')."
                )
            
            # self.agent._target_dir is already resolved and confirmed as an allowed directory.
            absolute_target_file_path = (self.agent._target_dir / target_file_relative_path).resolve()

            # Security check: Ensure the resolved absolute_target_file_path is still within the _target_dir.
            # This protects against tricky symlinks or unusual relative paths that might try to escape.
            if not str(absolute_target_file_path).startswith(str(self.agent._target_dir.resolve()) + os.sep) and \
               absolute_target_file_path != self.agent._target_dir.resolve(): # Allow if target_dir itself is the file (edge case)
                 raise ScribeInputError(
                    f"Resolved target file path '{absolute_target_file_path}' is outside the "
                    f"validated target project directory '{self.agent._target_dir}'. This is a security prevention."
                )
            self.agent._target_file_path = absolute_target_file_path # Store resolved absolute path

            # Validate --code-file (source of the new code content)
            if not self.agent._args.code_file: # Should be caught by argparse
                raise ScribeInputError("--code-file argument is mandatory and was not provided.")
            try:
                # This file MUST exist as it's an input provided by the NAI TUI or user.
                self.agent._temp_code_path = Path(self.agent._args.code_file).resolve(strict=True)
            except FileNotFoundError:
                raise ScribeInputError(f"Input --code-file not found at the specified path: {self.agent._args.code_file}")

            if not self.agent._temp_code_path.is_file(): # Should be caught by strict=True above, but double check
                raise ScribeInputError(f"Input --code-file '{self.agent._temp_code_path}' is not a regular file.")

            # Ensure parent directory for the target_file exists; create if not.
            # This is for cases where target_file is a new file in a new subdirectory.
            target_file_parent_dir = self.agent._target_file_path.parent
            if not target_file_parent_dir.exists():
                self._logger.info(f"Parent directory for target file ('{target_file_parent_dir}') does not exist. Attempting to create it.")
                try:
                    target_file_parent_dir.mkdir(parents=True, exist_ok=True)
                    self._logger.info(f"Successfully created directory: {target_file_parent_dir}")
                except OSError as e:
                    raise ScribeFileSystemError(f"Failed to create parent directory '{target_file_parent_dir}' for target file: {e.strerror}") from e
            elif not target_file_parent_dir.is_dir(): # Path exists but is not a directory
                raise ScribeInputError(f"The parent path '{target_file_parent_dir}' for the target file exists but is not a directory.")

            details["message"] = (
                f"Inputs validated successfully. Target file for operations: '{self.agent._target_file_path}'. "
                f"Source code will be read from: '{self.agent._temp_code_path}'."
            )
            self._logger.info(details["message"])
            return STATUS_SUCCESS, details
        except (ScribeInputError, ScribeFileSystemError, FileNotFoundError, PermissionError) as e: # Catch specific known errors
            self._logger.error(f"Input validation step failed: {type(e).__name__} - {e}", exc_info=False) # Log specific error
            self._logger.debug("Traceback for input validation failure:", exc_info=True) # Full traceback at DEBUG
            raise # Re-raise; _execute_step will catch ScribeError derivatives and format the report step.

    def setup_environment(self) -> Tuple[str, StepOutputDetails]:
        """Sets up the Python virtual environment for the target project."""
        self._logger.info("Setting up Python virtual environment for the target project...")
        details: StepOutputDetails = {}
        try:
            self.agent._env_manager.setup_venv() # This method now handles its own logging and error raising
            details["message"] = f"Python virtual environment setup or validated at: {self.agent._env_manager.venv_path}"
            details["venv_path"] = str(self.agent._env_manager.venv_path)
            details["python_executable"] = str(self.agent._env_manager.python_executable) if self.agent._env_manager.python_executable else "Not found"
            details["pip_executable"] = str(self.agent._env_manager.pip_executable) if self.agent._env_manager.pip_executable else "Not found"
            
            self._logger.info(f"Virtual environment configuration: {details['message']}")
            return STATUS_SUCCESS, details
        except ScribeEnvironmentError as e:
            self._logger.error(f"Virtual environment setup step failed: {e}", exc_info=True)
            raise # Re-raise for _execute_step

    def install_deps(self) -> Tuple[str, StepOutputDetails]:
        """Installs project dependencies into the virtual environment."""
        self._logger.info("Installing project dependencies into the virtual environment...")
        details: StepOutputDetails = {}
        try:
            # EnvironmentManager.install_dependencies handles logic for pyproject.toml/requirements.txt
            # and logs its own progress. It raises ScribeEnvironmentError on critical install failure.
            # If no dependency files are found, it logs and returns gracefully (not an error for this step).
            self.agent._env_manager.install_dependencies() 
            
            details["message"] = "Project dependencies installed successfully, or step was skipped if no dependency files (pyproject.toml/requirements.txt) were found."
            self._logger.info(details["message"])
            return STATUS_SUCCESS, details
        except ScribeEnvironmentError as e: # Catch errors from install_dependencies
            self._logger.error(f"Dependency installation step failed: {e}", exc_info=True)
            raise # Re-raise for _execute_step

    def audit_deps(self) -> Tuple[str, StepOutputDetails]: # V1.1: Processes CompletedProcess from ToolRunner
        """Audits installed project dependencies for known vulnerabilities using pip-audit."""
        self._logger.info("Auditing project dependencies for vulnerabilities using pip-audit...")
        details: StepOutputDetails = {"tool_name": "pip-audit"}
        
        try:
            # EnvironmentManager.run_pip_audit() now returns CompletedProcess
            # It attempts to install pip-audit if not found.
            audit_result_process = self.agent._env_manager.run_pip_audit()
            details["return_code"] = audit_result_process.returncode

            if audit_result_process.returncode == -1 and "TimeoutExpired" in audit_result_process.stderr: # Scribe-detected timeout
                timeout_err_msg = f"pip-audit command timed out. Stderr: {audit_result_process.stderr.strip()}"
                self._logger.error(timeout_err_msg)
                raise ScribeToolError(timeout_err_msg) # Raise to mark step as tool failure

            parsed_audit_json_data: Dict[str, Any] = {}
            vulnerabilities_list: List[Dict[str, Any]] = []

            if audit_result_process.stdout:
                try:
                    parsed_audit_json_data = json.loads(audit_result_process.stdout)
                    # Standard pip-audit JSON format has a "vulnerabilities" list
                    vulnerabilities_list = parsed_audit_json_data.get("vulnerabilities", [])
                    details["vulnerabilities"] = vulnerabilities_list # Store full list for details
                except json.JSONDecodeError as e:
                    self._logger.error(f"Failed to parse JSON output from pip-audit: {e}. Raw output (first 500 chars): {audit_result_process.stdout[:500]}")
                    details["message"] = "Audit run, but failed to parse pip-audit JSON output. Review raw output."
                    details["raw_output"] = self._truncate_output(audit_result_process.stdout)
                    # This is a WARNING for the step, as audit ran but its output is problematic.
                    return STATUS_WARNING, details
            else: # No stdout, check stderr for clues if RC is non-standard
                 if audit_result_process.returncode != 0 and audit_result_process.returncode != 1: # 0=ok, 1=vulns found
                    self._logger.warning(f"pip-audit produced no stdout and had RC={audit_result_process.returncode}. Stderr: {audit_result_process.stderr.strip()}")


            details["vulnerability_count"] = len(vulnerabilities_list)
            # Store full findings in the main report_data for potential top-level summary
            self.agent._report_data["audit_findings"] = vulnerabilities_list 

            if not vulnerabilities_list:
                details["message"] = "pip-audit found no vulnerabilities in dependencies."
                self._logger.info(details["message"])
                return STATUS_SUCCESS, details # No vulnerabilities found is a success

            # Process found vulnerabilities and determine status based on config
            config_fail_severity_str = self.agent._config.get_str("fail_on_audit_severity", "high") # Default to 'high'
            details["configured_fail_severity"] = config_fail_severity_str
            
            should_step_fail_due_to_severity = False
            max_found_severity_value = -1
            max_found_severity_str = "none"
            severity_value_map = {"low": 0, "moderate": 1, "high": 2, "critical": 3}
            
            # Determine failure threshold (numeric) from configured string.
            # If config_fail_severity_str is "null" or None (from get_str default if key missing), no failure threshold.
            failure_threshold_value = severity_value_map.get(config_fail_severity_str.lower(), 4) if config_fail_severity_str and config_fail_severity_str.lower() != "null" else 4


            for vuln_item in vulnerabilities_list:
                current_vuln_severity_str = str(vuln_item.get("severity", "unknown")).strip().lower()
                # Normalize severity string (e.g. "CVSS V3 score: High" -> "high")
                normalized_sev_str = current_vuln_severity_str
                for known_sev_key in severity_value_map.keys():
                    if known_sev_key in current_vuln_severity_str:
                        normalized_sev_str = known_sev_key
                        break
                
                current_vuln_severity_value = severity_value_map.get(normalized_sev_str, -1) # -1 for unknown severities
                if current_vuln_severity_value > max_found_severity_value:
                    max_found_severity_value = current_vuln_severity_value
                    max_found_severity_str = normalized_sev_str
                
                if config_fail_severity_str and config_fail_severity_str.lower() != "null":
                    if current_vuln_severity_value >= failure_threshold_value:
                        should_step_fail_due_to_severity = True
            
            details["highest_severity"] = max_found_severity_str
            details["message"] = (
                f"pip-audit found {len(vulnerabilities_list)} vulnerabilities. "
                f"Highest severity detected: '{max_found_severity_str}'. "
                f"Configured failure threshold: '{config_fail_severity_str or 'None (no fail threshold)'}'."
            )
            self._logger.warning(details["message"]) # Log as warning as vulnerabilities were found

            if should_step_fail_due_to_severity:
                return STATUS_FAILURE, details # Failure due to severity threshold
            return STATUS_WARNING, details # Warning because vulnerabilities exist but below threshold

        except FileNotFoundError as e: # If pip-audit (or pip itself) is not found by ToolRunner
            self._logger.warning(f"pip-audit tool or its dependencies (like pip) not found. Skipping dependency audit. Error: {e}")
            details["message"] = "pip-audit tool not found or pip is missing, audit step skipped."
            return STATUS_SKIPPED, details
        except (ScribeEnvironmentError, ScribeToolError) as e: # Catch other errors from EnvManager or ToolRunner
            self._logger.error(f"Dependency audit using pip-audit failed critically: {e}", exc_info=True)
            raise ScribeToolError(f"pip-audit execution or setup failed: {e}") from e # Re-raise as tool error

    def apply_code(self) -> Tuple[str, StepOutputDetails]:
        """
        Applies the code from the temporary --code-file to the specified --target-file
        within the project directory.
        """
        self._logger.info("Applying provided code from source file to target file location...")
        details: StepOutputDetails = {}
        # These paths should have been validated and set by `validate_inputs` step
        if not self.agent._target_file_path or not self.agent._temp_code_path:
            raise ScribeError(
                "Internal Scribe Error: Target file path or temporary code path is not set prior to 'apply_code' step. "
                "This indicates a flaw in the workflow step ordering or 'validate_inputs'."
            )

        try:
            self._logger.debug(f"Reading code content from source: {self.agent._temp_code_path}")
            code_to_apply_str = self.agent._temp_code_path.read_text(encoding='utf-8')
            
            self._logger.debug(f"Writing {len(code_to_apply_str)} bytes to target: {self.agent._target_file_path}")
            # Ensure parent directory exists (should have been handled by validate_inputs, but good practice)
            self.agent._target_file_path.parent.mkdir(parents=True, exist_ok=True)
            self.agent._target_file_path.write_text(code_to_apply_str, encoding='utf-8')
            
            details["message"] = (
                f"Successfully applied code (wrote {len(code_to_apply_str)} bytes) "
                f"from '{self.agent._temp_code_path.name}' to '{self.agent._target_file_path.name}'."
            )
            details["source_file"] = str(self.agent._temp_code_path)
            details["destination_file"] = str(self.agent._target_file_path)
            details["bytes_written"] = len(code_to_apply_str)
            self._logger.info(details["message"])
            return STATUS_SUCCESS, details
        except FileNotFoundError as e: # V1.1: More specific error handling
            self._logger.error(f"File not found during code application. Source: '{e.filename if e.filename == str(self.agent._temp_code_path) else 'Unknown source'}'. Error: {e.strerror}", exc_info=True)
            raise ScribeFileSystemError(f"Source code file '{self.agent._temp_code_path}' not found or target path invalid: {e.strerror}") from e
        except PermissionError as e:
            self._logger.error(f"Permission denied during code application. Path: '{e.filename}'. Error: {e.strerror}", exc_info=True)
            raise ScribeFileSystemError(f"Permission denied for file operation on '{e.filename}': {e.strerror}") from e
        except IsADirectoryError as e:
            self._logger.error(f"Path is a directory, not a file, during code application. Path: '{e.filename}'. Error: {e.strerror}", exc_info=True)
            raise ScribeFileSystemError(f"Expected a file but found a directory at '{e.filename}'. Check --code-file and --target-file paths.") from e
        except OSError as e: # Catch-all for other I/O related errors like disk full, etc.
            self._logger.error(f"General OS/IO error during code application. Path: '{e.filename}'. Error: {e.strerror} (errno {e.errno})", exc_info=True)
            raise ScribeFileSystemError(f"OS error during code application on '{e.filename}': {e.strerror}") from e
        except Exception as e: # Catch any other truly unexpected errors
            self._logger.error(f"Unexpected error during 'apply_code' step: {e}", exc_info=True)
            raise ScribeError(f"An unexpected error occurred while applying code: {e}") from e
        # --- Workflow Steps Logic (Continuation) ---
# class WorkflowSteps:
#     ... (previous methods from Part 5: __init__ to apply_code) ...

    def format_code(self) -> Tuple[str, StepOutputDetails]:
        """Formats the target code file using Ruff."""
        self._logger.info(f"Formatting target code file '{self.agent._target_file_path}' using Ruff format...")
        details: StepOutputDetails = {"tool_name": "ruff (format)"}
        if not self.agent._target_file_path: # Should have been set by validate_inputs
            raise ScribeError("Internal Scribe Error: Target file path not set for 'format_code' step.")
        if not self.agent._target_file_path.is_file(): # Code should have been applied
            raise ScribeFileSystemError(f"Target file '{self.agent._target_file_path}' does not exist or is not a file at formatting stage.")


        try:
            # ToolRunner._find_executable (called by run_tool) will raise FileNotFoundError if ruff isn't found.
            # The command for ruff format.
            format_tool_command = ["ruff", "format", str(self.agent._target_file_path)]
            
            process_result = self.agent._tool_runner.run_tool(
                format_tool_command,
                cwd=self.agent._target_dir, # Ruff usually works best from project root
                venv_path=self.agent._env_manager.venv_path # Ensure Ruff from venv is preferred if present
            )
            details["return_code"] = process_result.returncode

            # Ruff format is generally quiet on success (RC=0), possibly outputting "1 file reformatted." to stderr.
            # Non-zero RC usually indicates an internal error in Ruff or an invalid file, not formatting style issues.
            if process_result.returncode == 0:
                details["message"] = "Ruff successfully formatted the code (or no changes were needed)."
                # Capture stderr as Ruff often prints its success message there.
                output_summary = process_result.stderr.strip() or process_result.stdout.strip() or "No specific output from ruff format on success."
                details["stdout_summary"] = self._truncate_output(output_summary)
                self._logger.info(details["message"])
                return STATUS_SUCCESS, details
            elif process_result.returncode == -1 and "TimeoutExpired" in process_result.stderr: # Scribe-detected timeout
                timeout_msg = f"Ruff format command timed out. Stderr: {process_result.stderr.strip()}"
                self._logger.error(timeout_msg)
                raise ScribeToolError(timeout_msg)
            else: # Any other non-zero return code from ruff format is usually an error with the tool itself or file.
                error_msg = (
                    f"Ruff format command execution failed with return code {process_result.returncode}. "
                    f"This might indicate an internal Ruff error or an issue with the target file."
                )
                self._logger.error(error_msg)
                details["message"] = "Ruff format command execution failed."
                details["stderr_summary"] = self._truncate_output(process_result.stderr)
                details["stdout_summary"] = self._truncate_output(process_result.stdout)
                # This is treated as a tool failure, which should make the Scribe step FAIL.
                raise ScribeToolError(f"{error_msg} Stderr: {process_result.stderr.strip()}")

        except FileNotFoundError: # If ToolRunner couldn't find 'ruff'
            self._logger.warning("Ruff tool not found. Skipping code formatting step.")
            details["message"] = "Ruff tool not found, code formatting was skipped."
            return STATUS_SKIPPED, details
        except ScribeToolError as e: # Catch errors from run_tool or re-raised ones
            self._logger.error(f"Ruff format step encountered a tool error: {e}", exc_info=True)
            raise # Re-raise for _execute_step to handle and mark Scribe step as FAILURE

    def lint_code(self) -> Tuple[str, StepOutputDetails]:
        """Lints the target code file using Ruff check, with auto-fix enabled."""
        self._logger.info(f"Linting target code file '{self.agent._target_file_path}' using Ruff check (with --fix)...")
        details: StepOutputDetails = {"tool_name": "ruff (check --fix)"}
        if not self.agent._target_file_path or not self.agent._target_file_path.is_file():
            raise ScribeError("Internal Scribe Error: Target file path not set or file does not exist for 'lint_code' step.")

        try:
            # Ruff check with --fix will attempt to fix issues and report remaining ones.
            # --show-source includes the problematic lines in the output.
            lint_tool_command = ["ruff", "check", "--fix", "--show-source", str(self.agent._target_file_path)]
            
            process_result = self.agent._tool_runner.run_tool(
                lint_tool_command,
                cwd=self.agent._target_dir,
                venv_path=self.agent._env_manager.venv_path
            )
            details["return_code"] = process_result.returncode
            # Ruff check outputs findings (lint errors/warnings) to stdout.
            details["stdout_summary"] = self._truncate_output(process_result.stdout)
            # Stderr is usually empty unless there's a Ruff execution error.
            details["stderr_summary"] = self._truncate_output(process_result.stderr)

            if process_result.returncode == 0: # RC=0: No linting issues found, or all were auto-fixed.
                details["message"] = "Ruff check found no linting issues (or all were successfully auto-fixed)."
                self._logger.info(details["message"])
                return STATUS_SUCCESS, details
            elif process_result.returncode == 1: # RC=1: Linting issues were found and (some) could not be auto-fixed.
                details["message"] = "Ruff check found linting issues that were not auto-fixed. Review stdout_summary."
                self._logger.warning(details["message"])
                # Check Scribe config if this should be a FAILURE or WARNING
                if self.agent._config.get_bool("fail_on_lint_critical", True):
                    return STATUS_FAILURE, details
                else:
                    return STATUS_WARNING, details
            elif process_result.returncode == -1 and "TimeoutExpired" in process_result.stderr: # Scribe-detected timeout
                timeout_msg = f"Ruff check command timed out. Stderr: {process_result.stderr.strip()}"
                self._logger.error(timeout_msg)
                raise ScribeToolError(timeout_msg)
            else: # Any other RC (e.g., 2 for Ruff internal error) is a tool execution failure.
                error_msg = f"Ruff check command execution failed with unexpected return code {process_result.returncode}."
                self._logger.error(error_msg)
                details["message"] = error_msg
                raise ScribeToolError(f"{error_msg} Stdout: {process_result.stdout.strip()} Stderr: {process_result.stderr.strip()}")

        except FileNotFoundError:
            self._logger.warning("Ruff tool not found. Skipping code linting step.")
            details["message"] = "Ruff tool not found, code linting was skipped."
            return STATUS_SKIPPED, details
        except ScribeToolError as e:
            self._logger.error(f"Ruff lint check step encountered a tool error: {e}", exc_info=True)
            raise

    def type_check(self) -> Tuple[str, StepOutputDetails]:
        """Performs static type checking on the target file using MyPy."""
        self._logger.info(f"Performing static type checking on '{self.agent._target_file_path}' using MyPy...")
        details: StepOutputDetails = {"tool_name": "mypy"}
        if not self.agent._target_file_path or not self.agent._target_file_path.is_file():
            raise ScribeError("Internal Scribe Error: Target file path not set or file does not exist for 'type_check' step.")

        try:
            # MyPy needs to run from the project root (cwd) and often requires dependencies to be available
            # in the environment it uses (hence venv_path is important).
            # Configuration for MyPy is typically in mypy.ini or pyproject.toml [tool.mypy].
            type_check_tool_command = ["mypy", str(self.agent._target_file_path)]
            # Optional: Add stricter flags if desired, e.g. from Scribe config if available
            # mypy_flags = self.agent._config.get_list("mypy_flags", [])
            # type_check_tool_command.extend(mypy_flags)
            
            process_result = self.agent._tool_runner.run_tool(
                type_check_tool_command,
                cwd=self.agent._target_dir, # MyPy needs project context
                venv_path=self.agent._env_manager.venv_path
            )
            details["return_code"] = process_result.returncode
            # MyPy type errors are typically output to stdout.
            details["stdout_summary"] = self._truncate_output(process_result.stdout)
            # Stderr might contain MyPy configuration errors or other operational messages.
            details["stderr_summary"] = self._truncate_output(process_result.stderr)

            if process_result.returncode == 0: # RC=0: No type errors found.
                details["message"] = "MyPy found no static type errors."
                self._logger.info(details["message"])
                return STATUS_SUCCESS, details
            elif process_result.returncode == 1: # RC=1: Type errors were found.
                details["message"] = "MyPy found static type errors. Review stdout_summary."
                self._logger.warning(details["message"])
                if self.agent._config.get_bool("fail_on_mypy_error", True):
                    return STATUS_FAILURE, details
                else:
                    return STATUS_WARNING, details
            elif process_result.returncode == -1 and "TimeoutExpired" in process_result.stderr: # Scribe-detected timeout
                timeout_msg = f"MyPy type check command timed out. Stderr: {process_result.stderr.strip()}"
                self._logger.error(timeout_msg)
                raise ScribeToolError(timeout_msg)
            else: # Any other RC (e.g., 2 for MyPy internal/config error) is a tool execution failure.
                error_msg = f"MyPy command execution failed with unexpected return code {process_result.returncode}."
                self._logger.error(error_msg)
                details["message"] = error_msg
                raise ScribeToolError(f"{error_msg} Stdout: {process_result.stdout.strip()} Stderr: {process_result.stderr.strip()}")

        except FileNotFoundError: # If 'mypy' executable is not found
            self._logger.warning("MyPy tool not found. Skipping static type checking step.")
            details["message"] = "MyPy tool not found, static type checking was skipped."
            return STATUS_SKIPPED, details
        except ScribeToolError as e:
            self._logger.error(f"MyPy type check step encountered a tool error: {e}", exc_info=True)
            raise
        # --- Workflow Steps Logic (Continuation) ---
# class WorkflowSteps:
#     ... (previous methods from Part 6: format_code to type_check) ...

    def extract_signatures(self) -> Tuple[str, StepOutputDetails]:
        """
        Extracts function and class signatures from the target Python file using AST parsing.
        The extracted signatures string is returned via StepOutputDetails.raw_output.
        """
        self._logger.info(f"Extracting function and class signatures from: {self.agent._target_file_path}...")
        details: StepOutputDetails = {}
        if not self.agent._target_file_path or not self.agent._target_file_path.is_file():
            raise ScribeError("Internal Scribe Error: Target file path not set or file does not exist for 'extract_signatures' step.")

        signatures_found: List[str] = []
        try:
            self._logger.debug(f"Reading code from '{self.agent._target_file_path}' for AST parsing.")
            source_code_str = self.agent._target_file_path.read_text(encoding='utf-8')
            abstract_syntax_tree = ast.parse(source_code_str)

            for node_item in ast.walk(abstract_syntax_tree):
                current_signature: Optional[str] = None
                if isinstance(node_item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    # Reconstruct the signature string including decorators, async, def, name, args, and return annotation.
                    decorator_list_str = "".join([f"@{ast.unparse(decorator_node)}\n" for decorator_node in node_item.decorator_list])
                    args_str = ast.unparse(node_item.args)
                    returns_annotation_str = f" -> {ast.unparse(node_item.returns)}" if node_item.returns else ""
                    current_signature = (
                        f"{decorator_list_str}"
                        f"{'async ' if isinstance(node_item, ast.AsyncFunctionDef) else ''}"
                        f"def {node_item.name}({args_str}){returns_annotation_str}:"
                    )
                elif isinstance(node_item, ast.ClassDef):
                    decorator_list_str = "".join([f"@{ast.unparse(decorator_node)}\n" for decorator_node in node_item.decorator_list])
                    base_classes_str = ", ".join(ast.unparse(base_node) for base_node in node_item.bases)
                    keyword_args_str = ", ".join(f"{kw.arg}={ast.unparse(kw.value)}" for kw in node_item.keywords)
                    
                    inheritance_part = ""
                    if base_classes_str or keyword_args_str:
                        inheritance_parts = []
                        if base_classes_str: inheritance_parts.append(base_classes_str)
                        if keyword_args_str: inheritance_parts.append(keyword_args_str)
                        inheritance_part = f"({', '.join(inheritance_parts)})"
                    current_signature = f"{decorator_list_str}class {node_item.name}{inheritance_part}:"

                if current_signature:
                    signatures_found.append(current_signature)
            
            if not signatures_found:
                details["message"] = "No distinct function or class signatures were extracted from the target file."
                self._logger.info(details["message"])
                details["raw_output"] = "" # Ensure raw_output is present even if empty
                return STATUS_SUCCESS, details # Successfully processed, found nothing.
            
            concatenated_signatures = "\n\n".join(signatures_found)
            details["message"] = f"Successfully extracted {len(signatures_found)} function/class signatures."
            details["raw_output"] = concatenated_signatures # This is the primary output for this step
            self._logger.info(details["message"])
            self._logger.debug(f"Extracted signatures snippet (first 300 chars):\n{concatenated_signatures[:300]}...")
            return STATUS_SUCCESS, details

        except FileNotFoundError: # Should be caught by initial check, but defensive
             self._logger.error(f"Target file '{self.agent._target_file_path}' not found during signature extraction.")
             raise ScribeFileSystemError(f"Target file '{self.agent._target_file_path}' not found during signature extraction.") from None
        except SyntaxError as e:
            self._logger.error(f"Python syntax error encountered while parsing '{self.agent._target_file_path}' for signature extraction: {e}", exc_info=False)
            raise ScribeError(
                f"Failed to parse Python code for signature extraction due to SyntaxError: {e.msg} "
                f"(line {e.lineno}, offset {e.offset}). Ensure the target file is syntactically valid."
            ) from e
        except Exception as e: # Catch other potential errors (e.g., rare ast.unparse issues)
            self._logger.error(f"An unexpected error occurred during signature extraction: {e}", exc_info=True)
            raise ScribeError(f"Unexpected error during signature extraction: {e}") from e

    def generate_tests(self, extracted_signatures_details: StepOutputDetails) -> Tuple[str, StepOutputDetails]:
        """Generates AI unit tests based on extracted code signatures."""
        self._logger.info("Generating AI unit tests for the target code using extracted signatures...")
        details: StepOutputDetails = {
            "tool_name": "LLM (test generation)", # More specific than just "LLM"
            "llm_model": self.agent._llm_client._model, # Record model used
            "prompt_type": "test_generation",
            "notes": ["AI-generated tests are a starting point and REQUIRE THOROUGH HUMAN REVIEW for correctness, completeness, and security implications."]
        }

        if not self.agent._target_file_path or not self.agent._target_file_path.is_file():
            raise ScribeError("Internal Scribe Error: Target file path not set or file does not exist for 'generate_tests' step.")
        
        # Get the signatures string from the raw_output of the previous step's details
        signatures_to_use = extracted_signatures_details.get("raw_output") if isinstance(extracted_signatures_details, dict) else None
        if not signatures_to_use or not isinstance(signatures_to_use, str):
            details["message"] = "No valid signatures provided from 'extract_signatures' step. Skipping AI test generation."
            self._logger.info(details["message"])
            return STATUS_SKIPPED, details

        try:
            source_code_content = self.agent._target_file_path.read_text(encoding='utf-8')
            # LLMClient.generate_tests handles truncation and AST parsing of generated code
            generated_test_code_str = self.agent._llm_client.generate_tests(
                source_code_content,
                str(self.agent._target_file_path.name), # Pass relative/display name for prompt context
                signatures_to_use
            )

            if not generated_test_code_str: # LLMClient.generate_tests returns None on failure (API error, syntax error in gen code, empty response)
                details["message"] = "LLM failed to generate valid test code, or returned an empty/invalid response."
                self._logger.warning(details["message"] + " Check LLMClient logs for more details.")
                # This is a FAILURE of the test generation attempt itself.
                return STATUS_FAILURE, details
            
            details["message"] = "AI unit tests generated successfully (syntax validated by LLMClient)."
            details["response_summary"] = self._truncate_output(generated_test_code_str, 1000) # Store a snippet of generated code
            # The full generated code string is the primary output of this step for the next step (save_tests)
            details["raw_output"] = generated_test_code_str 
            self._logger.info(details["message"] + " " + (details.get("notes",[""])[0]))
            return STATUS_SUCCESS, details

        except FileNotFoundError: # Should be caught earlier
            self._logger.error(f"Target file '{self.agent._target_file_path}' not found during AI test generation.")
            raise ScribeFileSystemError(f"Target file '{self.agent._target_file_path}' not found.") from None
        except ScribeApiError as e: # Explicitly catch and pass on ScribeApiError from LLMClient
            self._logger.error(f"LLM API error occurred during AI test generation step: {e}", exc_info=False) # Error logged in LLMClient
            details["message"] = f"LLM API communication failed during test generation: {e}"
            return STATUS_FAILURE, details
        except Exception as e: # Catch any other unexpected errors
            self._logger.error(f"An unexpected error occurred during AI test generation: {e}", exc_info=True)
            raise ScribeError(f"Unexpected error in AI test generation workflow: {e}") from e

    def save_tests(self, ai_generated_tests_details: StepOutputDetails) -> Tuple[str, StepOutputDetails]:
        """Saves the AI-generated test code to a designated file."""
        self._logger.info("Saving AI-generated tests to file...")
        details: StepOutputDetails = {} # Will be populated with path or error

        # Get the generated test code string from the raw_output of the previous step's details
        test_code_str_to_save = ai_generated_tests_details.get("raw_output") if isinstance(ai_generated_tests_details, dict) else None

        if not test_code_str_to_save or not isinstance(test_code_str_to_save, str):
            details["message"] = "No valid test code string provided from 'generate_tests' step. Skipping save operation."
            self._logger.warning(details["message"])
            # If generate_tests failed or was skipped, this step also effectively skips/fails to save.
            return STATUS_WARNING, details # Warning, as we expected code but didn't get it.

        if not self.agent._target_file_path: # Should always be set by this point
            raise ScribeError("Internal Scribe Error: Target file path (for context) not set for 'save_tests' step.")

        original_file_stem = self.agent._target_file_path.stem
        # Sanitize the stem for use in a filename (replace non-alphanumeric with underscore)
        safe_filename_stem = ''.join(char if char.isalnum() else '_' for char in original_file_stem if char.isascii()) # Ensure ASCII for broader fs compat

        # Define the test directory and file path within the target project
        # SCRIBE_TEST_DIR is a constant like "tests/scribe_generated"
        generated_tests_dir_path = self.agent._target_dir.resolve() / SCRIBE_TEST_DIR
        test_output_filename = f"test_{safe_filename_stem}_scribe_generated.py"
        full_test_file_path = generated_tests_dir_path / test_output_filename
        
        details["generated_content_path"] = str(full_test_file_path) # For report

        try:
            self._logger.debug(f"Ensuring directory for generated tests exists: {generated_tests_dir_path}")
            generated_tests_dir_path.mkdir(parents=True, exist_ok=True) # Create if doesn't exist
            
            self._logger.info(f"Writing AI-generated tests ({len(test_code_str_to_save)} bytes) to: {full_test_file_path}")
            full_test_file_path.write_text(test_code_str_to_save, encoding='utf-8')
            
            details["message"] = f"AI-generated tests successfully saved to: {full_test_file_path}"
            # The primary output of this step is the path to the saved file, for the next step (execute_tests)
            details["raw_output"] = str(full_test_file_path) 
            self._logger.info(details["message"])
            return STATUS_SUCCESS, details
        except OSError as e:
            self._logger.error(f"OS error while writing AI-generated tests to '{full_test_file_path}': {e.strerror}", exc_info=True)
            raise ScribeFileSystemError(f"Failed to write tests to '{full_test_file_path}': {e.strerror}") from e
        except Exception as e:
            self._logger.error(f"An unexpected error occurred while saving AI-generated tests: {e}", exc_info=True)
            raise ScribeError(f"Unexpected error saving AI-generated tests: {e}") from e


    def execute_tests(self, saved_tests_file_details: StepOutputDetails) -> Tuple[str, StepOutputDetails]:
        """Executes the saved AI-generated tests using Pytest."""
        self._logger.info("Executing AI-generated unit tests using Pytest...")
        details: StepOutputDetails = {
            "tool_name": "pytest",
            "notes": ["Results for AI-generated tests. Verify test coverage, relevance, and correctness. False positives/negatives are possible."]
        }

        # Get the path to the saved test file from the raw_output of the previous step's details
        test_file_to_execute_str = saved_tests_file_details.get("raw_output") if isinstance(saved_tests_file_details, dict) else None

        if not test_file_to_execute_str or not isinstance(test_file_to_execute_str, str):
            details["message"] = "No valid test file path provided from 'save_tests' step. Skipping test execution."
            self._logger.warning(details["message"])
            return STATUS_SKIPPED, details
        
        test_file_to_execute_path = Path(test_file_to_execute_str)
        if not test_file_to_execute_path.is_file(): # Check if the test file actually exists
            details["message"] = f"Specified test file '{test_file_to_execute_path}' not found on disk. Cannot execute tests."
            self._logger.error(details["message"])
            return STATUS_FAILURE, details # This is a failure as we expected a file to run.

        details["test_file_executed"] = str(test_file_to_execute_path)

        try:
            # Pytest needs to be found (config tool_paths, venv, or PATH).
            # For Pytest to correctly discover and run tests that import code from the target project,
            # the target project's root directory (self.agent._target_dir) or relevant source directories
            # often need to be in the PYTHONPATH.
            
            current_pythonpath = os.environ.get('PYTHONPATH', '')
            # Ensure target_dir (project root) is in PYTHONPATH for imports to work correctly within tests.
            # Some projects might have a src/ layout, so adding target_dir generally helps.
            paths_to_add_to_pythonpath = {str(self.agent._target_dir.resolve())}
            # If the original target file Scribe worked on is in a subdirectory (e.g. src/module/file.py),
            # adding its parent (src/module) or even src/ to PYTHONPATH can also help resolve imports.
            # For simplicity, adding project root is a good first step.
            if self.agent._target_file_path: # Add parent of the file being tested
                 paths_to_add_to_pythonpath.add(str(self.agent._target_file_path.parent.resolve()))


            # Construct new PYTHONPATH: added paths first, then original PYTHONPATH
            modified_pythonpath_list = list(paths_to_add_to_pythonpath)
            if current_pythonpath:
                modified_pythonpath_list.extend(current_pythonpath.split(os.pathsep))
            
            # Remove duplicates while preserving order (Python 3.7+)
            final_pythonpath_str = os.pathsep.join(list(dict.fromkeys(modified_pythonpath_list)))

            test_execution_env_vars = os.environ.copy()
            test_execution_env_vars['PYTHONPATH'] = final_pythonpath_str
            self._logger.debug(f"Executing Pytest with modified PYTHONPATH: {final_pythonpath_str}")

            pytest_tool_command = ["pytest", str(test_file_to_execute_path), "-v"] # -v for verbose output
            
            process_result = self.agent._tool_runner.run_tool(
                pytest_tool_command,
                cwd=self.agent._target_dir, # Run pytest from the project root
                venv_path=self.agent._env_manager.venv_path, # Use project's venv
                env_vars=test_execution_env_vars
            )
            details["return_code"] = process_result.returncode
            details["stdout_summary"] = self._truncate_output(process_result.stdout, max_len=1000, head_len=400, tail_len=400)
            details["stderr_summary"] = self._truncate_output(process_result.stderr)
            
            # Store more complete test output in main report_data if needed for detailed review
            # This summary is for the step itself.
            self.agent._report_data["test_results_summary"] = {
                "tool": "pytest",
                "test_file": str(test_file_to_execute_path),
                "return_code": process_result.returncode,
                "stdout": process_result.stdout, # Potentially large, TUI might truncate/link
                "stderr": process_result.stderr
            }

            # Interpret Pytest exit codes:
            # 0: All tests passed
            # 1: Tests were collected and run but some failed
            # 2: Test execution was interrupted by the user
            # 3: Internal error occurred during test execution
            # 4: Pytest command line usage error
            # 5: No tests were collected
            if process_result.returncode == 0:
                details["message"] = "All AI-generated tests passed successfully according to Pytest."
                self._logger.info(details["message"] + " " + (details.get("notes",[""])[0]))
                return STATUS_SUCCESS, details
            elif process_result.returncode == 1:
                details["message"] = "Some AI-generated tests failed. Review Pytest output."
                self._logger.warning(details["message"] + " " + (details.get("notes",[""])[0]))
                if self.agent._config.get_bool("fail_on_test_failure", True):
                    return STATUS_FAILURE, details
                return STATUS_WARNING, details
            elif process_result.returncode == 5:
                details["message"] = "Pytest collected no tests. This may indicate issues with test discovery, the generated test file structure, or that no tests were valid."
                self._logger.warning(details["message"] + " " + (details.get("notes",[""])[0]))
                # No tests found is typically a WARNING, not a critical failure, unless configured otherwise.
                # It doesn't mean the tool failed, but the outcome isn't a pass.
                return STATUS_WARNING, details
            elif process_result.returncode == -1 and "TimeoutExpired" in process_result.stderr: # Scribe-detected timeout
                timeout_msg = f"Pytest execution command timed out. Stderr: {process_result.stderr.strip()}"
                self._logger.error(timeout_msg)
                raise ScribeToolError(timeout_msg)
            else: # Other Pytest exit codes (2, 3, 4) usually indicate issues with Pytest setup or execution itself.
                error_msg = f"Pytest execution failed with an unexpected return code: {process_result.returncode}."
                self._logger.error(error_msg)
                details["message"] = error_msg
                raise ScribeToolError(
                    f"{error_msg} This may indicate a problem with Pytest setup, test discovery, or an internal Pytest error. "
                    f"Stdout: {process_result.stdout.strip()} Stderr: {process_result.stderr.strip()}"
                )
        
        except FileNotFoundError: # If 'pytest' executable is not found
            self._logger.warning("Pytest tool not found. Skipping AI-generated test execution.")
            details["message"] = "Pytest tool not found, test execution was skipped."
            return STATUS_SKIPPED, details
        except ScribeToolError as e:
            self._logger.error(f"Pytest execution step encountered a tool error: {e}", exc_info=True)
            raise # Re-raise for _execute_step
        # --- Workflow Steps Logic (Continuation) ---
# class WorkflowSteps:
#     ... (previous methods from Part 7: extract_signatures to execute_tests) ...

    def review_code(self) -> Tuple[str, StepOutputDetails]:
        """Performs AI-driven code review simulation on the target file."""
        self._logger.info(f"Performing AI code review simulation for: {self.agent._target_file_path}...")
        details: StepOutputDetails = {
            "tool_name": "LLM (code review)", # More specific
            "llm_model": self.agent._llm_client._model,
            "prompt_type": "code_review",
            "notes": ["AI-generated review findings are advisory and REQUIRE HUMAN INTERPRETATION AND VALIDATION. They are not definitive."]
        }

        if not self.agent._target_file_path or not self.agent._target_file_path.is_file():
            raise ScribeError("Internal Scribe Error: Target file path not set or file does not exist for 'review_code' step.")

        try:
            source_code_content_for_review = self.agent._target_file_path.read_text(encoding='utf-8')
            
            # LLMClient.generate_review is expected to return Optional[List[Dict[str, str]]]
            # None indicates an API or parsing error within the client.
            # An empty list [] means successful call but LLM returned no findings / empty valid JSON.
            list_of_review_findings = self.agent._llm_client.generate_review(
                source_code_content_for_review,
                str(self.agent._target_file_path.name) # Pass relative/display name for prompt
            )

            if list_of_review_findings is None: # Indicates an error within LLMClient (API or parsing)
                details["message"] = "AI code review step failed: Could not retrieve or parse review findings from the LLM."
                self._logger.error(details["message"] + " Check LLMClient logs for more details.")
                # This is typically a WARNING for the overall Scribe run, as review is advisory.
                # The Scribe step itself "failed" to get good data, but doesn't stop other steps.
                return STATUS_WARNING, details 
            
            details["issues_found"] = list_of_review_findings # Store the list of findings dicts
            # Also store in the main report_data for potential top-level summary
            self.agent._report_data["ai_review_findings"] = list_of_review_findings

            if not list_of_review_findings: # Empty list means LLM found nothing or returned empty JSON
                details["message"] = "AI code review completed. The LLM did not flag any specific issues."
            else:
                details["message"] = f"AI code review completed. LLM provided {len(list_of_review_findings)} potential issues/suggestions."
            
            self._logger.info(details["message"] + " " + (details.get("notes",[""])[0]))
            # This step is always ADVISORY as its findings are for human consideration, not a pass/fail criteria by itself.
            return STATUS_ADVISORY, details

        except FileNotFoundError: # Should be caught by initial check
            self._logger.error(f"Target file '{self.agent._target_file_path}' not found during AI code review preparation.")
            raise ScribeFileSystemError(f"Target file '{self.agent._target_file_path}' not found.") from None
        except ScribeApiError as e: # Should be handled by LLMClient, but as a safeguard
            self._logger.error(f"LLM API error during AI code review step: {e}", exc_info=False)
            details["message"] = f"LLM API communication failed during code review: {e}"
            return STATUS_WARNING, details # Treat API errors in review as warnings
        except Exception as e:
            self._logger.error(f"An unexpected error occurred during AI code review: {e}", exc_info=True)
            raise ScribeError(f"Unexpected error in AI code review workflow: {e}") from e


    def run_precommit(self) -> Tuple[str, StepOutputDetails]:
        """Runs pre-commit hooks on the target file if pre-commit is configured in the project."""
        self._logger.info(f"Running pre-commit hooks (if configured) on: {self.agent._target_file_path}...")
        details: StepOutputDetails = {"tool_name": "pre-commit"}

        if not self.agent._target_file_path or not self.agent._target_file_path.is_file():
            raise ScribeError("Internal Scribe Error: Target file path not set or file does not exist for 'run_precommit' step.")

        # Check for a pre-commit configuration file in the target project's root
        precommit_config_file_path = self.agent._target_dir / ".pre-commit-config.yaml"
        if not precommit_config_file_path.is_file():
            details["message"] = "No '.pre-commit-config.yaml' found in target project root. Skipping pre-commit hooks."
            self._logger.info(details["message"])
            return STATUS_SKIPPED, details

        try:
            # pre-commit tool needs to be found (config tool_paths, venv, or PATH)
            # Command: pre-commit run --files <specific_target_file>
            precommit_tool_command = ["pre-commit", "run", "--files", str(self.agent._target_file_path)]
            
            process_result = self.agent._tool_runner.run_tool(
                precommit_tool_command,
                cwd=self.agent._target_dir, # pre-commit generally runs from the project root
                venv_path=self.agent._env_manager.venv_path # Hooks might need access to project's venv
            )
            details["return_code"] = process_result.returncode
            details["stdout_summary"] = self._truncate_output(process_result.stdout, max_len=1000)
            details["stderr_summary"] = self._truncate_output(process_result.stderr) # Errors/failures might also be on stderr

            # pre-commit exit codes:
            # 0: All hooks passed (or no hooks applicable to the files)
            # 1: Some hooks failed or made changes (if hooks modify files, they might exit 1 and expect re-staging)
            # Other codes might indicate errors with pre-commit itself.
            if process_result.returncode == 0:
                details["message"] = "Pre-commit hooks passed successfully (or no relevant hooks were run)."
                self._logger.info(details["message"])
                return STATUS_SUCCESS, details
            elif process_result.returncode == -1 and "TimeoutExpired" in process_result.stderr: # Scribe-detected timeout
                timeout_msg = f"Pre-commit execution command timed out. Stderr: {process_result.stderr.strip()}"
                self._logger.error(timeout_msg)
                raise ScribeToolError(timeout_msg)
            else: # Non-zero (typically 1 if hooks fail/modify)
                details["message"] = f"Pre-commit hooks failed or made changes (RC={process_result.returncode}). Review output."
                self._logger.warning(details["message"] + " Check stdout/stderr summaries.")
                # Pre-commit failures are generally considered a FAILURE for validation pipelines.
                return STATUS_FAILURE, details
        
        except FileNotFoundError: # If 'pre-commit' executable itself is not found
            self._logger.warning("pre-commit tool not found. Skipping pre-commit hooks execution.")
            details["message"] = "pre-commit tool not found, pre-commit hooks were skipped."
            return STATUS_SKIPPED, details
        except ScribeToolError as e:
            self._logger.error(f"Pre-commit hooks step encountered a tool error: {e}", exc_info=True)
            raise


    def commit_changes(self) -> Tuple[str, StepOutputDetails]:
        """Attempts to Git commit the validated changes if requested and applicable."""
        self._logger.info("Attempting to Git commit validated changes (if requested via --commit)...")
        details: StepOutputDetails = {"tool_name": "git"}
        self.agent._report_data["commit_attempted"] = self.agent._args.commit # Record intent in main report

        if not self.agent._args.commit: # Check if commit was actually requested via CLI flag
            details["message"] = "Commit step skipped: --commit flag was not provided by the user."
            self._logger.info(details["message"])
            return STATUS_SKIPPED, details
        
        if not self.agent._target_file_path: # Should be set
            raise ScribeError("Internal Scribe Error: Target file path not set for 'commit_changes' step.")
        
        if not self.agent.git_exe: # Path to git executable, cached in ScribeAgent.__init__
            details["message"] = "Git executable ('git') not found in Scribe's environment (checked config tool_paths & system PATH). Cannot commit."
            self._logger.warning(details["message"])
            # This is a WARNING because commit was requested but the tool is missing. It doesn't invalidate prior steps.
            return STATUS_WARNING, details

        try:
            # 1. Verify we are inside a Git working tree for the target project
            is_git_repo_command = [self.agent.git_exe, "rev-parse", "--is-inside-work-tree"]
            repo_check_proc = self.agent._tool_runner.run_tool(is_git_repo_command, cwd=self.agent._target_dir)
            if repo_check_proc.returncode != 0 or repo_check_proc.stdout.strip().lower() != "true":
                details["message"] = f"Target directory '{self.agent._target_dir}' is not a Git repository or not inside a work tree. Skipping commit."
                self._logger.warning(details["message"])
                return STATUS_WARNING, details

            # 2. Check status of the specific target file to see if there are changes
            # `git status --porcelain <file>` shows status codes if changed/staged/untracked. Empty if clean.
            git_status_command = [self.agent.git_exe, "status", "--porcelain", str(self.agent._target_file_path)]
            status_proc = self.agent._tool_runner.run_tool(git_status_command, cwd=self.agent._target_dir)
            details["raw_output"] = status_proc.stdout.strip() # Store porcelain status for debugging

            if status_proc.returncode != 0:
                details["message"] = "Failed to get Git status for the target file before commit attempt."
                details["stderr_summary"] = self._truncate_output(status_proc.stderr)
                self._logger.error(f"{details['message']} Stderr: {status_proc.stderr.strip()}")
                return STATUS_FAILURE, details # Failure of the git status operation

            if not status_proc.stdout.strip(): # Empty output means file is clean w.r.t index and work tree
                details["message"] = f"No changes detected by 'git status --porcelain' for file '{self.agent._target_file_path.name}'. Nothing to commit."
                self._logger.info(details["message"])
                self.agent._report_data["commit_sha"] = "NO_CHANGES" # Special marker
                return STATUS_SUCCESS, details # Success, but effectively a no-op commit-wise

            # 3. Stage (add) the target file
            self._logger.info(f"Staging file for commit: {self.agent._target_file_path}")
            git_add_command = [self.agent.git_exe, "add", str(self.agent._target_file_path)]
            add_proc = self.agent._tool_runner.run_tool(git_add_command, cwd=self.agent._target_dir)
            if add_proc.returncode != 0:
                details["message"] = f"Failed to 'git add' the target file '{self.agent._target_file_path.name}'."
                details["stderr_summary"] = self._truncate_output(add_proc.stderr)
                self._logger.error(f"{details['message']} Stderr: {add_proc.stderr.strip()}")
                return STATUS_FAILURE, details

            # 4. Perform the commit
            commit_msg_template_str = self.agent._config.get_str("commit_message_template", "feat(Scribe): Auto-commit validated changes to {target_file}")
            final_commit_message = commit_msg_template_str.format(target_file=self.agent._target_file_path.name)
            self._logger.info(f"Attempting Git commit with message: \"{final_commit_message}\"")
            git_commit_command = [self.agent.git_exe, "commit", "-m", final_commit_message]
            commit_proc = self.agent._tool_runner.run_tool(git_commit_command, cwd=self.agent._target_dir)

            details["return_code"] = commit_proc.returncode
            details["stdout_summary"] = self._truncate_output(commit_proc.stdout)
            details["stderr_summary"] = self._truncate_output(commit_proc.stderr)

            if commit_proc.returncode != 0:
                # Handle specific "nothing to commit" cases if 'git add' didn't result in actual diff to HEAD
                if "nothing to commit" in commit_proc.stdout.lower() or \
                   "nothing to commit" in commit_proc.stderr.lower() or \
                   "no changes added to commit" in commit_proc.stdout.lower(): # Git commit --dry-run might say this
                    details["message"] = "Git commit command reported 'nothing to commit', possibly because 'git add' staged no effective changes."
                    self._logger.info(details["message"])
                    self.agent._report_data["commit_sha"] = "NO_EFFECTIVE_CHANGES_STAGED"
                    return STATUS_SUCCESS, details # Success, as there's nothing to fail on here
                
                details["message"] = f"Git commit command failed (RC={commit_proc.returncode})."
                self._logger.error(f"{details['message']} Review git output. Stdout: {commit_proc.stdout.strip()} Stderr: {commit_proc.stderr.strip()}")
                return STATUS_FAILURE, details

            # 5. If commit succeeded, get the new commit SHA
            git_get_sha_command = [self.agent.git_exe, "rev-parse", "HEAD"]
            sha_proc = self.agent._tool_runner.run_tool(git_get_sha_command, cwd=self.agent._target_dir)
            if sha_proc.returncode == 0 and sha_proc.stdout.strip():
                new_commit_sha = sha_proc.stdout.strip()
                details["message"] = f"Changes successfully committed. New commit SHA: {new_commit_sha}"
                details["commit_sha"] = new_commit_sha
                self.agent._report_data["commit_sha"] = new_commit_sha # Update main report
                self._logger.info(details["message"])
                return STATUS_SUCCESS, details
            else: # Commit likely succeeded, but couldn't get SHA
                details["message"] = "Commit was likely successful, but failed to retrieve the new commit SHA."
                self._logger.warning(details["message"] + f" rev-parse stdout: {sha_proc.stdout.strip()}, stderr: {sha_proc.stderr.strip()}")
                return STATUS_WARNING, details

        except ScribeToolError as e: # Covers failures in ToolRunner for any git command
            self._logger.error(f"A Git command failed execution during commit_changes step: {e}", exc_info=False) # Error is usually descriptive
            details["message"] = f"Git operation error: {str(e)[:500]}" # Keep it somewhat concise
            return STATUS_FAILURE, details # Failure of the step due to tool error
        except Exception as e: # Catch any other unexpected errors
            self._logger.error(f"An unexpected error occurred during Git commit operations: {e}", exc_info=True)
            raise ScribeError(f"Unexpected error during Git commit: {e}") from e


    def generate_report(self) -> Tuple[str, StepOutputDetails]:
        """
        Finalizes and generates the Scribe run report.
        The generated report string is returned via StepOutputDetails.raw_output.
        This step should ideally always succeed if ScribeAgent is still running.
        """
        self._logger.info("Finalizing and generating Scribe validation report...")
        details: StepOutputDetails = {}
        try:
            # Update final fields in the main report_data dictionary
            self.agent._report_data["end_time"] = datetime.now(timezone.utc).isoformat()
            
            # Calculate total duration if start_time is valid
            if self.agent._report_data.get("start_time"):
                try:
                    start_datetime_obj = datetime.fromisoformat(self.agent._report_data["start_time"])
                    end_datetime_obj = datetime.fromisoformat(self.agent._report_data["end_time"])
                    self.agent._report_data["total_duration_seconds"] = round((end_datetime_obj - start_datetime_obj).total_seconds(), 3)
                except ValueError: # Should not happen if start_time is always ISO
                    self._logger.error("Could not parse start/end times to calculate total_duration_seconds.", exc_info=True)
                    self.agent._report_data["total_duration_seconds"] = -1.0 # Indicate error
            
            # Overall status is determined by self.agent._overall_success flag,
            # which is updated by ScribeAgent._add_step_result after each step.
            self.agent._report_data["overall_status"] = STATUS_SUCCESS if self.agent._overall_success else STATUS_FAILURE
            
            # The ReportGenerator instance handles the actual formatting (JSON or text)
            generated_report_string = self.agent._report_generator.generate(self.agent._report_data)
            
            details["message"] = f"Final Scribe report generated successfully in '{self.agent._args.report_format}' format."
            # The primary output of this step IS the report string itself.
            details["raw_output"] = generated_report_string 
            self._logger.info(details["message"])
            # Log a snippet of the report for quick glance in debug logs, careful if it's huge
            self._logger.debug(f"Generated report snippet (first 300 chars): {generated_report_string[:300]}...")
            return STATUS_SUCCESS, details
        except Exception as e:
            self._logger.critical(f"CRITICAL error during final report generation: {e}", exc_info=True)
            # This is a severe failure if Scribe cannot even produce its final report.
            details["message"] = f"Fatal error during final report generation: {e}"
            # Try to construct a minimal emergency error report string
            emergency_report_str = json.dumps({
                "scribe_version": APP_VERSION,
                "run_id": self.agent._run_id if hasattr(self.agent, '_run_id') else "unknown_run",
                "overall_status": STATUS_FAILURE,
                "error_message": f"CRITICAL: Report generation step itself failed: {e}",
                "steps": self.agent._report_data.get("steps", []) # Include any steps processed so far
            }, indent=2, default=str) # Use default=str for safety
            details["raw_output"] = emergency_report_str # This becomes Scribe's output
            return STATUS_FAILURE, details

# End of WorkflowSteps class# --- Scribe Agent Orchestrator ---
class ScribeAgent:
    """
    Orchestrates the entire Scribe validation workflow.
    Initializes all necessary components (configuration, tool runners, environment
    manager, LLM client, report generator, and workflow step logic).
    The run() method executes the validation pipeline based on the steps
    defined in the configuration.
    """
    def __init__(self, args: argparse.Namespace):
        self._args = args # Parsed command-line arguments
        # Logging is assumed to be already set up by main() before this class is instantiated.
        self._logger = logging.getLogger(APP_NAME)
        self._logger.info(f"Initializing {APP_NAME} Orchestrator v{APP_VERSION} for run...")

        self._start_time_utc = datetime.now(timezone.utc)
        # V1.1: Include PID for more unique run_id, helpful if multiple Scribe instances
        # run close together (e.g., in parallel tests or CI).
        self._run_id = self._start_time_utc.strftime('%Y%m%d_%H%M%S_%f')[:-3] + f"_pid{os.getpid()}"
        self._logger.info(f"Scribe Agent Run ID: {self._run_id}")

        # V1.1: Determine if running in NAI context for ScribeConfig defaults.
        # This could be passed via a hidden CLI flag, an environment variable,
        # or inferred if Scribe is bundled in a known NAI structure.
        # For now, assuming it might be an attribute on args or an env var.
        # Example: is_nai_context_flag = getattr(args, 'nai_context', os.getenv("NAI_CONTEXT", "false").lower() == 'true')
        is_nai_context_flag = False # Default to false unless explicitly set/detected

        self._config: ScribeConfig = ScribeConfig(args.config_file, is_nai_context=is_nai_context_flag)
        self._tool_runner: ToolRunner = ToolRunner(self._config) # V1.1: ToolRunner now takes config

        # Validate the target directory early, as many components depend on it.
        # This raises ScribeInputError if validation fails.
        self._target_dir: Path = self._validate_target_dir()
        self._logger.info(f"Validated target project directory for Scribe operations: {self._target_dir}")

        self._env_manager: EnvironmentManager = EnvironmentManager(
            self._target_dir,
            args.python_version, # Currently informational; venv uses Scribe's Python
            self._tool_runner,
            self._config # V1.1: Pass config for timeouts etc.
        )
        self._llm_client: LLMClient = LLMClient(self._config, args) # args for CLI overrides of LLM settings
        self._report_generator: ReportGenerator = ReportGenerator(args.report_format)
        
        # This dictionary will be populated with all data for the final report.
        self._report_data: FinalReport = self._initialize_report()
        self._overall_success: bool = True # Tracks if any critical step results in FAILURE

        # These paths are critical and will be populated by the 'validate_inputs' workflow step
        self._target_file_path: Optional[Path] = None # Absolute path to the file being modified/validated
        self._temp_code_path: Optional[Path] = None   # Absolute path to the --code-file (source of new code)

        # Cache the path to the Git executable if found.
        self.git_exe: Optional[str] = self._find_git_executable()

        # Instantiate the WorkflowSteps class, providing a reference to this ScribeAgent instance
        # so step methods can access shared components (config, tool_runner, etc.) and agent state.
        self.steps = WorkflowSteps(self)
        self._logger.info("ScribeAgent and its components initialized successfully.")

    def _find_git_executable(self) -> Optional[str]:
        """
        Finds the 'git' executable using ScribeConfig's tool_paths or system PATH.
        Returns the string path to Git, or None if not found.
        """
        self._logger.debug("Attempting to locate 'git' executable...")
        try:
            # Use ToolRunner's internal _find_executable logic by asking it to find 'git'
            # without a venv context, so it checks config then PATH.
            git_path_obj = self._tool_runner._find_executable("git", venv_path=None)
            if git_path_obj:
                self._logger.info(f"Git executable found at: {git_path_obj}")
                return str(git_path_obj)
        except FileNotFoundError:
            self._logger.warning("'git' executable not found in Scribe config 'tool_paths' or system PATH. Git-dependent steps will be skipped or may fail.")
        except Exception as e: # Catch any other unexpected errors
            self._logger.error(f"An unexpected error occurred while trying to find 'git': {e}", exc_info=True)
        return None

    def _validate_target_dir(self) -> Path:
        """
        Validates the target directory specified by --target-dir argument.
        Ensures it exists, is a directory, and is within allowed base paths from Scribe config.
        Returns the resolved, absolute Path object for the target directory.
        Raises ScribeInputError on validation failure.
        """
        self._logger.debug(f"Validating target directory from CLI argument: '{self._args.target_dir}'")
        if not self._args.target_dir: # Should be caught by argparse if 'required=True'
            raise ScribeInputError("--target-dir argument is mandatory and was not provided.")
        
        try:
            # Resolve the path (handles ., .., symlinks) and ensure it's absolute.
            # strict=True means it must exist.
            target_dir_absolute = Path(self._args.target_dir).resolve(strict=True)
        except FileNotFoundError:
            raise ScribeInputError(f"Target directory '{self._args.target_dir}' does not exist.")
        except Exception as e: # Catch other potential errors from Path().resolve()
            raise ScribeInputError(f"Invalid target directory path specified '{self._args.target_dir}': {e}")

        if not target_dir_absolute.is_dir():
            raise ScribeInputError(f"Specified target path '{target_dir_absolute}' is not a directory.")

        # Security check against 'allowed_target_bases' from Scribe configuration
        configured_allowed_base_paths_str = self._config.get_list("allowed_target_bases", []) # Already resolved in ScribeConfig
        if not configured_allowed_base_paths_str:
            # This case should ideally be prevented by ScribeConfig validation ensuring defaults are lists.
            self._logger.warning(
                "CRITICAL CONFIG ISSUE: 'allowed_target_bases' is empty or not found in Scribe configuration. "
                "For security, Scribe requires this to be defined. Assuming a restrictive default is missing."
            )
            # This should ideally be a ScribeConfigurationError.
            # To prevent accidental operation on unintended dirs, could raise here.
            # For now, proceed but with a strong warning. Later, might make this fatal.
            # However, ScribeConfig validation should make this list always exist.
            pass # Pass for now, relies on ScribeConfig having populated this from defaults


        # Convert string paths from config to Path objects for reliable comparison
        allowed_base_paths_resolved = [Path(p_str) for p_str in configured_allowed_base_paths_str]

        is_path_allowed = False
        for base_p in allowed_base_paths_resolved:
            # Check if target_dir_absolute is identical to base_p or is a sub-directory of base_p.
            # str(path).startswith(str(base) + os.sep) is a common way to check for subdirectories.
            # Path.is_relative_to() is Python 3.9+ but more robust for symlinks etc. if available.
            # Using string comparison for broader compatibility and because paths are resolved.
            if target_dir_absolute == base_p or \
               str(target_dir_absolute).startswith(str(base_p.resolve()) + os.sep):
                is_path_allowed = True
                break
        
        if not is_path_allowed:
            self._logger.error(
                f"Target directory '{target_dir_absolute}' is not within any of the allowed base directories. "
                f"Allowed bases configured in Scribe: {configured_allowed_base_paths_str}"
            )
            raise ScribeInputError(
                f"Operation on target directory '{target_dir_absolute}' is denied due to security policy "
                "(not within 'allowed_target_bases'). Please check Scribe configuration."
            )
        
        self._logger.debug(f"Target directory '{target_dir_absolute}' successfully validated against allowed bases.")
        return target_dir_absolute

    def _initialize_report(self) -> FinalReport:
        """Initializes the structure for the final JSON/text report."""
        self._logger.debug("Initializing Scribe run report data structure.")
        # Using cast for type checker, assuming all fields will be correctly populated.
        return cast(FinalReport, {
            "scribe_version": APP_VERSION,
            "run_id": self._run_id,
            "start_time": self._start_time_utc.isoformat(), # Record start time in ISO format (UTC)
            "end_time": "",             # To be filled at the end of the run
            "total_duration_seconds": 0.0, # To be calculated at the end
            "overall_status": STATUS_PENDING, # Initial status
            "target_project_dir": str(self._args.target_dir), # Report the original arg path
            "target_file_relative": self._args.target_file, # Report the original arg
            "language": self._args.language,
            "python_version": self._args.python_version, # Python version used for venv/checks
            "commit_attempted": self. _args.commit, # Record if user intended to commit
            "commit_sha": None,          # Will be filled by 'commit_changes' step if successful
            "steps": [],                 # List of StepResult dictionaries
            # Top-level summaries can be populated by relevant steps if they produce complex data
            # that also needs a summary view at the report's root.
            "audit_findings": None,      # E.g., populated by 'audit_deps'
            "ai_review_findings": None,  # E.g., populated by 'review_code'
            "test_results_summary": None # E.g., populated by 'execute_tests'
        })

    def _add_step_result(self,
                         step_name_str: str,
                         status_code_str: str, 
                         step_start_datetime: datetime,
                         step_details_obj: Union[str, StepOutputDetails, Dict[str, Any], List[Any], None] = None,
                         error_msg_str: Optional[str] = None):
        """
        Adds the result of a completed workflow step to the main report data.
        Updates the overall success flag if a step fails.
        Logs the step result.
        """
        step_end_datetime = datetime.now(timezone.utc)
        duration_secs = round((step_end_datetime - step_start_datetime).total_seconds(), 3)

        # Ensure step_details_obj is serializable for the report using ReportGenerator's helper.
        # This handles various types including subprocess.CompletedProcess if it were passed directly.
        # WorkflowSteps methods are now designed to return serializable StepOutputDetails dicts.
        serializable_step_details = self._report_generator._make_serializable(step_details_obj)

        current_step_result: StepResult = cast(StepResult, {
            "name": step_name_str,
            "status": status_code_str,
            "start_time": step_start_datetime.isoformat(),
            "end_time": step_end_datetime.isoformat(),
            "duration_seconds": duration_secs,
            "details": serializable_step_details, # This should be the StepOutputDetails dict or similar
            "error_message": str(error_msg_str) if error_msg_str else None
        })
        self._report_data["steps"].append(current_step_result)

        # Update overall success: if any step results in FAILURE, the entire run is a FAILURE.
        # WARNING or ADVISORY steps do not change _overall_success from True to False,
        # but if _overall_success is already False, it stays False.
        if status_code_str == STATUS_FAILURE:
            if self._overall_success: # Only log the first time it transitions to False
                self._logger.warning(f"Overall Scribe run status changed to FAILURE due to step: '{step_name_str}'.")
            self._overall_success = False

        # Determine log level based on step status
        log_level_for_step = logging.INFO
        if status_code_str == STATUS_FAILURE: log_level_for_step = logging.ERROR
        elif status_code_str == STATUS_WARNING: log_level_for_step = logging.WARNING
        # SKIPPED and ADVISORY can be INFO or DEBUG depending on desired verbosity. Let's use INFO.
        
        log_line_message = f"Step '{step_name_str}': {status_code_str} (Duration: {duration_secs:.3f}s)"
        
        # Append a summary of details or error to the log line
        if error_msg_str:
            log_line_message += f" | Error: {str(error_msg_str)[:250]}" # Truncate for log line
        elif isinstance(serializable_step_details, dict) and serializable_step_details.get("message"):
            log_line_message += f" | Message: {str(serializable_step_details['message'])[:200]}"
        elif isinstance(serializable_step_details, str) and serializable_step_details: # If details is just a string
             log_line_message += f" | Detail: {serializable_step_details[:200]}"
        
        self._logger.log(log_level_for_step, log_line_message)
        # For detailed debugging, one might log the full serializable_step_details object
        self._logger.debug(f"Full details object for step '{step_name_str}': {json.dumps(serializable_step_details, default=str, indent=2)}")


    def _execute_step(self,
                      workflow_step_function: Callable[..., Any], # The method from self.steps (e.g., self.steps.format_code)
                      *step_func_args: Any, **step_func_kwargs: Any) -> Any: # Args/kwargs for the step_function
        """
        Executes a single workflow step function.
        Handles timing, adds result to report (via _add_step_result), catches exceptions.
        Updates self._overall_success flag based on step outcome.
        Returns the primary output of the step function if successful (e.g., data for next step), else None.
        """
        step_function_name = getattr(workflow_step_function, '__name__', str(workflow_step_function))
        self._logger.info(f"--- Starting Scribe Workflow Step: {step_function_name} ---")
        step_invocation_start_time = datetime.now(timezone.utc)
        
        current_step_status: str = STATUS_FAILURE # Default to failure unless step succeeds
        current_step_details: Union[str, StepOutputDetails, Dict[str, Any], List[Any], None] = None
        current_step_error_msg: Optional[str] = None
        step_primary_return_value: Any = None # Value to pass to subsequent steps if needed

        # If a preceding critical step failed, and this is not 'generate_report', skip execution.
        # The 'generate_report' step should always attempt to run to provide output.
        if not self._overall_success and step_function_name != "generate_report":
            current_step_status = STATUS_SKIPPED
            current_step_error_msg = "Skipped due to critical failure in a preceding Scribe step."
            current_step_details = {"message": current_step_error_msg} # Basic detail for skipped step
            self._logger.warning(f"Skipping step '{step_function_name}' due to prior overall failure status.")
        else:
            try:
                # WorkflowSteps methods are expected to return a tuple: (STATUS_CODE_STR, details_object)
                # or raise a ScribeError derivative for automatic FAILURE.
                raw_output_from_step_func = workflow_step_function(*step_func_args, **step_func_kwargs)

                if isinstance(raw_output_from_step_func, tuple) and len(raw_output_from_step_func) >= 1:
                    current_step_status = str(raw_output_from_step_func[0]) # First element is status string
                    if len(raw_output_from_step_func) > 1:
                        current_step_details = raw_output_from_step_func[1] # Second is details object
                    
                    # If the step itself reported FAILURE, try to extract an error message from its details if not already set.
                    if current_step_status == STATUS_FAILURE and not current_step_error_msg:
                        if isinstance(current_step_details, dict) and current_step_details.get("message"):
                            current_step_error_msg = str(current_step_details["message"])
                        elif isinstance(current_step_details, str):
                             current_step_error_msg = current_step_details
                        else:
                            current_step_error_msg = f"Step '{step_function_name}' reported FAILURE status."
                    
                    # If successful or advisory/warning, the primary output for the next step might be in 'raw_output' of details,
                    # or the details object itself if it's not a dict, or if 'raw_output' is not present.
                    if current_step_status in [STATUS_SUCCESS, STATUS_ADVISORY, STATUS_WARNING]:
                        if isinstance(current_step_details, dict) and "raw_output" in current_step_details:
                            step_primary_return_value = current_step_details["raw_output"]
                        elif not isinstance(current_step_details, dict): # If details is a simple string/value (e.g. from older step design)
                             step_primary_return_value = current_step_details
                        # else: step_primary_return_value remains None if details is a dict without 'raw_output'

                else: # Should not happen if WorkflowSteps methods adhere to the return contract.
                    self._logger.error(
                        f"Step '{step_function_name}' returned an unexpected result format: type '{type(raw_output_from_step_func)}'. "
                        "Expected a tuple (status_str, details_obj). Treating as SUCCESS with raw output as detail."
                    )
                    current_step_status = STATUS_SUCCESS # Assume success if format is wrong but no exception.
                    current_step_details = {"raw_output": str(raw_output_from_step_func), "message": "Step returned non-standard output."}
                    step_primary_return_value = raw_output_from_step_func

            except ScribeError as e: # Catch specific Scribe errors (ScribeConfigurationError, ScribeInputError, etc.)
                self._logger.error(f"A ScribeError occurred in step '{step_function_name}': {type(e).__name__} - {e}", exc_info=False)
                self._logger.debug(f"Traceback for ScribeError in '{step_function_name}':", exc_info=True) # Full trace for debug
                current_step_status = STATUS_FAILURE
                current_step_error_msg = f"{type(e).__name__}: {e}" # Use the specific error type and message
                current_step_details = {"error_type": type(e).__name__, "error_details_str": str(e)}
            except Exception as e: # Catch any other unhandled Python exceptions from the step function
                self._logger.critical(f"CRITICAL: An unhandled exception occurred in step '{step_function_name}': {type(e).__name__} - {e}", exc_info=True)
                current_step_status = STATUS_FAILURE
                current_step_error_msg = f"Unhandled Exception {type(e).__name__}: {e}"
                current_step_details = {
                    "error_type": type(e).__name__,
                    "error_details_str": str(e),
                    "traceback_snippet": traceback.format_exc(limit=5) # Include a snippet for the report
                }

        # Add the result of this step to the main report data.
        # This also updates self._overall_success if current_step_status is FAILURE.
        self._add_step_result(
            step_function_name,
            current_step_status,
            step_invocation_start_time,
            current_step_details,
            current_step_error_msg
        )
        self._logger.info(f"--- Finished Scribe Workflow Step: {step_function_name} (Resulting Status: {current_step_status}) ---")
        
        # Return the primary output of the step only if it wasn't a critical failure or skip.
        # This value is used by ScribeAgent.run() to pass data between dependent steps.
        if current_step_status in [STATUS_SUCCESS, STATUS_ADVISORY, STATUS_WARNING]:
            return step_primary_return_value
        
        return None # For FAILURE or SKIPPED, no meaningful value to pass to next step logic in `run()`

    # The main run() method and _cleanup_temp_file() will follow in the next part.
    # --- Scribe Agent Orchestrator (Continuation) ---
# class ScribeAgent:
#     ... (previous methods from Part 9: __init__ to _execute_step) ...

    def run(self) -> int:
        """
        Executes the full Scribe validation workflow based on configured steps.
        Manages step dependencies, conditional skipping, and overall success status.
        Prints the final report to stdout and returns an exit code (0 for success, 1 for failure).
        """
        self._logger.info(f"Starting Scribe validation workflow (Run ID: {self._run_id}).")
        self._logger.info(f"Target Project Directory: {self._args.target_dir}")
        self._logger.info(f"Target File (relative path in project): {self._args.target_file}")
        self._logger.info(f"Source Code File (to apply): {self._args.code_file}")
        if self._config.config_path:
            self._logger.info(f"Using Scribe configuration from: {self._config.config_path}")
        else:
            self._logger.info("Using Scribe internal default configuration.")


        # V1.1: Map of step names (from config) to their corresponding WorkflowSteps methods.
        # This allows the 'validation_steps' in .scribe.toml to fully drive the workflow.
        step_execution_map: Dict[str, Callable[..., Any]] = {
            "validate_inputs": self.steps.validate_inputs,
            "setup_environment": self.steps.setup_environment,
            "install_deps": self.steps.install_deps,
            "audit_deps": self.steps.audit_deps,
            "apply_code": self.steps.apply_code,
            "format_code": self.steps.format_code,
            "lint_code": self.steps.lint_code,
            "type_check": self.steps.type_check,
            "extract_signatures": self.steps.extract_signatures,
            "generate_tests": self.steps.generate_tests,     # Depends on 'extract_signatures' output
            "save_tests": self.steps.save_tests,             # Depends on 'generate_tests' output
            "execute_tests": self.steps.execute_tests,       # Depends on 'save_tests' output
            "review_code": self.steps.review_code,
            "run_precommit": self.steps.run_precommit,
            "commit_changes": self.steps.commit_changes,
            "generate_report": self.steps.generate_report   # Should always run, even on failure
        }

        # Get the ordered list of steps to execute from the Scribe configuration.
        configured_step_execution_order = self._config.get_list("validation_steps", [])
        
        if not configured_step_execution_order:
            self._logger.critical("CRITICAL CONFIGURATION ERROR: 'validation_steps' is empty or not defined in Scribe configuration. Cannot proceed.")
            self._add_step_result( # Add a specific failure step to the report
                "workflow_initialization_failure", STATUS_FAILURE, self._start_time_utc,
                error_message="No 'validation_steps' found in Scribe configuration."
            )
            self._overall_success = False # Ensure overall status reflects this critical failure
            # Fall through to the 'finally' block to attempt report generation.
        else:
            self._logger.info(f"Beginning execution of {len(configured_step_execution_order)} configured validation steps.")
            self._logger.debug(f"Configured step order: {', '.join(configured_step_execution_order)}")


        # Cache for storing the primary outputs of steps, if needed by subsequent steps.
        # E.g., 'extract_signatures' output is needed by 'generate_tests'.
        previous_step_outputs_cache: Dict[str, Any] = {}

        try:
            for current_step_name in configured_step_execution_order:
                if current_step_name not in step_execution_map:
                    self._logger.error(
                        f"Unknown step '{current_step_name}' encountered in 'validation_steps' configuration. This step will be skipped."
                    )
                    self._add_step_result(current_step_name, STATUS_SKIPPED, datetime.now(timezone.utc),
                                          details={"message": f"Unknown step name '{current_step_name}' in config."})
                    continue # Skip to the next configured step

                step_method_to_invoke = step_execution_map[current_step_name]
                current_step_args: List[Any] = [] # Arguments to pass to the step method
                skip_this_step_flag = False # Flag to determine if current step should be skipped

                # --- Conditional Skipping Logic ---
                # 1. Check CLI skip flags first
                if current_step_name in ["setup_environment", "install_deps", "audit_deps"] and self._args.skip_deps:
                    skip_this_step_flag = True
                    self._logger.info(f"Skipping step '{current_step_name}' due to --skip-deps CLI flag.")
                elif current_step_name in ["extract_signatures", "generate_tests", "save_tests", "execute_tests"] and self._args.skip_tests:
                    skip_this_step_flag = True
                    self._logger.info(f"Skipping step '{current_step_name}' due to --skip-tests CLI flag.")
                elif current_step_name == "review_code" and self._args.skip_review:
                    skip_this_step_flag = True
                    self._logger.info(f"Skipping step '{current_step_name}' due to --skip-review CLI flag.")
                elif current_step_name == "commit_changes" and not self._args.commit:
                    # The 'commit_changes' step itself also checks this flag, but good to be explicit here for logging.
                    skip_this_step_flag = True
                    self._logger.info(f"Skipping step '{current_step_name}' as --commit CLI flag was not provided.")

                # 2. Check step dependencies if not already skipped by CLI flag
                if not skip_this_step_flag:
                    if current_step_name == "generate_tests":
                        extracted_sigs_details = previous_step_outputs_cache.get("extract_signatures")
                        if not isinstance(extracted_sigs_details, dict) or not extracted_sigs_details.get("raw_output"):
                            skip_this_step_flag = True
                            self._logger.info(f"Skipping '{current_step_name}': 'extract_signatures' step did not produce valid signature data (or was skipped/failed).")
                        else:
                            current_step_args = [extracted_sigs_details] # Pass the StepOutputDetails object
                    elif current_step_name == "save_tests":
                        generated_tests_details = previous_step_outputs_cache.get("generate_tests")
                        if not isinstance(generated_tests_details, dict) or not generated_tests_details.get("raw_output"):
                            skip_this_step_flag = True
                            self._logger.info(f"Skipping '{current_step_name}': 'generate_tests' step did not produce test code (or was skipped/failed).")
                        else:
                            current_step_args = [generated_tests_details]
                    elif current_step_name == "execute_tests":
                        saved_tests_details = previous_step_outputs_cache.get("save_tests")
                        if not isinstance(saved_tests_details, dict) or not saved_tests_details.get("raw_output"):
                            skip_this_step_flag = True
                            self._logger.info(f"Skipping '{current_step_name}': 'save_tests' step did not provide a test file path (or was skipped/failed).")
                        else:
                            current_step_args = [saved_tests_details]
                
                # --- Execute or Skip Step ---
                if skip_this_step_flag:
                    self._add_step_result(current_step_name, STATUS_SKIPPED, datetime.now(timezone.utc),
                                          details={"message": "Step skipped due to CLI flag or unmet prerequisite."})
                else:
                    # _execute_step handles detailed logging, error catching, and adding result to report.
                    # It returns the primary output of the step (e.g., signatures string, generated test code string, path to saved tests).
                    step_primary_output = self._execute_step(step_method_to_invoke, *current_step_args) # No kwargs currently used
                    previous_step_outputs_cache[current_step_name] = step_primary_output # Cache output for dependent steps

                    # If a critical step fails (and _overall_success becomes False), and it's not 'generate_report',
                    # halt further step execution. _execute_step handles updating _overall_success.
                    if not self._overall_success and current_step_name != "generate_report":
                        self._logger.warning(
                            f"Workflow execution halted after critical failure in step: '{current_step_name}'. "
                            "The final 'generate_report' step will still attempt to run."
                        )
                        break # Exit the loop of configured steps

        except ScribeConfigurationError as e: # Catch config errors that might arise if validation_steps has unknown items, etc.
            self._logger.critical(f"Scribe Configuration Error during workflow step execution: {e}", exc_info=True)
            self._add_step_result("workflow_step_orchestration", STATUS_FAILURE, self._start_time_utc, error_message=str(e))
            self._overall_success = False # Mark as overall failure
        except Exception as e: # Broad catch-all for truly unexpected errors in the run loop orchestration itself
            self._logger.critical(f"CRITICAL Unhandled Exception in ScribeAgent.run() step orchestrator: {e}", exc_info=True)
            self._add_step_result("workflow_orchestration_critical_error", STATUS_FAILURE, datetime.now(timezone.utc),
                                  error_message=f"Unhandled orchestrator exception: {type(e).__name__} - {e}",
                                  details={"traceback_snippet": traceback.format_exc(limit=5)})
            self._overall_success = False
        finally:
            # The 'generate_report' step is critical for output and should always attempt to run,
            # even if preceding steps failed or the loop was broken.
            # The _execute_step method's logic (if not self._overall_success and name != "generate_report")
            # already ensures it will run if called within the loop when _overall_success is False.
            # This 'finally' block ensures it runs if the loop completes, or if it was broken *before*
            # 'generate_report' was reached (and 'generate_report' IS in the configured steps).

            final_report_output_string: str = "{}" # Default to empty JSON if report gen fails badly

            # Check if 'generate_report' was configured to run and if it actually ran as the last step
            report_step_name = "generate_report"
            was_report_generated_in_main_loop = False
            if self._report_data["steps"] and self._report_data["steps"][-1]["name"] == report_step_name:
                 # And the status wasn't SKIPPED due to unknown step name
                 if self._report_data["steps"][-1]["status"] != STATUS_SKIPPED or \
                    (isinstance(self._report_data["steps"][-1]["details"],dict) and "Unknown step" not in self._report_data["steps"][-1]["details"].get("message","")):
                    was_report_generated_in_main_loop = True

            if report_step_name in step_execution_map and (report_step_name in configured_step_execution_order and not was_report_generated_in_main_loop):
                self._logger.info(
                    "Ensuring 'generate_report' step runs as it was not the final completed step in the loop, or loop was interrupted."
                )
                # _execute_step will run it even if _overall_success is False.
                # The return value of _execute_step(self.steps.generate_report) is the report string itself (from details.raw_output).
                report_step_execution_result = self._execute_step(step_execution_map[report_step_name])
                if isinstance(report_step_execution_result, str): # If raw_output was a string
                    final_report_output_string = report_step_execution_result
                elif report_step_execution_result is None and self._report_data["steps"]: # If it failed, try to get from last step
                     last_step_details = self._report_data["steps"][-1].get("details")
                     if isinstance(last_step_details, dict) and isinstance(last_step_details.get("raw_output"),str):
                        final_report_output_string = last_step_details["raw_output"]

            elif was_report_generated_in_main_loop: # Report was already generated as the last step
                last_step_details = self._report_data["steps"][-1].get("details")
                if isinstance(last_step_details, dict) and isinstance(last_step_details.get("raw_output"), str):
                    final_report_output_string = last_step_details["raw_output"]
                else:
                    self._logger.error("Could not retrieve final report string from the last executed step's details. Outputting minimal JSON.")
            else: # generate_report was not in config or step_map (should not happen with defaults)
                self._logger.error("'generate_report' step is not configured or available. Cannot produce final report via standard mechanism.")
                # Create a basic report if possible
                self._report_data["overall_status"] = STATUS_FAILURE if not self._overall_success else STATUS_SUCCESS
                self._report_data["end_time"] = datetime.now(timezone.utc).isoformat()
                final_report_output_string = json.dumps(self._report_data, indent=2, default=str)


            print(final_report_output_string) # Print the final report (JSON or text) to standard output.
            
            self._cleanup_temp_file() # Remove the temporary --code-file
            
            self._logger.info(
                f"--- Scribe Agent Workflow Ended. Overall Run Status: {self._report_data.get('overall_status', 'UNKNOWN')} ---"
            )
        
        return 0 if self._overall_success else 1 # Return standard OS exit code

    def _cleanup_temp_file(self):
        """
        Removes the temporary code file (specified by --code-file via self._temp_code_path)
        if it was set and still exists. This is for hygiene.
        """
        if self._temp_code_path and isinstance(self._temp_code_path, Path): # Ensure it's a Path object
            if self._temp_code_path.exists():
                try:
                    self._temp_code_path.unlink()
                    self._logger.info(f"Successfully cleaned up temporary source code file: {self._temp_code_path}")
                except OSError as e:
                    self._logger.warning(
                        f"Could not remove temporary source code file '{self._temp_code_path}': {e.strerror}. "
                        "Manual cleanup may be required."
                    )
            else:
                self._logger.debug(f"Temporary source code file '{self._temp_code_path}' not found. No cleanup needed for it.")
        else:
            # This might happen if validate_inputs didn't run or failed before setting _temp_code_path.
            self._logger.debug("Temporary code file path (_temp_code_path) was not set. No cleanup action taken for it.")

# End of ScribeAgent class

# --- Argument Parser Setup ---
def setup_arg_parser() -> argparse.ArgumentParser:
    """
    Sets up and returns the command-line argument parser for Project Scribe.
    Includes all V1.1 relevant arguments with descriptions and defaults.
    """
    parser = argparse.ArgumentParser(
        description=f"{APP_NAME} v{APP_VERSION} - Apex Automated Code Validation & Integration Agent.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter, # Provides default values in help messages
        epilog=(
            "Example Usage:\n"
            f"  python {sys.argv[0]} --target-dir ./my_project --code-file /tmp/new_code.py "
            "--target-file src/module_to_update.py --commit --log-level DEBUG --log-file ./scribe_run.log\n\n"
            "Note: For LLM features, ensure Ollama is running and accessible. "
            f"Configure LLM settings via ./{DEFAULT_CONFIG_FILENAME} or CLI overrides."
        )
    )
    parser.add_argument(
        '-v', '--version',
        action='version',
        version=f'%(prog)s {APP_VERSION} (Omnitide Nexus Edition)' # Added Nexus branding
    )

    # Core Inputs: Essential information for Scribe to operate
    core_input_group = parser.add_argument_group('Core Inputs (Required for Scribe Operation)')
    core_input_group.add_argument(
        '--target-dir',
        type=Path, # Converts argument to a Path object
        required=True,
        help="Path to the root directory of the target project that Scribe will operate on."
    )
    core_input_group.add_argument(
        '--code-file',
        type=Path,
        required=True,
        help="Path to the temporary file containing the new or modified code content that Scribe should apply and then validate."
    )
    core_input_group.add_argument(
        '--target-file',
        type=str, # Will be resolved relative to --target-dir
        required=True,
        help="Relative path (from --target-dir) to the file within the project where the content from --code-file should be applied."
    )

    # Configuration & General Behavior Options
    config_behavior_group = parser.add_argument_group('Configuration & General Behavior')
    config_behavior_group.add_argument(
        '--language',
        type=str,
        default="python",
        choices=["python"], # Currently, Scribe is tailored for Python projects
        help="Specifies the primary programming language of the code being validated. (Currently fixed to 'python')."
    )
    config_behavior_group.add_argument(
        '--python-version',
        type=str,
        default=DEFAULT_PYTHON_VERSION, # Default Python version Scribe might target for venv
        help="Target Python version string (e.g., '3.9', '3.11') for project environment context. Scribe itself requires Python 3.11+."
    )
    config_behavior_group.add_argument(
        '--config-file',
        type=Path, # Allow Path object for easier handling
        default=None, # If None, ScribeConfig searches default locations (e.g., CWD)
        help=f"Path to a specific Scribe configuration file (e.g., 'custom.scribe.toml'). Overrides default search for '{DEFAULT_CONFIG_FILENAME}'."
    )
    config_behavior_group.add_argument(
        '--commit',
        action='store_true', # Becomes args.commit = True if flag is present
        help="If specified, Scribe will attempt to Git commit the changes to --target-file if all critical validation steps pass."
    )
    config_behavior_group.add_argument(
        '--report-format',
        choices=REPORT_FORMATS, # ["json", "text"]
        default=DEFAULT_REPORT_FORMAT, # "json"
        help="Format for the final validation report that Scribe outputs to stdout."
    )

    # Flags to Skip Specific Validation Stages
    skip_flags_group = parser.add_argument_group('Skip Flags (for bypassing certain validation stages)')
    skip_flags_group.add_argument(
        '--skip-deps',
        action='store_true',
        help="Skip environment setup, project dependency installation, and dependency auditing (pip-audit) steps."
    )
    skip_flags_group.add_argument(
        '--skip-tests',
        action='store_true',
        help="Skip all AI-driven test steps: signature extraction, test generation, saving tests, and executing tests."
    )
    skip_flags_group.add_argument(
        '--skip-review',
        action='store_true',
        help="Skip the AI-driven code review simulation step."
    )

    # LLM Configuration Overrides (for advanced users or CI environments)
    llm_overrides_group = parser.add_argument_group('LLM Configuration Overrides (CLI takes precedence over .scribe.toml)')
    llm_overrides_group.add_argument(
        '--ollama-base-url',
        type=str,
        default=None, # If None, value from ScribeConfig (config file or default) is used
        help=f"Override the Ollama API base URL. (Default from config: '{DEFAULT_OLLAMA_BASE_URL}')"
    )
    llm_overrides_group.add_argument(
        '--ollama-model',
        type=str,
        default=None, # If None, value from ScribeConfig is used
        help=f"Override the Ollama model name to be used by Scribe. (Default from config: '{DEFAULT_OLLAMA_MODEL}')"
    )

    # Logging Configuration
    logging_group = parser.add_argument_group('Logging Configuration')
    logging_group.add_argument(
        '--log-level',
        choices=LOG_LEVELS, # ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        default=DEFAULT_LOG_LEVEL, # "INFO"
        help="Set the verbosity level for console logging."
    )
    logging_group.add_argument(
        '--log-file',
        type=Path, # Allow Path object
        default=None, # No log file by default
        help="Path to a file where Scribe will write detailed DEBUG-level logs. If not provided, only console logging occurs."
    )
    # Example of a hidden flag for internal context, not for general user help:
    # parser.add_argument('--nai-context', action='store_true', help=argparse.SUPPRESS)

    return parser

# --- Main Execution Function ---
def main(cli_args: Optional[Sequence[str]] = None) -> int:
    """
    Main entry point for the Project Scribe agent.
    Parses command-line arguments, sets up logging, instantiates the ScribeAgent,
    and runs the validation workflow.
    Returns an OS exit code: 0 for overall success, non-zero for errors.
    """
    # Perform critical dependency checks at the very beginning
    if not HTTP_LIB:
        # No logger is configured yet at this point, so print directly to stderr.
        print(f"FATAL ERROR ({APP_NAME}): An HTTP library ('httpx' or 'requests') is required for LLM communication, "
              "but neither could be imported. Please install one (e.g., 'pip install httpx requests').", file=sys.stderr)
        return 1 # Standard exit code for critical missing dependency

    # The tomllib check is at the top of the file and will sys.exit(1) if Python < 3.11.

    # If cli_args is None (standard execution), use sys.argv[1:].
    # If provided (e.g., for testing), use the provided sequence.
    effective_cli_args = sys.argv[1:] if cli_args is None else cli_args

    arg_parser_instance = setup_arg_parser()
    parsed_args: argparse.Namespace
    try:
        parsed_args = arg_parser_instance.parse_args(effective_cli_args)
    except SystemExit as e: # Handles -h, --help, --version which call sys.exit
        return e.code if isinstance(e.code, int) else 0 # --version usually exits 0
    except Exception as e: # Catch other potential argparse errors
        # Argparse usually prints its own error message to stderr before exiting.
        print(f"Error during command-line argument parsing: {e}", file=sys.stderr)
        # arg_parser_instance.print_usage(sys.stderr) # Can be redundant if argparse already did.
        return 2 # Specific exit code for argument parsing errors

    # Set up logging as early as possible after arguments are parsed (to use log_level, log_file)
    # setup_logging itself handles internal errors by printing to stderr if logger can't be made.
    try:
        setup_logging(parsed_args.log_level, parsed_args.log_file)
    except Exception as e: # Should be rare if setup_logging is robust
        print(f"FATAL: Unexpected critical error during logging system setup: {e}", file=sys.stderr)
        return 1 # Critical error before main agent can start

    main_logger = logging.getLogger(APP_NAME) # Get the main application logger
    main_logger.info(f"--- {APP_NAME} v{APP_VERSION} (Omnitide Nexus Edition) Execution Started ---")
    main_logger.debug(f"Effective command-line arguments: {parsed_args}")
    main_logger.debug(f"Python version: {sys.version.split()[0]}, Platform: {sys.platform}")
    main_logger.debug(f"HTTP library in use: {HTTP_LIB or 'None Found'}")


    final_exit_code: int = 1 # Default to a failure exit code

    try:
        # Instantiate the main ScribeAgent orchestrator
        scribe_agent_instance = ScribeAgent(parsed_args)
        # Run the Scribe workflow; ScribeAgent.run() returns 0 on success, 1 on failure.
        final_exit_code = scribe_agent_instance.run()
        main_logger.info(f"{APP_NAME} workflow completed. Final reported exit code: {final_exit_code}")

    except ScribeConfigurationError as e:
        # These errors are critical and usually mean Scribe cannot operate as intended.
        # ScribeConfig or ScribeAgent init might raise this if validation fails hard.
        main_logger.critical(f"CRITICAL Scribe Configuration Error: {e}. This often indicates a malformed "
                           f"'.scribe.toml' or invalid essential settings.", exc_info=True)
        # Try to print a minimal JSON error to stdout, as per Scribe's output contract.
        print(json.dumps({"overall_status": STATUS_FAILURE, "error_message": f"Critical Scribe Configuration Error: {e}"}, indent=2))
        final_exit_code = 3 # Specific exit code for critical configuration errors
    except ScribeInputError as e:
        # Errors related to invalid inputs (e.g., --target-dir not found, --code-file inaccessible).
        # ScribeAgent init or early steps in `run()` might raise this.
        main_logger.error(f"Scribe Input Error: {e}", exc_info=False) # Usually direct, detailed traceback less needed in main log for this
        main_logger.debug("Traceback for ScribeInputError:", exc_info=True)
        print(json.dumps({"overall_status": STATUS_FAILURE, "error_message": f"Scribe Input Error: {e}"}, indent=2))
        final_exit_code = 4 # Specific exit code for input validation errors
    except Exception as e: # Catch-all for any other unhandled exceptions from ScribeAgent init or run
        main_logger.critical(f"CRITICAL Unhandled Exception at main execution level: {type(e).__name__} - {e}", exc_info=True)
        # Provide a minimal JSON error output if Scribe crashed before producing its own report.
        print(json.dumps({"overall_status": STATUS_FAILURE, "error_message": f"Critical Unhandled Exception: {type(e).__name__} - {e}"}, indent=2))
        final_exit_code = 1 # General critical failure code
    finally:
        main_logger.info(f"--- {APP_NAME} v{APP_VERSION} Execution Ended (Final Exit Code: {final_exit_code}) ---")
        logging.shutdown() # Cleanly close all logging handlers (e.g., flush file buffers)

    return final_exit_code

# --- Script Entry Point (`if __name__ == "__main__":`) ---
if __name__ == "__main__":
    # This block ensures that main() is called only when the script is executed directly
    # (not when imported as a module). The exit code from main() is passed to sys.exit(),
    # which makes it available to the calling shell or process.
    sys.exit(main())        logging.shutdown() # Cleanly close all logging handlers (e.g., flush file buffers)

    return final_exit_code

# --- Script Entry Point (`if __name__ == "__main__":`) ---
if __name__ == "__main__":
    # This block ensures that main() is called only when the script is executed directly
    # (not when imported as a module). The exit code from main() is passed to sys.exit(),
    # which makes it available to the calling shell or process.
    sys.exit(main())
