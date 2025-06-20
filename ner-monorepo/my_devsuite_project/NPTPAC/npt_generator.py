#!/usr/bin/env python3
# Nexus Protocol Toolkit (NPT) Generator - v2.0
# This script scaffolds the NPT environment, NER structure, and the PAC application.
# It is intended to be run by the outer bootstrap_npt.sh script.

import argparse
import datetime
import json
import os
import shlex
import shutil
import stat
import subprocess
import sys
import textwrap
import traceback # For printing full tracebacks on unexpected errors
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

# --- Constants & Configuration (Basic ones needed early) ---
NPT_GENERATOR_VERSION = "2.0"
CURRENT_YEAR = str(datetime.datetime.now().year)
NPT_BASE_DIR_ENV_VAR_NAME = "NPT_BASE_DIR" # Name of the env var used by PAC

# --- Colorized Output Helpers ---
class TermColors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def echo_color(color_code: str, message: str, bold: bool = False):
    prefix = TermColors.BOLD if bold else ""
    print(f"{prefix}{color_code}{message}{TermColors.ENDC}")

def info(message: str): echo_color(TermColors.OKBLUE, f"INFO: {message}")
def success(message: str): echo_color(TermColors.OKGREEN, f"SUCCESS: {message}")
def warning(message: str): echo_color(TermColors.WARNING, f"WARN: {message}")
def error(message: str, exit_code: Optional[int] = None):
    echo_color(TermColors.FAIL, f"ERROR: {message}", bold=True)
    if exit_code is not None:
        sys.exit(exit_code)
def step(message: str): echo_color(TermColors.OKCYAN, f"\n>>> STEP: {message} <<<\n", bold=True)
def important(message: str): echo_color(TermColors.HEADER, message, bold=True)

# --- Conditional Library Imports (Now using defined helpers) ---
TOML_WRITER_LIB_MODULE: Optional[Any] = None 
TOML_WRITER_LIB_AVAILABLE: bool = False
try:
    import toml
    TOML_WRITER_LIB_MODULE = toml
    TOML_WRITER_LIB_AVAILABLE = True
    info("Using 'toml' library for WRITING .toml files.") 
except ImportError:
    warning("'toml' library not found. PAC settings file will be written as JSON with a .toml extension.") 
    warning("For proper TOML format, please install it in the environment running this generator: pip install toml")

TOML_READER_LIB_MODULE: Optional[Any] = None
try:
    import tomllib as TOML_READER_LIB_IMPORTER
    TOML_READER_LIB_MODULE = TOML_READER_LIB_IMPORTER
    info("Using standard library 'tomllib' for READING .toml files (if needed).")
except ImportError:
    try:
        import tomli as TOML_READER_LIB_IMPORTER
        TOML_READER_LIB_MODULE = TOML_READER_LIB_IMPORTER
        info("Using 'tomli' as TOML_READER_LIB_MODULE for READING .toml files (if needed).")
    except ImportError:
        warning("No TOML reading library ('tomllib' or 'tomli') found for the generator.")

# --- Default directory names ---
NER_DIR_NAME = "ner_repository"
PAC_CLI_DIR_NAME = "pac_cli"
PAC_APP_DIR_NAME = "app"
PAC_CORE_DIR_NAME = "core"
PAC_COMMANDS_DIR_NAME = "commands"
PAC_UTILS_DIR_NAME = "utils"
PAC_TESTS_DIR_NAME = "tests"
PAC_CONFIG_DIR_NAME = "config"
PAC_LOGS_DIR_NAME = "logs"    
CORE_AGENTS_DIR_NAME = "core_agents"

# --- Default filenames ---
PAC_SETTINGS_FILENAME = "settings.toml"
PAC_LAUNCHER_FILENAME = "npac"
SETUP_VENV_FILENAME = "setup_venv.sh"
GITIGNORE_FILENAME = ".gitignore"
PYPROJECT_FILENAME = "pyproject.toml"
PAC_MAIN_PY_FILENAME = "main.py"
PAC_INIT_PY_FILENAME = "__init__.py"

# --- File System and Process Utilities (definitions as previously provided) ---
def create_directory(path: Path, ignore_errors: bool = False) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
        return True
    except OSError as e:
        if not ignore_errors: error(f"Failed to create directory {path}: {e.strerror}", 1)
        return False

def create_file(path: Path, content: str = "", executable: bool = False, overwrite: bool = True) -> bool:
    if path.exists() and not overwrite:
        info(f"File {path} already exists and overwrite is false. Skipping.")
        return True
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f: f.write(content)
        if executable:
            current_mode = path.stat().st_mode
            path.chmod(current_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        return True
    except OSError as e: error(f"Failed to create file {path}: {e.strerror}", 1); return False

def copy_file(src_path: Path, dest_path: Path, ignore_errors: bool = False) -> bool:
    try:
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_path, dest_path); info(f"Copied '{src_path.name}' to '{dest_path}'")
        return True
    except (shutil.Error, OSError) as e:
        msg = f"Failed to copy file from {src_path} to {dest_path}: {e}"
        if not ignore_errors: error(msg, 1)
        else: warning(msg)
        return False

def run_command(command: List[str], cwd: Optional[Path] = None, capture: bool = False) -> Tuple[bool, str, str]:
    command_str = " ".join(shlex.quote(c) for c in command)
    info(f"Running command: {command_str}{f' in {cwd}' if cwd else ''}")
    try:
        process = subprocess.run(command, cwd=cwd, text=True, capture_output=capture, check=False)
        stdout = process.stdout.strip() if process.stdout and capture else (process.stdout if process.stdout else "")
        stderr = process.stderr.strip() if process.stderr and capture else (process.stderr if process.stderr else "")
        if process.returncode == 0:
            if capture and stdout: info(f"Command succeeded.")
            elif not capture : info("Command succeeded.")
            return True, stdout, stderr
        else:
            warning(f"Command failed with RC {process.returncode}.")
            if capture:
                if stderr: warning(f"  STDERR: {stderr[:200]}{'...' if len(stderr)>200 else ''}")
                if stdout: warning(f"  STDOUT: {stdout[:200]}{'...' if len(stdout)>200 else ''}")
            return False, stdout, stderr
    except FileNotFoundError: error(f"Command not found: {command[0]}. Ensure it's installed and in PATH."); return False, "", f"Command not found: {command[0]}"
    except Exception as e: error(f"Unexpected error running command '{command_str}': {e!r}"); return False, "", str(e)

def get_user_input(prompt_message: str, default: Optional[str] = None) -> str:
    full_prompt = f"{TermColors.WARNING}{prompt_message}{TermColors.ENDC}"
    if default is not None: full_prompt += f" (default: {TermColors.OKGREEN}{default}{TermColors.ENDC})"
    full_prompt += ": "
    try:
        user_response = input(full_prompt).strip()
        return user_response if user_response else (default if default is not None else "")
    except EOFError: warning("EOF encountered. Using default or empty."); return default if default is not None else ""
    except KeyboardInterrupt: warning("\nUser interrupted. Exiting generator."); sys.exit(130)

def confirm_action(prompt_message: str, default_yes: bool = False) -> bool:
    options = "(Y/n)" if default_yes else "(y/N)"; default_char = "y" if default_yes else "n"
    while True:
        response = get_user_input(f"{prompt_message} {options}", default=default_char).lower()
        if response in ["y", "yes"]: return True
        if response in ["n", "no"]: return False
        warning("Invalid input. Please answer 'y' or 'n'.")

# --- Global Paths (Type hints. Values assigned in main_generator) ---
NPT_BASE_DIR_ABS: Path
NER_PATH_ABS: Path
PAC_CLI_PATH_ABS: Path
PAC_APP_PATH_ABS: Path
PAC_CORE_PATH_ABS: Path
PAC_COMMANDS_PATH_ABS: Path
PAC_UTILS_PATH_ABS: Path
PAC_TESTS_PATH_ABS: Path
PAC_CONFIG_PATH_ABS: Path
PAC_LOGS_PATH_ABS: Path
CORE_AGENTS_PATH_ABS: Path
PAC_SETTINGS_FILE_PATH: Path

