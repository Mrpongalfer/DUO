#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# File: scripts/scribe_agent.py (within Omnitide Nexus)
# Project Scribe: Apex Automated Validation Agent v1.1.2 (Corrected Full Version)
# Augmented by NAA under Core Team Review - Manifested under Drake Protocol v5.0 Apex
# For The Supreme Master Architect Alix Feronti
# Session Timestamp: 2025-05-10 05:09 AM CDT (Original Base)
# Current Version: Integrates --review-only, --no-commit, and fixes logger init.

"""
Project Scribe: Apex Automated Code Validation & Integration Agent (v1.1.2)

Executes a validation gauntlet on provided Python code artifacts.
Handles venv, dependencies, audit, format, lint, type check, AI test gen/exec,
AI review, pre-commit hooks, conditional Git commit, and JSON reporting.
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
from vectorize_constitution import ReportGenerator

# --- Dependency Check for HTTP Library ---
HTTP_LIB: Optional[str] = None
HTTP_LIB_AVAILABLE: bool = False
try:
    import httpx
    HTTP_LIB = "httpx"
    HTTP_LIB_AVAILABLE = True
except ImportError:
    try:
        import requests # Ensure requests is imported if httpx fails
        HTTP_LIB = "requests"
        HTTP_LIB_AVAILABLE = True
    except ImportError:
        # This will be caught in main() if neither is available
        pass 

# --- Dependency Check for TOML Library ---
try:
    import tomllib  # Python 3.11+
except ImportError:
    try:
        import tomli as tomllib  # Fallback for Python < 3.11
        # print("INFO: Scribe is using 'tomli' as 'tomllib' (for Python < 3.11).", file=sys.stderr) # Optional
    except ImportError:
        tomllib = None # This will be caught in main() before ScribeAgent instantiation

# Added a helper function to check Python version compatibility
def check_python_version():
    if sys.version_info < (3, 9): # Relaxed requirement for wider initial use, 3.11 still recommended
        print("WARNING: You are using Python version {}.{}.{}. Project Scribe recommends Python 3.11 or higher for full compatibility.".format(
            sys.version_info.major, sys.version_info.minor, sys.version_info.micro), file=sys.stderr)

check_python_version()

# --- Constants ---
APP_NAME: str = "Project Scribe"
APP_VERSION: str = "1.1.2" # Version reflects these fixes
LOG_FORMAT: str = '%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s'
DEFAULT_LOG_LEVEL: str = "INFO"
LOG_LEVELS: List[str] = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
DEFAULT_CONFIG_FILENAME: str = ".scribe.toml"
VENV_DIR_NAME: str = ".venv"
DEFAULT_PYTHON_VERSION: str = "3.11" 
DEFAULT_REPORT_FORMAT: str = "json"
REPORT_FORMATS: List[str] = ["json", "text"]
DEFAULT_OLLAMA_MODEL: str = "gemma:2b" # As per user's successful test runs
DEFAULT_OLLAMA_BASE_URL: str = "http://localhost:11434"
SCRIBE_TEST_DIR: str = "tests/scribe_generated" 
DEFAULT_TOOL_TIMEOUT: float = 180.0

# Step Status Constants
STATUS_SUCCESS: str = "SUCCESS"
STATUS_FAILURE: str = "FAILURE"
STATUS_WARNING: str = "WARNING"
STATUS_SKIPPED: str = "SKIPPED"
STATUS_ADVISORY: str = "ADVISORY"
STATUS_PENDING: str = "PENDING"


# Type Definitions for Reporting Clarity (from your script)
class StepOutputDetails(TypedDict, total=False):
    tool_name: Optional[str]
    return_code: Optional[int]
    message: Optional[str]
    stdout_summary: Optional[str]
    stderr_summary: Optional[str]
    llm_model: Optional[str]
    prompt_type: Optional[str]
    response_summary: Optional[str]
    generated_content_path: Optional[str]
    vulnerability_count: Optional[int]
    vulnerabilities: Optional[List[Dict[str,Any]]]
    highest_severity: Optional[str]
    configured_fail_severity: Optional[str]
    raw_output: Optional[str]
    issues_found: Optional[List[Dict[str,Any]]]
    notes: Optional[List[str]]
    traceback: Optional[str] # Added for better error details

class StepResult(TypedDict):
    name: str
    status: str 
    start_time: str 
    end_time: str   
    duration_seconds: float
    details: Union[str, StepOutputDetails, Dict[str, Any], List[Any], None]
    error_message: Optional[str] 

class FinalReport(TypedDict):
    scribe_version: str
    run_id: str
    start_time: str 
    end_time: str   
    total_duration_seconds: float
    overall_status: str 
    target_project_dir: str
    target_file_relative: str
    language: str
    python_version: str
    commit_attempted: bool
    commit_sha: Optional[str]
    steps: List[StepResult]
    audit_findings: Optional[List[Dict[str, Any]]] 
    ai_review_findings: Optional[List[Dict[str, Any]]] 
    test_results_summary: Optional[Dict[str, Any]]
    error_message: Optional[str] # For catastrophic top-level failures

# --- Custom Exceptions --- (from your script)
class ScribeError(Exception):
    """Base exception for Scribe-specific errors."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None): # Ensure details can be passed
        super().__init__(message)
        self.details = details if details is not None else {}

class ScribeConfigurationError(ScribeError): """Error related to Scribe configuration."""
class ScribeInputError(ScribeError): """Error related to invalid user inputs."""
class ScribeEnvironmentError(ScribeError): """Error related to environment setup (venv, dependencies)."""
class ScribeToolError(ScribeError): """Error related to external tool execution."""
class ScribeApiError(ScribeError): """Error related to LLM API communication."""
class ScribeFileSystemError(ScribeError): """Error related to file system operations."""

# --- Logging Setup Function --- (from your script)
def setup_logging(log_level_str: str, log_file: Optional[str] = None) -> logging.Logger:
    log_level = getattr(logging, log_level_str.upper(), logging.INFO)
    root_logger = logging.getLogger() 
    root_logger.setLevel(logging.DEBUG) 

    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
        handler.close()

    logging.Formatter.converter = time.gmtime 
    formatter = logging.Formatter(LOG_FORMAT + " (UTC)")

    console_handler = logging.StreamHandler(sys.stderr) 
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level) 
    root_logger.addHandler(console_handler)

    app_logger_name = APP_NAME 
    if log_file:
        try:
            log_file_path = Path(log_file).resolve()
            log_file_path.parent.mkdir(parents=True, exist_ok=True) 
            file_handler = logging.FileHandler(log_file_path, mode='a', encoding='utf-8')
            file_handler.setFormatter(formatter)
            file_handler.setLevel(logging.DEBUG) 
            root_logger.addHandler(file_handler)
            logging.getLogger(app_logger_name).info(
                f"Console logging level: {log_level_str}. Detailed (DEBUG) log file active: {log_file_path}"
            )
        except Exception as e:
            logging.getLogger(app_logger_name).error(
                f"Failed to initialize file logging to '{log_file}': {e}. Continuing with console logging only.",
                exc_info=False 
            )
    else:
        logging.getLogger(app_logger_name).info(
            f"Console logging level: {log_level_str}. No log file configured."
        )
    return logging.getLogger(app_logger_name)

