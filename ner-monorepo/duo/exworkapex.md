#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# File: scripts/scribe_agent.py (within Omnitide Nexus)
# Project Scribe: Apex Automated Validation Agent v1.2.0 (Finalized & Polished)
# Augmented by NAA under Core Team Review - Manifested under Drake Protocol v5.0 Apex
# For The Supreme Master Architect Alix Feronti
# Current Version: Streamlined for optimal standalone performance.

"""
Project Scribe: Apex Automated Code Validation & Integration Agent (v1.2.0)

Executes a validation gauntlet on provided Python code artifacts.
Handles venv, dependencies, audit, format, lint, type check, AI test gen/exec,
AI review, pre-commit hooks, conditional Git commit, and JSON reporting.
Streamlined for optimal standalone performance and explicit error handling.
"""

import argparse
import ast
import json
import logging
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import (Any, Callable, Dict, List, Optional, Sequence, Tuple,
                    TypedDict, Union, cast)
from urllib.parse import urlparse

# --- Dependency Check for HTTP Library ---
HTTP_LIB: Optional[str] = None
HTTP_LIB_AVAILABLE: bool = False
try:
    import httpx
    HTTP_LIB = "httpx"
    HTTP_LIB_AVAILABLE = True
except ImportError:
    try:
        import requests
        HTTP_LIB = "requests"
        HTTP_LIB_AVAILABLE = True
    except ImportError:
        pass

# --- Dependency Check for TOML Library ---
try:
    import tomllib  # Python 3.11+
except ImportError:
    try:
        import tomli as tomllib  # Fallback for Python < 3.11
    except ImportError:
        tomllib = None

# Added a helper function to check Python version compatibility
def check_python_version():
    if sys.version_info < (3, 9):
        print("WARNING: You are using Python version {}.{}.{}. Project Scribe recommends Python 3.11 or higher for full compatibility.".format(
            sys.version_info.major, sys.version_info.minor, sys.version_info.micro), file=sys.stderr)

check_python_version()

# --- Constants ---
APP_NAME: str = "Project Scribe"
APP_VERSION: str = "1.2.0" # Version reflects finalized state
LOG_FORMAT: str = '%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s'
DEFAULT_LOG_LEVEL: str = "INFO"
LOG_LEVELS: List[str] = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
DEFAULT_CONFIG_FILENAME: str = ".scribe.toml"
VENV_DIR_NAME: str = ".venv"
DEFAULT_PYTHON_VERSION: str = "3.11"
DEFAULT_REPORT_FORMAT: str = "json"
REPORT_FORMATS: List[str] = ["json", "text"]
DEFAULT_OLLAMA_MODEL: str = "gemma:2b"
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


# Type Definitions for Reporting Clarity
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
    traceback: Optional[str]

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
    error_message: Optional[str]