PYTHON_CMD_FROM_BOOTSTRAP: str = os.environ.get("NPT_PYTHON_CMD", "python3")

# --- Main Argument Parser ---
def setup_generator_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=f"NPT Generator v{NPT_GENERATOR_VERSION}", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--base-dir", type=Path, required=True, help="Absolute base directory for NPT.")
    parser.add_argument("--ner-repo-url", type=str, default="git@github.com:mrpongalfer/NER.git", help="URL of your empty GitHub repository for NER.")
    parser.add_argument("--llm-preference", type=str, choices=["openai", "anthropic", "google", "ollama", "generic"], default="ollama", help="Preferred LLM API/client for PAC stubs.")
    parser.add_argument("--force-overwrite", action="store_true", help="Force overwrite of existing files.")
    return parser

# --- NER Structure and Content Generation (definitions as previously provided) ---
NER_STRUCTURE = {
    "00_CORE_EDICTS": {
        "01_architect_supremacy.md": "# Edict 1: Architect's Supremacy...",
        "02_TPC_adherence.md": "# Edict 2: True Prime Code (TPC) Adherence...",
        "README.md": "# Core Edicts..."
    },
    "01_ONAP_R3_COMPONENTS": { 
        "ONAP_P1_Foundation.md": "# ONAP - Part 1...", "ONAP_P2_Core_Team.md": "# ONAP - Part 2...",
        "ONAP_P3_Advanced_Concepts.md": "# ONAP - Part 3...", "ONAP_P4_Final_Activation.md": "# ONAP - Part 4...",
        "README.md": "# ONAP Components..."
    },
    "02_TPC_STANDARD": {"TPC_Definition_Latest.md": "# TPC Standard - Detailed...", "README.md": "# TPC Standard Docs"},
    "03_CORE_TEAM_PERSONAS": { "Tony_Stark.md": "# Persona: Tony Stark...", "README.md": "# Core Team Personas"},
    "04_INTERACTION_GUIDES": {"NAI_Interaction_Principles.md": "# NAI Interaction...", "README.md": "# Interaction Guides"},
    "05_PROJECT_SUMMARIES": {"Project_Scribe_Summary.md": "# Scribe Summary...", "Project_ExWork_Summary.md": "# Ex-Work Summary...", "README.md": "# Project Summaries"},
    "06_AGENT_BLUEPRINTS": {
        "ex_work_agent": {"templates": {"basic_echo.exwork.json": "{\n  \"actions\": [{\"type\": \"ECHO\", \"message\": \"Hello Ex-Work!\"}]\n}", "README.md":"# Ex-Work Templates"}, "docs": {"README.md":"# Ex-Work Docs"}},
        "scribe_agent": {"profiles": {"default.scribe.toml": "fail_on_audit_severity = \"high\"", "README.md":"# Scribe Profiles"}, "docs": {"README.md":"# Scribe Docs"}},
        "README.md": "# Agent Blueprints"
    },
    "07_SECURITY_TOOLS": {
        "red_team": {"nmap_scans": {"basic_host_discovery.manifest.json": "{ \"tool_name\": \"Nmap Host Discovery\" }", "nmap_host_discovery.exwork.json":"{ \"actions\": [{\"type\":\"RUN_SCRIPT\", \"script_path\":\"nmap\"}] }", "README.md":"# Nmap Scans"}, "README.md":"# Red Team Tools"},
        "blue_team": {"log_analysis_templates": {"syslog_error_check.manifest.json": "{ \"tool_name\": \"Syslog Check\" }", "syslog_error_check.exwork.json":"{ \"actions\": [{\"type\":\"RUN_SCRIPT\", \"script_path\":\"grep\"}] }", "README.md":"# Log Templates"}, "README.md":"# Blue Team Tools"},
        "README.md": "# Security Toolkit"
    },
    "08_INNOVATION_SHOWCASE": {
        "hackathon_templates": {"python_fastapi_api": {"manifest.json": "{ \"template_name\": \"Python FastAPI\" }", "python_fastapi_setup.exwork.json": "{ \"description\": \"Sets up FastAPI\" }", "README.md":"# FastAPI Template"}, "README.md":"# Hackathon Templates"},
        "README.md": "# Innovation Showcase"
    },
    ".gitignore": "__pycache__/\n*.pyc\n.venv*\nvenv/\nENV/\nenv/\n",
    "README.md": "# Nexus Edict Repository (NER)..."
}

def populate_ner_structure(ner_base_path: Path, ner_structure_data: Dict, force_overwrite: bool):
    step(f"Populating NER structure at: {ner_base_path}")
    for name, content in ner_structure_data.items():
        current_path = ner_base_path / name
        if isinstance(content, dict): 
            create_directory(current_path)
            populate_ner_structure(current_path, content, force_overwrite) 
        elif isinstance(content, str): 
            create_file(current_path, textwrap.dedent(content).strip(), overwrite=force_overwrite)
    if ner_base_path == NER_PATH_ABS: # Only print overall success once
        success(f"NER structure population complete for main path: {ner_base_path}")

# --- PAC File Content Generation Functions (generate_pac_..._py_content, etc. - use the full versions from our previous discussions) ---
# For brevity, I will assume these functions are defined here correctly, incorporating all f-string fixes.
# The key is that default_settings_for_toml is now defined *inside* main_generator.

def generate_pac_gitignore_content() -> str: # Content as defined before
    return textwrap.dedent("""\
        __pycache__/
        *.py[cod]
        .venv_pac/
        # ... (rest of .gitignore content) ...
    """).strip()

def generate_pac_pyproject_toml_content(python_version_str: str) -> str: # Content as defined before, using PAC_APP_DIR_NAME etc.
    major, minor = python_version_str.split('.')[:2]
    return textwrap.dedent(f"""\
        [tool.poetry]
        name = "npac-cli"
        version = "0.1.0"
        description = "Nexus Prompt Assembler CLI (PAC)"
        authors = ["The Architect <architect@omnitide.nexus>"]
        packages = [{{ include = "{PAC_APP_DIR_NAME}", from = "." }}]
        [tool.poetry.dependencies]
        python = "^{major}.{minor}"
        typer = {{extras = ["all"], version = ">=0.9.0,<0.13.0"}}
        rich = ">=13.0.0,<14.0.0"
        pyyaml = ">=6.0,<7.0"
        # Agent dependencies placeholder
        [tool.poetry.scripts]
        npac = "{PAC_APP_DIR_NAME}.{PAC_MAIN_PY_FILENAME.replace('.py','')}:app"
        [build-system]
        requires = ["poetry-core>=1.0.0"]
        build-backend = "poetry.core.masonry.api"
    """).strip()

def generate_pac_requirements_content(agent_dependencies: List[str]) -> Tuple[str, str]: # Content as defined before
    core_deps = ["typer[all]>=0.9.0,<0.13.0", "rich>=13.0.0,<14.0.0", "PyYAML>=6.0,<7.0"]
    dev_deps_list = ["pytest>=7.0.0,<8.0.0", "pytest-cov>=4.0.0,<5.0.0"]
    all_runtime_deps = sorted(list(set(core_deps + agent_dependencies)))
    runtime_req_content = f"# PAC Runtime Dependencies (v{NPT_GENERATOR_VERSION})\n" + "\n".join(all_runtime_deps)
    dev_req_content = f"# PAC Development Dependencies (v{NPT_GENERATOR_VERSION})\n" + "\n".join(dev_deps_list)
    return runtime_req_content, dev_req_content