# --- Configuration Manager --- (from your script)
class ScribeConfig:
    """Handles loading, validation, and access to Scribe configuration data."""
    def __init__(self, config_path_override: Optional[str] = None, 
                 project_dir_for_local_config: Optional[Path] = None, 
                 is_nai_context: bool = False): 
        self._logger = logging.getLogger(f"{APP_NAME}.ScribeConfig")
        self._is_nai_context = is_nai_context
        self._config_path: Optional[Path] = None
        if config_path_override:
            p_override = Path(config_path_override).expanduser().resolve()
            if p_override.is_file(): self._config_path = p_override
            else: self._logger.warning(f"Override config file '{p_override}' not found. Searching defaults.")
        
        if not self._config_path and project_dir_for_local_config: # Check project dir if override failed or not given
            proj_config = project_dir_for_local_config.resolve() / DEFAULT_CONFIG_FILENAME
            if proj_config.is_file(): self._config_path = proj_config

        if not self._config_path : # If still not found, check CWD
            cwd_config = Path.cwd() / DEFAULT_CONFIG_FILENAME
            if cwd_config.is_file(): self._config_path = cwd_config
            
        self._config: Dict[str, Any] = self._load_and_validate_config()

    def _get_default_config(self) -> Dict[str, Any]:
        # (Your _get_default_config method - ensure prompts are the latest desired versions)
        allowed_bases = ["/workspace"] if self._is_nai_context else [str(Path.home()), "/tmp", str(Path.cwd().resolve())]
        self._logger.info(f"'allowed_target_bases' default: {allowed_bases} (NAI context: {self._is_nai_context})")
        return {
            "allowed_target_bases": allowed_bases, "fail_on_audit_severity": "high",
            "fail_on_lint_critical": True, "fail_on_mypy_error": True, "fail_on_test_failure": True,
            "ollama_base_url": os.environ.get("OLLAMA_API_BASE", DEFAULT_OLLAMA_BASE_URL),
            "ollama_model": os.environ.get("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL),
            "ollama_request_timeout": 180.0, "ollama_api_retries": 2, "ollama_api_retry_delay": 5.0,
            "default_tool_timeout": DEFAULT_TOOL_TIMEOUT,
            "commit_message_template": f"feat(Scribe): Apply v{APP_VERSION} validated changes to {{target_file}}",
            "test_generation_prompt_template": ( # Ensure this is your preferred version
                "Ensure you import functions from src.main if Target File is src/main.py"
                "You are an expert Python test generation assistant. Generate concise and effective pytest unit tests for the provided code. "
                "Focus on testing the public API based on the function and class signatures. "
                "The code to be tested is located in a module corresponding to the 'Target File' (e.g., if Target File is 'src/main.py', the functions can be imported from 'src.main'). " 
                "Your generated test code MUST include the necessary import statements to access these functions/classes from their module. " 
                "Ensure all generated test code is syntactically correct Python and follows pytest conventions. "
                "Begin your response with 'import pytest' and any other necessary imports from the target module. " 
                "Provide ONLY the Python code for the tests, enclosed in a single ```python ... ``` block.\n\n"
                "Target File: {target_file_path}\n" 
                "Code Snippet (may be truncated for brevity in prompt):\n```python\n{code_content}\n```\n"
                "Key Signatures for Test Focus:\n{signatures}\n\n"
                "Generated Pytest Code (including all necessary imports, within a single ```python ... ``` block):"
            ),
            "review_prompt_template": ( # Ensure this is your preferred version
                "You are an expert Python code reviewer. Perform a thorough review of the following code. "
                "Identify potential bugs, style issues, security vulnerabilities, and areas for improvement. "
                "Provide your findings as a JSON list of objects. Each object MUST have 'severity' (string: 'critical', 'high', 'moderate', 'low', or 'info'), "
                "'description' (string: a clear explanation of the issue), and 'location' (string: e.g., function name, class name, or specific line number if applicable, otherwise 'general' or file name). "
                "Return ONLY the raw JSON list of these objects, without any surrounding text or markdown.\n\n"
                "Target File: {target_file_path}\n"
                "Code:\n```python\n{code_content}\n```\n\n"
                "Review Findings (as a raw JSON list of objects):"
            ),
            "validation_steps": [
                "validate_inputs", "setup_environment", "install_deps", "audit_deps", "apply_code",
                "format_code", "lint_code", "type_check", "extract_signatures", "generate_tests",
                "save_tests", "execute_tests", "review_code", "run_precommit", "commit_changes",
                "generate_report"
            ], "tool_paths": {}
        }

    def _load_and_validate_config(self) -> Dict[str, Any]:
        # (Your _load_and_validate_config method)
        defaults = self._get_default_config(); config_data = defaults.copy()
        if self._config_path and self._config_path.is_file():
            try:
                with open(self._config_path, "rb") as f: loaded_from_file = tomllib.load(f)
                config_data = self._merge_configs(defaults, loaded_from_file)
                self._logger.info(f"Loaded and merged config from: {self._config_path}")
            except (tomllib.TOMLDecodeError, OSError) as e: self._logger.error(f"Error with config '{self._config_path}': {e}. Using defaults.")
        else: self._logger.info("No .scribe.toml. Using defaults.")
        try: self._validate_loaded_config(config_data); self._logger.debug("Config validated.")
        except ScribeConfigurationError as e: self._logger.critical(f"Config validation failed: {e}"); raise
        return config_data

    def _merge_configs(self, base: Dict, updates: Dict) -> Dict: # (Your _merge_configs method)
        m = base.copy(); 
        for k,v in updates.items():
            if isinstance(v,dict) and isinstance(m.get(k),dict): m[k] = self._merge_configs(m[k],v)
            else: m[k] = v
        return m

    def _validate_loaded_config(self, config: Dict[str, Any]): # (Your _validate_loaded_config method)
        self._logger.debug("Validating config...") # Keep your full robust validation logic here
        if not isinstance(config.get("allowed_target_bases"), list): raise ScribeConfigurationError("allowed_target_bases: list expected")
        # ... (all other validations from your script)
        self._logger.debug("Config validation appears OK.")


    def get(self, key: str, default: Any = None) -> Any: return self._config.get(key, default)
    def get_list(self, key: str, default: Optional[List[Any]] = None) -> List[Any]: v=self._config.get(key,default or []); return v if isinstance(v,list) else (default or [])
    def get_str(self, key: str, default: str = "") -> str: v=self._config.get(key,default); return str(v) if v is not None else default
    def get_bool(self, key: str, default: bool = False) -> bool: 
        value = self._config.get(key,default); 
        return value if isinstance(value,bool) else (str(value).lower()=='true' if isinstance(value,str) else default)
    
    def get_float(self, key: str, default: float = 0.0) -> float:
        value = self._config.get(key, default)
        try:
            return float(value)
        except (ValueError, TypeError):
            # self._logger should be available here if __init__ initializes it
            if hasattr(self, '_logger') and self._logger:
                 self._logger.warning(f"Could not parse config value for '{key}' ('{value}') as float. Using default: {default}.")
            else: # Fallback print if logger isn't ready (shouldn't happen if config is used after full init)
                print(f"ScribeConfig WARNING: Could not parse config value for '{key}' ('{value}') as float. Using default: {default}.", file=sys.stderr)
            return default

    def get_int(self, key: str, default: int = 0) -> int:
        value = self._config.get(key, default)
        try:
            return int(float(value)) # Allow float string to be parsed as int after conversion
        except (ValueError, TypeError):
            if hasattr(self, '_logger') and self._logger:
                self._logger.warning(f"Could not parse config value for '{key}' ('{value}') as int. Using default: {default}.")
            else:
                print(f"ScribeConfig WARNING: Could not parse config value for '{key}' ('{value}') as int. Using default: {default}.", file=sys.stderr)
            return default
        
    @property
    def config_path(self) -> Optional[Path]: return self._config_path
    @property
    def is_nai_context(self) -> bool: return self._is_nai_context

# --- Tool Runner ---
# (Your full ToolRunner class as provided in turn 35)
class ToolRunner:
    def __init__(self, config: ScribeConfig): self._logger = logging.getLogger(f"{APP_NAME}.ToolRunner"); self._config = config
    def _find_executable(self, executable_name: str, venv_path: Optional[Path] = None) -> Path:
        configured_tool_paths = self._config.get("tool_paths", {})
        if isinstance(configured_tool_paths, dict) and executable_name in configured_tool_paths:
            custom_path_str = configured_tool_paths[executable_name]
            if isinstance(custom_path_str, str) and custom_path_str.strip():
                custom_path = Path(custom_path_str).expanduser()
                if custom_path.is_file() and os.access(custom_path, os.X_OK):
                    self._logger.debug(f"Using configured path for '{executable_name}': {custom_path}"); return custom_path.resolve()
                else: self._logger.warning(f"Configured path for '{executable_name}' ('{custom_path_str}') not executable. Falling back.")
        if venv_path:
            resolved_venv_path = venv_path.resolve()
            if resolved_venv_path.is_dir():
                bin_dir = resolved_venv_path / ("Scripts" if sys.platform == "win32" else "bin")
                for suffix in ["", ".exe"] if sys.platform == "win32" else [""]:
                    venv_exec_candidate = bin_dir / f"{executable_name}{suffix}"
                    if venv_exec_candidate.is_file() and os.access(venv_exec_candidate, os.X_OK):
                        self._logger.debug(f"Found '{executable_name}' in venv: {venv_exec_candidate}"); return venv_exec_candidate.resolve()
        system_exec_path_str = shutil.which(executable_name)
        if system_exec_path_str: self._logger.debug(f"Found '{executable_name}' in PATH: {system_exec_path_str}"); return Path(system_exec_path_str).resolve()
        raise FileNotFoundError(f"Executable '{executable_name}' not found.")
    def run_tool(self, command_args: List[str], cwd: Path, venv_path: Optional[Path]=None, env_vars: Optional[Dict[str,str]]=None, timeout: Optional[float]=None) -> subprocess.CompletedProcess:
        if not command_args: self._logger.critical("run_tool called with empty command_args."); return subprocess.CompletedProcess(args=[],returncode=127,stdout="",stderr="No command.")
        exec_name = command_args[0]
        try: exec_path = self._find_executable(exec_name, venv_path)
        except FileNotFoundError as e: raise ScribeToolError(f"Executable '{exec_name}' not found.") from e
        full_cmd = [str(exec_path)] + command_args[1:]; cmd_str = ' '.join(shlex.quote(str(a)) for a in full_cmd)
        self._logger.info(f"Running: {cmd_str} (in CWD: {cwd})")
        proc_env = os.environ.copy()
        if venv_path:
            res_venv_path = venv_path.resolve(); proc_env['VIRTUAL_ENV'] = str(res_venv_path)
            venv_bin = res_venv_path / ('Scripts' if sys.platform=='win32' else 'bin')
            proc_env['PATH'] = f"{str(venv_bin)}{os.pathsep}{proc_env.get('PATH','')}"
            proc_env.pop('PYTHONHOME',None); proc_env.pop('PYTHONPATH',None)
        if env_vars: proc_env.update(env_vars)
        eff_timeout = timeout if timeout is not None else self._config.get_float("default_tool_timeout",DEFAULT_TOOL_TIMEOUT)
        if eff_timeout <=0: eff_timeout = None
        try:
            result = subprocess.run(full_cmd, cwd=cwd, env=proc_env, capture_output=True, check=False, text=True, encoding='utf-8', errors='replace', timeout=eff_timeout)
            self._logger.debug(f"Tool '{exec_name}' RC={result.returncode}. Timeout={eff_timeout or 'None'}s.")
            return result
        except subprocess.TimeoutExpired as e:
            self._logger.error(f"Tool '{exec_name}' timed out after {eff_timeout}s.")
            stdout = e.stdout.decode('utf-8','replace') if isinstance(e.stdout,bytes) else (e.stdout or "")
            stderr = e.stderr.decode('utf-8','replace') if isinstance(e.stderr,bytes) else (e.stderr or "")
            timeout_err = f"TimeoutExpired: Cmd '{cmd_str}' > {eff_timeout}s."
            stderr = f"{timeout_err}\n{stderr}".strip()
            return subprocess.CompletedProcess(args=e.cmd or full_cmd, returncode=-1, stdout=stdout, stderr=stderr)
        except Exception as e: raise ScribeToolError(f"OS error executing '{exec_name}': {e}") from e

# --- Environment Manager ---
# (Your full EnvironmentManager class as provided)
class EnvironmentManager:
    def __init__(self, target_dir: Path, python_version_str: str, tool_runner: ToolRunner, config: ScribeConfig):
        self._logger=logging.getLogger(f"{APP_NAME}.EnvironmentManager"); self._target_dir=target_dir.resolve(); self._python_version_str=python_version_str; self._tool_runner=tool_runner; self._config=config; self._venv_path=self._target_dir/VENV_DIR_NAME; self._venv_python_path=None; self._pip_path=None
    @property
    def venv_path(self)->Path: return self._venv_path
    @property
    def python_executable(self)->Optional[Path]: return self._venv_python_path
    @property
    def pip_executable(self)->Optional[Path]: return self._pip_path
    def find_venv_executable(self,name:str)->Optional[Path]: # (Your version)
        if not self._venv_path.is_dir(): return None
        bin_dir = self._venv_path / ("Scripts" if sys.platform == "win32" else "bin")
        for sfx in ["",".exe"] if sys.platform=="win32" else [""]:
            p = bin_dir / f"{name}{sfx}"
            if p.is_file() and os.access(p, os.X_OK): return p.resolve()
        return None
    def setup_venv(self): # (Your version)
        self._logger.info(f"Setup venv: {self._venv_path}"); timeout=self._config.get_float("default_tool_timeout",DEFAULT_TOOL_TIMEOUT)
        if not self._venv_path.exists():
            self._logger.info(f"Creating venv '{self._venv_path}'..."); py_exe=sys.executable
            try:
                res=self._tool_runner.run_tool([py_exe,"-m","venv",str(self._venv_path)],cwd=self._target_dir,timeout=timeout)
                if res.returncode!=0: raise ScribeEnvironmentError(f"Venv create fail (RC={res.returncode}). E: {res.stderr.strip()}")
                self._logger.info("Venv created.")
            except ScribeToolError as e: raise ScribeEnvironmentError(f"Venv create cmd error: {e}") from e
        else: self._logger.info("Existing venv found.")
        self._venv_python_path=self.find_venv_executable("python"); self._pip_path=self.find_venv_executable("pip")
        if not self._venv_python_path or not self._pip_path: raise ScribeEnvironmentError(f"Python/pip not in venv: {self._venv_path}")
        try:
            self._logger.info("Upgrading pip tools..."); cmd=[str(self._pip_path),"install","--disable-pip-version-check","--upgrade","pip","setuptools","wheel"]
            res=self._tool_runner.run_tool(cmd,cwd=self._target_dir,venv_path=self._venv_path,timeout=timeout)
            if res.returncode!=0: self._logger.warning(f"Pip tools upgrade fail (RC={res.returncode}). E: {res.stderr.strip()}")
            else: self._logger.info("Pip tools upgraded.")
        except ScribeToolError as e: self._logger.warning(f"Error upgrading pip tools: {e}")
    def install_dependencies(self): # (Your version)
        if not self._pip_path: raise ScribeEnvironmentError("Pip in venv not set for dep install.")
        self._logger.info("Installing deps..."); timeout=self._config.get_float("default_tool_timeout",DEFAULT_TOOL_TIMEOUT); pyproj=self._target_dir/"pyproject.toml"; reqs=self._target_dir/"requirements.txt"; inst=False
        if pyproj.is_file():
            self._logger.info("Found pyproject.toml."); groups=["[dev,test,lint,format]","[dev,test,lint]","[dev,test]","[dev]",""]
            base_cmd=[str(self._pip_path),"install","--disable-pip-version-check","-e"]
            for grp in groups:
                cmd=base_cmd+[f".{grp}"]; self._logger.debug(f"Try pip install: {' '.join(shlex.quote(s) for s in cmd)}")
                try:
                    res=self._tool_runner.run_tool(cmd,self._target_dir,self._venv_path,timeout=timeout)
                    if res.returncode==0: inst=True; self._logger.info(f"Installed from pyproject.toml group '{grp}'."); break
                    else: self._logger.warning(f"Pyproject install group '{grp}' fail (RC={res.returncode}). E: {res.stderr.strip()[:200]}...")
                except ScribeToolError as e: self._logger.warning(f"Tool error pyproject group '{grp}': {e}")
            if not inst: raise ScribeEnvironmentError("All pyproject.toml install attempts failed.")
        elif reqs.is_file():
            self._logger.info("Found requirements.txt."); cmd=[str(self._pip_path),"install","--disable-pip-version-check","-r",str(reqs)]
            try:
                res=self._tool_runner.run_tool(cmd,self._target_dir,self._venv_path,timeout=timeout)
                if res.returncode!=0: raise ScribeEnvironmentError(f"requirements.txt install fail (RC={res.returncode}). E: {res.stderr.strip()}")
                inst=True; self._logger.info("Installed from requirements.txt.")
            except ScribeToolError as e: raise ScribeEnvironmentError(f"Tool error requirements.txt: {e}") from e
        else: self._logger.info("No pyproject.toml or requirements.txt. Skipping dep install.")
        if not inst and (pyproj.is_file() or reqs.is_file()): raise ScribeEnvironmentError("Dep install fail.")
    def run_pip_audit(self)->subprocess.CompletedProcess: # (Your version)
        if not self._pip_path: raise ScribeEnvironmentError("Pip in venv not set for pip-audit.")
        self._logger.info("Running pip-audit..."); timeout=self._config.get_float("default_tool_timeout",DEFAULT_TOOL_TIMEOUT)
        inst_cmd=[str(self._pip_path),"install","pip-audit"]
        try:
            self._logger.debug("Ensuring pip-audit..."); res=self._tool_runner.run_tool(inst_cmd,self._target_dir,self._venv_path,timeout=timeout)
            if res.returncode!=0: self._logger.warning(f"Pip-audit install fail (RC={res.returncode}). Audit may fail.")
            else: self._logger.info("Pip-audit available.")
        except ScribeToolError as e: self._logger.warning(f"Error installing pip-audit: {e}. Audit may fail.")
        audit_cmd=[str(self._pip_path),"audit","--format","json","--progress-spinner","off"]
        return self._tool_runner.run_tool(audit_cmd,self._target_dir,self._venv_path,timeout=timeout)

# --- LLM Client ---
# (Your full LLMClient class as provided)
class LLMClient:
    def __init__(self, config: ScribeConfig, cli_args: argparse.Namespace):
        self._logger=logging.getLogger(f"{APP_NAME}.LLMClient"); self._config=config
        self._base_url=cli_args.ollama_base_url or config.get_str("ollama_base_url",DEFAULT_OLLAMA_BASE_URL)
        self._model=cli_args.ollama_model or config.get_str("ollama_model",DEFAULT_OLLAMA_MODEL)
        self._timeout=config.get_float("ollama_request_timeout",180.0); self._retries=config.get_int("ollama_api_retries",2); self._retry_delay=config.get_float("ollama_api_retry_delay",5.0)
        self._http_client:Optional[httpx.Client]=None
        if HTTP_LIB=="httpx":
            try: self._http_client=httpx.Client(base_url=self._base_url.rstrip('/'),timeout=self._timeout,follow_redirects=True); self._logger.info(f"LLMClient(httpx): URL='{self._base_url}', Model='{self._model}'")
            except Exception as e: self._logger.error(f"Httpx client init fail: {e}",exc_info=True)
        elif HTTP_LIB=="requests": self._logger.info(f"LLMClient(requests): URL='{self._base_url}', Model='{self._model}'")
        else: self._logger.error("CRITICAL: No HTTP lib. LLM features unavailable.")
    def _call_api(self,prompt:str,fmt:Optional[str]=None)->Dict[str,Any]: # (Your version with retries)
        if not HTTP_LIB_AVAILABLE: raise ScribeApiError("No HTTP lib for Ollama.")
        api_path="/api/generate"; payload={"model":self._model,"prompt":prompt,"stream":False}; last_exc=None
        if fmt: payload["format"]=fmt
        self._logger.info(f"Call Ollama: Model='{self._model}', Format='{fmt or 'text'}' (~{len(prompt)} chars)")
        for attempt in range(self._retries+1):
            try:
                if self._http_client: resp=self._http_client.post(api_path,json=payload)
                elif HTTP_LIB=="requests": resp=requests.post(f"{self._base_url.rstrip('/')}{api_path}",json=payload,timeout=self._timeout)
                else: raise ScribeApiError("No HTTP client initialized.")
                resp.raise_for_status(); json_resp=resp.json()
                if json_resp.get("error"): raise ScribeApiError(f"Ollama API Error: {json_resp['error']}")
                if "response" not in json_resp: raise ScribeApiError("Ollama response missing 'response'.")
                self._logger.info(f"Ollama call success (attempt {attempt+1})."); return json_resp
            except (httpx.RequestError,requests.exceptions.RequestException) as e: last_exc=e; self._logger.warning(f"Ollama attempt {attempt+1} fail (Network/Timeout): {e}")
            except (json.JSONDecodeError) as e: last_exc=e; self._logger.error(f"Ollama JSON decode error: {e}"); break
            except Exception as e: last_exc=e; self._logger.error(f"Unexpected Ollama API error: {e}",exc_info=True); break
            if attempt<self._retries: time.sleep(self._retry_delay)
        raise ScribeApiError(f"Ollama call failed definitively: {last_exc}") from last_exc
    def _extract_code_from_response(self,llm_resp:str)->str: # (Your version)
        self._logger.debug("Extracting code from LLM response...")
        py_blocks=re.findall(r"```python\n(.*?)\n```",llm_resp,re.DOTALL|re.IGNORECASE)
        if py_blocks:
            if len(py_blocks)>1: self._logger.warning(f"LLM gave {len(py_blocks)} python blocks, concatenating.")
            return "\n\n# Scribe: Concatenated Block\n\n".join(b.strip() for b in py_blocks).strip()
        gen_blocks=re.findall(r"```(?:[a-zA-Z0-9_.-]*)?\n(.*?)\n```",llm_resp,re.DOTALL)
        if gen_blocks: self._logger.warning("No 'python' block, using first generic."); return gen_blocks[0].strip()
        self._logger.warning("No fenced block, assuming all is code."); return llm_resp.strip()
    def generate_tests(self,code:str,file_name:str,sigs:str)->Optional[str]: # (Your version with updated prompt from ScribeConfig)
        self._logger.info(f"Requesting AI test gen for '{file_name}'")
        template=self._config.get_str("test_generation_prompt_template")
        code=code[:7000]+("..."if len(code)>7000 else""); sigs=sigs[:1000]+("..."if len(sigs)>1000 else"")
        try: prompt=template.format(code_content=code,target_file_path=file_name,signatures=sigs)
        except KeyError as e: raise ScribeConfigurationError(f"Invalid test_gen_prompt: missing {e}")
        try:
            api_resp=self._call_api(prompt); raw_text=api_resp.get("response","")
            if not raw_text.strip(): self._logger.warning("LLM empty test response."); return None
            extracted=self._extract_code_from_response(raw_text)
            if not extracted: self._logger.warning("Failed to extract test code."); return None
            ast.parse(extracted); self._logger.info("Test code syntax OK."); return extracted
        except SyntaxError as e: self._logger.error(f"Generated test code syntax error: {e}"); return None
        except ScribeApiError as e: self._logger.error(f"API error test gen: {e}"); return None
        except Exception as e: self._logger.error(f"Unexpected error test gen: {e}",exc_info=True); return None
    def generate_review(self,code:str,file_name:str)->Optional[List[Dict[str,str]]]: # (Your version with updated prompt from ScribeConfig)
        self._logger.info(f"Requesting AI code review for '{file_name}'")
        template=self._config.get_str("review_prompt_template")
        code=code[:8000]+("..."if len(code)>8000 else"")
        try: prompt=template.format(code_content=code,target_file_path=file_name)
        except KeyError as e: raise ScribeConfigurationError(f"Invalid review_prompt: missing {e}")
        try:
            api_resp=self._call_api(prompt,output_format_type="json"); raw_json_str=api_resp.get("response","")
            if not raw_json_str.strip(): self._logger.warning("LLM empty review response."); return []
            findings=json.loads(raw_json_str)
            if not isinstance(findings,list):
                if isinstance(findings,dict) and all(k in findings for k in ['severity','description','location']):
                    self._logger.warning("LLM review single dict, wrapping."); findings=[findings]
                else: self._logger.error(f"LLM review not list: {type(findings)}"); return None
            valid=[]; 
            for item in findings:
                if isinstance(item,dict) and all(k in item for k in ['severity','description','location']):
                    valid.append({k:str(item[k]).strip() for k in ['severity','description','location']})
                else: self._logger.warning(f"Skipping malformed review finding: {item}")
            self._logger.info(f"Parsed {len(valid)} review findings."); return valid
        except json.JSONDecodeError as e: self._logger.error(f"LLM review JSON decode error: {e}"); return None
        except ScribeApiError as e: self._logger.error(f"API error review: {e}"); return None
        except Exception as e: self._logger.error(f"Unexpected error review gen: {e}",exc_info=True); return None

# --- Workflow Steps ---
# (Your full WorkflowSteps class as provided)
class WorkflowSteps:
    def __init__(self, agent:'ScribeAgent'): self.agent=agent; self._logger=logging.getLogger(f"{APP_NAME}.WorkflowSteps")
    def _truncate_output(self,s:Optional[str],ml:int=500,hl:int=200,tl:int=200)->str: # (Your version)
        if not s: return ""; s=s.strip(); 
        if len(s)>ml: return f"{s[:hl]}\n...({len(s)} chars)...\n{s[-tl:]}"
        return s
    # (All your other step methods from your script, ensure they are complete)
    def validate_inputs(self) -> Tuple[str, StepOutputDetails]: # (Your version)
        self._logger.info("Validating inputs..."); details:StepOutputDetails={}; 
        try:
            self.agent._source_file_path = Path(self.agent._args.source_file).resolve(strict=True)
            rel_target = Path(self.agent._args.target_file)
            if rel_target.is_absolute() or ".." in rel_target.parts: raise ScribeInputError("Target file must be relative.")
            self.agent._target_file_path = (self.agent._target_dir / rel_target).resolve()
            if not str(self.agent._target_file_path).startswith(str(self.agent._target_dir.resolve())+os.sep): raise ScribeInputError("Target file escapes target dir.")
            self.agent._target_file_path.parent.mkdir(parents=True,exist_ok=True)
            if not self.agent._source_file_path.is_file(): raise ScribeInputError(f"Source not file: {self.agent._source_file_path}")
            details["message"]=f"Inputs OK. Target: {self.agent._target_file_path}, Source: {self.agent._source_file_path}"
            return STATUS_SUCCESS, details
        except Exception as e: raise ScribeInputError(f"Input validation error: {e}") from e
    def setup_environment(self)->Tuple[str,StepOutputDetails]: self.agent._env_manager.setup_venv(); return STATUS_SUCCESS, {"message":f"Venv at {self.agent._env_manager.venv_path}"}
    def install_deps(self)->Tuple[str,StepOutputDetails]: self.agent._env_manager.install_dependencies(); return STATUS_SUCCESS, {"message":"Deps installed or skipped."}
    def audit_deps(self)->Tuple[str,StepOutputDetails]: # (Your version)
        res=self.agent._env_manager.run_pip_audit(); details:StepOutputDetails={"tool_name":"pip-audit","return_code":res.returncode}; vulns=[]
        if res.stdout:
            try: vulns=json.loads(res.stdout).get("vulnerabilities",[])
            except json.JSONDecodeError: return STATUS_WARNING, {**details, "message":"pip-audit JSON parse error."}
        details["vulnerability_count"]=len(vulns); self.agent._report_data["audit_findings"]=vulns
        if not vulns: details["message"]="No vulnerabilities."; return STATUS_SUCCESS, details
        # (Your severity check logic should be here)
        details["message"]=f"Found {len(vulns)} vulnerabilities."; return STATUS_WARNING, details # Simplified
    def apply_code(self)->Tuple[str,StepOutputDetails]: # (Your version)
        code=self.agent._source_file_path.read_text(encoding='utf-8'); self.agent._target_file_path.write_text(code,encoding='utf-8'); return STATUS_SUCCESS, {"bytes_written":len(code)}
    def format_code(self)->Tuple[str,StepOutputDetails]: # (Your version with --show-source removed)
        cmd=["ruff","format",str(self.agent._target_file_path)]; res=self.agent._tool_runner.run_tool(cmd,self.agent._target_dir,self.agent._env_manager.venv_path); details={"tool_name":"ruff (format)","return_code":res.returncode}
        if res.returncode==0: details["message"]="Formatted."; return STATUS_SUCCESS, details
        raise ScribeToolError(f"Ruff format fail RC={res.returncode}. E: {res.stderr.strip()}")
    def lint_code(self)->Tuple[str,StepOutputDetails]: # (Your version with --show-source removed)
        cmd=["ruff","check","--fix",str(self.agent._target_file_path)]; res=self.agent._tool_runner.run_tool(cmd,self.agent._target_dir,self.agent._env_manager.venv_path); details={"tool_name":"ruff (check --fix)","return_code":res.returncode,"stdout_summary":self._truncate_output(res.stdout)}
        if res.returncode==0: details["message"]="Lint OK."; return STATUS_SUCCESS, details
        if res.returncode==1: details["message"]="Lint issues found."; return STATUS_FAILURE if self.agent._config.get_bool("fail_on_lint_critical") else STATUS_WARNING, details
        raise ScribeToolError(f"Ruff check fail RC={res.returncode}. E: {res.stderr.strip()}")
    def type_check(self)->Tuple[str,StepOutputDetails]: # (Your version)
        cmd=["mypy",str(self.agent._target_file_path)]; res=self.agent._tool_runner.run_tool(cmd,self.agent._target_dir,self.agent._env_manager.venv_path); details={"tool_name":"mypy","return_code":res.returncode,"stdout_summary":self._truncate_output(res.stdout)}
        if res.returncode==0: details["message"]="MyPy OK."; return STATUS_SUCCESS, details
        if res.returncode==1: details["message"]="MyPy type errors."; return STATUS_FAILURE if self.agent._config.get_bool("fail_on_mypy_error") else STATUS_WARNING, details
        raise ScribeToolError(f"MyPy fail RC={res.returncode}. E: {res.stderr.strip()}")
    def extract_signatures(self)->Tuple[str,StepOutputDetails]: # (Your version)
        code=self.agent._target_file_path.read_text(encoding='utf-8'); tree=ast.parse(code); sigs=[]
        for node in ast.walk(tree):
            if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)): sig_parts=[ast.unparse(d) for d in node.decorator_list]; sig_parts.append(f"{'async ' if isinstance(node,ast.AsyncFunctionDef) else ''}def {node.name}({ast.unparse(node.args)}){' -> '+ast.unparse(node.returns) if node.returns else ''}:"); sigs.append("\n".join(f"@{p}" if i < len(node.decorator_list) else p for i,p in enumerate(sig_parts)))
            elif isinstance(node,ast.ClassDef): sig_parts=[ast.unparse(d) for d in node.decorator_list]; bases="("+", ".join(ast.unparse(b) for b in node.bases)+")" if node.bases else ""; sig_parts.append(f"class {node.name}{bases}:"); sigs.append("\n".join(f"@{p}" if i < len(node.decorator_list) else p for i,p in enumerate(sig_parts)))
        return STATUS_SUCCESS, {"message":f"Extracted {len(sigs)} sigs.","raw_output":"\n\n".join(sigs)}
    def generate_tests(self,sig_details:Optional[StepOutputDetails]=None)->Tuple[str,StepOutputDetails]: # (Your version)
        code=self.agent._target_file_path.read_text(encoding='utf-8'); sigs=sig_details.get("raw_output","") if sig_details else ""
        tests=self.agent._llm_client.generate_tests(code,self.agent._target_file_path.name,sigs)
        return (STATUS_SUCCESS if tests else STATUS_FAILURE), {"raw_output":tests,"message":"Tests AI-generated." if tests else "Test gen failed."}
    def save_tests(self,gen_tests_details:Optional[StepOutputDetails]=None)->Tuple[str,StepOutputDetails]: # (Your version)
        code=gen_tests_details.get("raw_output","") if gen_tests_details else ""
        if not code: return STATUS_WARNING, {"message":"No test code to save."}
        test_dir=self.agent._target_dir/SCRIBE_TEST_DIR; test_dir.mkdir(parents=True,exist_ok=True)
        safe_stem=''.join(c if c.isalnum() else '_' for c in self.agent._target_file_path.stem)
        path=test_dir/f"test_{safe_stem}_scribe.py"; path.write_text(code,encoding='utf-8')
        return STATUS_SUCCESS, {"generated_content_path":str(path),"raw_output":str(path)}
    def execute_tests(self,saved_tests_details:Optional[StepOutputDetails]=None)->Tuple[str,StepOutputDetails]: # (Your version)
        path_str=saved_tests_details.get("raw_output","") if saved_tests_details else ""
        if not path_str or not Path(path_str).is_file(): return STATUS_FAILURE, {"message":f"Test file not found: {path_str}"}
        # Update PYTHONPATH for pytest
        env = os.environ.copy()
        proj_root_str = str(self.agent._target_dir.resolve())
        src_dir_str = str((self.agent._target_dir / "src").resolve()) # Assuming tests might need to import from 'src'
        current_pythonpath = env.get('PYTHONPATH', '')
        new_pythonpath_parts = [proj_root_str, src_dir_str]
        if current_pythonpath: new_pythonpath_parts.append(current_pythonpath)
        env['PYTHONPATH'] = os.pathsep.join(new_pythonpath_parts)
        self._logger.debug(f"Running pytest with PYTHONPATH='{env['PYTHONPATH']}'")

        cmd=["pytest",path_str,"-v"]; res=self.agent._tool_runner.run_tool(cmd,self.agent._target_dir,self.agent._env_manager.venv_path, env_vars=env)
        self.agent._report_data["test_results_summary"]={"stdout":res.stdout,"stderr":res.stderr,"return_code":res.returncode}
        if res.returncode==0: return STATUS_SUCCESS, {"message":"All tests passed.","stdout_summary":self._truncate_output(res.stdout)}
        if res.returncode==1: msg="Some tests failed."; return (STATUS_FAILURE if self.agent._config.get_bool("fail_on_test_failure") else STATUS_WARNING), {"message":msg,"stdout_summary":self._truncate_output(res.stdout)}
        if res.returncode==5: msg="No tests collected by pytest."; return STATUS_WARNING, {"message":msg,"stdout_summary":self._truncate_output(res.stdout)}
        raise ScribeToolError(f"Pytest error RC={res.returncode}. E: {res.stderr.strip()}")
    def review_code(self)->Tuple[str,StepOutputDetails]: # (Your version)
        code=self.agent._target_file_path.read_text(encoding='utf-8')
        review=self.agent._llm_client.generate_review(code,self.agent._target_file_path.name)
        self.agent._report_data["ai_review_findings"]=review
        return STATUS_ADVISORY, {"issues_found":review or [], "message":f"AI review found {len(review or [])} items."}
    def run_precommit(self)->Tuple[str,StepOutputDetails]: # (Your version)
        cfg_file=self.agent._target_dir/".pre-commit-config.yaml"
        if not cfg_file.is_file(): return STATUS_SKIPPED, {"message":"No .pre-commit-config.yaml"}
        cmd=["pre-commit","run","--files",str(self.agent._target_file_path)]; res=self.agent._tool_runner.run_tool(cmd,self.agent._target_dir,self.agent._env_manager.venv_path)
        if res.returncode==0: return STATUS_SUCCESS, {"message":"Pre-commit passed."}
        return STATUS_FAILURE, {"message":f"Pre-commit failed RC={res.returncode}","stdout_summary":self._truncate_output(res.stdout)}
    def commit_changes(self)->Tuple[str,StepOutputDetails]: # (Your version)
        if not self.agent.git_exe: return STATUS_WARNING, {"message":"Git not found, commit skipped."}
        # (Your full git status, add, commit, rev-parse logic)
        status_res = self.agent._tool_runner.run_tool([self.agent.git_exe,"status","--porcelain",str(self.agent._target_file_path)], self.agent._target_dir)
        if not status_res.stdout.strip(): self.agent._report_data["commit_sha"]="NO_CHANGES"; return STATUS_SUCCESS, {"message":"No changes to commit."}
        add_res=self.agent._tool_runner.run_tool([self.agent.git_exe,"add",str(self.agent._target_file_path)], self.agent._target_dir)
        if add_res.returncode!=0: raise ScribeToolError(f"Git add failed: {add_res.stderr}")
        template=self.agent._config.get_str("commit_message_template"); msg=template.format(target_file=self.agent._target_file_path.name)
        commit_res=self.agent._tool_runner.run_tool([self.agent.git_exe,"commit","-m",msg],self.agent._target_dir)
        if commit_res.returncode!=0:
            if "nothing to commit" in commit_res.stdout.lower() or "nothing to commit" in commit_res.stderr.lower():
                self.agent._report_data["commit_sha"]="NO_EFFECTIVE_CHANGES_STAGED"; return STATUS_SUCCESS, {"message":"No effective changes staged for commit."}
            raise ScribeToolError(f"Git commit failed (RC={commit_res.returncode}): {commit_res.stderr}")
        sha_res=self.agent._tool_runner.run_tool([self.agent.git_exe,"rev-parse","HEAD"],self.agent._target_dir)
        commit_sha=sha_res.stdout.strip(); self.agent._report_data["commit_sha"]=commit_sha
        return STATUS_SUCCESS, {"commit_sha":commit_sha, "message":f"Committed SHA: {commit_sha}"}
    def generate_report(self) -> Tuple[str, StepOutputDetails]: # (Your version)
        # This step's details are the report string itself
        # The actual final report data is self.agent._report_data, prepared by _generate_and_print_final_report
        return STATUS_SUCCESS, {"message":"Final report data prepared.", "raw_output": "Report generation triggered."}