# --- Custom Exceptions ---
class ScribeError(Exception):
    """Base exception for Scribe-specific errors."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.details = details if details is not None else {}

class ScribeConfigurationError(ScribeError): """Error related to Scribe configuration."""
class ScribeInputError(ScribeError): """Error related to invalid user inputs."""
class ScribeEnvironmentError(ScribeError): """Error related to environment setup (venv, dependencies)."""
class ScribeToolError(ScribeError): """Error related to external tool execution."""
class ScribeApiError(ScribeError): """Error related to LLM API communication."""
class ScribeFileSystemError(ScribeError): """Error related to file system operations."""

# --- Logging Setup Function ---
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

# --- Configuration Manager ---
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

        if not self._config_path and project_dir_for_local_config:
            proj_config = project_dir_for_local_config.resolve() / DEFAULT_CONFIG_FILENAME
            if proj_config.is_file(): self._config_path = proj_config

        if not self._config_path :
            cwd_config = Path.cwd() / DEFAULT_CONFIG_FILENAME
            if cwd_config.is_file(): self._config_path = cwd_config

        self._config: Dict[str, Any] = self._load_and_validate_config()

    def _get_default_config(self) -> Dict[str, Any]:
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
            "test_generation_prompt_template": (
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
            "validation_steps": [
                "validate_inputs", "setup_environment", "install_deps", "audit_deps", "apply_code",
                "format_code", "lint_code", "type_check", "extract_signatures", "generate_tests",
                "save_tests", "execute_tests", "review_code", "run_precommit", "commit_changes",
                "generate_report"
            ], "tool_paths": {}
        }

    def _load_and_validate_config(self) -> Dict[str, Any]:
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

    def _merge_configs(self, base: Dict, updates: Dict) -> Dict:
        m = base.copy();
        for k,v in updates.items():
            if isinstance(v,dict) and isinstance(m.get(k),dict): m[k] = self._merge_configs(m[k],v)
            else: m[k] = v
        return m

    def _validate_loaded_config(self, config: Dict[str, Any]):
        self._logger.debug("Validating config...")
        if not isinstance(config.get("allowed_target_bases"), list): raise ScribeConfigurationError("allowed_target_bases: list expected")
        if not all(isinstance(b, str) for b in config["allowed_target_bases"]): raise ScribeConfigurationError("allowed_target_bases must contain only strings.")
        if not isinstance(config.get("fail_on_audit_severity"), str) or config["fail_on_audit_severity"].lower() not in ["low", "moderate", "high", "critical"]: raise ScribeConfigurationError("fail_on_audit_severity must be 'low', 'moderate', 'high', or 'critical'.")
        if not isinstance(config.get("fail_on_lint_critical"), bool): raise ScribeConfigurationError("fail_on_lint_critical: boolean expected.")
        if not isinstance(config.get("fail_on_mypy_error"), bool): raise ScribeConfigurationError("fail_on_mypy_error: boolean expected.")
        if not isinstance(config.get("fail_on_test_failure"), bool): raise ScribeConfigurationError("fail_on_test_failure: boolean expected.")
        if not isinstance(config.get("ollama_base_url"), str) or not urlparse(config["ollama_base_url"]).scheme: raise ScribeConfigurationError("ollama_base_url: valid URL string expected.")
        if not isinstance(config.get("ollama_model"), str) or not config["ollama_model"]: raise ScribeConfigurationError("ollama_model: string expected.")
        if not isinstance(config.get("ollama_request_timeout"), (int, float)) or config["ollama_request_timeout"] <= 0: raise ScribeConfigurationError("ollama_request_timeout: positive number expected.")
        if not isinstance(config.get("ollama_api_retries"), int) or config["ollama_api_retries"] < 0: raise ScribeConfigurationError("ollama_api_retries: non-negative integer expected.")
        if not isinstance(config.get("ollama_api_retry_delay"), (int, float)) or config["ollama_api_retry_delay"] <= 0: raise ScribeConfigurationError("ollama_api_retry_delay: positive number expected.")
        if not isinstance(config.get("default_tool_timeout"), (int, float)) or config["default_tool_timeout"] <= 0: raise ScribeConfigurationError("default_tool_timeout: positive number expected.")
        if not isinstance(config.get("commit_message_template"), str) or not config["commit_message_template"]: raise ScribeConfigurationError("commit_message_template: non-empty string expected.")
        if not isinstance(config.get("test_generation_prompt_template"), str) or not config["test_generation_prompt_template"]: raise ScribeConfigurationError("test_generation_prompt_template: non-empty string expected.")
        if not isinstance(config.get("review_prompt_template"), str) or not config["review_prompt_template"]: raise ScribeConfigurationError("review_prompt_template: non-empty string expected.")
        if not isinstance(config.get("validation_steps"), list) or not all(isinstance(s, str) for s in config["validation_steps"]): raise ScribeConfigurationError("validation_steps: list of strings expected.")
        if not isinstance(config.get("tool_paths"), dict): raise ScribeConfigurationError("tool_paths: dictionary expected.")
        self._logger.debug("Config validation appears OK.")


    def get(self, key: str, default: Any = None) -> Any: return self._config.get(key, default)
    def get_list(self, key: str, default: Optional[List[Any]] = None) -> List[Any]: v=self._config.get(key,default or []); return v if isinstance(v,list) else (default or [])
    def get_str(self, key: str, default: str = "") -> str: v=self._config.get(key,default); return str(v) if v is not None else default
    def get_bool(self, key: str, default: bool = False) -> bool: v=self._config.get(key,default); return v if isinstance(v,bool) else (str(v).lower()=='true' if isinstance(v,str) else default)
    def get_float(self, key: str, default: float = 0.0) -> float: try: return float(self._config.get(key,default)) except: return default
    def get_int(self, key: str, default: int = 0) -> int: try: return int(float(self._config.get(key,default))) except: return default
    @property
    def config_path(self) -> Optional[Path]: return self._config_path
    @property
    def is_nai_context(self) -> bool: return self._is_nai_context

# --- Tool Runner ---
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
class EnvironmentManager:
    def __init__(self, target_dir: Path, python_version_str: str, tool_runner: ToolRunner, config: ScribeConfig):
        self._logger=logging.getLogger(f"{APP_NAME}.EnvironmentManager"); self._target_dir=target_dir.resolve(); self._python_version_str=python_version_str; self._tool_runner=tool_runner; self._config=config; self._venv_path=self._target_dir/VENV_DIR_NAME; self._venv_python_path=None; self._pip_path=None
    @property
    def venv_path(self)->Path: return self._venv_path
    @property
    def python_executable(self)->Optional[Path]: return self._venv_python_path
    @property
    def pip_executable(self)->Optional[Path]: return self._pip_path
    def find_venv_executable(self,name:str)->Optional[Path]:
        if not self._venv_path.is_dir(): return None
        bin_dir = self._venv_path / ("Scripts" if sys.platform == "win32" else "bin")
        for sfx in ["",".exe"] if sys.platform=="win32" else [""]:
            p = bin_dir / f"{name}{sfx}"
            if p.is_file() and os.access(p, os.X_OK): return p.resolve()
        return None
    def setup_venv(self):
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
    def install_dependencies(self):
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
    def run_pip_audit(self)->subprocess.CompletedProcess:
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
    def _call_api(self,prompt:str,fmt:Optional[str]=None)->Dict[str,Any]:
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
    def _extract_code_from_response(self,llm_resp:str)->str:
        self._logger.debug("Extracting code from LLM response...")
        py_blocks=re.findall(r"```python\n(.*?)\n```",llm_resp,re.DOTALL|re.IGNORECASE)
        if py_blocks:
            if len(py_blocks)>1: self._logger.warning(f"LLM gave {len(py_blocks)} python blocks, concatenating.")
            return "\n\n# Scribe: Concatenated Block\n\n".join(b.strip() for b in py_blocks).strip()
        gen_blocks=re.findall(r"```(?:[a-zA-Z0-9_.-]*)?\n(.*?)\n```",llm_resp,re.DOTALL)
        if gen_blocks: self._logger.warning("No 'python' block, using first generic."); return gen_blocks[0].strip()
        self._logger.warning("No fenced block, assuming all is code."); return llm_resp.strip()
    def generate_tests(self,code:str,file_name:str,sigs:str)->Optional[str]:
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
    def generate_review(self,code:str,file_name:str)->Optional[List[Dict[str,str]]]:
        self._logger.info(f"Requesting AI code review for '{file_name}'")
        template=self._config.get_str("review_prompt_template")
        code=code[:8000]+("..."if len(code)>8000 else"")
        try: prompt=template.format(code_content=code,target_file_path=file_name)
        except KeyError as e: raise ScribeConfigurationError(f"Invalid review_prompt: missing {e}")
        try:
            api_resp=self._call_api(prompt,fmt="json"); raw_json_str=api_resp.get("response","")
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
class WorkflowSteps:
    def __init__(self, agent:'ScribeAgent'): self.agent=agent; self._logger=logging.getLogger(f"{APP_NAME}.WorkflowSteps")
    def _truncate_output(self,s:Optional[str],ml:int=500,hl:int=200,tl:int=200)->str:
        if not s: return ""; s=s.strip();
        if len(s)>ml: return f"{s[:hl]}\n...({len(s)} chars)...\n{s[-tl:]}"
        return s
    def validate_inputs(self) -> Tuple[str, StepOutputDetails]:
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
    def audit_deps(self)->Tuple[str,StepOutputDetails]:
        res=self.agent._env_manager.run_pip_audit(); details:StepOutputDetails={"tool_name":"pip-audit","return_code":res.returncode}; vulns=[]
        if res.stdout:
            try: vulns=json.loads(res.stdout).get("vulnerabilities",[])
            except json.JSONDecodeError: return STATUS_WARNING, {**details, "message":"pip-audit JSON parse error."}
        details["vulnerability_count"]=len(vulns); self.agent._report_data["audit_findings"]=vulns
        if not vulns: details["message"]="No vulnerabilities."; return STATUS_SUCCESS, details

        fail_severity_threshold_str = self.agent._config.get_str("fail_on_audit_severity", "high").lower()
        severity_rank = {"low":1, "moderate":2, "high":3, "critical":4}
        configured_threshold = severity_rank.get(fail_severity_threshold_str, 3)

        highest_severity_found = "low"
        for vuln in vulns:
            vuln_severity_str = vuln.get("severity", "low").lower()
            if severity_rank.get(vuln_severity_str, 0) > severity_rank.get(highest_severity_found, 0):
                highest_severity_found = vuln_severity_str
            if severity_rank.get(vuln_severity_str, 0) >= configured_threshold:
                details["message"] = f"Audit found {len(vulns)} vulnerabilities. Criticality ({highest_severity_found}) meets/exceeds configured fail threshold ({fail_severity_threshold_str})."
                details["highest_severity"] = highest_severity_found
                details["configured_fail_severity"] = fail_severity_threshold_str
                return STATUS_FAILURE, details

        details["message"]=f"Audit found {len(vulns)} vulnerabilities. Highest severity: {highest_severity_found}. Below fail threshold ({fail_severity_threshold_str})."
        details["highest_severity"] = highest_severity_found
        details["configured_fail_severity"] = fail_severity_threshold_str
        return STATUS_WARNING, details


    def apply_code(self)->Tuple[str,StepOutputDetails]:
        code=self.agent._source_file_path.read_text(encoding='utf-8'); self.agent._target_file_path.write_text(code,encoding='utf-8'); return STATUS_SUCCESS, {"bytes_written":len(code)}
    def format_code(self)->Tuple[str,StepOutputDetails]:
        cmd=["ruff","format",str(self.agent._target_file_path)]; res=self.agent._tool_runner.run_tool(cmd,self.agent._target_dir,self.agent._env_manager.venv_path); details={"tool_name":"ruff (format)","return_code":res.returncode}
        if res.returncode==0: details["message"]="Formatted."; return STATUS_SUCCESS, details
        raise ScribeToolError(f"Ruff format fail RC={res.returncode}. E: {res.stderr.strip()}")
    def lint_code(self)->Tuple[str,StepOutputDetails]:
        cmd=["ruff","check","--fix",str(self.agent._target_file_path)]; res=self.agent._tool_runner.run_tool(cmd,self.agent._target_dir,self.agent._env_manager.venv_path); details={"tool_name":"ruff (check --fix)","return_code":res.returncode,"stdout_summary":self._truncate_output(res.stdout)}
        if res.returncode==0: details["message"]="Lint OK."; return STATUS_SUCCESS, details
        if res.returncode==1: details["message"]="Lint issues found."; return STATUS_FAILURE if self.agent._config.get_bool("fail_on_lint_critical") else STATUS_WARNING, details
        raise ScribeToolError(f"Ruff check fail RC={res.returncode}. E: {res.stderr.strip()}")
    def type_check(self)->Tuple[str,StepOutputDetails]:
        cmd=["mypy",str(self.agent._target_file_path)]; res=self.agent._tool_runner.run_tool(cmd,self.agent._target_dir,self.agent._env_manager.venv_path); details={"tool_name":"mypy","return_code":res.returncode,"stdout_summary":self._truncate_output(res.stdout)}
        if res.returncode==0: details["message"]="MyPy OK."; return STATUS_SUCCESS, details
        if res.returncode==1: details["message"]="MyPy type errors."; return STATUS_FAILURE if self.agent._config.get_bool("fail_on_mypy_error") else STATUS_WARNING, details
        raise ScribeToolError(f"MyPy fail RC={res.returncode}. E: {res.stderr.strip()}")
    def extract_signatures(self)->Tuple[str,StepOutputDetails]:
        code=self.agent._target_file_path.read_text(encoding='utf-8')
        try:
            tree=ast.parse(code); sigs=[]
            for node in ast.walk(tree):
                if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)): sig_parts=[ast.unparse(d) for d in node.decorator_list]; sig_parts.append(f"{'async ' if isinstance(node,ast.AsyncFunctionDef) else ''}def {node.name}({ast.unparse(node.args)}){' -> '+ast.unparse(node.returns) if node.returns else ''}:"); sigs.append("\n".join(f"@{p}" if i < len(node.decorator_list) else p for i,p in enumerate(sig_parts)))
                elif isinstance(node,ast.ClassDef): sig_parts=[ast.unparse(d) for d in node.decorator_list]; bases="("+", ".join(ast.unparse(b) for b in node.bases)+")" if node.bases else ""; sig_parts.append(f"class {node.name}{bases}:"); sigs.append("\n".join(f"@{p}" if i < len(node.decorator_list) else p for i,p in enumerate(sig_parts)))
            return STATUS_SUCCESS, {"message":f"Extracted {len(sigs)} sigs.","raw_output":"\n\n".join(sigs)}
        except SyntaxError as e:
            raise ScribeInputError(f"SyntaxError in target code during signature extraction: {e}") from e
        except Exception as e:
            raise ScribeError(f"Unexpected error during signature extraction: {e}") from e

    def generate_tests(self,sig_details:Optional[StepOutputDetails]=None)->Tuple[str,StepOutputDetails]:
        code=self.agent._target_file_path.read_text(encoding='utf-8'); sigs=sig_details.get("raw_output","") if sig_details else ""
        tests=self.agent._llm_client.generate_tests(code,self.agent._target_file_path.name,sigs)
        return (STATUS_SUCCESS if tests else STATUS_FAILURE), {"raw_output":tests,"message":"Tests AI-generated." if tests else "Test gen failed."}
    def save_tests(self,gen_tests_details:Optional[StepOutputDetails]=None)->Tuple[str,StepOutputDetails]:
        code=gen_tests_details.get("raw_output","") if gen_tests_details else ""
        if not code: return STATUS_WARNING, {"message":"No test code to save."}
        test_dir=self.agent._target_dir/SCRIBE_TEST_DIR; test_dir.mkdir(parents=True,exist_ok=True)
        safe_stem=''.join(c if c.isalnum() else '_' for c in self.agent._target_file_path.stem)
        path=test_dir/f"test_{safe_stem}_scribe.py"; path.write_text(code,encoding='utf-8')
        return STATUS_SUCCESS, {"generated_content_path":str(path),"raw_output":str(path)}
    def execute_tests(self,saved_tests_details:Optional[StepOutputDetails]=None)->Tuple[str,StepOutputDetails]:
        path_str=saved_tests_details.get("raw_output","") if saved_tests_details else ""
        if not path_str or not Path(path_str).is_file(): return STATUS_FAILURE, {"message":f"Test file not found: {path_str}"}
        env = os.environ.copy()
        proj_root_str = str(self.agent._target_dir.resolve())
        src_dir_str = str((self.agent._target_dir / "src").resolve())
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
    def review_code(self)->Tuple[str,StepOutputDetails]:
        code=self.agent._target_file_path.read_text(encoding='utf-8')
        review=self.agent._llm_client.generate_review(code,self.agent._target_file_path.name)
        self.agent._report_data["ai_review_findings"]=review
        return STATUS_ADVISORY, {"issues_found":review or [], "message":f"AI review found {len(review or [])} items."}
    def run_precommit(self)->Tuple[str,StepOutputDetails]:
        cfg_file=self.agent._target_dir/".pre-commit-config.yaml"
        if not cfg_file.is_file(): return STATUS_SKIPPED, {"message":"No .pre-commit-config.yaml"}
        cmd=["pre-commit","run","--files",str(self.agent._target_file_path)]; res=self.agent._tool_runner.run_tool(cmd,self.agent._target_dir,self.agent._env_manager.venv_path)
        if res.returncode==0: return STATUS_SUCCESS, {"message":"Pre-commit passed."}
        return STATUS_FAILURE, {"message":f"Pre-commit failed RC={res.returncode}","stdout_summary":self._truncate_output(res.stdout)}
    def commit_changes(self)->Tuple[str,StepOutputDetails]:
        if not self.agent.git_exe: return STATUS_WARNING, {"message":"Git not found, commit skipped."}
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
    def generate_report(self) -> Tuple[str, StepOutputDetails]:
        return STATUS_SUCCESS, {"message":"Final report data prepared.", "raw_output": "Report generation triggered."}

# --- Report Generator ---
class ReportGenerator:
    def __init__(self, format_str: str):
        self._format = format_str
        if self._format not in REPORT_FORMATS:
            raise ScribeConfigurationError(f"Unsupported report format: {self._format}. Supported: {REPORT_FORMATS}")
    def generate(self, report_data: FinalReport) -> str:
        if self._format == 'json':
            try: return json.dumps(report_data, indent=2, default=str)
            except TypeError as e: logging.getLogger(APP_NAME).error(f"JSON serialize error: {e}"); return json.dumps({"error":"JSON serialize failed", "details":str(e)})
        elif self._format == 'text':
            lines = [f"Scribe Report ID: {report_data.get('run_id', 'N/A')}"]
            lines.append(f"Overall Status: {report_data.get('overall_status', 'UNKNOWN')}")
            # Add more details for text report
            if report_data.get('error_message'):
                lines.append(f"Error: {report_data['error_message']}")
            lines.append(f"Duration: {report_data.get('total_duration_seconds', 0.0):.3f}s")
            lines.append(f"Target Project: {report_data.get('target_project_dir', 'N/A')}")
            lines.append(f"Target File: {report_data.get('target_file_relative', 'N/A')}")
            lines.append(f"Commit Attempted: {'Yes' if report_data.get('commit_attempted', False) else 'No'}")
            if report_data.get('commit_sha'):
                lines.append(f"Commit SHA: {report_data['commit_sha']}")
            
            lines.append("\n--- Steps ---")
            for step in report_data.get('steps', []):
                lines.append(f"  [{step.get('status', 'N/A')}] {step.get('name')}: {step.get('message', '')} (Duration: {step.get('duration_seconds', 0.0):.3f}s)")
                if step.get('error_message'):
                    lines.append(f"    Error: {step['error_message']}")
                if step.get('details', {}).get('traceback'):
                    lines.append(f"    Traceback: {step['details']['traceback']}")
            
            if report_data.get('audit_findings'):
                lines.append("\n--- Audit Findings ---")
                for finding in report_data['audit_findings']:
                    lines.append(f"  - Severity: {finding.get('severity', 'N/A')}, Description: {finding.get('description', 'N/A')}")
            
            if report_data.get('ai_review_findings'):
                lines.append("\n--- AI Review Findings ---")
                for finding in report_data['ai_review_findings']:
                    lines.append(f"  - Severity: {finding.get('severity', 'N/A')}, Description: {finding.get('description', 'N/A')}, Location: {finding.get('location', 'N/A')}")

            if report_data.get('test_results_summary'):
                lines.append("\n--- Test Results Summary ---")
                trs = report_data['test_results_summary']
                lines.append(f"  Return Code: {trs.get('return_code', 'N/A')}")
                if trs.get('stdout'):
                    lines.append(f"  STDOUT:\n{trs['stdout']}")
                if trs.get('stderr'):
                    lines.append(f"  STDERR:\n{trs['stderr']}")

            return "\n".join(lines)
        return f"Error: Unknown report format '{self._format}'."

# --- Main Entry Point ---
def main():
    """Main entry point for the Scribe Agent."""
    # Initial checks for critical dependencies (HTTP_LIB_AVAILABLE and tomllib should be set globally)
    if not HTTP_LIB_AVAILABLE:
        print("FATAL ERROR: Scribe requires either 'httpx' or 'requests' for LLM features.", file=sys.stderr)
        print("Please run: pip install httpx or pip install requests", file=sys.stderr) # Clarified install command
        sys.exit(1)
    
    if not tomllib:
        print("FATAL ERROR: Could not import 'tomllib' (Python 3.11+) or 'tomli' (fallback).\n"
              "Project Scribe requires one of these. For Python < 3.11, please run: pip install tomli",
              file=sys.stderr)
        sys.exit(1)
    
    try:
        agent = ScribeAgent()
        agent.run()
    except ScribeError as e:
        print(f"CRITICAL SCRIBE ERROR (during agent instantiation or early setup): {e}", file=sys.stderr)
        if hasattr(e, 'details') and e.details: print(f"Details: {e.details}", file=sys.stderr)
        sys.exit(1)
    except SystemExit as e:
        sys.exit(e.code)
    except Exception as e:
        print(f"UNEXPECTED SYSTEM ERROR (during agent instantiation or Scribe lifecycle): {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()