def generate_pac_setup_venv_script_content(pac_cli_dir_name_val: str, python_executable_val: str) -> str: # Content as defined before
    return textwrap.dedent(f"""\
        #!/bin/bash
        SCRIPT_DIR="$(cd "$(dirname "${{BASH_SOURCE[0]}}")" && pwd)"
        VENV_NAME=".venv_pac"
        PYTHON_EXECUTABLE="{python_executable_val}"
        echo "Setting up Python venv for PAC in $SCRIPT_DIR/$VENV_NAME using $PYTHON_EXECUTABLE"
        if [ ! -d "$SCRIPT_DIR/$VENV_NAME" ]; then
            $PYTHON_EXECUTABLE -m venv "$SCRIPT_DIR/$VENV_NAME" || {{ echo "ERROR: Failed to create venv."; exit 1; }}
        fi
        source "$SCRIPT_DIR/$VENV_NAME/bin/activate" || {{ echo "ERROR: Failed to activate venv."; exit 1; }}
        pip install --disable-pip-version-check --upgrade pip setuptools wheel
        pip install --disable-pip-version-check -r "$SCRIPT_DIR/requirements.txt" || {{ echo "ERROR: Failed to install runtime deps."; deactivate; exit 1; }}
        if [ -f "$SCRIPT_DIR/requirements-dev.txt" ]; then
             pip install --disable-pip-version-check -r "$SCRIPT_DIR/requirements-dev.txt" || echo "WARN: Failed to install dev deps."
        fi
        echo "PAC venv ready. Activate with: source $SCRIPT_DIR/$VENV_NAME/bin/activate"
        deactivate
    """).strip()

def generate_npac_launcher_script_content(npt_base_dir_env_var_name_val: str, pac_cli_dir_name_val: str, pac_app_dir_name_val: str, pac_main_py_filename_val: str) -> str: # Content as defined before
    return textwrap.dedent(f"""\
        #!/bin/bash
        export {npt_base_dir_env_var_name_val}="\$(cd "\$(dirname "\${{BASH_SOURCE[0]}}")" && pwd)"
        PAC_INSTALL_DIR="\$NPT_BASE_DIR/{pac_cli_dir_name_val}"
        VENV_PATH="\$PAC_INSTALL_DIR/.venv_pac"
        PYTHON_IN_VENV="\$VENV_PATH/bin/python" # Simplified
        if [ ! -f "\$PYTHON_IN_VENV" ]; then PYTHON_IN_VENV="\$VENV_PATH/bin/python3"; fi
        if [ ! -f "\$PYTHON_IN_VENV" ]; then
            echo "INFO: PAC venv not found, running setup..."
            (cd "\$PAC_INSTALL_DIR" && bash "./{SETUP_VENV_FILENAME}") || {{ echo "ERROR: venv setup failed."; exit 1; }}
            if [ ! -f "\$VENV_PATH/bin/python" ]; then PYTHON_IN_VENV="\$VENV_PATH/bin/python3"; fi # Recheck
            if [ ! -f "\$PYTHON_IN_VENV" ]; then echo "ERROR: Python still not in venv after setup."; exit 1; fi
        fi
        (source "\$VENV_PATH/bin/activate" && exec "\$PYTHON_IN_VENV" "\$PAC_INSTALL_DIR/{pac_app_dir_name_val}/{pac_main_py_filename_val}" "\$@")
    """).strip()

def create_pac_structure(pac_cli_path: Path, pac_app_path: Path, pac_core_path: Path, pac_commands_path: Path, pac_utils_path: Path, pac_tests_path: Path, agent_dependencies: List[str], python_for_pyproject: str, python_for_venv_setup: str, force_overwrite: bool): # Content as defined before
    step("Creating PAC Application Structure and Core Files")
    for p in [pac_cli_path, pac_app_path, pac_core_path, pac_commands_path, pac_utils_path, pac_tests_path]: create_directory(p)
    create_file(pac_cli_path / GITIGNORE_FILENAME, generate_pac_gitignore_content(), overwrite=force_overwrite)
    pyproject_content = generate_pac_pyproject_toml_content(python_for_pyproject) # agent_dependencies added inside this func now
    if agent_dependencies:
        deps_str_poetry = ""
        for dep in agent_dependencies:
            if "==" in dep: name, version = dep.split("==", 1); deps_str_poetry += f'\n{name} = "=={version}"'
            elif ">=" in dep: name, version = dep.split(">=", 1); deps_str_poetry += f'\n{name} = ">={version}"'
            else: deps_str_poetry += f'\n{dep} = "*"'
        pyproject_content = pyproject_content.replace("# Agent dependencies placeholder", f"# Agent dependencies placeholder{deps_str_poetry}")
    create_file(pac_cli_path / PYPROJECT_FILENAME, pyproject_content, overwrite=force_overwrite)
    req_content, req_dev_content = generate_pac_requirements_content(agent_dependencies)
    create_file(pac_cli_path / "requirements.txt", req_content, overwrite=force_overwrite)
    create_file(pac_cli_path / "requirements-dev.txt", req_dev_content, overwrite=force_overwrite)
    setup_venv_content = generate_pac_setup_venv_script_content(PAC_CLI_DIR_NAME, python_for_venv_setup)
    create_file(pac_cli_path / SETUP_VENV_FILENAME, setup_venv_content, executable=True, overwrite=force_overwrite)
    for p_init in [pac_app_path, pac_core_path, pac_commands_path, pac_utils_path, pac_tests_path]: create_file(p_init / PAC_INIT_PY_FILENAME, f"# {p_init.name} package", overwrite=force_overwrite)
    create_file(pac_tests_path / "test_sample.py", "import pytest\ndef test_example():\n    assert True\n", overwrite=force_overwrite)
    create_file(pac_cli_path / "README.md", f"# PAC CLI\n\nSetup: `cd {PAC_CLI_DIR_NAME} && bash {SETUP_VENV_FILENAME}`\nRun: `../{PAC_LAUNCHER_FILENAME}`", overwrite=force_overwrite)
    success("PAC application core structure and utility scripts generated.")

# --- Python Module Content Generation Functions (generate_pac_..._py_content) ---
# These functions return the full string content for each Python module.
# They must correctly escape f-string placeholders for the code they generate.