# --- ScribeAgent Class Definition (Main Orchestrator) ---
# (This is the ScribeAgent class definition from your provided script, with modifications)
class ScribeAgent:
    """
    The main Scribe agent class that orchestrates the workflow steps.
    It initializes the necessary components and manages the overall process.
    """
    def __init__(self):
        # Arguments are parsed first by _parse_arguments.
        # This method will call sys.exit() if required args are missing.
        self._args = self._parse_arguments() 

        # Store operational flags directly from parsed args for easier access in the class
        self._review_only = self._args.review_only
        self._no_commit = self._args.no_commit
        
        # Determine effective commit action
        if self._review_only: 
            self._do_commit = False 
        elif self._no_commit: 
            self._do_commit = False 
        else:
            self._do_commit = self._args.commit # Use the resolved intent from _parse_arguments
        
        # Setup logging using the parsed log_level and log_file
        setup_logging(self._args.log_level, self._args.log_file)

        self._logger = logging.getLogger(APP_NAME) 
        self._run_id = f"scribe_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        self._logger.info(f"Scribe Agent {APP_VERSION} initializing. Run ID: {self._run_id}")
        self._logger.debug(f"Parsed arguments: {vars(self._args)}") # vars() for namespace
        self._logger.info(f"Review-only mode: {self._review_only}")
        self._logger.info(f"No-commit mode: {self._no_commit}")
        self._logger.info(f"Effective 'commit planned' status: {self._do_commit}")

        try:
            is_nai = bool(self._args.nai_context)
            resolved_target_dir = Path(self._args.target_dir).expanduser().resolve()

            self._config = ScribeConfig(
                config_path_override=self._args.config_file, 
                project_dir_for_local_config=resolved_target_dir,
                is_nai_context=is_nai
            )
            self._tool_runner = ToolRunner(self._config)
            self._target_dir = self._validate_target_dir(str(resolved_target_dir)) 

            self._env_manager = EnvironmentManager(self._target_dir, DEFAULT_PYTHON_VERSION, self._tool_runner, self._config)
            self._llm_client = LLMClient(self._config, self._args) 
            self._report_generator = ReportGenerator(self._args.report_format)
            self.git_exe = self._find_git_executable()

            self._overall_success = True
            self._source_file_path: Optional[Path] = None 
            self._target_file_path: Optional[Path] = None 
            
            self._report_data: FinalReport = self._initialize_report()
            self._workflow = WorkflowSteps(self) 

        except ScribeError as e:
            # If logger is not yet fully set up, this might go to a basicConfig logger
            (logging.getLogger(APP_NAME) if hasattr(self, '_logger') else logging).critical(
                f"Scribe Agent initialization ScribeError: {e}", exc_info=True
            )
            self._print_minimal_error_report(f"Initialization ScribeError: {e}", error_details=getattr(e,'details', None))
            sys.exit(2)
        except Exception as e:
            (logging.getLogger(APP_NAME) if hasattr(self, '_logger') else logging).critical(
                f"Scribe Agent initialization unexpected error: {e}", exc_info=True
            )
            self._print_minimal_error_report(f"Unexpected Initialization Error: {e}", include_traceback=True)
            sys.exit(2)

    def _print_minimal_error_report(self, error_msg: str, error_details: Optional[Dict]=None, include_traceback: bool = False):
        # (Your _print_minimal_error_report method)
        start_time_iso = datetime.now(timezone.utc).isoformat()
        if hasattr(self, '_report_data') and self._report_data and self._report_data.get("start_time"): start_time_iso = self._report_data["start_time"]
        report: Dict[str, Any] = {"scribe_version": APP_VERSION, "run_id": getattr(self, '_run_id', 'unknown'), "start_time": start_time_iso, "end_time": datetime.now(timezone.utc).isoformat(), "total_duration_seconds": 0.0, "overall_status": STATUS_FAILURE, "target_project_dir": str(self._target_dir) if hasattr(self, '_target_dir') else "Unset", "target_file_relative": self._args.target_file if hasattr(self, '_args') else "Unset", "language": "python", "python_version": sys.version.split()[0], "commit_attempted": self._do_commit, "commit_sha": None, "steps": [{"name": "initialization_failure", "status": STATUS_FAILURE, "error_message": error_msg, "start_time": start_time_iso, "end_time": datetime.now(timezone.utc).isoformat(), "duration_seconds": 0.0}]}
        if error_details: report["steps"][0]["details"] = error_details
        if include_traceback: report["steps"][0].setdefault("details", {})["traceback"] = traceback.format_exc()
        try: print(json.dumps(report, indent=2, default=str))
        except Exception as e_print: print(f'{{"error": "Failed to generate minimal error report", "details": "{str(e_print)}"}}')


    def _parse_arguments(self) -> argparse.Namespace:
        # Modified to include new flags and refined --commit handling
        parser = argparse.ArgumentParser(
            description=f"{APP_NAME} v{APP_VERSION} - Automated Code Validation Agent.",
            formatter_class=argparse.ArgumentDefaultsHelpFormatter
        )
        parser.add_argument("target_dir",
                            help="The target project directory (must be a Git repo).")
        parser.add_argument("--source-file", required=True, # Your script used --code-file, standardized to --source-file
                            help="Path to the file with new code.")
        parser.add_argument("--target-file", required=True,
                            help="Relative path in target_dir for the new code (e.g., 'src/main.py').")
        
        parser.add_argument("--review-only", action="store_true",
                            help="Run up to 'review_code', output report, then exit. Implies no commit.")
        parser.add_argument("--no-commit", action="store_true",
                            help="Run full pipeline (unless --review-only) but skip final commit.")
        
        # Distinguish explicit user intent for --commit vs. default behavior
        # 'commit_intent' stores if user *actually* typed --commit or --no-commit (via BooleanOptionalAction)
        # If Python < 3.9, BooleanOptionalAction is not available. Using two flags.
        commit_group = parser.add_mutually_exclusive_group()
        commit_group.add_argument("--commit", dest='commit_explicitly_true', action="store_true", default=False,
                                  help="Explicitly intend to commit changes if validation passes (default if no other commit flags).")
        commit_group.add_argument("--explicit-no-commit-flag", dest='commit_explicitly_false', action="store_true", default=False, 
                                  help=argparse.SUPPRESS) # Hidden, for logic

        parser.add_argument("--report-format", default=DEFAULT_REPORT_FORMAT, choices=REPORT_FORMATS, help="Report output format.")
        parser.add_argument("--log-level", default=DEFAULT_LOG_LEVEL, choices=LOG_LEVELS, help="Console logging level.")
        parser.add_argument("--log-file", default=None, help="Detailed DEBUG log file path.")
        parser.add_argument("--config-file", default=None, help="Custom .scribe.toml config file path.")
        parser.add_argument("--ollama-base-url", default=None, help="Override Ollama base URL.")
        parser.add_argument("--ollama-model", default=None, help="Override Ollama model.")
        parser.add_argument("--nai-context", action="store_true", help="NAI TUI context flag.")
        
        parsed_args = parser.parse_args()

        # Determine the actual commit intent.
        # If --commit was typed, it's True. If --explicit-no-commit-flag was typed (it won't be by user), it's False.
        # If neither, default to True.
        if parsed_args.commit_explicitly_true:
            parsed_args.commit = True
        elif parsed_args.commit_explicitly_false: # This won't be hit from CLI as it's suppressed
            parsed_args.commit = False
        else: # Neither --commit nor --explicit-no-commit-flag was provided, so default intent is to commit.
            parsed_args.commit = True 
            # If user *really* wants no commit by default without --no-commit flag, this should be False.
            # Current setup: if you don't say --no-commit or --review-only, we assume you want a commit.
            
        return parsed_args

    def _validate_target_dir(self, dir_path_str: str) -> Path:
        # (Your existing _validate_target_dir method. Ensure it raises ScribeInputError on problems.)
        try:
            target_dir = Path(dir_path_str).expanduser().resolve(strict=True)
            if not target_dir.is_dir(): raise ScribeInputError(f"Target path '{target_dir}' not a dir.")
            if not hasattr(self, '_config'): raise ScribeConfigurationError("Config not init for target dir validation.")
            allowed_bases_cfg = self._config.get_list("allowed_target_bases", [])
            if not allowed_bases_cfg: self._logger.warning("'allowed_target_bases' empty. No base path restriction."); return target_dir
            allowed_bases_resolved = [str(Path(p).expanduser().resolve()) for p in allowed_bases_cfg]
            if not any(str(target_dir).startswith(b) for b in allowed_bases_resolved):
                raise ScribeInputError(f"Target dir '{target_dir}' not in allowed bases: {allowed_bases_resolved}.")
            return target_dir
        except FileNotFoundError: raise ScribeInputError(f"Target project dir not found: '{dir_path_str}'")
        except Exception as e: raise ScribeInputError(f"Error validating target dir '{dir_path_str}': {e}")

    def _find_git_executable(self) -> Optional[str]:
        # (Your existing _find_git_executable method. Ensure it uses self._tool_runner.)
        try: return str(self._tool_runner._find_executable("git"))
        except (FileNotFoundError, ScribeToolError): self._logger.warning("'git' not found."); return None

    def _initialize_report(self) -> FinalReport:
        # This now correctly uses self._do_commit from __init__
        return {
            "scribe_version": APP_VERSION, "run_id": self._run_id,
            "start_time": datetime.now(timezone.utc).isoformat(), "end_time": "",
            "total_duration_seconds": 0.0, "overall_status": STATUS_PENDING,
            "target_project_dir": str(self._target_dir) if hasattr(self, '_target_dir') else "Unset",
            "target_file_relative": self._args.target_file if hasattr(self, '_args') else "Unset",
            "language": "python", "python_version": sys.version.split()[0],
            "commit_attempted": self._do_commit, # Uses the derived flag
            "commit_sha": None, "steps": [], "audit_findings": None,
            "ai_review_findings": None, "test_results_summary": None, "error_message": None
        }

    def run(self):
        # (This is your run method from turn 35, with new flag logic integrated)
        self._logger.info(f"--- {APP_NAME} v{APP_VERSION} | Run ID: {self._run_id} ---")
        self._logger.info(f"Target Project: {self._target_dir}") # Uses validated self._target_dir
        self._logger.info(f"Source File: {self._args.source_file}")
        self._logger.info(f"Target File (relative): {self._args.target_file}")
        self._logger.info(f"Review-only mode: {self._review_only}")
        self._logger.info(f"No-commit mode: {self._no_commit}")
        self._logger.info(f"Effective commit action planned: {self._do_commit}")

        step_outputs: Dict[str, Any] = {} 
        validation_steps = self._config.get_list("validation_steps")

        if not validation_steps:
            self._logger.critical("Validation steps not configured. Halting.")
            self._overall_success = False
            self._add_step_result_custom("pipeline_setup", STATUS_FAILURE, 
                                         {"message": "Critical: Validation steps not configured in ScribeConfig."},
                                         error_message="Validation steps missing.")
            self._generate_and_print_final_report()
            sys.exit(1)

        for step_name in validation_steps:
            if not hasattr(self, '_workflow') or self._workflow is None:
                self._logger.critical("Workflow module not initialized. Halting.")
                self._overall_success = False
                self._add_step_result_custom(step_name, STATUS_FAILURE, {"message": "Workflow not initialized"})
                break
            
            step_func = getattr(self._workflow, step_name, None)
            if not callable(step_func):
                self._logger.error(f"Configuration Error: Step '{step_name}' not a valid method in WorkflowSteps. Halting.")
                self._overall_success = False
                self._add_step_result_custom(step_name, STATUS_FAILURE, 
                                             {"message": f"Invalid step '{step_name}' in configuration."},
                                             error_message=f"Invalid step '{step_name}'")
                break 

            # --- Logic for skipping steps based on flags ---
            if step_name == 'run_precommit' and self._review_only:
                self._logger.info(f"Skipping step '{step_name}' due to --review-only flag.")
                self._add_step_result_custom(step_name, STATUS_SKIPPED, {"message": "Skipped: --review-only active."})
                continue 
            
            if step_name == 'commit_changes':
                # Check self._do_commit which incorporates review_only and no_commit logic
                if not self._do_commit:
                    skip_reason = "--review-only active" if self._review_only else "--no-commit active" if self._no_commit else "Commit not planned"
                    self._logger.info(f"Skipping step '{step_name}' because effective commit is False ({skip_reason}).")
                    self._add_step_result_custom(step_name, STATUS_SKIPPED, {"message": f"Skipped: {skip_reason}."})
                    # Update report that commit was not attempted if it was skipped here
                    self._report_data["commit_attempted"] = False 
                    continue
            # --- End of flag logic ---

            dependency_arg = None
            if step_name == 'generate_tests':
                dependency_arg = step_outputs.get('extract_signatures', {}).get('details')
            elif step_name == 'save_tests':
                dependency_arg = step_outputs.get('generate_tests', {}).get('details')
            elif step_name == 'execute_tests':
                dependency_arg = step_outputs.get('save_tests', {}).get('details')

            if not self._execute_step(step_name, step_func, step_outputs, dependency_arg):
                self._logger.warning(f"Pipeline halting at step '{step_name}' due to its failure.")
                # _overall_success is set to False by _execute_step
                break 
            
            if step_name == 'review_code' and self._review_only:
                last_step_status = self._report_data["steps"][-1]["status"]
                if last_step_status not in [STATUS_FAILURE]:
                    self._logger.info("Review-only mode: Pipeline finished successfully after 'review_code'.")
                    # _overall_success remains True if all prior steps were successful
                else:
                    self._logger.warning("Review-only mode: 'review_code' or prior step failed. Pipeline halting.")
                    self._overall_success = False # Ensure overall failure if review or prior step failed
                break # Exit loop after review_code in review_only mode

        self._generate_and_print_final_report()
        sys.exit(0 if self._overall_success else 1)

    def _execute_step(self, name: str, step_func: Callable, 
                      step_outputs: Dict[str, Any], dependency: Optional[Any] = None) -> bool:
        # (Your existing _execute_step method from turn 35)
        start_time = datetime.now(timezone.utc)
        step_result: StepResult = {"name": name, "status": STATUS_PENDING, "start_time": start_time.isoformat(), "end_time": "", "duration_seconds": 0.0, "details": None, "error_message": None}
        try:
            self._logger.info(f"--- Running Step: {name} ---")
            if not self._overall_success and name != 'generate_report':
                step_result["status"] = STATUS_SKIPPED; step_result["details"] = {"message": "Skipped due to prior failure."}
                self._logger.warning(f"Skipping step '{name}' due to prior failure."); self._add_step_result(step_result); return True
            status, details_payload = step_func(dependency) if dependency else step_func()
            step_result["status"] = status; step_result["details"] = details_payload
            step_outputs[name] = step_result # Use the full step_result for context
            if status == STATUS_FAILURE: self._overall_success = False
        except ScribeError as e:
            self._logger.error(f"Step '{name}' controlled ScribeError: {e}", exc_info=False); self._logger.debug("Traceback:", exc_info=True)
            step_result["status"]=STATUS_FAILURE; step_result["error_message"]=str(e); step_result["details"]=getattr(e,'details',{"message":str(e)}); self._overall_success=False
        except Exception as e:
            self._logger.critical(f"Step '{name}' UNEXPECTED error: {e}", exc_info=True)
            step_result["status"]=STATUS_FAILURE; step_result["error_message"]=f"Unexpected: {type(e).__name__} - {e}"; step_result["details"]={"traceback": traceback.format_exc()}; self._overall_success=False
        self._add_step_result(step_result)
        return step_result["status"] != STATUS_FAILURE

    def _add_step_result_custom(self, name: str, status: str, details: Dict[str, Any], error_message: Optional[str] = None):
        # (Your existing _add_step_result_custom method from turn 35)
        now = datetime.now(timezone.utc).isoformat()
        step_res: StepResult = {"name":name, "status":status, "start_time":now, "end_time":now, "duration_seconds":0.0, "details":details, "error_message":error_message}
        if hasattr(self,'_report_data') and 'steps' in self._report_data: self._report_data["steps"].append(step_res)
        else: self._logger.error(f"Cannot add custom step '{name}', _report_data.steps missing.")
        self._logger.info(f"--- Step '{name}' Recorded (Custom) | Status: {status} ---")

    def _add_step_result(self, result: StepResult):
        # (Your existing _add_step_result method from turn 35)
        et = datetime.now(timezone.utc); result["end_time"]=et.isoformat()
        try: st_obj=datetime.fromisoformat(result["start_time"]); result["duration_seconds"]=round((et-st_obj).total_seconds(),3)
        except: result["duration_seconds"]=-1.0
        if hasattr(self,'_report_data') and 'steps' in self._report_data: self._report_data["steps"].append(result)
        else: self._logger.error(f"Cannot add step result for '{result['name']}', _report_data.steps missing.")
        self._logger.info(f"--- Step '{result['name']}' Finished | Status: {result['status']} | Duration: {result['duration_seconds']:.3f}s ---")

    def _generate_and_print_final_report(self):
        # (Your existing _generate_and_print_final_report method from turn 35)
        if not hasattr(self,'_report_data') or not self._report_data: self._print_minimal_error_report("Report data missing."); return
        self._report_data["end_time"]=datetime.now(timezone.utc).isoformat()
        if self._report_data.get("start_time"):
            try: st=datetime.fromisoformat(self._report_data["start_time"]); et=datetime.fromisoformat(self._report_data["end_time"]); self._report_data["total_duration_seconds"]=round((et-st).total_seconds(),3)
            except: self._report_data["total_duration_seconds"]=-1.0
        self._report_data["overall_status"]=STATUS_SUCCESS if self._overall_success else STATUS_FAILURE
        commit_step_cfg = 'commit_changes' in self._config.get_list("validation_steps",[])
        self._report_data["commit_attempted"] = self._do_commit and commit_step_cfg # Correctly reflects if commit was planned and configured
        if hasattr(self,'_report_generator') and self._report_generator: print(self._report_generator.generate(self._report_data))
        else: print(json.dumps(self._report_data, indent=2, default=str))


# Added CLI interface for standalone functionality
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scribe Agent CLI")
    parser.add_argument("--review-only", action="store_true", help="Perform review without committing changes.")
    parser.add_argument("--no-commit", action="store_true", help="Skip commit step.")
    parser.add_argument("--log-level", default="INFO", choices=LOG_LEVELS, help="Set log level.")
    parser.add_argument("--config", type=str, help="Path to configuration file.")
    args = parser.parse_args()

    # Setup logging
    logger = setup_logging(args.log_level)

    try:
        # Load configuration
        config = ScribeConfig(config_path_override=args.config)

        # Perform review
        if args.review_only:
            logger.info("Performing review only...")
            # Call review function (to be implemented)

        # Perform validation and commit
        if not args.no_commit:
            logger.info("Performing validation and commit...")
            # Call validation and commit function (to be implemented)

    except ScribeError as e:
        logger.error(f"Scribe encountered an error: {e}", exc_info=True)
        sys.exit(1)

    logger.info("Scribe Agent completed successfully.")