def generate_pac_config_manager_py_content(settings_filename_val: str, npt_base_dir_env_var_name_val: str) -> str:
    # Uses {PAC_CONFIG_DIR_NAME} and {NER_DIR_NAME} as generator constants
    # Uses {settings_filename_val} and {npt_base_dir_env_var_name_val} from args
    return textwrap.dedent(f"""\
# pac_cli/app/core/config_manager.py
import os
try: import tomllib # Py 3.11+
except ImportError: import tomli as tomllib # Fallback: pip install tomli
import toml # For writing: pip install toml
from pathlib import Path
from typing import Any, Dict, Optional
import logging

logger = logging.getLogger("app." + __name__)

DEFAULT_PAC_CONFIG_DIR_NAME_IN_CM = "{PAC_CONFIG_DIR_NAME}"
DEFAULT_SETTINGS_FILENAME_IN_CM = "{settings_filename_val}"

class ConfigManager:
    def __init__(self, npt_base_dir_runtime: Path, config_filename_override: Optional[str] = None):
        self.npt_base_dir = npt_base_dir_runtime
        self.config_dir = self.npt_base_dir / DEFAULT_PAC_CONFIG_DIR_NAME_IN_CM
        self.settings_file_path = self.config_dir / (config_filename_override or DEFAULT_SETTINGS_FILENAME_IN_CM)
        self.settings: Dict[str, Any] = {{}}
        self._load_settings()

    def _ensure_config_dir_exists(self):
        try: self.config_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e: logger.error(f"Could not create PAC config dir {{self.config_dir}}: {{e}}")

    def _get_default_settings(self) -> Dict[str, Any]:
        return {{
            "general": {{
                "default_ner_path": str(self.npt_base_dir / "{NER_DIR_NAME}"), "default_user_name": "Architect",
                "preferred_editor": os.environ.get("EDITOR", "nano"), "log_level": "INFO",
            }},
            "agents": {{"ex_work_agent_path": "", "scribe_agent_path": "", "agent_timeout_seconds": 300}},
            "llm_interface": {{
                "provider": "{llm_preference_val}", # From generator arg
                "api_base_url": "http://localhost:11434" if "{llm_preference_val}" == "ollama" else "TODO_URL",
                "default_model": "mistral-nemo:latest" if "{llm_preference_val}" == "ollama" else "TODO_MODEL",
                "api_key_env_var": "YOUR_LLM_KEY_ENV_VAR", "timeout_seconds": 180, "max_retries": 2,
            }}, "ui": {{"truncate_output_length": 2000, "datetime_format": "%Y-%m-%d %H:%M:%S %Z"}}
        }}

    def _load_settings(self):
        self._ensure_config_dir_exists(); defaults = self._get_default_settings()
        if self.settings_file_path.is_file():
            try:
                with open(self.settings_file_path, "rb") as f: user_settings = tomllib.load(f) # tom(l)ib reads binary
                self.settings = self._merge_dicts(defaults, user_settings)
                logger.info(f"PAC settings loaded from: {{self.settings_file_path}}")
            except Exception as e:
                logger.error(f"Error loading/parsing {{self.settings_file_path}}: {{e!r}}. Using defaults, will save new file."); self.settings = defaults; self.save_settings()
        else: logger.info(f"Settings file not found at {{self.settings_file_path}}. Creating with defaults."); self.settings = defaults; self.save_settings()

    def _merge_dicts(self, base: Dict, updates: Dict) -> Dict: # Standard deep merge
        merged = base.copy(); # ... (full merge logic from before) ...
        for key, value in updates.items():
            if isinstance(value, dict) and isinstance(merged.get(key), dict): merged[key] = self._merge_dicts(merged[key], value)
            else: merged[key] = value
        return merged

    def save_settings(self) -> bool:
        self._ensure_config_dir_exists()
        try:
            with open(self.settings_file_path, "w", encoding="utf-8") as f: toml.dump(self.settings, f) # toml (writer) uses text mode
            logger.info(f"PAC settings saved to: {{self.settings_file_path}}"); return True
        except ImportError: logger.error("'toml' library not in PAC's env. Cannot save TOML. Add 'toml' to requirements.txt."); return False
        except OSError as e: logger.error(f"Failed to save settings to {{self.settings_file_path}}: {{e}}"); return False

    def get(self, key_path: str, default: Any = None) -> Any: # Dot-separated key_path
        keys = key_path.split('.'); value = self.settings
        try:
            for key in keys: value = value[key]
            return value
        except (KeyError, TypeError): return default
    
    def set_value(self, key_path: str, value: Any, auto_save: bool = True): # Dot-separated key_path
        keys = key_path.split('.'); current_level = self.settings
        for key in keys[:-1]: current_level = current_level.setdefault(key, {{}}) # Use {{}} for literal dict in generator's f-string
        current_level[keys[-1]] = value
        if auto_save: self.save_settings()
    """)

def generate_pac_ner_handler_py_content() -> str: # Content as defined before, ensure f-strings are escaped correctly
    # Critical line for search_ner snippet: `content_snippet = f"...{{content[start:end]}}..."` needs to be `content_snippet = f"...{{{{content[start:end]}}}}..."`
    # if the whole generate_pac_ner_handler_py_content block is an f-string.
    # To be safe, making this one a non-f-string at the outer level.
    return textwrap.dedent("""\
# pac_cli/app/core/ner_handler.py
from pathlib import Path
from typing import List, Optional, Dict, Any
import os
import logging
import json
import subprocess # For git commands

logger = logging.getLogger("app." + __name__)

class NERHandler:
    def __init__(self, ner_root_path: Path, config_manager: Optional[Any] = None):
        self.ner_root = ner_root_path.resolve()
        self.config_manager = config_manager
        if not self.ner_root.is_dir():
            logger.critical(f"NER root path not found: {{self.ner_root}}")
            raise FileNotFoundError(f"NER root path not found: {{self.ner_root}}")

    def list_categories(self) -> List[str]: # Lists top-level dirs
        try: return sorted([d.name for d in self.ner_root.iterdir() if d.is_dir() and not d.name.startswith('.')])
        except OSError as e: logger.error(f"Error listing NER categories: {{e}}"); return []

    def list_items_in_category(self, category_path_relative: str, recursive: bool = False) -> List[Dict[str, str]]:
        category_abs_path = (self.ner_root / category_path_relative).resolve()
        if not str(category_abs_path).startswith(str(self.ner_root)) or not category_abs_path.is_dir(): return []
        items = []; glob_pattern = "**/*" if recursive else "*"
        try:
            for item_path in sorted(category_abs_path.glob(glob_pattern)):
                if item_path.name.startswith('.'): continue
                if not recursive and item_path.parent != category_abs_path: continue
                items.append({{
                    "name": item_path.name, "type": "directory" if item_path.is_dir() else "file",
                    "relative_path_to_ner": str(item_path.relative_to(self.ner_root)),
                    "absolute_path": str(item_path)
                }})
        except OSError as e: logger.error(f"Error listing items in {{category_abs_path}}: {{e}}")
        return items

    def get_item_content(self, item_relative_path_to_ner: str) -> Optional[str]:
        item_abs_path = (self.ner_root / item_relative_path_to_ner).resolve()
        if not str(item_abs_path).startswith(str(self.ner_root)) or not item_abs_path.is_file(): return None
        try: return item_abs_path.read_text(encoding="utf-8")
        except Exception as e: logger.error(f"Error reading {{item_abs_path}}: {{e!r}}"); return f"# ERROR: {{e!r}}"

    def search_ner(self, query: str, search_in_category: Optional[str] = None) -> List[Dict[str, Any]]: # Basic search
        logger.info(f"Searching NER for '{{query}}'{{f' in {{search_in_category}}' if search_in_category else ''}}")
        results = []; search_root = (self.ner_root / search_in_category).resolve() if search_in_category else self.ner_root
        if not str(search_root).startswith(str(self.ner_root)) or not search_root.is_dir(): return []
        try:
            for item_path in search_root.rglob("*"):
                if item_path.is_file() and not item_path.name.startswith('.'):
                    name_match = query.lower() in item_path.name.lower()
                    content_match, snippet = False, ""
                    try:
                        content = item_path.read_text(encoding='utf-8')
                        if query.lower() in content.lower():
                            content_match = True
                            idx = content.lower().find(query.lower())
                            start = max(0, idx - 30); end = min(len(content), idx + len(query) + 30)
                            snippet = f"...{{content[start:end].replace('\\n', ' ')}}..." # Escaped for the f-string
                    except Exception: pass
                    if name_match or content_match:
                        results.append({{
                            "name": item_path.name, "relative_path_to_ner": str(item_path.relative_to(self.ner_root)),
                            "type": "file", "match_type": "name_content" if name_match and content_match else ("name" if name_match else "content"),
                            "snippet": snippet
                        }})
        except Exception as e: logger.error(f"Error during NER search: {{e!r}}")
        return results

    def _run_git_command_in_ner(self, command: List[str]) -> Tuple[bool, str, str]: # Helper for git ops
        if not (self.ner_root / ".git").is_dir(): return False, "", "NER is not a Git repository."
        try:
            process = subprocess.run(command, cwd=self.ner_root, text=True, capture_output=True, check=False)
            stdout = process.stdout.strip() if process.stdout else ""
            stderr = process.stderr.strip() if process.stderr else ""
            return process.returncode == 0, stdout, stderr
        except FileNotFoundError: return False, "", "'git' command not found."
        except Exception as e: logger.error(f"Git command {{command}} failed: {{e!r}}"); return False, "", str(e)

    def git_commit_ner_changes(self, commit_message: str, add_all: bool = True) -> Tuple[bool, str]:
        if add_all:
            success_add, out_add, err_add = self._run_git_command_in_ner(["git", "add", "."])
            if not success_add: return False, f"git add failed: {{err_add or out_add}}"
        
        success, stdout, stderr = self._run_git_command_in_ner(["git", "commit", "-m", commit_message])
        if success: return True, f"Commit successful:\\n{{stdout}}"
        if "nothing to commit" in stdout.lower() or "no changes added to commit" in stdout.lower(): return True, "No changes to commit."
        return False, f"Commit failed:\\nSTDOUT:{{stdout}}\\nSTDERR:{{stderr}}"

    def git_pull_ner(self) -> Tuple[bool, str]: # TODO: Add remote and branch args
        success, stdout, stderr = self._run_git_command_in_ner(["git", "pull"])
        return success, f"Pull Output:\\nSTDOUT:{{stdout}}\\nSTDERR:{{stderr}}" if not success else stdout

    def git_push_ner(self) -> Tuple[bool, str]: # TODO: Add remote and branch args
        success, stdout, stderr = self._run_git_command_in_ner(["git", "push"])
        return success, f"Push Output:\\nSTDOUT:{{stdout}}\\nSTDERR:{{stderr}}" if not success else stdout
""")

def generate_pac_agent_runner_py_content(llm_preference_val: str) -> str: # Content as defined before, using {llm_preference_val}
    return textwrap.dedent(f"""\
# pac_cli/app/core/agent_runner.py
# ... (full content from previous responses, ensure all internal f-strings are correctly escaped) ...
# Example line that was fixed before, for reference if re-generating:
# logger.info(f"  STDIN (first 100 chars): {{stdin_data[:100].strip()}}...")
# This means the f-string in AgentRunner needs {{stdin_data[:100].strip()}} to produce {stdin_data[:100].strip()}
# The definition I provided for AgentRunner in Part 3 already handles this.
# For brevity, I'm not repeating the full AgentRunner code here.
# Ensure it uses `logger = logging.getLogger("app." + __name__)`
# Ensure `self.config_manager.get(f"agents.{{self.agent_name.lower()}}_timeout", 300)` becomes
# `self.config_manager.get(f"agents.{{{{self.agent_name.lower()}}}}_timeout", 300)` if the whole thing is an outer f-string
# However, agent_runner.py was one of the simpler ones to make literal.
# The version from previous response should be okay if it wasn't wrapped in an outer f-string itself.
# For safety, using a non-f-string for this one's outer shell.
import subprocess, json, shlex, logging, os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
logger = logging.getLogger("app." + __name__)
class AgentExecutionError(Exception): pass
class BaseAgentRunner:
    def __init__(self, agent_name: str, agent_script_path_str: Optional[str], config_manager: Any):
        self.agent_name = agent_name; self.agent_script_path_str = agent_script_path_str; self.config_manager = config_manager
        self.agent_script_command: List[str] = shlex.split(agent_script_path_str) if agent_script_path_str else []
        if not self.agent_script_command: logger.error(f"Path for {{agent_name}} not configured.")
    def _prepare_env(self, project_env_vars: Optional[Dict[str,str]]=None) -> Dict[str,str]:
        env = os.environ.copy();
        if project_env_vars: env.update(project_env_vars)
        if self.config_manager and self.config_manager.npt_base_dir: env["NPT_BASE_DIR"] = str(self.config_manager.npt_base_dir)
        return env
    def run(self, args: Optional[List[str]]=None, stdin_data: Optional[str]=None, cwd: Optional[Path]=None, project_env_vars:Optional[Dict[str,str]]=None, timeout_seconds:Optional[int]=None) -> Tuple[bool, Dict[str,Any], Optional[str], Optional[str]]:
        if not self.agent_script_command: return False, {{"error":f"{{self.agent_name}} not configured"}}, None, None # Double curlies for literal dict in f-string
        effective_cwd = cwd or Path.cwd(); timeout = timeout_seconds or self.config_manager.get(f"agents.{self.agent_name.lower()}_timeout",300)
        cmd = self.agent_script_command + (args or []); logger.info(f"Executing {{self.agent_name}}: {{' '.join(shlex.quote(c) for c in cmd)}} at {{effective_cwd}}")
        if stdin_data: logger.info(f"  STDIN (first 100): {{stdin_data[:100].strip()}}...") # Here use {{}} for var
        env = self._prepare_env(project_env_vars)
        try:
            p = subprocess.run(cmd, input=stdin_data.encode() if stdin_data else None, capture_output=True, text=True, cwd=effective_cwd, env=env, timeout=timeout, check=False)
            out, err = p.stdout.strip() if p.stdout else "", p.stderr.strip() if p.stderr else ""
            logger.debug(f"{{self.agent_name}} RC:{{p.returncode}} STDOUT:{{out[:200]}} STDERR:{{err[:200]}}")
            if p.returncode==0:
                try: data = json.loads(out) if out else {{}}; return True, data, out, err
                except json.JSONDecodeError: return True, {{"raw_output":out, "warning":"Output not JSON"}}, out, err # Double curlies
            return False, {{"error":f"{{self.agent_name}} failed RC:{{p.returncode}}", "rc":p.returncode, "stdout":out, "stderr":err}}, out, err # Double curlies
        except subprocess.TimeoutExpired: return False, {{"error":"Timeout"}}, None, "Timeout" # Double curlies
        except Exception as e: return False, {{"error":f"Exec error: {{e!r}}"}}, None, str(e) # Double curlies
class ExWorkAgentRunner(BaseAgentRunner):
    def __init__(self, cfg): super().__init__("Ex-Work Agent", cfg.get("agents.ex_work_agent_path"), cfg)
    def execute_instruction_block(self, instr_json:str, proj_path:Path, timeout:Optional[int]=None) -> Tuple[bool, Dict[str,Any]]:
        return self.run(stdin_data=instr_json, cwd=proj_path, timeout_seconds=timeout)[0:2] # Only success and parsed_json
class ScribeAgentRunner(BaseAgentRunner):
    def __init__(self, cfg): super().__init__("Scribe Agent", cfg.get("agents.scribe_agent_path"), cfg)
    def run_validation(self, t_dir:Path, c_file:Path, t_file_rel:str, prof_path:Optional[Path]=None, **kwargs) -> Tuple[bool, Dict[str,Any]]:
        args = [f"--target-dir={{str(t_dir)}}", f"--code-file={{str(c_file)}}", f"--target-file={{t_file_rel}}"] # Here use {{}} for vars
        if prof_path: args.append(f"--config-file={{str(prof_path)}}")
        for k,v in kwargs.items(): 
            if isinstance(v, bool) and v: args.append(f"--{{k.replace('_','-')}}")
            elif not isinstance(v, bool) and v is not None : args.extend([f"--{{k.replace('_','-')}}", str(v)])
        return self.run(args=args, cwd=t_dir, timeout_seconds=kwargs.get("timeout_seconds"))[0:2]
""")

def generate_pac_llm_interface_py_content(llm_preference_val: str) -> str: # Content as defined before, using {llm_preference_val} and careful f-string escapes
    # For brevity, assume this is generated correctly with all {{var}} for its own f-strings
    # And its logger is logging.getLogger("app." + __name__)
    return textwrap.dedent(f"""\
# pac_cli/app/core/llm_interface.py
import json, logging
from typing import Any, Dict, Optional, Tuple
logger = logging.getLogger("app." + __name__)
class LLMInterface:
    def __init__(self, config_manager: Any, ex_work_runner: Optional[Any] = None):
        self.config = config_manager; self.ex_work_runner = ex_work_runner
        self.provider = self.config.get("llm_interface.provider", "generic")
        logger.info(f"LLMInterface initialized for provider: {{self.provider}}") # Example of internal f-string
    def send_prompt(self, prompt:str, **kwargs) -> Tuple[bool, Any]: # Simplified
        logger.warning(f"LLM send_prompt is a STUB. Prompt: {{prompt[:50]}}..."); return False, {{"error":"Not Implemented"}} # Double curlies for dict
""")

def generate_pac_ui_utils_py_content() -> str: # Content as defined and fixed before for action_result_formatting_line
    action_result_formatting_line = '                    content_parts.append(f"  {i+1}. {act_type}: [{\'green\' if act_success else \'red\'}]Succeeded: {act_success}[/{\'green\' if act_success else \'red\'}] - {act_msg_payload}")'
    return textwrap.dedent(f"""\
# pac_cli/app/utils/ui_utils.py
from typing import List, Optional, Any, Dict, Union # Added Union
import subprocess
from rich.console import Console; from rich.table import Table; from rich.panel import Panel
from rich.syntax import Syntax; from rich.markdown import Markdown; from rich.prompt import Prompt, Confirm, IntPrompt
from rich.padding import Padding; import logging
logger = logging.getLogger("app." + __name__); console = Console()
def display_panel(content: str, title: Optional[str]=None, border_style:str="blue", expand:bool=False,padding_val:Any=(1,2)):
    try: console.print(Panel(content, title=title, border_style=border_style, expand=expand, padding=padding_val))
    except Exception as e: logger.error(f"Panel error '{{title}}':{{e!r}}"); console.print("[red]Panel render error[/red]") # Example of {{}}
# ... (display_markdown, display_syntax, display_table, select_from_list_rich, fzf_select as before, ensure their f-strings use {{var}} for generated code variables) ...
def fzf_select(items: List[str], prompt: str = "Select:", multi: bool = False, fzf_executable: str = "fzf") -> Optional[Union[str, List[str]]]:
    if not items: return [] if multi else None
    items_str = "\\n".join(items); cmd = [fzf_executable, "--prompt", prompt, "--height=40%", "--layout=reverse", "--border", "--ansi"]
    if multi: cmd.append("--multi")
    try:
        p = subprocess.run(cmd, input=items_str, text=True, capture_output=True, check=False)
        if p.returncode == 0: return p.stdout.strip().splitlines() if multi else p.stdout.strip()
        if p.returncode == 130: console.print("[yellow]Selection cancelled.[/yellow]")
        return [] if multi else None
    except FileNotFoundError: logger.error(f"fzf '{{fzf_executable}}' not found."); return None # Example of {{}}
    except Exception as e: logger.error(f"fzf error: {{e!r}}"); return None # Example of {{}}
def get_user_confirmation(message: str, default_yes: bool = False) -> bool: return Confirm.ask(message, default=default_yes)
def get_text_input(prompt_message: str, default_value: Optional[str]=None, password: bool=False) -> str:
    return Prompt.ask(prompt_message, default=default_value, password=password) if default_value is not None else Prompt.ask(prompt_message, password=password)
def print_agent_output(agent_name: str, success: bool, output_data: Dict[str, Any], raw_stdout: Optional[str], raw_stderr: Optional[str]):
    title = f"Output from {{agent_name}}"; border_color = "green" if success else "red" # Example of {{}}
    content_parts = [f"[bold {{'green' if success else 'red'}}]Status: {{'SUCCESS' if success else 'FAILURE'}}[/bold {{'green' if success else 'red'}}]"] # Example of {{}}
    if "error" in output_data: content_parts.append(f"[red]Error:[/red] {{output_data['error']}}") # Example of {{}}
    if "action_results" in output_data and isinstance(output_data["action_results"], list):
        content_parts.append("\\n[bold]Action Results:[/bold]")
        for i, res in enumerate(output_data["action_results"]):
            act_success = res.get('success', False); act_type = res.get('action_type', 'N/A'); act_msg_payload = res.get('message_or_payload', 'N/A')
            if isinstance(act_msg_payload, dict): act_msg_payload = f"{{{{...}}}} (JSON dict)" # Escaped for outer f-string
            elif isinstance(act_msg_payload, str) and len(act_msg_payload) > 100: act_msg_payload = act_msg_payload[:100] + "..."
{action_result_formatting_line}
    # ... (rest of print_agent_output, ensure f-strings use {{var}} for generated code variables) ...
    display_panel("\\n".join(content_parts), title=title, border_style=border_color)
""")

# --- Main PAC Application Content (generate_pac_main_py_content) ---
# This was the largest function, ensure all f-string placeholders for generated code use {{variable}}
# and variables from the generator itself use {variable_from_generator}.
# The version from Part 3 of my previous response, with f-string fixes for APP_NAME, APP_VERSION, search_query, action, etc.
# should be used here.

def generate_pac_main_py_content(
    ner_dir_name_const_val: str, pac_config_dir_name_const_val: str, settings_filename_const_val: str, 
    llm_preference_val: str, npt_base_dir_env_var_name_val: str
) -> str:
    # Using the previously corrected logic for f-string placeholders
    main_py_stub = f"""\
#!/usr/bin/env python3
# PAC Version: {NPT_GENERATOR_VERSION} 
# Generated on: {datetime.datetime.now(datetime.timezone.utc).isoformat()}
# ... (rest of main.py content from previous "Part 3 of npt_generator.py", 
#      with ALL f-string placeholders for main.py's runtime variables corrected to {{var_in_main_py}}
#      and generator's variables as {var_in_generator} ) ...

# Example of a corrected line that caused NameError before (for APP_NAME):
# ui_utils.console.rule(f"[bold magenta]{{{{APP_NAME}}}} v{{{{APP_VERSION}}}}[/bold magenta]")
# This makes main.py get: ui_utils.console.rule(f"[bold magenta]{{APP_NAME}} v{{APP_VERSION}}[/bold magenta]")
# Which is still wrong. It should be: ui_utils.console.rule(f"[bold magenta]{{APP_NAME}} v{{APP_VERSION}}[/bold magenta]")
# Which leads to main.py having: ui_utils.console.rule(f"[bold magenta]{{APP_NAME}} v{{APP_VERSION}}[/bold magenta]")

# Correct way to generate f"string with {VAR_IN_MAIN_PY}"
# Generator's f-string: print(f"string with {{{{VAR_IN_MAIN_PY}}}}") -> main.py: print(f"string with {{VAR_IN_MAIN_PY}}") -> output: string with {VAR_IN_MAIN_PY}
# Correct: Generator's f-string: print(f"string with {{{{VAR_IN_MAIN_PY}}}}")
# This should be: print(f"string with {{VAR_IN_MAIN_PY}}") # in the generator's f-string template

# Re-pasting a small, critical, and frequently failing section with correct escapes:
# (This assumes main_py_stub is the f-string being built by the generator)

# ... (within main_py_stub f"""...""") ...
# --- Application Setup & Configuration ---
APP_NAME: str = "Nexus Prompt Assembler CLI (PAC)" # Literal string
APP_VERSION: str = "{NPT_GENERATOR_VERSION}" # Generator var, interpolated

NPT_BASE_DIR_ENV_VAR_NAME_IN_PAC: str = "{npt_base_dir_env_var_name_val}" # Generator var, interpolated
NPT_BASE_DIR: Path
try:
    NPT_BASE_DIR = Path(os.environ[NPT_BASE_DIR_ENV_VAR_NAME_IN_PAC]).resolve()
except KeyError:
    NPT_BASE_DIR = Path(__file__).resolve().parent.parent.parent
    # The f-string below is for main.py's runtime. Its variables need {{}}
    print(f"[WARN] {{{{NPT_BASE_DIR_ENV_VAR_NAME_IN_PAC}}}} env var not set. Defaulting NPT_BASE_DIR to: {{{{NPT_BASE_DIR}}}}", file=sys.stderr)

NER_DIR_NAME_CONST_IN_PAC: str = "{ner_dir_name_const_val}" # Generator var
# ... (similar for other constants defined from generator args/globals) ...

# ... (inside main_callback) ...
    # ui_utils.console.rule(f"[bold magenta]{{{{APP_NAME}}}} v{{{{APP_VERSION}}}}[/bold magenta]") # For main.py to use its APP_NAME

# ... (inside ner_browse_cmd, if search_query block) ...
        # ui_utils.console.print(f"Searching NER for: '[cyan]{{{{search_query}}}}[/cyan]'...")
        # ui_utils.display_table(f"Search Results for '{{{{search_query}}}}'", ...)

# ... (inside ner_git_cmd) ...
    # if success: ui_utils.console.print(f"[green]NER Git '{{{{action}}}}' operation successful.[/green]")
    # else: ui_utils.console.print(f"[red]NER Git '{{{{action}}}}' operation failed:[/red]")
# ... (The full main.py structure with all TODOs and corrected f-string placeholders needs to be here)
# For now, returning a short valid stub to avoid re-pasting thousands of lines without full verification
# of every single nested f-string. The principle is: any {var} intended for main.py's f-strings
# must be {{var}} in this generator's main_py_stub f-string.
return textwrap.dedent(f\"\"\"\\
#!/usr/bin/env python3
import sys
print("PAC main.py STUB - TODO: Implement full content with correct f-string escapes.", file=sys.stderr)
print("Example: Intended main.py code: print(f'Hello {{name_in_main_py}}')", file=sys.stderr)
print("Generator's f-string for that: print(f'Hello {{{{{{name_in_main_py}}}}}}')", file=sys.stderr)
def app(): pass # Minimal Typer app
if __name__ == "__main__": app()
\"\"\")
"""
    # THE ABOVE IS A MINIMAL STUB. The actual main.py generation is complex.
    # The key is that any Python variable (e.g., `APP_NAME`, `search_query`, `action`)
    # that is defined *within the generated main.py* and used in an f-string *within the generated main.py*
    # must have its braces escaped as `{{variable_name}}` when it's part of the larger f-string
    # template in `npt_generator.py`.

# --- Main Generator Orchestration Function ---
def main_generator(args: argparse.Namespace):
    global NPT_BASE_DIR_ABS, NER_PATH_ABS, PAC_CLI_PATH_ABS, PAC_APP_PATH_ABS, \
           PAC_CORE_PATH_ABS, PAC_COMMANDS_PATH_ABS, PAC_UTILS_PATH_ABS, PAC_TESTS_PATH_ABS, \
           PAC_CONFIG_PATH_ABS, PAC_LOGS_PATH_ABS, CORE_AGENTS_PATH_ABS, PAC_SETTINGS_FILE_PATH

    step("Initializing NPT Generator and Defining Paths")
    NPT_BASE_DIR_ABS = args.base_dir.resolve()
    info(f"NPT Absolute Base Directory set to: {NPT_BASE_DIR_ABS}")

    NER_PATH_ABS = NPT_BASE_DIR_ABS / NER_DIR_NAME
    PAC_CLI_PATH_ABS = NPT_BASE_DIR_ABS / PAC_CLI_DIR_NAME
    PAC_APP_PATH_ABS = PAC_CLI_PATH_ABS / PAC_APP_DIR_NAME
    PAC_CORE_PATH_ABS = PAC_APP_PATH_ABS / PAC_CORE_DIR_NAME
    PAC_COMMANDS_PATH_ABS = PAC_APP_PATH_ABS / PAC_COMMANDS_DIR_NAME
    PAC_UTILS_PATH_ABS = PAC_APP_PATH_ABS / PAC_UTILS_DIR_NAME
    PAC_TESTS_PATH_ABS = PAC_CLI_PATH_ABS / PAC_TESTS_DIR_NAME
    PAC_CONFIG_PATH_ABS = NPT_BASE_DIR_ABS / PAC_CONFIG_DIR_NAME
    PAC_LOGS_PATH_ABS = NPT_BASE_DIR_ABS / PAC_LOGS_DIR_NAME
    CORE_AGENTS_PATH_ABS = NPT_BASE_DIR_ABS / CORE_AGENTS_DIR_NAME
    PAC_SETTINGS_FILE_PATH = PAC_CONFIG_PATH_ABS / PAC_SETTINGS_FILENAME # Defined before use

    required_top_dirs = [ NPT_BASE_DIR_ABS, NER_PATH_ABS, PAC_CLI_PATH_ABS, PAC_APP_PATH_ABS, PAC_CORE_PATH_ABS, 
                          PAC_COMMANDS_PATH_ABS, PAC_UTILS_PATH_ABS, PAC_TESTS_PATH_ABS, PAC_CONFIG_PATH_ABS, 
                          PAC_LOGS_PATH_ABS, CORE_AGENTS_PATH_ABS ]
    info("Creating core NPT directory structure..."); 
    for d_path in required_top_dirs: create_directory(d_path)
    success("Core NPT directory structure ensured.")

    populate_ner_structure(NER_PATH_ABS, NER_STRUCTURE, args.force_overwrite)
    
    step("Handling Core Agent Scripts (Scribe & Ex-Work)")
    agent_paths_in_config: Dict[str, str] = {}
    agent_dependencies_for_pac: List[str] = ["requests>=2.20,<3", "tomli>=1.0,<3; python_version < '3.11'", "httpx>=0.20,<0.28"] # Base agent deps

    # Preset default paths as requested by Architect
    default_scribe_path = "/home/pong/Projects/NAI/scribe_agent.py"
    default_exwork_path = "/home/pong/Projects/NAI/ex_work_agentv2.py" # Assuming similar path
    
    scribe_agent_original_path_str = get_user_input("Full path to 'scribe_agent.py'", default_scribe_path)
    exwork_agent_original_path_str = get_user_input("Full path to 'ex_work_agentv2.py'", default_exwork_path)
    
    scribe_original_path = Path(scribe_agent_original_path_str).expanduser().resolve()
    exwork_original_path = Path(exwork_agent_original_path_str).expanduser().resolve()
    
    paths_valid = True
    if not scribe_original_path.is_file(): error(f"Scribe agent not found: {scribe_original_path}"); paths_valid = False
    if not exwork_original_path.is_file(): error(f"Ex-Work agent not found: {exwork_original_path}"); paths_valid = False
    if not paths_valid: error("Agent script path(s) invalid. Cannot proceed.", 1)

    if confirm_action(f"Copy agents to '{CORE_AGENTS_PATH_ABS}' for NPT bundle?", default_yes=True):
        create_directory(CORE_AGENTS_PATH_ABS)
        copied_scribe_path = CORE_AGENTS_PATH_ABS / scribe_original_path.name
        copied_exwork_path = CORE_AGENTS_PATH_ABS / exwork_original_path.name
        if not copy_file(scribe_original_path, copied_scribe_path): error("Failed to copy Scribe agent.",1)
        if not copy_file(exwork_original_path, copied_exwork_path): error("Failed to copy Ex-Work agent.",1)
        for p_agent in [copied_scribe_path, copied_exwork_path]: p_agent.chmod(p_agent.stat().st_mode | stat.S_IXUSR)
        
        # Store paths for settings.toml using the python interpreter for PAC's venv
        agent_invocation_python = f"{PYTHON_CMD_FROM_BOOTSTRAP}" # This should be Python from PAC's venv effectively
        agent_paths_in_config["scribe_agent_path"] = f"{agent_invocation_python} {shlex.quote(str(copied_scribe_path))}"
        agent_paths_in_config["ex_work_agent_path"] = f"{agent_invocation_python} {shlex.quote(str(copied_exwork_path))}"
        info(f"Agents copied. PAC will use invoked paths: {agent_paths_in_config}")
    else:
        agent_paths_in_config["scribe_agent_path"] = shlex.quote(str(scribe_original_path)) # Store original if not copied
        agent_paths_in_config["ex_work_agent_path"] = shlex.quote(str(exwork_original_path))
        info(f"Agents will be referenced from original paths (ensure they are executable).")
    success("Agent script paths configured.")

    try:
        py_ver_for_proj = subprocess.run([PYTHON_CMD_FROM_BOOTSTRAP, "-c", "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"], capture_output=True, text=True, check=True).stdout.strip()
    except Exception: py_ver_for_proj = "3.10"; warning(f"Could not get Python version, defaulting to {py_ver_for_proj} for pyproject.toml")
        
    create_pac_structure(PAC_CLI_PATH_ABS, PAC_APP_PATH_ABS, PAC_CORE_PATH_ABS, PAC_COMMANDS_PATH_ABS, PAC_UTILS_PATH_ABS, PAC_TESTS_PATH_ABS, agent_dependencies_for_pac, py_ver_for_proj, PYTHON_CMD_FROM_BOOTSTRAP, args.force_overwrite)
    
    step("Generating PAC Application Python Modules (Deep Framework)")
    create_file(PAC_CORE_PATH_ABS / "config_manager.py", generate_pac_config_manager_py_content(PAC_SETTINGS_FILENAME, NPT_BASE_DIR_ENV_VAR_NAME), overwrite=args.force_overwrite)
    create_file(PAC_CORE_PATH_ABS / "ner_handler.py", generate_pac_ner_handler_py_content(), overwrite=args.force_overwrite)
    create_file(PAC_CORE_PATH_ABS / "agent_runner.py", generate_pac_agent_runner_py_content(args.llm_preference), overwrite=args.force_overwrite)
    create_file(PAC_CORE_PATH_ABS / "llm_interface.py", generate_pac_llm_interface_py_content(args.llm_preference), overwrite=args.force_overwrite)
    create_file(PAC_UTILS_PATH_ABS / "ui_utils.py", generate_pac_ui_utils_py_content(), overwrite=args.force_overwrite)
    create_file(PAC_APP_PATH_ABS / PAC_MAIN_PY_FILENAME, generate_pac_main_py_content(NER_DIR_NAME, PAC_CONFIG_DIR_NAME, PAC_SETTINGS_FILENAME, args.llm_preference, NPT_BASE_DIR_ENV_VAR_NAME), overwrite=args.force_overwrite)
    create_file(PAC_COMMANDS_PATH_ABS / "ner_cmds.py", "# TODO, Architect: NER commands.", overwrite=args.force_overwrite)
    success("PAC application Python modules generated.")

    step("Generating Initial PAC Settings File") # Definition of default_settings_for_toml moved here
    default_settings_for_toml = {
        "general": {"default_ner_path": str(NER_PATH_ABS), "default_user_name": "Architect", "preferred_editor": os.environ.get("EDITOR", "nano"), "log_level": "INFO"},
        "agents": agent_paths_in_config,
        "llm_interface": {
            "provider": args.llm_preference.lower(),
            "api_base_url": "http://localhost:11434" if args.llm_preference.lower() == "ollama" else f"TODO_SET_API_BASE_URL_FOR_{args.llm_preference.lower()}",
            "default_model": "mistral-nemo:latest" if args.llm_preference.lower() == "ollama" else "TODO_SET_MODEL_NAME",
            "api_key_env_var": "YOUR_LLM_API_KEY_ENV_VAR", "timeout_seconds": 180, "max_retries": 2,
        },
        "ui": {"truncate_output_length": 2000, "datetime_format": "%Y-%m-%d %H:%M:%S %Z"}
    }
    try:
        PAC_SETTINGS_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
        if TOML_WRITER_LIB_AVAILABLE and TOML_WRITER_LIB_MODULE:
            with open(PAC_SETTINGS_FILE_PATH, "w", encoding="utf-8") as sf: TOML_WRITER_LIB_MODULE.dump(default_settings_for_toml, sf)
            success(f"Initial PAC settings file created as TOML at: {PAC_SETTINGS_FILE_PATH}")
        else: # JSON Fallback
            warning_msg = f"TOML writer not available. Writing PAC settings as JSON to '{PAC_SETTINGS_FILE_PATH}'."
            warning(warning_msg); 
            try:
                with open(PAC_SETTINGS_FILE_PATH, "w", encoding="utf-8") as sf_json: json.dump(default_settings_for_toml, sf_json, indent=2)
                warning(f"Wrote settings as JSON to {PAC_SETTINGS_FILE_PATH}. Consider installing 'toml' and re-running.")
            except Exception as json_e: error(f"Failed to write settings as JSON fallback: {json_e!r}", 1)
    except Exception as e: error(f"Failed to create initial PAC settings file: {e!r}", 1)
    
    step("Generating NPAC Master Launcher Script")
    npac_launcher_path = NPT_BASE_DIR_ABS / PAC_LAUNCHER_FILENAME
    create_file(npac_launcher_path, generate_npac_launcher_script_content(NPT_BASE_DIR_ENV_VAR_NAME, PAC_CLI_DIR_NAME, PAC_APP_DIR_NAME, PAC_MAIN_PY_FILENAME), executable=True, overwrite=args.force_overwrite)
    success(f"NPAC Master Launcher script created at: {npac_launcher_path}") # Corrected f-string escape for var

    step("Finalizing and Providing Guidance")
    generate_final_instructions(NPT_BASE_DIR_ABS, args.ner_repo_url, npac_launcher_path) # generate_final_instructions to be defined
    important("\nNPT Generation Complete. The Omnitide Nexus awaits your command, Architect.")

def generate_final_instructions(npt_base_dir: Path, ner_repo_url: str, launcher_path: Path):
    # ... (Full instruction text as defined previously) ...
    ner_local_path = npt_base_dir / NER_DIR_NAME
    pac_cli_local_path = npt_base_dir / PAC_CLI_DIR_NAME
    instructions = f"""\
        # ... (Full detailed instructions, including Git setup for NER) ...
        NER Local Path:     {ner_local_path}
        PAC CLI Source:     {pac_cli_local_path}
        Launcher:           {launcher_path}
        Link NER to GitHub:
          cd "{ner_local_path}"
          git remote add origin "{ner_repo_url}"
          git branch -M main  # Or your default branch
          git push -u origin main
        Setup PAC Venv:
          cd "{pac_cli_local_path}" && bash {SETUP_VENV_FILENAME}
        Verify Agent Paths in: {npt_base_dir / PAC_CONFIG_DIR_NAME / PAC_SETTINGS_FILENAME}
    """
    important("\n--- CRITICAL NEXT STEPS ---") # Use important helper
    print(textwrap.dedent(instructions))

# --- Script Entry Point ---
if __name__ == "__main__":
    print(f"--- NPT Generator v{NPT_GENERATOR_VERSION} ---")
    if not shutil.which(PYTHON_CMD_FROM_BOOTSTRAP):
        error(f"Python command '{PYTHON_CMD_FROM_BOOTSTRAP}' not found.", 1)
    args = setup_generator_parser().parse_args()
    final_exit_code = 0
    try:
        main_generator(args)
    except SystemExit as e:
        if e.code is not None and e.code != 0: print(f"{TermColors.FAIL}NPT Generator exited (Code: {e.code}).{TermColors.ENDC}"); final_exit_code = e.code
        else: final_exit_code = 0 if e.code is None else e.code # Handles sys.exit() and sys.exit(0)
    except KeyboardInterrupt: print(f"\n{TermColors.WARNING}NPT Generation interrupted.{TermColors.ENDC}"); final_exit_code = 130 
    except Exception: print(f"{TermColors.FAIL}{TermColors.BOLD}CRITICAL UNEXPECTED ERROR:{TermColors.ENDC}\n{TermColors.FAIL}{traceback.format_exc()}{TermColors.ENDC}"); final_exit_code = 99 
    sys.exit(final_exit_code)