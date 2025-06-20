#!/usr/bin/env python3
# Agent Ex-Work: Executes structured JSON commands with self-improvement features.
# Version: 2.3 (Apex Edition - Fully Developed)

import base64
import datetime
import json
import logging
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import requests

# Ensure pycryptodomex is installed for ENCRYPT_DECRYPT_TARGET
try:
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import pad, unpad

    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    # Logging a warning if Crypto is not available can be done when handler is called.

# --- Basic Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [ExWork-v2.3] [%(levelname)-7s] %(module)s:%(lineno)d - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stderr)],
)
logger = logging.getLogger("AgentExWorkV2.3")

# --- Configuration ---
# PROJECT_ROOT will be determined by CWD where agent is run, or overridden by CLI/orchestrator.
# The bootstrap script will ensure this agent is called with omniapp_root as CWD.
PROJECT_ROOT = Path.cwd().resolve()
HISTORY_FILE_NAME = ".exwork_history.jsonl"  # Name, will be joined with PROJECT_ROOT
HISTORY_FILE = PROJECT_ROOT / HISTORY_FILE_NAME

# Ollama settings can be overridden by ExWork task parameters
DEFAULT_OLLAMA_ENDPOINT_BASE = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
DEFAULT_OLLAMA_MODEL = os.environ.get(
    "OLLAMA_MODEL",
    "mistral-nemo:12b-instruct-2407-q4_k_m",  # Example, ensure this model is available
)
# Tool paths - use shutil.which for dynamic lookup
# These are defaults, can be overridden if needed by specific environment or config.
RUFF_EXECUTABLE_NAME = "ruff"
NMAP_EXECUTABLE_NAME = "nmap"
SYSCTL_EXECUTABLE_NAME = "sysctl"
IP_ROUTE_EXECUTABLE_NAME = "ip"  # For 'ip route' on Linux
MODPROBE_EXECUTABLE_NAME = "modprobe"
PATCH_EXECUTABLE_NAME = "patch"

# --- Global State ---
_pending_signoffs: Dict[str, Dict[str, Any]] = (
    {}
)  # In-memory, for single run. Orchestrator handles persistent state.

# --- Action Handler Registration ---
ACTION_HANDLERS: Dict[str, Callable[[Dict, Path, str], Tuple[bool, Any]]] = {}


def handler(name: str):
    """Decorator to register action handlers."""

    def decorator(func: Callable[[Dict, Path, str], Tuple[bool, Any]]):
        ACTION_HANDLERS[name] = func
        logger.debug(f"Registered action handler for: {name}")
        return func

    return decorator


# --- Helper Functions ---


def resolve_path(
    project_root: Path,
    requested_path: str,
    ensure_exists: bool = False,
    ensure_is_file: bool = False,
    ensure_is_dir: bool = False,
) -> Optional[Path]:
    """
    Safely resolves a path relative to the project root. Prevents directory traversal.
    Can optionally ensure the path exists, is a file, or is a directory.
    """
    try:
        # Normalize slashes for cross-platform compatibility before joining
        normalized_req_path = os.path.normpath(requested_path.replace("\\", "/"))

        # Disallow paths starting with / or C: etc. unless they are IDENTICAL to project_root
        # and disallow '..' at the start of a relative path to prevent trivial escapes before join.
        if (
            normalized_req_path.startswith("/")
            or (len(normalized_req_path) > 1 and normalized_req_path[1] == ":")
        ) and not str(Path(normalized_req_path).resolve()).startswith(
            str(project_root.resolve())
        ):
            if str(Path(normalized_req_path).resolve()) == str(
                project_root.resolve()
            ):  # Allow if it's the project root itself
                pass
            else:
                logger.error(
                    f"Security: Absolute path '{requested_path}' provided that is not within project root '{project_root}'."
                )
                return None

        if (
            normalized_req_path.startswith("..")
            or "/../" in normalized_req_path
            or "\\..\\" in normalized_req_path
        ):
            # Further check after resolving to be sure
            pass

        # Create a Path object for the requested path
        relative_p = Path(normalized_req_path)

        # Resolve the absolute path
        # If relative_p is already absolute, project_root is ignored by the / operator.
        # If relative_p is relative, it's joined with project_root.
        abs_path = (project_root / relative_p).resolve()

        # Security check: Ensure the resolved path is within the project_root
        if not (
            abs_path == project_root
            or str(abs_path).startswith(str(project_root) + os.sep)
        ):
            logger.error(
                f"Security: Path '{requested_path}' resolved to '{abs_path}', which is outside the project root '{project_root}'."
            )
            return None

        if ensure_exists and not abs_path.exists():
            logger.error(
                f"Validation: Resolved path '{abs_path}' (from '{requested_path}') does not exist."
            )
            return None
        if ensure_is_file and not abs_path.is_file():
            logger.error(
                f"Validation: Resolved path '{abs_path}' (from '{requested_path}') is not a file."
            )
            return None
        if ensure_is_dir and not abs_path.is_dir():
            logger.error(
                f"Validation: Resolved path '{abs_path}' (from '{requested_path}') is not a directory."
            )
            return None

        return abs_path
    except Exception as e:
        logger.error(
            f"Error resolving path '{requested_path}' relative to '{project_root}': {e}",
            exc_info=True,
        )
        return None


def log_execution_history(record: Dict[str, Any]):
    """Appends an execution record to the history file."""
    global HISTORY_FILE  # Ensure we're using the correctly initialized HISTORY_FILE
    record_final = {
        "timestamp_iso": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "action_name": record.get("action_name", "UNKNOWN_ACTION"),
        "command_str_for_log": record.get(
            "command_str_for_log", "N/A"
        ),  # Renamed for clarity
        "cwd": str(record.get("cwd", PROJECT_ROOT)),
        "success": record.get("success", False),
        "exit_code": record.get("exit_code", -1),
        # Ensure snippets are strings before slicing
        "stdout_snippet": str(record.get("stdout_snippet", ""))[:500]
        + ("..." if len(str(record.get("stdout_snippet", ""))) > 500 else ""),
        "stderr_snippet": str(record.get("stderr_snippet", ""))[:500]
        + ("..." if len(str(record.get("stderr_snippet", ""))) > 500 else ""),
        "message_or_payload": record.get(
            "message_or_payload", ""
        ),  # Renamed for consistency
        "duration_s": round(record.get("duration_s", 0.0), 3),
        "step_id_from_block": record.get("step_id_from_block", "N/A"),  # Renamed
        "action_specific_params": record.get("action_specific_params", {}),  # Renamed
    }
    try:
        with open(HISTORY_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(record_final) + "\n")
    except Exception as e:
        logger.error(f"Failed to log execution history to {HISTORY_FILE}: {e}")


def _run_subprocess(
    command_list: List[str],  # Changed to enforce list for clarity and shlex usage
    cwd: Path,
    action_name: str,
    action_params: Dict,  # For logging
    step_id_from_block: str,  # For logging
    timeout_seconds: int = 300,
    shell_mode: bool = False,  # Explicitly named
    custom_env: Optional[Dict[str, str]] = None,  # Explicitly named
) -> Tuple[
    bool, str, str, str, int
]:  # success, user_message, stdout, stderr, exit_code
    """
    Helper to run subprocess. Now returns exit_code as well.
    Command should be a list of arguments unless shell_mode is True.
    """
    start_time = time.time()

    # For logging, create a string representation of the command
    if shell_mode:
        # If shell_mode is True, command_list is expected to be a single command string
        if (
            not isinstance(command_list, list)
            or len(command_list) != 1
            or not isinstance(command_list[0], str)
        ):
            logger.error(
                "Internal Error: _run_subprocess called with shell_mode=True but command_list is not a single string in a list."
            )
            # This is an internal error, so we make it fail hard to catch during dev.
            # In a production agent, might return a failure tuple.
            raise ValueError(
                "For shell_mode=True, command_list must be a list containing a single command string."
            )
        command_str_for_log = command_list[0]
        actual_command_to_run = (
            command_str_for_log  # Pass string to subprocess.run when shell=True
        )
    else:
        # For shell_mode=False, command_list is a list of executable and args
        if not command_list or not all(isinstance(c, str) for c in command_list):
            logger.error(
                "Internal Error: _run_subprocess called with shell_mode=False but command_list is not a list of strings or is empty."
            )
            raise ValueError(
                "For shell_mode=False, command_list must be a non-empty list of strings."
            )
        command_str_for_log = " ".join(shlex.quote(c) for c in command_list)
        actual_command_to_run = (
            command_list  # Pass list to subprocess.run when shell=False
        )

    logger.info(
        f"Running ({action_name}): {command_str_for_log} in CWD='{cwd}'{' (shell_mode=True)' if shell_mode else ''}"
    )

    stdout_str = ""
    stderr_str = ""
    process_exit_code = -1  # Default for unexpected errors before process runs
    user_message = ""  # For user-facing summary

    effective_env = os.environ.copy()
    if custom_env:
        effective_env.update(custom_env)

    try:
        # Ensure cwd exists and is a directory
        if not cwd.is_dir():
            err_msg = f"Working directory '{cwd}' does not exist or is not a directory."
            logger.error(err_msg)
            # Log history before returning failure
            log_execution_history(
                {
                    "action_name": action_name,
                    "command_str_for_log": command_str_for_log,
                    "cwd": str(cwd),
                    "success": False,
                    "exit_code": -5,  # Specific code for CWD error
                    "stdout_snippet": "",
                    "stderr_snippet": err_msg,
                    "message_or_payload": err_msg,
                    "duration_s": time.time() - start_time,
                    "step_id_from_block": step_id_from_block,
                    "action_specific_params": action_params,
                }
            )
            return False, err_msg, "", err_msg, -5

        result = subprocess.run(
            actual_command_to_run,  # This is either a string (shell=True) or list (shell=False)
            cwd=cwd,
            capture_output=True,
            text=True,  # Decodes output as text
            check=False,  # We handle exit codes manually
            timeout=timeout_seconds,
            encoding="utf-8",  # Explicit encoding
            errors="replace",  # Replace undecodable characters
            shell=shell_mode,
            env=effective_env,
        )
        stdout_str = result.stdout.strip() if result.stdout else ""
        stderr_str = result.stderr.strip() if result.stderr else ""
        process_exit_code = result.returncode

        if process_exit_code == 0:
            success = True
            user_message = f"Action '{action_name}' completed successfully."
            logger.info(f"Finished {action_name}. Exit Code: {process_exit_code}")
        else:
            success = False
            user_message = (
                f"Action '{action_name}' failed with Exit Code: {process_exit_code}."
            )
            logger.error(
                f"Finished {action_name}. Exit Code: {process_exit_code}. Stderr: {stderr_str[:300]}..."
            )  # Log part of stderr

    except subprocess.TimeoutExpired:
        success = False
        process_exit_code = -2  # Using negative codes for agent-detected issues
        user_message = (
            f"Action '{action_name}' timed out after {timeout_seconds} seconds."
        )
        stderr_str = f"TimeoutExpired: Command exceeded {timeout_seconds}s limit."  # Override stderr
        logger.error(user_message)
    except FileNotFoundError:
        # This occurs if the executable in command_list[0] (for shell=False) isn't found
        executable_name = (
            command_list[0]
            if isinstance(command_list, list) and command_list
            else "Unknown command"
        )
        success = False
        process_exit_code = -3
        user_message = f"Command not found: '{executable_name}'. Ensure it is installed and in PATH."
        stderr_str = f"FileNotFoundError: Executable '{executable_name}' not found."
        logger.error(user_message)
    except PermissionError:
        executable_name = (
            command_list[0]
            if isinstance(command_list, list) and command_list
            else "Unknown command"
        )
        success = False
        process_exit_code = -6  # New code for permission denied
        user_message = f"Permission denied when trying to execute '{executable_name}'."
        stderr_str = f"PermissionError: Cannot execute '{executable_name}'."
        logger.error(user_message)
    except Exception as e:
        success = False
        process_exit_code = -4
        error_type_name = type(e).__name__
        user_message = f"Action '{action_name}' encountered an unexpected error: {error_type_name}."
        stderr_str = f"UnexpectedError: {error_type_name}: {str(e)}"
        logger.error(
            f"Error during '{action_name}': {stderr_str}", exc_info=True
        )  # Full traceback for unexpected

    log_execution_history(
        {
            "action_name": action_name,
            "command_str_for_log": command_str_for_log,
            "cwd": str(cwd),
            "success": success,
            "exit_code": process_exit_code,
            "stdout_snippet": stdout_str,
            "stderr_snippet": stderr_str,  # These are already snippets in the record
            "message_or_payload": user_message,
            "duration_s": time.time() - start_time,
            "step_id_from_block": step_id_from_block,
            "action_specific_params": action_params,
        }
    )
    return success, user_message, stdout_str, stderr_str, process_exit_code


# --- Action Handlers (using resolve_path and _run_subprocess where appropriate) ---


@handler(name="ECHO")
def handle_echo(
    action_data: Dict, project_root: Path, step_id_from_block: str
) -> Tuple[bool, str]:
    message = action_data.get("message", "No message provided for ECHO.")
    # For consistency and to allow web UI to capture, log it.
    # Actual "echo" to console for interactive CLI can be handled by orchestrator if needed.
    logger.info(f"ECHO (Step: {step_id_from_block}): {message}")
    # The "payload" of echo is the message itself.
    return True, message  # Success, and the message is the result.


@handler(name="CREATE_OR_REPLACE_FILE")
def handle_create_or_replace_file(
    action_data: Dict, project_root: Path, step_id_from_block: str
) -> Tuple[bool, str]:
    relative_path = action_data.get("path")
    content_base64 = action_data.get("content_base64")

    if not isinstance(relative_path, str) or not relative_path:
        return (
            False,
            "Validation Error: Missing or invalid 'path' (string) for CREATE_OR_REPLACE_FILE.",
        )
    if not isinstance(
        content_base64, str
    ):  # content_base64 can be empty string for empty file
        return (
            False,
            "Validation Error: Missing or invalid 'content_base64' (string) for CREATE_OR_REPLACE_FILE.",
        )

    file_path = resolve_path(project_root, relative_path)
    if not file_path:
        return (
            False,
            f"Path Resolution Error: Invalid or unsafe path '{relative_path}'.",
        )

    try:
        # Handle potentially long strings for base64 decoding
        # Python's base64 module handles large strings efficiently.
        decoded_content = base64.b64decode(
            content_base64, validate=True
        )  # validate=True checks for non-b64 chars

        logger.info(f"Attempting to write {len(decoded_content)} bytes to: {file_path}")
        # Ensure parent directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(decoded_content)

        return (
            True,
            f"File '{file_path.relative_to(project_root)}' ({len(decoded_content)} bytes) written successfully.",
        )
    except (
        base64.binascii.Error,
        ValueError,
    ) as b64e:  # binascii.Error is for padding, ValueError for non-b64 chars if validate=True
        logger.error(
            f"Base64 decode error for '{relative_path}': {b64e}", exc_info=True
        )
        return False, f"Base64 Decode Error: {b64e}. Ensure content is valid base64."
    except Exception as e:
        logger.error(f"Error writing file '{relative_path}': {e}", exc_info=True)
        return False, f"File Write Error: {type(e).__name__} - {e}"


@handler(name="APPEND_TO_FILE")
def handle_append_to_file(
    action_data: Dict, project_root: Path, step_id_from_block: str
) -> Tuple[bool, str]:
    relative_path = action_data.get("path")
    content_base64 = action_data.get("content_base64")
    add_newline_if_missing = action_data.get(
        "add_newline_if_missing", True
    )  # Default true

    if not isinstance(relative_path, str) or not relative_path:
        return (
            False,
            "Validation Error: Missing or invalid 'path' (string) for APPEND_TO_FILE.",
        )
    if not isinstance(content_base64, str):
        return (
            False,
            "Validation Error: Missing or invalid 'content_base64' (string) for APPEND_TO_FILE.",
        )

    file_path = resolve_path(project_root, relative_path)
    if not file_path:
        return (
            False,
            f"Path Resolution Error: Invalid or unsafe path '{relative_path}'.",
        )

    try:
        decoded_content = base64.b64decode(content_base64, validate=True)

        logger.info(
            f"Attempting to append {len(decoded_content)} bytes to: {file_path}"
        )
        file_path.parent.mkdir(parents=True, exist_ok=True)  # Ensure parent dir

        # Atomically check and append newline (if file exists and is not empty)
        if (
            add_newline_if_missing
            and file_path.exists()
            and file_path.stat().st_size > 0
        ):
            with file_path.open("rb+") as f:  # Open for reading and writing in binary
                f.seek(-1, os.SEEK_END)  # Go to the last byte
                if f.read(1) != b"\n":
                    f.seek(0, os.SEEK_END)  # Go back to end to append
                    f.write(b"\n")  # Append newline

        with file_path.open("ab") as f:  # Append in binary mode
            f.write(decoded_content)

        return (
            True,
            f"Appended {len(decoded_content)} bytes to '{file_path.relative_to(project_root)}'.",
        )
    except (base64.binascii.Error, ValueError) as b64e:
        logger.error(
            f"Base64 decode error for '{relative_path}' on append: {b64e}",
            exc_info=True,
        )
        return False, f"Base64 Decode Error during append: {b64e}."
    except Exception as e:
        logger.error(f"Error appending to file '{relative_path}': {e}", exc_info=True)
        return False, f"File Append Error: {type(e).__name__} - {e}"


@handler(name="RUN_SCRIPT")
def handle_run_script(
    action_data: Dict, project_root: Path, step_id_from_block: str
) -> Tuple[bool, Dict[str, Any]]:
    relative_script_path = action_data.get("script_path")
    args_list = action_data.get("args", [])  # Expect a list of strings
    script_cwd_option = action_data.get(
        "cwd", "project_root"
    )  # "script_dir" or "project_root"
    timeout_val = action_data.get("timeout", 300)
    shell_val = action_data.get("shell", False)  # Default to False for security

    if not isinstance(relative_script_path, str) or not relative_script_path:
        return False, {"error": "Validation Error: Missing or invalid 'script_path'."}
    if not isinstance(args_list, list) or not all(
        isinstance(str(a), str) for a in args_list
    ):  # Ensure all args can be strings
        return False, {
            "error": "Validation Error: 'args' must be a list of strings/convertible-to-string."
        }
    if shell_val and not isinstance(
        relative_script_path, str
    ):  # If shell=True, script_path becomes the command string
        return False, {
            "error": "Validation Error: If 'shell' is true, 'script_path' must be a single command string, not a path to execute directly with args."
        }

    # If not using shell, script_path must be resolved and exist
    script_path_resolved: Optional[Path] = None
    command_to_execute: List[str]

    if not shell_val:
        script_path_resolved = resolve_path(
            project_root, relative_script_path, ensure_exists=True, ensure_is_file=True
        )
        if not script_path_resolved:
            return False, {
                "error": f"Script Resolution Error: Script '{relative_script_path}' not found or is not a file within project boundaries."
            }

        # Security: Limit executable scripts to project root or a ./scripts subdirectory
        scripts_subdir = (project_root / "scripts").resolve()
        if not (
            script_path_resolved.parent == project_root
            or str(script_path_resolved.parent).startswith(str(scripts_subdir))
        ):
            if not (
                script_path_resolved.parent == project_root
                or str(script_path_resolved).startswith(str(scripts_subdir) + os.sep)
            ):  # check if it IS the scripts_subdir
                logger.error(
                    f"Security: Script '{script_path_resolved}' is not in project root or a direct 'scripts' subdirectory."
                )
                return False, {
                    "error": "Security Policy: Scripts must reside in project root or a 'scripts/' subdirectory."
                }

        # Attempt to make script executable if it's not (common issue)
        if not os.access(script_path_resolved, os.X_OK):
            try:
                logger.info(
                    f"Script '{script_path_resolved}' not executable, attempting chmod +x..."
                )
                script_path_resolved.chmod(
                    script_path_resolved.stat().st_mode | 0o111
                )  # Add execute for user/group/other
            except Exception as e_chmod:
                logger.warning(
                    f"Could not make script '{script_path_resolved}' executable: {e_chmod}. Execution might fail."
                )

        command_to_execute = [str(script_path_resolved)] + [str(a) for a in args_list]
    else:  # shell=True, relative_script_path is the command string
        # When shell=True, `relative_script_path` is the command string itself, args_list should be empty or incorporated into command string by user
        if args_list:  # Args should be part of the command string when shell=True
            logger.warning(
                "RUN_SCRIPT with shell=True: 'args' field is typically ignored; embed arguments in the 'script_path' command string."
            )
        command_to_execute = [
            relative_script_path
        ]  # _run_subprocess expects a list, for shell=True it's a list with one item (the command string)

    effective_cwd: Path
    if (
        script_cwd_option == "script_dir" and script_path_resolved
    ):  # script_dir only makes sense if not shell and path resolved
        effective_cwd = script_path_resolved.parent
    else:  # Default to project_root or if script_cwd_option is invalid/shell=True
        effective_cwd = project_root

    success, user_msg, stdout_str, stderr_str, exit_code_val = _run_subprocess(
        command_to_execute,
        effective_cwd,
        f"RUN_SCRIPT '{relative_script_path}'",
        action_data,  # Pass original action_data for logging
        step_id_from_block,
        timeout_seconds=timeout_val,
        shell_mode=shell_val,
    )

    # Payload should include stdout, stderr, and exit code
    payload = {
        "message": user_msg,
        "stdout": stdout_str,
        "stderr": stderr_str,
        "exit_code": exit_code_val,
    }
    return success, payload


@handler(name="LINT_FORMAT_FILE")  # Uses Ruff
def handle_lint_format_file(
    action_data: Dict, project_root: Path, step_id_from_block: str
) -> Tuple[bool, Dict[str, Any]]:
    relative_target_path = action_data.get(
        "path", "."
    )  # Default to current dir (project root)
    run_format = action_data.get("format", True)
    run_lint_fix = action_data.get("lint_fix", True)  # Ruff check --fix

    if not isinstance(relative_target_path, str):
        return False, {
            "error": "Validation Error: Invalid 'path' for LINT_FORMAT_FILE."
        }

    target_path_obj = resolve_path(
        project_root, relative_target_path, ensure_exists=True
    )  # Path can be file or dir
    if not target_path_obj:
        return False, {
            "error": f"Path Resolution Error: Lint/Format target '{relative_target_path}' not found or invalid."
        }

    target_path_str_for_ruff = (
        "."
        if str(target_path_obj) == str(project_root)
        else str(target_path_obj.relative_to(project_root))
    )
    if target_path_str_for_ruff == ".":  # Ruff prefers explicit '.' for current dir
        target_path_str_for_ruff_display = str(project_root)
    else:
        target_path_str_for_ruff_display = str(target_path_obj)

    ruff_exe = shutil.which(RUFF_EXECUTABLE_NAME)
    if not ruff_exe:
        logger.warning(
            f"'{RUFF_EXECUTABLE_NAME}' not found in PATH. LINT_FORMAT_FILE action will be skipped."
        )
        return False, {
            "error": f"Tool Not Found: '{RUFF_EXECUTABLE_NAME}' executable not found. Install Ruff."
        }

    overall_success = True
    messages = []
    full_stdout = []
    full_stderr = []

    results_payload = {
        "target_path": str(target_path_obj),
        "formatting_applied": False,
        "linting_applied": False,
        "details": [],
    }

    if run_format:
        logger.info(f"Running Ruff format on: {target_path_str_for_ruff_display}")
        fmt_cmd_list = [
            ruff_exe,
            "format",
            target_path_str_for_ruff,
            "--quiet",
        ]  # Use quiet to reduce chatter
        fmt_s, fmt_m, fmt_o, fmt_e, fmt_rc = _run_subprocess(
            fmt_cmd_list, project_root, "RUFF_FORMAT", action_data, step_id_from_block
        )

        msg = f"Ruff Format on '{target_path_str_for_ruff_display}': {fmt_m}"
        messages.append(msg)
        full_stdout.append(
            f"--- Ruff Format STDOUT ---\n{fmt_o if fmt_o else '<empty>'}"
        )
        full_stderr.append(
            f"--- Ruff Format STDERR ---\n{fmt_e if fmt_e else '<empty>'}"
        )
        results_payload["details"].append(
            {
                "step": "format",
                "success": fmt_s,
                "message": msg,
                "stdout": fmt_o,
                "stderr": fmt_e,
                "rc": fmt_rc,
            }
        )
        if fmt_s:
            results_payload["formatting_applied"] = (
                True  # Or check if output indicates changes. Ruff format is tricky here.
            )
        # Often, successful formatting has empty stdout/stderr on no changes.
        # Non-zero RC usually means error.
        if not fmt_s:
            overall_success = False

    if run_lint_fix:
        logger.info(f"Running Ruff check --fix on: {target_path_str_for_ruff_display}")
        # --exit-zero means it exits 0 even if lint issues found and fixed/unfixed.
        # We need to parse output to determine if issues remain.
        # Or use --exit-non-zero-on-fix to get RC 1 if fixes were made.
        # For now, let's rely on parsing output for unfixed issues.
        lint_cmd_list = [
            ruff_exe,
            "check",
            target_path_str_for_ruff,
            "--fix",
            "--show-source",
        ]  # show-source for details
        lint_s, lint_m, lint_o, lint_e, lint_rc = _run_subprocess(
            lint_cmd_list,
            project_root,
            "RUFF_CHECK_FIX",
            action_data,
            step_id_from_block,
        )

        msg = f"Ruff Check/Fix on '{target_path_str_for_ruff_display}': {lint_m}"
        messages.append(msg)
        full_stdout.append(
            f"--- Ruff Check/Fix STDOUT ---\n{lint_o if lint_o else '<empty>'}"
        )
        full_stderr.append(
            f"--- Ruff Check/Fix STDERR ---\n{lint_e if lint_e else '<empty>'}"
        )
        results_payload["details"].append(
            {
                "step": "lint_fix",
                "success": lint_s,
                "message": msg,
                "stdout": lint_o,
                "stderr": lint_e,
                "rc": lint_rc,
            }
        )
        results_payload["linting_applied"] = True  # Assume it ran

        # Ruff 'check --fix' exits 0 if no errors OR if all fixable errors fixed.
        # Exits 1 if there are unfixed errors. Exits 2 for tool error.
        if lint_rc == 1:  # Unfixed linting issues remain
            overall_success = False
            messages.append("NOTE: Ruff check found unfixed linting issues.")
        elif lint_rc != 0:  # Tool error
            overall_success = False
            messages.append(
                f"NOTE: Ruff check command itself failed with RC {lint_rc}."
            )

    results_payload["final_message"] = "\n".join(messages).strip()
    results_payload["full_stdout"] = "\n".join(
        full_stdout
    ).strip()  # For comprehensive review
    results_payload["full_stderr"] = "\n".join(full_stderr).strip()

    return overall_success, results_payload


# Git Handlers (Ensure Git is installed and project_root is a Git repo)
def _is_git_repo(
    project_root: Path, step_id_from_block: str, action_data: dict
) -> bool:
    git_exe = shutil.which("git")
    if not git_exe:
        logger.warning("Git executable not found. Skipping Git operation.")
        return False

    # Check if project_root is part of a git repository
    # `git rev-parse --is-inside-work-tree` is a good check
    check_cmd = [git_exe, "rev-parse", "--is-inside-work-tree"]
    success, _, stdout, _, rc = _run_subprocess(
        check_cmd, project_root, "GIT_REPO_CHECK", action_data, step_id_from_block
    )

    if success and stdout.strip().lower() == "true":
        return True
    else:
        logger.warning(
            f"Directory '{project_root}' is not a Git repository or 'git rev-parse' failed (RC: {rc}). Git operations will be skipped."
        )
        return False


@handler(name="GIT_ADD")
def handle_git_add(
    action_data: Dict, project_root: Path, step_id_from_block: str
) -> Tuple[bool, Dict[str, Any]]:
    if not _is_git_repo(project_root, step_id_from_block, action_data):
        return False, {"error": "Not a Git repository or Git not found."}

    paths_to_add = action_data.get(
        "paths", ["."]
    )  # Default to adding all changes in project_root
    if not isinstance(paths_to_add, list) or not all(
        isinstance(p, str) for p in paths_to_add
    ):
        return False, {
            "error": "Validation Error: 'paths' for GIT_ADD must be a list of strings."
        }

    # Validate paths relative to project_root. For git add, paths are usually relative from repo root.
    # Our project_root IS the repo root for this agent's context.
    validated_git_paths = []
    for p_str in paths_to_add:
        # If path is '.', it means all changes in CWD (project_root)
        if p_str == ".":
            validated_git_paths.append(".")
            continue

        # For specific files/dirs, ensure they resolve safely within project_root (though git handles this well)
        # For 'git add', the path must exist relative to the CWD (project_root)
        resolved_p_for_check = resolve_path(
            project_root, p_str, ensure_exists=False
        )  # Git add can add new untracked files
        if not resolved_p_for_check:
            logger.warning(
                f"Path '{p_str}' for GIT_ADD seems invalid or outside project. Git might handle it, but be cautious."
            )
            # Let git try it, it will fail if pathspec is truly bad
        validated_git_paths.append(
            p_str
        )  # Use the original relative path string for git command

    if not validated_git_paths:
        return False, {"error": "No valid paths provided for GIT_ADD after validation."}

    git_exe = shutil.which("git")  # Should be found if _is_git_repo passed
    add_cmd_list = [git_exe, "add"] + validated_git_paths

    success, user_msg, stdout, stderr, rc = _run_subprocess(
        add_cmd_list, project_root, "GIT_ADD", action_data, step_id_from_block
    )
    return success, {
        "message": user_msg,
        "stdout": stdout,
        "stderr": stderr,
        "exit_code": rc,
    }


@handler(name="GIT_COMMIT")
def handle_git_commit(
    action_data: Dict, project_root: Path, step_id_from_block: str
) -> Tuple[bool, Dict[str, Any]]:
    if not _is_git_repo(project_root, step_id_from_block, action_data):
        return False, {"error": "Not a Git repository or Git not found."}

    commit_message = action_data.get("message")
    allow_empty_commit = action_data.get("allow_empty", False)

    if not isinstance(commit_message, str) or not commit_message:
        return False, {
            "error": "Validation Error: Missing or empty 'message' for GIT_COMMIT."
        }

    git_exe = shutil.which("git")
    commit_cmd_list = [git_exe, "commit", "-m", commit_message]
    if allow_empty_commit:
        commit_cmd_list.append("--allow-empty")

    success, user_msg, stdout, stderr, rc = _run_subprocess(
        commit_cmd_list, project_root, "GIT_COMMIT", action_data, step_id_from_block
    )

    # Special handling: if commit fails because "nothing to commit", treat as success unless allow_empty=true was the goal
    if (
        not success
        and rc != 0
        and (
            "nothing to commit" in stderr.lower()
            or "no changes added to commit" in stdout.lower()
        )
    ):
        if not allow_empty_commit:
            logger.info(
                "GIT_COMMIT: Nothing to commit, and allow_empty was false. Considering this a successful no-op."
            )
            return True, {
                "message": "Nothing to commit.",
                "stdout": stdout,
                "stderr": stderr,
                "exit_code": 0,
            }  # Report as 0 for success

    return success, {
        "message": user_msg,
        "stdout": stdout,
        "stderr": stderr,
        "exit_code": rc,
    }


# Helper for CALL_LOCAL_LLM and future DIAGNOSE_ERROR
def _call_ollama_api(
    prompt: str,
    model_override: Optional[str],
    endpoint_base_override: Optional[str],
    options_override: Optional[Dict],
    step_id: str,
    action_name_for_log: str,
) -> Tuple[bool, Any]:
    model_to_use = model_override or DEFAULT_OLLAMA_MODEL
    endpoint_base_to_use = endpoint_base_override or DEFAULT_OLLAMA_ENDPOINT_BASE
    api_endpoint_generate = f"{endpoint_base_to_use.rstrip('/')}/api/generate"

    payload = {
        "model": model_to_use,
        "prompt": prompt,
        "stream": False,  # ExWork expects a single response for now
    }
    if options_override and isinstance(options_override, dict):
        payload["options"] = options_override

    action_params_log = {
        "model": model_to_use,
        "endpoint": api_endpoint_generate,
        "prompt_length": len(prompt),
        "options_provided": options_override is not None,
    }
    start_time = time.time()
    logger.info(
        f"Calling Ollama API ({action_name_for_log}): Endpoint='{api_endpoint_generate}', Model='{model_to_use}'"
    )

    response_payload: Any = None
    api_success = False
    message_to_user = ""

    try:
        # Add a timeout to requests call, e.g. 60 seconds for LLM response
        # TODO: Make this timeout configurable if not already in "options_override"
        llm_timeout = (
            options_override.get("request_timeout", 180) if options_override else 180
        )

        response = requests.post(
            api_endpoint_generate, json=payload, timeout=llm_timeout
        )
        response.raise_for_status()  # Raises HTTPError for bad responses (4xx or 5xx)

        response_json = response.json()
        if response_json.get("error"):  # Ollama specific error in JSON
            message_to_user = f"Ollama API Error: {response_json['error']}"
            logger.error(message_to_user)
            response_payload = {
                "error": message_to_user,
                "raw_ollama_response": response_json,
            }
        elif "response" in response_json:
            api_success = True
            message_to_user = "LLM call successful. Received response."
            # The main payload for user is the LLM's text response.
            response_payload = response_json[
                "response"
            ]  # This is the actual generated text
            logger.info(
                f"LLM ({model_to_use}) responded. Length: {len(str(response_payload))}"
            )
        else:
            message_to_user = "Ollama API response missing 'response' field."
            logger.error(message_to_user)
            response_payload = {
                "error": message_to_user,
                "raw_ollama_response": response_json,
            }

    except requests.exceptions.Timeout:
        message_to_user = f"Ollama API request timed out after {llm_timeout} seconds."
        logger.error(message_to_user)
        response_payload = {"error": message_to_user}
    except requests.exceptions.RequestException as e:
        message_to_user = f"Ollama API Request Error: {type(e).__name__} - {e}"
        logger.error(message_to_user, exc_info=True)
        response_payload = {"error": message_to_user, "details": str(e)}
    except json.JSONDecodeError as e_json:
        message_to_user = f"Failed to decode JSON response from Ollama API: {e_json}"
        logger.error(
            f"{message_to_user}. Response text: {response.text[:500] if 'response' in locals() else 'N/A'}"
        )
        response_payload = {
            "error": message_to_user,
            "raw_response_text": response.text if "response" in locals() else None,
        }

    log_execution_history(
        {
            "action_name": action_name_for_log,
            "command_str_for_log": f"Ollama API Call: {api_endpoint_generate}, Model: {model_to_use}",
            "cwd": str(PROJECT_ROOT),  # Not really a CWD for API calls
            "success": api_success,
            "exit_code": (
                0 if api_success else -10
            ),  # Arbitrary code for LLM API failure
            "stdout_snippet": str(response_payload)[:500] if api_success else "",
            "stderr_snippet": message_to_user if not api_success else "",
            "message_or_payload": message_to_user,  # Summary message
            "duration_s": time.time() - start_time,
            "step_id_from_block": step_id,
            "action_specific_params": action_params_log,
        }
    )

    # The main return payload for CALL_LOCAL_LLM is the LLM's direct response string if successful,
    # or an error dictionary if not.
    return api_success, (
        response_payload
        if api_success
        else {"error": message_to_user, "llm_response_obj": response_payload}
    )


@handler(name="CALL_LOCAL_LLM")
def handle_call_local_llm(
    action_data: Dict, project_root: Path, step_id_from_block: str
) -> Tuple[bool, Any]:
    prompt = action_data.get("prompt")
    if not isinstance(prompt, str) or not prompt:
        return False, {
            "error": "Validation Error: Missing or empty 'prompt' for CALL_LOCAL_LLM."
        }

    # Extract parameters that _call_ollama_api expects
    model = action_data.get("model")  # Optional, defaults handled by helper
    api_endpoint_base = action_data.get("api_endpoint_base")  # Optional
    options = action_data.get("options")  # Optional, dict for Ollama options

    return _call_ollama_api(
        prompt, model, api_endpoint_base, options, step_id_from_block, "CALL_LOCAL_LLM"
    )


@handler(name="DIAGNOSE_ERROR")  # Enhanced to call LLM
def handle_diagnose_error(
    action_data: Dict, project_root: Path, step_id_from_block: str
) -> Tuple[bool, Any]:
    logger.info(
        f"DIAGNOSE_ERROR called for step_id: {step_id_from_block}. Params: {action_data}"
    )

    failed_command = action_data.get("failed_command_string", "N/A")
    stdout_content = action_data.get("stdout", "")
    stderr_content = action_data.get("stderr", "")
    exit_code = action_data.get("exit_code", "N/A")
    # context_info can be a dict with more structured info about the failure
    context_info = action_data.get("context", {})
    # history_lookback = action_data.get("history_lookback", 0) # TODO: Implement fetching ExWork history if needed

    if not stderr_content and not stdout_content:
        return False, {
            "error": "DIAGNOSE_ERROR requires 'stderr' or 'stdout' from the failed command."
        }

    # Construct a detailed prompt for the LLM
    # (This prompt can be significantly more sophisticated based on your AI Ops vision)
    prompt_parts = [
        "You are an expert AIOps troubleshooting assistant. An automated task has failed.",
        "Please analyze the following error information and provide a concise diagnosis and actionable suggestions for remediation.",
        "Output your response as a JSON object with keys: 'diagnosis' (string: brief summary of the likely cause), 'confidence' (string: e.g., High, Medium, Low), 'remediation_steps' (list of strings: specific steps to fix it), and 'suggested_exwork_actions' (list of ExWork JSON action objects, if applicable, to attempt automated fix, or empty list).",
        f"\nFailed Command: {failed_command}",
        f"Exit Code: {exit_code}",
    ]
    if isinstance(context_info, dict) and context_info:
        prompt_parts.append(f"Additional Context: {json.dumps(context_info)}")
    if stdout_content:
        prompt_parts.append(
            f"\nSTDOUT from command (last 1000 chars):\n```\n{stdout_content[-1000:]}\n```"
        )
    if stderr_content:
        prompt_parts.append(
            f"\nSTDERR from command (last 1000 chars):\n```\n{stderr_content[-1000:]}\n```"
        )

    # TODO: Add relevant ExWork history snippet if history_lookback > 0

    full_prompt = "\n".join(prompt_parts)

    # Use the LLM call helper. Model/endpoint can be specified in DIAGNOSE_ERROR action_data,
    # or will use ExWork agent defaults.
    llm_model = action_data.get("llm_model_override")
    llm_endpoint = action_data.get("llm_endpoint_override")
    llm_options = action_data.get(
        "llm_options_override", {"temperature": 0.5}
    )  # Example option

    success, llm_response_payload = _call_ollama_api(
        full_prompt,
        llm_model,
        llm_endpoint,
        llm_options,
        step_id_from_block,
        "DIAGNOSE_ERROR_LLM_CALL",
    )

    if not success:
        # llm_response_payload already contains an error structure from _call_ollama_api
        return False, {
            "error": "LLM call for error diagnosis failed.",
            "llm_call_details": llm_response_payload,
        }

    # Attempt to parse the LLM's response (which should be JSON as per prompt)
    try:
        # llm_response_payload here IS the string from ollama "response" field
        diagnosis_json = json.loads(llm_response_payload)
        # Validate expected keys
        if not all(k in diagnosis_json for k in ["diagnosis", "remediation_steps"]):
            logger.warning(
                "LLM diagnosis response did not contain all expected keys. Raw: "
                + str(llm_response_payload)[:300]
            )
            # Return the raw LLM text if parsing/validation fails but call was "success"
            return True, {
                "diagnosis_text_raw": llm_response_payload,
                "warning": "LLM response format unexpected.",
            }

        return True, diagnosis_json  # Return the structured JSON diagnosis
    except json.JSONDecodeError:
        logger.error(
            f"Failed to parse LLM diagnosis JSON response: {llm_response_payload[:500]}..."
        )
        # Return the raw LLM text if parsing fails
        return True, {
            "diagnosis_text_raw": llm_response_payload,
            "error": "Could not parse LLM diagnosis as JSON.",
        }


@handler(name="REQUEST_SIGNOFF")  # No changes needed based on previous, seems fine
def handle_request_signoff(
    action_data: Dict, project_root: Path, step_id_from_block: str
) -> Tuple[bool, Dict[str, Any]]:
    message = action_data.get("message", "Proceed with critical action?")
    # Use action_data's "id" field if provided for the signoff_id, else generate one.
    # This allows orchestrator to pre-define signoff_ids for tracking.
    signoff_id = action_data.get(
        "id", str(uuid.uuid4())
    )  # "id" is common for action items.

    logger.info(
        f"Action requires sign-off (Step: {step_id_from_block}). ID: {signoff_id}. Prompt: {message}"
    )

    # The payload returned signals to an orchestrator that sign-off is needed.
    # ExWork agent itself doesn't wait here.
    return True, {
        "exwork_status": "AWAITING_SIGNOFF",
        "signoff_prompt": message,
        "signoff_id": sign_id,  # Store the actual signoff_id used
        "original_step_id": step_id_from_block,  # Keep track of which block requested it
    }


@handler(name="RESPOND_TO_SIGNOFF")  # No changes needed based on previous
def handle_respond_to_signoff(
    action_data: Dict, project_root: Path, step_id_from_block: str
) -> Tuple[bool, str]:
    signoff_id_to_respond = action_data.get("signoff_id")
    response_value = str(action_data.get("response", "no")).lower().strip()  # Normalize

    if not signoff_id_to_respond:
        return False, "Validation Error: Missing 'signoff_id' for RESPOND_TO_SIGNOFF."

    # This action primarily logs the external response.
    # The orchestrator would use this log or its own state to decide how to proceed
    # with the workflow that was awaiting this signoff_id.
    if response_value in ["yes", "true", "approve", "approved"]:
        msg = f"Sign-off ID '{signoff_id_to_respond}' recorded as externally APPROVED. Workflow may proceed if designed to."
        logger.info(msg)
        return True, msg
    else:
        msg = f"Sign-off ID '{signoff_id_to_respond}' recorded as externally REJECTED/DENIED (response: '{response_value}'). Workflow should handle rejection."
        logger.warning(msg)  # Warning as it's a rejection
        return True, msg  # The action itself succeeded in recording the response.


@handler(name="APPLY_PATCH")  # Refactored to use `patch` command non-interactively
def handle_apply_patch(
    action_data: Dict, project_root: Path, step_id_from_block: str
) -> Tuple[bool, Dict[str, Any]]:
    logger.info(
        f"APPLY_PATCH called for step_id: {step_id_from_block}. Params: {action_data}"
    )

    relative_target_file_path = action_data.get(
        "path"
    )  # Path to the file to be patched
    patch_content_base64 = action_data.get(
        "patch_content_base64"
    )  # Patch content itself (diff format)
    # Options for `patch` command
    strip_level = action_data.get("strip_level", "1")  # `patch -pX`
    dry_run = action_data.get("dry_run", False)

    if not isinstance(relative_target_file_path, str) or not relative_target_file_path:
        return False, {
            "error": "Validation Error: Missing or invalid 'path' for APPLY_PATCH."
        }
    if not isinstance(
        patch_content_base64, str
    ):  # Can be empty if patch content means delete all etc.
        return False, {"error": "Validation Error: Missing 'patch_content_base64'."}

    target_file_abs = resolve_path(
        project_root, relative_target_file_path, ensure_exists=True, ensure_is_file=True
    )
    if not target_file_abs:
        return False, {
            "error": f"Path Resolution Error: Target file '{relative_target_file_path}' for patch not found or invalid."
        }

    patch_exe = shutil.which(PATCH_EXECUTABLE_NAME)
    if not patch_exe:
        return False, {
            "error": f"Tool Not Found: '{PATCH_EXECUTABLE_NAME}' executable not found. Install patch utility."
        }

    try:
        patch_content_bytes = base64.b64decode(patch_content_base64, validate=True)
        if (
            not patch_content_bytes
        ):  # Empty patch content is usually not useful unless it's a specific signal
            return False, {"error": "Validation Error: Decoded patch content is empty."}
    except (base64.binascii.Error, ValueError) as b64e:
        return False, {"error": f"Base64 Decode Error for patch content: {b64e}."}

    # `patch` command typically takes patch from stdin and applies to file
    # Need to operate in the directory of the target file for patch to find it correctly if patch paths are relative
    patch_command_list = [
        patch_exe,
        f"-p{strip_level}",
        "--quiet",
        "--force",
    ]  # --force to try harder, --quiet
    if dry_run:
        patch_command_list.append("--dry-run")

    # The file to patch is implicitly the target_file_abs. `patch` reads the diff from stdin and applies it to files mentioned *in the diff itself*
    # relative to its CWD. So CWD should be project_root if diff paths are like 'a/src/file.py'.
    # If the patch is for a single file and paths in diff are like '--- a/file.py' '+++ b/file.py',
    # then CWD should be target_file_abs.parent and `patch` command should be `patch <target_file_name>`
    # For simplicity, assume patch content has paths relative to project_root (e.g. a/src/module.py)
    # and `patch` is run from project_root. The `target_file_path` param is mostly for identifying which file
    # the patch *intends* to modify, but patch tool itself uses paths within the diff.

    # Let's refine: `patch <file_to_patch> -i <patch_file>` or `patch <file_to_patch> < <patch_file>`
    # Or `patch -i <patch_file>` and run from file_to_patch's parent dir if diff paths are simple.
    # Using stdin for patch content is common.

    # Create a temporary file for the patch content
    # Using a temporary file for the patch content is more robust for subprocess.
    with tempfile.NamedTemporaryFile(
        mode="wb", delete=False, dir=project_root, prefix="exwork_patch_"
    ) as tmp_patch_file:
        tmp_patch_file.write(patch_content_bytes)
        tmp_patch_file_name = tmp_patch_file.name

    # Command: patch -p<strip_level> --input=<temp_patch_file> <original_file_to_patch_if_needed_by_patch_version>
    # Most `patch` versions infer target from diff, but some older ones might need it.
    # We'll run from project_root, assuming paths in diff are relative to it.
    # patch_command_list.append(str(target_file_abs.relative_to(project_root))) # Sometimes needed
    patch_command_list.extend(["--input", tmp_patch_file_name])

    logger.info(
        f"Applying patch from temp file {tmp_patch_file_name} to context of {project_root} (target hint: {target_file_abs})"
    )

    success, user_msg, stdout, stderr, rc = _run_subprocess(
        patch_command_list,
        project_root,  # Run patch from project root
        "APPLY_PATCH",
        action_data,
        step_id_from_block,
    )

    os.remove(tmp_patch_file_name)  # Clean up temp patch file

    # `patch` exits 0 on success, 1 if some hunks failed, 2 for serious trouble.
    if rc == 0:
        final_message = f"Patch applied successfully. {user_msg}"
        if dry_run:
            final_message = f"Patch DRY RUN successful. {user_msg}"
        return True, {
            "message": final_message,
            "stdout": stdout,
            "stderr": stderr,
            "exit_code": rc,
            "dry_run": dry_run,
        }
    elif rc == 1:  # Hunks failed
        final_message = f"Patch applied with some hunks failing. {user_msg}"
        if dry_run:
            final_message = f"Patch DRY RUN indicated some hunks would fail. {user_msg}"
        logger.warning(final_message + f" Stdout: {stdout}, Stderr: {stderr}")
        # Still report overall success=False for the ExWork action if hunks failed.
        return False, {
            "error": final_message,
            "stdout": stdout,
            "stderr": stderr,
            "exit_code": rc,
            "dry_run": dry_run,
        }
    else:  # rc == 2 or other
        final_message = f"Patch application failed. {user_msg}"
        if dry_run:
            final_message = f"Patch DRY RUN indicated failure. {user_msg}"
        return False, {
            "error": final_message,
            "stdout": stdout,
            "stderr": stderr,
            "exit_code": rc,
            "dry_run": dry_run,
        }


# EXECUTE_SYSTEM_COMMAND - largely okay, ensure path resolution for CWD
@handler(name="EXECUTE_SYSTEM_COMMAND")
def handle_execute_system_command(
    action_data: Dict, project_root: Path, step_id_from_block: str
) -> Tuple[bool, Dict[str, Any]]:
    command_str = action_data.get("command_string")  # This is the full command string
    use_shell = action_data.get("shell", False)  # Default False for security
    relative_cwd = action_data.get(
        "working_directory"
    )  # Optional, relative to project_root
    timeout_val = action_data.get("timeout", 300)
    env_vars = action_data.get("env")  # Optional dict of env vars

    if not isinstance(command_str, str) or not command_str:
        return False, {
            "error": "Validation Error: Missing or invalid 'command_string'."
        }
    if not isinstance(use_shell, bool):
        return False, {"error": "Validation Error: 'shell' must be a boolean."}

    effective_cwd = project_root
    if relative_cwd:
        if not isinstance(relative_cwd, str):
            return False, {
                "error": "Validation Error: 'working_directory' must be a string path."
            }
        resolved_cwd = resolve_path(
            project_root, relative_cwd, ensure_exists=True, ensure_is_dir=True
        )
        if not resolved_cwd:
            return False, {
                "error": f"Path Resolution Error: Specified 'working_directory' ({relative_cwd}) is invalid or not found."
            }
        effective_cwd = resolved_cwd

    # _run_subprocess expects command as a list of one string if shell=True
    command_arg_for_subprocess = (
        [command_str] if use_shell else shlex.split(command_str)
    )
    if (
        not command_arg_for_subprocess and not use_shell
    ):  # shlex.split on empty/whitespace string
        return False, {
            "error": "Validation Error: 'command_string' parsed to empty for shell=False."
        }

    if use_shell:
        logger.warning(
            f"Executing system command with shell=True: '{command_str}'. Ensure this is from a trusted source or properly sanitized if dynamic."
        )

    success, user_msg, stdout, stderr, rc = _run_subprocess(
        command_arg_for_subprocess,
        effective_cwd,
        "EXECUTE_SYSTEM_COMMAND",
        action_data,
        step_id_from_block,
        timeout_seconds=timeout_val,
        shell_mode=use_shell,
        custom_env=env_vars,
    )
    return success, {
        "message": user_msg,
        "stdout": stdout,
        "stderr": stderr,
        "exit_code": rc,
    }


# READ_FILE_CONTENT - largely okay, ensure path validation
@handler(name="READ_FILE_CONTENT")
def handle_read_file_content(
    action_data: Dict, project_root: Path, step_id_from_block: str
) -> Tuple[bool, Any]:  # Payload can be dict or string error
    relative_path = action_data.get("path")
    encoding = action_data.get("encoding", "utf-8")
    output_format = action_data.get("output_format", "string")  # "string" or "base64"

    if not isinstance(relative_path, str) or not relative_path:
        return False, {"error": "Validation Error: Missing or invalid 'path'."}

    file_path = resolve_path(
        project_root, relative_path, ensure_exists=True, ensure_is_file=True
    )
    if not file_path:
        return False, {
            "error": f"Path Resolution Error: File '{relative_path}' not found, not a file, or invalid."
        }

    try:
        if output_format == "base64":
            content_bytes = file_path.read_bytes()
            # Handle long strings by not storing excessively large base64 in logs directly
            # The actual content is returned in the payload.
            content_encoded = base64.b64encode(content_bytes).decode("ascii")
            logger.info(
                f"Read {len(content_bytes)} bytes from '{file_path.relative_to(project_root)}' and base64 encoded."
            )
            return True, {
                "file_path": str(file_path.relative_to(project_root)),
                "content_base64": content_encoded,
                "bytes_read": len(content_bytes),
            }
        elif output_format == "string":
            content_str = file_path.read_text(encoding=encoding)
            logger.info(
                f"Read {len(content_str)} characters from '{file_path.relative_to(project_root)}'."
            )
            return True, {
                "file_path": str(file_path.relative_to(project_root)),
                "content_string": content_str,
                "characters_read": len(content_str),
            }
        else:
            return False, {
                "error": f"Validation Error: Invalid 'output_format': {output_format}. Must be 'string' or 'base64'."
            }
    except Exception as e:
        logger.error(f"Error reading file '{relative_path}': {e}", exc_info=True)
        return False, {"error": f"File Read Error: {type(e).__name__} - {e}"}


# COPY_FILE - largely okay, ensure path validation
@handler(name="COPY_FILE")
def handle_copy_file(
    action_data: Dict, project_root: Path, step_id_from_block: str
) -> Tuple[bool, str]:  # Returns simple message string
    source_relative = action_data.get("source_relative_path")
    dest_relative = action_data.get("destination_relative_path")
    overwrite = action_data.get("overwrite", False)  # Default to not overwrite

    if not all(isinstance(p, str) and p for p in [source_relative, dest_relative]):
        return (
            False,
            "Validation Error: Missing or invalid 'source_relative_path' or 'destination_relative_path'.",
        )

    source_abs = resolve_path(
        project_root, source_relative, ensure_exists=True, ensure_is_file=True
    )
    if not source_abs:
        return (
            False,
            f"Path Resolution Error: Source file '{source_relative}' not found or invalid.",
        )

    # For destination, we don't ensure_exists as it might be a new file.
    # But its parent directory must be resolvable within project_root.
    dest_abs = resolve_path(project_root, dest_relative)
    if not dest_abs:
        return (
            False,
            f"Path Resolution Error: Destination path '{dest_relative}' is invalid or unsafe.",
        )

    # If destination is an existing directory, append source filename
    if dest_abs.is_dir():
        dest_abs = dest_abs / source_abs.name
        logger.info(
            f"Destination '{dest_relative}' is a directory, appending source filename: new destination is '{dest_abs.relative_to(project_root)}'"
        )

    if dest_abs.exists() and not overwrite:
        return (
            False,
            f"Copy Error: Destination file '{dest_abs.relative_to(project_root)}' already exists and 'overwrite' is false.",
        )
    if (
        dest_abs.exists() and not dest_abs.is_file() and overwrite
    ):  # Trying to overwrite a dir with a file
        return (
            False,
            f"Copy Error: Cannot overwrite destination '{dest_abs.relative_to(project_root)}' because it exists and is not a file.",
        )

    try:
        dest_abs.parent.mkdir(
            parents=True, exist_ok=True
        )  # Ensure destination parent directory exists
        shutil.copy2(source_abs, dest_abs)  # copy2 preserves metadata
        msg = f"File '{source_abs.relative_to(project_root)}' copied to '{dest_abs.relative_to(project_root)}'."
        logger.info(msg)
        return True, msg
    except Exception as e:
        logger.error(
            f"Error copying file from '{source_relative}' to '{dest_relative}': {e}",
            exc_info=True,
        )
        return False, f"File Copy Error: {type(e).__name__} - {e}"


# HTTP_REQUEST - largely okay, just ensure action_params_log is safe
@handler(name="HTTP_REQUEST")
def handle_http_request(
    action_data: Dict, project_root: Path, step_id_from_block: str
) -> Tuple[bool, Any]:  # Payload can be dict or string error
    url = action_data.get("url")
    method = action_data.get("method", "GET").upper()
    headers = action_data.get("headers", {})
    json_payload_for_request = action_data.get(
        "json_payload"
    )  # Renamed to avoid confusion
    params_for_request = action_data.get("params")  # Query params
    timeout_val = action_data.get("timeout", 60)  # Seconds
    allow_redirects_val = action_data.get("allow_redirects", True)
    verify_ssl_val = action_data.get("verify_ssl", True)

    if not isinstance(url, str) or not url:
        return False, {"error": "Validation Error: Missing or invalid 'url'."}
    if method not in ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]:
        return False, {"error": f"Validation Error: Invalid HTTP method: {method}"}
    if not isinstance(headers, dict):
        return False, {"error": "Validation Error: 'headers' must be a dictionary."}
    if json_payload_for_request is not None and not isinstance(
        json_payload_for_request, dict
    ):
        # Could also allow string if content-type is e.g. application/xml
        return False, {
            "error": "Validation Error: 'json_payload' must be a dictionary if provided."
        }
    if params_for_request is not None and not isinstance(params_for_request, dict):
        return False, {
            "error": "Validation Error: 'params' (query parameters) must be a dictionary if provided."
        }

    # For logging, avoid logging full sensitive payloads if any.
    # For now, just indicate presence. True AIOps might log more with masking.
    action_params_log_safe = {
        "url": url,
        "method": method,
        "headers_provided": bool(headers),
        "json_payload_provided": json_payload_for_request is not None,
        "params_provided": params_for_request is not None,
    }
    start_time = time.time()

    response_from_request: Optional[requests.Response] = None
    try:
        logger.info(f"Making HTTP {method} request to: {url}")
        response_from_request = requests.request(
            method,
            url,
            headers=headers,
            json=json_payload_for_request,
            params=params_for_request,
            timeout=timeout_val,
            allow_redirects=allow_redirects_val,
            verify=verify_ssl_val,
        )
        response_from_request.raise_for_status()  # Raises HTTPError for 4xx/5xx client/server errors

        # Try to parse content, default to text if JSON fails
        response_content_parsed: Any
        content_type_detected = "text"  # Default
        try:
            response_content_parsed = response_from_request.json()
            content_type_detected = "json"
        except json.JSONDecodeError:
            response_content_parsed = response_from_request.text
            content_type_detected = "text"  # Already default, but explicit

        success = True
        result_payload = {
            "status_code": response_from_request.status_code,
            "headers": dict(
                response_from_request.headers
            ),  # Convert CaseInsensitiveDict
            "content_type": content_type_detected,
            "content": response_content_parsed,
            "url_final": response_from_request.url,  # Effective URL after redirects
        }
        message_to_user = f"HTTP {method} to {url} successful (Status: {response_from_request.status_code})."
        logger.info(message_to_user)

    except requests.exceptions.Timeout:
        success = False
        message_to_user = (
            f"HTTP Request Timeout: Request to {url} timed out after {timeout_val}s."
        )
        result_payload = {"error": message_to_user, "url": url, "method": method}
        logger.error(message_to_user)
    except requests.exceptions.HTTPError as http_err:  # For 4xx/5xx responses
        success = False
        status_code = (
            http_err.response.status_code
            if http_err.response is not None
            else "Unknown"
        )
        message_to_user = f"HTTP Error {status_code}: {http_err}"
        # Try to get response body for more context on error
        error_body = (
            http_err.response.text[:500]
            if http_err.response is not None
            else "No response body."
        )
        result_payload = {
            "error": message_to_user,
            "status_code": status_code,
            "url": url,
            "method": method,
            "error_body_snippet": error_body,
        }
        logger.error(f"{message_to_user}. Response: {error_body}")
    except (
        requests.exceptions.RequestException
    ) as req_err:  # Catch other request errors (DNS, ConnectionError, etc.)
        success = False
        message_to_user = f"HTTP Request Failed: {type(req_err).__name__} - {req_err}"
        result_payload = {
            "error": message_to_user,
            "url": url,
            "method": method,
            "details": str(req_err),
        }
        logger.error(message_to_user, exc_info=True)

    log_execution_history(
        {
            "action_name": "HTTP_REQUEST",
            "success": success,
            "message_or_payload": message_to_user,
            "duration_s": time.time() - start_time,
            "step_id_from_block": step_id_from_block,
            "action_specific_params": action_params_log_safe,
            "command_str_for_log": f"HTTP {method} {url}",  # Simplified log command
            "stdout_snippet": (
                json.dumps(result_payload, default=str)[:500] if success else ""
            ),  # Log result snippet
            "stderr_snippet": (
                message_to_user if not success else ""
            ),  # Log error message on failure
        }
    )
    return success, result_payload


# REPLACE_TEXT_IN_FILE - okay, ensure path validation
@handler(name="REPLACE_TEXT_IN_FILE")
def handle_replace_text_in_file(
    action_data: Dict, project_root: Path, step_id_from_block: str
) -> Tuple[bool, str]:  # Returns message string
    relative_path = action_data.get("path")
    old_text_pattern = action_data.get("old_text")  # Can be string or regex pattern
    new_text_replacement = action_data.get("new_text")
    max_replacements = action_data.get("count", 0)  # 0 means all occurrences
    is_regex_mode = action_data.get("is_regex", False)
    encoding_val = action_data.get("encoding", "utf-8")

    if not all(
        isinstance(s, str)
        for s in [
            relative_path,
            old_text_pattern if old_text_pattern is not None else "",
            new_text_replacement if new_text_replacement is not None else "",
        ]
    ):  # Check type, allow empty for replacement
        return (
            False,
            "Validation Error: 'path', 'old_text', or 'new_text' are missing or not strings.",
        )
    if old_text_pattern is None:  # old_text cannot be None
        return False, "Validation Error: 'old_text' cannot be null/None."
    if not isinstance(max_replacements, int) or max_replacements < 0:
        return False, "Validation Error: 'count' must be a non-negative integer."

    file_path_abs = resolve_path(
        project_root, relative_path, ensure_exists=True, ensure_is_file=True
    )
    if not file_path_abs:
        return (
            False,
            f"Path Resolution Error: File '{relative_path}' not found, not a file, or invalid.",
        )

    try:
        original_content = file_path_abs.read_text(encoding=encoding_val)
        modified_content: str
        num_actual_replacements: int

        if is_regex_mode:
            try:
                modified_content, num_actual_replacements = re.subn(
                    old_text_pattern,
                    new_text_replacement,
                    original_content,
                    count=max_replacements,
                )
            except re.error as re_err:
                logger.error(
                    f"Invalid regex pattern '{old_text_pattern}': {re_err}",
                    exc_info=True,
                )
                return (
                    False,
                    f"Regex Error: Invalid pattern '{old_text_pattern}': {re_err}",
                )
        else:  # Simple string replacement
            if max_replacements == 0:  # Replace all
                modified_content = original_content.replace(
                    old_text_pattern, new_text_replacement
                )
                num_actual_replacements = original_content.count(
                    old_text_pattern
                )  # Count before replace for accuracy
            else:  # Replace up to 'count' occurrences
                modified_content = original_content.replace(
                    old_text_pattern, new_text_replacement, max_replacements
                )
                # To count actual replacements for limited replace:
                temp_str = original_content
                actual_replaced_count = 0
                start_index = 0
                for _ in range(max_replacements):
                    found_at = temp_str.find(old_text_pattern, start_index)
                    if found_at == -1:
                        break
                    actual_replaced_count += 1
                    start_index = found_at + len(
                        old_text_pattern
                    )  # Move past this found instance
                num_actual_replacements = actual_replaced_count

        if original_content == modified_content:
            msg = f"No changes made to '{file_path_abs.relative_to(project_root)}'. Pattern '{old_text_pattern}' not found or replacement is identical."
            logger.info(msg)
            return True, msg  # Success, but no effective change

        file_path_abs.write_text(modified_content, encoding=encoding_val)
        msg = f"Successfully replaced text in '{file_path_abs.relative_to(project_root)}'. {num_actual_replacements} replacement(s) made."
        logger.info(msg)
        return True, msg

    except Exception as e:
        logger.error(f"Error replacing text in '{relative_path}': {e}", exc_info=True)
        return False, f"Text Replacement Error: {type(e).__name__} - {e}"


# --- Linux Specific Handlers (Assume Linux for now as per user direction) ---
# These use shutil.which to find executables. Error handling for tool-not-found is included.


@handler(name="NETWORK_MAP_AND_PROBE")  # Uses Nmap
def handle_network_map_and_probe(
    action_data: Dict, project_root: Path, step_id_from_block: str
) -> Tuple[bool, Dict[str, Any]]:
    target_spec = action_data.get(
        "target_subnet", "127.0.0.1"
    )  # Renamed for clarity (can be IP, range, hostname)
    probe_profile = action_data.get("probe_level", "basic_ping_scan")  # Renamed
    # Output file is relative to a 'reports' subdir in project_root
    output_file_rel_default = f"reports/nmap_scan_{target_spec.replace('/', '_').replace(' ', '_')}_{step_id_from_block}.xml"
    output_file_rel = action_data.get("output_file_relative", output_file_rel_default)

    if not isinstance(target_spec, str) or not target_spec:
        return False, {"error": "Validation Error: Invalid or missing 'target_subnet'."}
    allowed_probe_levels = [
        "basic_ping_scan",
        "aggressive_os_detection_service_scan",
        "fast_scan",
        "top_ports_scan",
        "custom_args",
    ]
    if probe_profile not in allowed_probe_levels:
        return False, {
            "error": f"Validation Error: Invalid 'probe_level'. Must be one of {allowed_probe_levels}."
        }

    output_file_abs = resolve_path(project_root, output_file_rel)
    if not output_file_abs:
        return False, {
            "error": f"Path Resolution Error: Invalid output file path '{output_file_rel}'."
        }
    output_file_abs.parent.mkdir(
        parents=True, exist_ok=True
    )  # Ensure reports dir exists

    nmap_exe = shutil.which(NMAP_EXECUTABLE_NAME)
    if not nmap_exe:
        return False, {
            "error": f"Tool Not Found: Nmap executable '{NMAP_EXECUTABLE_NAME}' not found. Install Nmap."
        }

    nmap_args_list = [
        nmap_exe,
        "-oX",
        str(output_file_abs),
    ]  # XML output is good for parsing

    if probe_profile == "aggressive_os_detection_service_scan":
        nmap_args_list.extend(["-T4", "-A", "-v"])
    elif probe_profile == "basic_ping_scan":
        nmap_args_list.extend(["-sn"])  # Ping scan only
    elif probe_profile == "fast_scan":
        nmap_args_list.extend(["-F"])  # Fast scan (fewer ports)
    elif probe_profile == "top_ports_scan":
        nmap_args_list.extend(["--top-ports", "1000"])  # Scan top 1000 ports
    elif probe_profile == "custom_args":
        custom_nmap_args_str = action_data.get("nmap_custom_args_string", "")
        if not custom_nmap_args_str:
            return False, {
                "error": "Validation Error: 'nmap_custom_args_string' is required for 'custom_args' probe_level."
            }
        nmap_args_list.extend(
            shlex.split(custom_nmap_args_str)
        )  # Split user-provided string of args

    nmap_args_list.append(target_spec)  # Add target last

    # Nmap can take a long time, default timeout might be too short.
    nmap_timeout = action_data.get("timeout", 900)  # Default 15 minutes for Nmap

    success, user_msg, stdout, stderr, rc = _run_subprocess(
        nmap_args_list,
        project_root,
        "NETWORK_MAP_AND_PROBE",
        action_data,
        step_id_from_block,
        timeout_seconds=nmap_timeout,
    )

    payload = {
        "message": user_msg,
        "stdout": stdout,
        "stderr": stderr,
        "exit_code": rc,
        "output_file": str(output_file_abs.relative_to(project_root)),
    }
    if success:
        payload["message"] = (
            f"Nmap scan completed. Results in '{output_file_abs.relative_to(project_root)}'. {user_msg}"
        )
    return success, payload


@handler(name="MANIPULATE_ROUTING_TABLE")  # Uses `ip route` (Linux assumed)
def handle_manipulate_routing_table(
    action_data: Dict, project_root: Path, step_id_from_block: str
) -> Tuple[bool, Dict[str, Any]]:
    operation = action_data.get("operation", "").lower()  # "add", "delete"
    destination_cidr = action_data.get("destination_cidr")
    gateway_ip = action_data.get("gateway_ip")  # Optional
    interface_dev = action_data.get("interface")  # Optional

    if operation not in [
        "add",
        "del",
        "delete",
    ]:  # Allow "del" as common alias for "delete"
        return False, {
            "error": "Validation Error: Invalid 'operation'. Must be 'add' or 'delete' (or 'del')."
        }
    if not isinstance(destination_cidr, str) or not destination_cidr:
        return False, {
            "error": "Validation Error: Missing or invalid 'destination_cidr'."
        }
    if operation == "add" and not (gateway_ip or interface_dev):
        return False, {
            "error": "Validation Error: For 'add' route, 'gateway_ip' or 'interface' must be provided."
        }

    ip_exe = shutil.which(IP_ROUTE_EXECUTABLE_NAME)
    if not ip_exe:
        return False, {
            "error": f"Tool Not Found: '{IP_ROUTE_EXECUTABLE_NAME}' command not found. This action is Linux-specific."
        }

    # Construct 'ip route' command (Linux specific)
    # Example: sudo ip route add 192.168.100.0/24 via 10.0.0.1 dev eth0
    cmd_list = [
        "sudo",
        ip_exe,
        "route",
        operation if operation != "del" else "delete",
        destination_cidr,
    ]
    if gateway_ip:
        cmd_list.extend(["via", gateway_ip])
    if interface_dev:
        cmd_list.extend(["dev", interface_dev])

    success, user_msg, stdout, stderr, rc = _run_subprocess(
        cmd_list,
        project_root,
        "MANIPULATE_ROUTING_TABLE",
        action_data,
        step_id_from_block,
    )
    return success, {
        "message": user_msg,
        "stdout": stdout,
        "stderr": stderr,
        "exit_code": rc,
    }


@handler(name="ENCRYPT_DECRYPT_TARGET")  # Uses PyCryptodome
def handle_encrypt_decrypt_target(
    action_data: Dict, project_root: Path, step_id_from_block: str
) -> Tuple[bool, str]:  # Returns message string
    if not CRYPTO_AVAILABLE:
        return (
            False,
            "Crypto Error: PyCryptodome library not available. Cannot perform encryption/decryption.",
        )

    operation = action_data.get("operation")  # "encrypt" or "decrypt"
    relative_target_path = action_data.get("target_path")
    key_base64 = action_data.get("key_base64")  # AES key, base64 encoded

    if operation not in ["encrypt", "decrypt"]:
        return (
            False,
            "Validation Error: Invalid 'operation'. Must be 'encrypt' or 'decrypt'.",
        )
    if not isinstance(relative_target_path, str) or not relative_target_path:
        return False, "Validation Error: Missing or invalid 'target_path'."
    if not isinstance(key_base64, str) or not key_base64:
        return False, "Validation Error: Missing or invalid 'key_base64'."

    target_abs_path = resolve_path(
        project_root, relative_target_path, ensure_exists=True, ensure_is_file=True
    )
    if not target_abs_path:
        return (
            False,
            f"Path Resolution Error: Target file '{relative_target_path}' not found or invalid.",
        )

    try:
        key_bytes = base64.b64decode(key_base64)
        if len(key_bytes) not in [16, 24, 32]:  # AES key sizes (128, 192, 256 bit)
            return (
                False,
                "Crypto Error: Invalid AES key length after base64 decode. Must be 16, 24, or 32 bytes.",
            )

        iv_size = AES.block_size  # 16 bytes for AES

        if operation == "encrypt":
            cipher = AES.new(key_bytes, AES.MODE_CBC)  # Creates a random IV
            iv_for_storage = cipher.iv  # Get the IV to store it with ciphertext

            plaintext_bytes = target_abs_path.read_bytes()
            padded_plaintext = pad(plaintext_bytes, AES.block_size)
            ciphertext_bytes = cipher.encrypt(padded_plaintext)

            # Prepend IV to ciphertext for storage
            target_abs_path.write_bytes(iv_for_storage + ciphertext_bytes)
            return (
                True,
                f"File '{target_abs_path.relative_to(project_root)}' encrypted successfully.",
            )

        else:  # Decrypt
            encrypted_data_with_iv = target_abs_path.read_bytes()
            if len(encrypted_data_with_iv) < iv_size:
                return (
                    False,
                    "Crypto Error: Encrypted file is too short to contain an IV.",
                )

            iv_from_file = encrypted_data_with_iv[:iv_size]
            ciphertext_from_file = encrypted_data_with_iv[iv_size:]

            cipher = AES.new(key_bytes, AES.MODE_CBC, iv=iv_from_file)
            decrypted_padded_bytes = cipher.decrypt(ciphertext_from_file)
            try:
                original_plaintext_bytes = unpad(decrypted_padded_bytes, AES.block_size)
            except (
                ValueError
            ) as unpad_err:  # Error if unpadding fails (wrong key or corrupted data)
                logger.error(
                    f"Unpadding error during decryption (likely wrong key or data corruption): {unpad_err}",
                    exc_info=True,
                )
                return (
                    False,
                    f"Decryption Error: Failed to unpad data. Check key or file integrity. ({unpad_err})",
                )

            target_abs_path.write_bytes(original_plaintext_bytes)
            return (
                True,
                f"File '{target_abs_path.relative_to(project_root)}' decrypted successfully.",
            )

    except (base64.binascii.Error, ValueError) as b64e_key:
        return False, f"Base64 Decode Error for key: {b64e_key}."
    except Exception as e:
        logger.error(
            f"Error during {operation} of '{relative_target_path}': {e}", exc_info=True
        )
        return False, f"Crypto Operation Error ({operation}): {type(e).__name__} - {e}"


@handler(name="SECURE_WIPE_TARGET")  # Linux focus implies `shred` or manual overwrite
def handle_secure_wipe_target(
    action_data: Dict, project_root: Path, step_id_from_block: str
) -> Tuple[bool, str]:  # Returns message string
    relative_target_path = action_data.get("target_path")
    passes_val = action_data.get("passes", 3)  # Number of overwrite passes
    use_shred_if_available = action_data.get(
        "use_shred", True
    )  # Use `shred` tool if present

    if not isinstance(relative_target_path, str) or not relative_target_path:
        return False, "Validation Error: Missing or invalid 'target_path'."
    if not isinstance(passes_val, int) or passes_val <= 0:
        return False, "Validation Error: 'passes' must be a positive integer."

    target_abs_path = resolve_path(
        project_root, relative_target_path, ensure_exists=True, ensure_is_file=True
    )
    if not target_abs_path:
        return (
            False,
            f"Path Resolution Error: Target file '{relative_target_path}' for wipe not found or invalid.",
        )

    shred_exe = shutil.which("shred") if use_shred_if_available else None

    if shred_exe:
        logger.info(
            f"Using 'shred' utility to wipe '{target_abs_path}'. Passes: {passes_val}."
        )
        # `shred -n <passes> -u <file>` (-u also removes the file after shredding)
        # -z for a final overwrite with zeros.
        shred_cmd_list = [
            "sudo",
            shred_exe,
            "-n",
            str(passes_val),
            "-u",
            "-z",
            str(target_abs_path),
        ]
        success, user_msg, stdout, stderr, rc = _run_subprocess(
            shred_cmd_list,
            project_root,
            "SECURE_WIPE_SHRED",
            action_data,
            step_id_from_block,
        )
        if success:
            return (
                True,
                f"File '{target_abs_path.relative_to(project_root)}' securely wiped and removed using shred. {user_msg}",
            )
        else:
            return (
                False,
                f"Secure wipe using shred failed. {user_msg}. Stdout: {stdout}, Stderr: {stderr}",
            )
    else:  # Manual overwrite Python implementation (as fallback, less robust than shred)
        logger.warning(
            f"'shred' utility not found or not used. Performing manual overwrite for '{target_abs_path}'. This is slower and might be less secure on some filesystems/hardware."
        )
        try:
            file_size = target_abs_path.stat().st_size
            if file_size == 0:  # Nothing to overwrite if empty
                target_abs_path.unlink()  # Just delete
                return (
                    True,
                    f"Empty file '{target_abs_path.relative_to(project_root)}' removed.",
                )

            with target_abs_path.open(
                "r+b"
            ) as f:  # Open for read/write binary, without truncating
                for i in range(passes_val):
                    logger.info(
                        f"Overwrite pass {i+1}/{passes_val} for '{target_abs_path}'..."
                    )
                    f.seek(0)
                    # Write random data. For very large files, do this in chunks.
                    # os.urandom is cryptographically secure.
                    # Chunking for large files:
                    chunk_size = 1024 * 1024  # 1MB chunks
                    written_bytes = 0
                    while written_bytes < file_size:
                        bytes_to_write = min(chunk_size, file_size - written_bytes)
                        f.write(os.urandom(bytes_to_write))
                        written_bytes += bytes_to_write
                    f.flush()  # Ensure data is written from buffer
                    os.fsync(f.fileno())  # Try to ensure it hits disk

                # Final overwrite with zeros (optional, shred does this with -z)
                logger.info(f"Final overwrite with zeros for '{target_abs_path}'...")
                f.seek(0)
                written_bytes = 0
                while written_bytes < file_size:
                    bytes_to_write = min(chunk_size, file_size - written_bytes)
                    f.write(b"\0" * bytes_to_write)
                    written_bytes += bytes_to_write
                f.flush()
                os.fsync(f.fileno())

            target_abs_path.unlink()  # Delete the file after overwriting
            return (
                True,
                f"File '{target_abs_path.relative_to(project_root)}' securely wiped with {passes_val} manual passes and removed.",
            )
        except Exception as e:
            logger.error(
                f"Error during manual secure wipe of '{relative_target_path}': {e}",
                exc_info=True,
            )
            return False, f"Manual Secure Wipe Error: {type(e).__name__} - {e}"


@handler(name="MANIPULATE_KERNEL_PARAMETER")  # Uses `sysctl` (Linux)
def handle_manipulate_kernel_parameter(
    action_data: Dict, project_root: Path, step_id_from_block: str
) -> Tuple[bool, Dict[str, Any]]:
    parameter_key = action_data.get("parameter")
    value_to_set = action_data.get("value")  # Value should be a string

    if not isinstance(parameter_key, str) or not parameter_key:
        return False, {"error": "Validation Error: Missing or invalid 'parameter' key."}
    if value_to_set is None:  # Value can be empty string, but not None
        return False, {
            "error": "Validation Error: Missing 'value' for kernel parameter."
        }

    sysctl_exe = shutil.which(SYSCTL_EXECUTABLE_NAME)
    if not sysctl_exe:
        return False, {
            "error": f"Tool Not Found: Sysctl executable '{SYSCTL_EXECUTABLE_NAME}' not found. This action is Linux-specific."
        }

    # Command: sudo sysctl -w parameter.key="value"
    # Ensure value is quoted if it contains spaces or special chars, though sysctl usually handles simple values.
    # For safety, if value might have special chars, shlex.quote or similar would be needed if not using list form of command.
    # Here, we construct a single string for the assignment part.
    sysctl_assignment_str = (
        f"{parameter_key}={str(value_to_set)}"  # Ensure value is string
    )
    cmd_list = ["sudo", sysctl_exe, "-w", sysctl_assignment_str]

    success, user_msg, stdout, stderr, rc = _run_subprocess(
        cmd_list,
        project_root,
        "MANIPULATE_KERNEL_PARAMETER",
        action_data,
        step_id_from_block,
    )
    return success, {
        "message": user_msg,
        "stdout": stdout,
        "stderr": stderr,
        "exit_code": rc,
    }


@handler(name="LOAD_KERNEL_MODULE")  # Uses `modprobe` (Linux)
def handle_load_kernel_module(
    action_data: Dict, project_root: Path, step_id_from_block: str
) -> Tuple[bool, Dict[str, Any]]:
    module_name_to_load = action_data.get("module_name")
    module_options_str = action_data.get(
        "options", ""
    )  # String of options like "param1=val1 param2=val2"

    if not isinstance(module_name_to_load, str) or not module_name_to_load:
        return False, {"error": "Validation Error: Missing or invalid 'module_name'."}
    if not isinstance(module_options_str, str):
        return False, {
            "error": "Validation Error: 'options' for module must be a string."
        }

    modprobe_exe = shutil.which(MODPROBE_EXECUTABLE_NAME)
    if not modprobe_exe:
        return False, {
            "error": f"Tool Not Found: Modprobe executable '{MODPROBE_EXECUTABLE_NAME}' not found. This action is Linux-specific."
        }

    cmd_list = ["sudo", modprobe_exe, module_name_to_load]
    if module_options_str:
        # shlex.split is good for parsing options string into list if options have spaces/quotes
        # However, modprobe usually takes options directly as separate args or one quoted string.
        # For simplicity, if options are `param=value foo=bar`, they become separate args.
        cmd_list.extend(shlex.split(module_options_str))

    success, user_msg, stdout, stderr, rc = _run_subprocess(
        cmd_list, project_root, "LOAD_KERNEL_MODULE", action_data, step_id_from_block
    )
    return success, {
        "message": user_msg,
        "stdout": stdout,
        "stderr": stderr,
        "exit_code": rc,
    }


# --- Agent Management (Placeholders/Conceptual - require significant external infrastructure) ---
# These are highly dependent on how agent updates and deployments are managed in your specific environment.
# The current implementation runs a local script.


@handler(name="AGENT_SELF_UPDATE")
def handle_agent_self_update(
    action_data: Dict, project_root: Path, step_id_from_block: str
) -> Tuple[bool, Dict[str, Any]]:
    relative_update_script_path = action_data.get(
        "update_script"
    )  # Script to perform the update
    if (
        not isinstance(relative_update_script_path, str)
        or not relative_update_script_path
    ):
        return False, {"error": "Validation Error: Missing or invalid 'update_script'."}

    update_script_abs = resolve_path(
        project_root,
        relative_update_script_path,
        ensure_exists=True,
        ensure_is_file=True,
    )
    if not update_script_abs:
        return False, {
            "error": f"Path Resolution Error: Update script '{relative_update_script_path}' not found or invalid."
        }

    logger.info(f"Attempting agent self-update using script: {update_script_abs}")
    # This script is expected to handle the update logic, e.g., git pull, download new version, restart agent.
    # It runs with ExWork's current privileges.
    command_list = [str(update_script_abs)]

    success, user_msg, stdout, stderr, rc = _run_subprocess(
        command_list, project_root, "AGENT_SELF_UPDATE", action_data, step_id_from_block
    )
    # For a true self-update, the agent might restart, so response might not be captured by current instance.
    # Orchestrator should handle this.
    return success, {
        "message": user_msg,
        "stdout": stdout,
        "stderr": stderr,
        "exit_code": rc,
    }


@handler(name="AGENT_DEPLOY_TO_HOST")
def handle_agent_deploy_to_host(
    action_data: Dict, project_root: Path, step_id_from_block: str
) -> Tuple[bool, Dict[str, Any]]:
    target_host_desc = action_data.get("host")  # e.g., user@hostname or IP
    relative_deploy_script_path = action_data.get(
        "deploy_script"
    )  # Script that knows how to deploy

    if not isinstance(target_host_desc, str) or not target_host_desc:
        return False, {
            "error": "Validation Error: Missing or invalid 'host' for deployment."
        }
    if (
        not isinstance(relative_deploy_script_path, str)
        or not relative_deploy_script_path
    ):
        return False, {"error": "Validation Error: Missing or invalid 'deploy_script'."}

    deploy_script_abs = resolve_path(
        project_root,
        relative_deploy_script_path,
        ensure_exists=True,
        ensure_is_file=True,
    )
    if not deploy_script_abs:
        return False, {
            "error": f"Path Resolution Error: Deploy script '{relative_deploy_script_path}' not found or invalid."
        }

    logger.info(
        f"Attempting to deploy agent to '{target_host_desc}' using script: {deploy_script_abs}"
    )
    # Deploy script would handle scp/rsync, remote execution, service setup.
    # This script would need credentials or key-based access to the target_host.
    command_list = [str(deploy_script_abs), target_host_desc]

    success, user_msg, stdout, stderr, rc = _run_subprocess(
        command_list,
        project_root,
        "AGENT_DEPLOY_TO_HOST",
        action_data,
        step_id_from_block,
    )
    return success, {
        "message": user_msg,
        "stdout": stdout,
        "stderr": stderr,
        "exit_code": rc,
    }


# INJECT_INTO_PROCESS - Linux Version (Conceptual - Very Advanced and Dangerous)
# For Linux, this usually involves ptrace or custom kernel modules.
# This is a placeholder to acknowledge the Linux focus. Direct, safe, generic process injection
# from a Python script is extremely complex and usually involves OS-specific C libraries or tools.
# GDB can be scripted for this, but that's also complex.
@handler(name="INJECT_INTO_PROCESS")
def handle_inject_into_process(
    action_data: Dict, project_root: Path, step_id_from_block: str
) -> Tuple[bool, str]:
    logger.warning(
        "INJECT_INTO_PROCESS for Linux is highly advanced, OS-dependent, and risky."
    )
    logger.warning(
        "This ExWork handler is a conceptual placeholder for Linux and is NOT a functional safe implementation."
    )

    process_id = action_data.get("process_id")
    # payload_path_or_content = action_data.get("payload") # Path to shellcode file or direct shellcode
    # injection_method = action_data.get("method", "ptrace_gdb_script") # Example methods

    if not isinstance(process_id, int) or process_id <= 0:
        return False, "Validation Error: Invalid 'process_id'."

    # Actual implementation would be very complex and involve:
    # 1. Choosing an injection technique (e.g., ptrace, LD_PRELOAD modification for next launch, shared library injection).
    # 2. Crafting or loading a Linux-compatible payload (e.g., ELF shared library, raw shellcode).
    # 3. Using tools like GDB scripting, or custom C code with ptrace, or tools like `linux-inject`.
    # This is far beyond simple subprocess execution.

    return (
        False,
        "INJECT_INTO_PROCESS (Linux) is not implemented due to complexity and security risks. This is a conceptual placeholder.",
    )


# --- Core Agent Logic ---
def process_instruction_block(
    instruction_json_str: str, current_project_root: Path
) -> Tuple[bool, List[Dict[str, Any]]]:
    action_results_summary_list: List[Dict[str, Any]] = []
    overall_block_success_flag = True

    # Update global PROJECT_ROOT and HISTORY_FILE for this block's execution context
    # This is important if ExWork agent might be called with different project roots over its lifetime (if run as a service)
    # For single invocation from CLI with fixed CWD, it's less critical but good practice.
    global PROJECT_ROOT, HISTORY_FILE
    PROJECT_ROOT = current_project_root.resolve()
    HISTORY_FILE = PROJECT_ROOT / HISTORY_FILE_NAME
    Path(HISTORY_FILE).parent.mkdir(
        parents=True, exist_ok=True
    )  # Ensure history log dir exists

    try:
        instruction_block_data = json.loads(instruction_json_str)
    except json.JSONDecodeError as json_err:
        logger.error(
            f"FATAL JSON Decode Error: {json_err}. Input (first 500 chars): {instruction_json_str[:500]}..."
        )
        action_results_summary_list.append(
            {
                "action_id": "BLOCK_PARSE_ERROR",  # Using 'action_id' for consistency in results list
                "action_type": "JSON_PARSING",
                "success": False,
                "result_payload": {
                    "error": f"JSON Decode Error: {json_err}",
                    "details": str(json_err),
                },
            }
        )
        return False, action_results_summary_list

    if not isinstance(instruction_block_data, dict):
        logger.error("FATAL: Instruction block is not a JSON object (dictionary).")
        action_results_summary_list.append(
            {
                "action_id": "BLOCK_VALIDATION_ERROR",
                "action_type": "BLOCK_STRUCTURE",
                "success": False,
                "result_payload": {"error": "Instruction block must be a JSON object."},
            }
        )
        return False, action_results_summary_list

    block_step_id = instruction_block_data.get(
        "step_id", str(uuid.uuid4())
    )  # Use provided or generate
    block_description = instruction_block_data.get("description", "N/A")
    actions_to_execute = instruction_block_data.get("actions", [])

    logger.info(
        f"Processing ExWork Block - StepID: {block_step_id}, Description: '{block_description}'"
    )
    if not isinstance(actions_to_execute, list):
        logger.error(
            f"Block '{block_step_id}': 'actions' field must be a list. Found type: {type(actions_to_execute)}."
        )
        action_results_summary_list.append(
            {
                "action_id": "BLOCK_ACTIONS_VALIDATION_ERROR",
                "action_type": "BLOCK_STRUCTURE",
                "success": False,
                "result_payload": {"error": "'actions' field must be a list."},
            }
        )
        return False, action_results_summary_list

    for i, current_action_data in enumerate(actions_to_execute):
        action_num_human = i + 1
        action_id_from_data = current_action_data.get(
            "id", f"action_{action_num_human}"
        )  # Prefer 'id' from action if present

        if not isinstance(current_action_data, dict):
            logger.error(
                f"Block '{block_step_id}', Action {action_num_human}: Data is not a dictionary. Skipping."
            )
            action_results_summary_list.append(
                {
                    "action_id": action_id_from_data,
                    "action_type": "ACTION_VALIDATION",
                    "success": False,
                    "result_payload": {
                        "error": f"Action {action_num_human} data is not a dictionary."
                    },
                }
            )
            overall_block_success_flag = False
            continue  # Move to next action if this one is malformed

        action_type_name = current_action_data.get("type")
        logger.info(
            f"--- Block '{block_step_id}': Executing Action {action_num_human}/{len(actions_to_execute)} (ID: '{action_id_from_data}', Type: '{action_type_name}') ---"
        )

        handler_function = ACTION_HANDLERS.get(action_type_name)
        if handler_function:
            action_start_time = time.time()
            try:
                action_success, action_result_payload = handler_function(
                    current_action_data, PROJECT_ROOT, block_step_id
                )
            except Exception as handler_exc:  # Catch unexpected errors within a handler
                logger.error(
                    f"Block '{block_step_id}', Action '{action_id_from_data}' ({action_type_name}): Unhandled exception in handler: {handler_exc}",
                    exc_info=True,
                )
                action_success = False
                action_result_payload = {
                    "error": f"Handler Exception: {type(handler_exc).__name__} - {handler_exc}",
                    "traceback": traceback.format_exc(limit=3),
                }

            action_duration_s = time.time() - action_start_time

            action_summary_entry = {
                "action_id": action_id_from_data,
                "action_type": action_type_name,
                "success": action_success,
                "result_payload": action_result_payload,  # This can be a string or a dict
                "duration_seconds": round(action_duration_s, 3),
            }
            action_results_summary_list.append(action_summary_entry)

            if not action_success:
                logger.error(
                    f"Block '{block_step_id}', Action '{action_id_from_data}' ({action_type_name}) FAILED. Result: {str(action_result_payload)[:500]}..."
                )
                overall_block_success_flag = False
                # Halt further actions in this block on first failure
                logger.info(
                    f"Halting execution of block '{block_step_id}' due to action failure."
                )
                break
            else:
                logger.info(
                    f"Block '{block_step_id}', Action '{action_id_from_data}' ({action_type_name}) SUCCEEDED. Duration: {action_duration_s:.3f}s"
                )
        else:
            logger.error(
                f"Block '{block_step_id}', Action '{action_id_from_data}': Unknown action type '{action_type_name}'. Halting block."
            )
            action_results_summary_list.append(
                {
                    "action_id": action_id_from_data,
                    "action_type": action_type_name,
                    "success": False,
                    "result_payload": {
                        "error": f"Unknown action type: '{action_type_name}'."
                    },
                }
            )
            overall_block_success_flag = False
            break  # Halt on unknown action type

    logger.info(
        f"--- Finished Processing ExWork Block - StepID: {block_step_id}. Overall Block Success: {overall_block_success_flag} ---"
    )
    return overall_block_success_flag, action_results_summary_list


def main_exwork_agent(
    json_input_str: Optional[str] = None, cli_project_root: Optional[str] = None
):
    """
    Main logic for ExWork agent.
    Can take JSON input string and project_root as args for programmatic calls,
    or reads from stdin if json_input_str is None.
    """
    global PROJECT_ROOT, HISTORY_FILE  # Allow main function to set these based on CWD or args

    if cli_project_root:
        effective_project_root = Path(cli_project_root).resolve()
        if not effective_project_root.is_dir():
            logger.critical(
                f"Provided project root '{cli_project_root}' is not a valid directory. Exiting."
            )
            # Output a JSON error structure if called programmatically and failing early
            sys.stdout.write(
                json.dumps(
                    {
                        "overall_success": False,
                        "status_message": f"Invalid project root: {cli_project_root}",
                    }
                )
                + "\n"
            )
            sys.exit(2)  # Specific exit code for bad project root
    else:
        effective_project_root = Path.cwd().resolve()

    # Initialize global PROJECT_ROOT and HISTORY_FILE here based on effective_project_root
    PROJECT_ROOT = effective_project_root
    HISTORY_FILE = PROJECT_ROOT / HISTORY_FILE_NAME
    try:
        HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    except Exception as e_dir:
        # This is critical, agent might not be able to log history.
        logger.error(
            f"Could not create history log directory {HISTORY_FILE.parent}: {e_dir}. History logging will fail."
        )
        # Proceeding anyway, but history will be lost.

    # Check for required external tools and log warnings if missing
    # This is informational; individual handlers will fail if their specific tool is missing.
    for tool_name in [
        RUFF_EXECUTABLE_NAME,
        NMAP_EXECUTABLE_NAME,
        SYSCTL_EXECUTABLE_NAME,
        IP_ROUTE_EXECUTABLE_NAME,
        MODPROBE_EXECUTABLE_NAME,
        PATCH_EXECUTABLE_NAME,
        "git",
    ]:
        if not shutil.which(tool_name):
            logger.warning(
                f"External tool '{tool_name}' not found in PATH. Related ExWork actions may fail."
            )
    if not CRYPTO_AVAILABLE:
        logger.warning(
            "PyCryptodome library not found. ENCRYPT_DECRYPT_TARGET action will fail."
        )

    logger.info("--- Agent Ex-Work V2.3 (Apex Edition, Linux Focused) Initialized ---")
    logger.info(f"Project Root (CWD for this run): {PROJECT_ROOT}")
    logger.info(f"History Log File: {HISTORY_FILE}")

    input_json_to_process: str
    if json_input_str is None:  # Read from stdin if no direct input string
        logger.info(
            "Expecting JSON instruction block from stdin. Send EOF (Ctrl+D / Ctrl+Z+Enter) after JSON."
        )
        stdin_lines = []
        try:
            for line in sys.stdin:
                stdin_lines.append(line)
        except KeyboardInterrupt:
            logger.info("Interrupted by user while reading stdin. Exiting.")
            sys.stdout.write(
                json.dumps(
                    {
                        "overall_success": False,
                        "status_message": "Interrupted by user during stdin read.",
                    }
                )
                + "\n"
            )
            sys.exit(130)  # Standard exit code for Ctrl+C
        except Exception as e_stdin:
            logger.error(f"Error reading from stdin: {e_stdin}", exc_info=True)
            sys.stdout.write(
                json.dumps(
                    {
                        "overall_success": False,
                        "status_message": f"Stdin read error: {e_stdin}",
                    }
                )
                + "\n"
            )
            sys.exit(1)
        input_json_to_process = "".join(stdin_lines)
    else:
        input_json_to_process = json_input_str

    if not input_json_to_process.strip():
        logger.warning("No JSON input provided. Exiting.")
        sys.stdout.write(
            json.dumps(
                {"overall_success": False, "status_message": "No JSON input received."}
            )
            + "\n"
        )
        sys.exit(0)  # Not an error, just no work to do.

    logger.info(f"Processing {len(input_json_to_process)} bytes of instruction JSON...")
    block_processing_start_time = time.time()

    overall_success_status, list_of_action_results = process_instruction_block(
        input_json_to_process, PROJECT_ROOT
    )

    block_processing_duration_s = round(time.time() - block_processing_start_time, 3)
    final_status_message = f"ExWork block processing finished. Overall Success: {overall_success_status}. Duration: {block_processing_duration_s}s"
    logger.info(final_status_message)

    # Final output payload for orchestrator / CLI / WebUI
    output_summary_payload = {
        "overall_success": overall_success_status,
        "status_message": final_status_message,
        "total_duration_seconds": block_processing_duration_s,
        "action_results": list_of_action_results,  # List of dicts, one for each action
    }

    sys.stdout.write(
        json.dumps(output_summary_payload, indent=2) + "\n"
    )  # Pretty print if stdout is a TTY, compact if piped.
    # For now, always indent for readability.
    sys.stdout.flush()

    if not overall_success_status:
        sys.exit(1)  # Standard failure exit code
    else:
        sys.exit(0)  # Standard success exit code


if __name__ == "__main__":
    # Allow passing project_root and input JSON via CLI args for testing/dev
    # This is a simple CLI for the agent itself, not the main Omnitide CLI.
    # Example: python exworkagent.py --root /path/to/project --json '{"actions":...}'
    #          python exworkagent.py --root /path/to/project < task.json

    # Basic argument parsing for standalone agent execution
    # This is NOT using Typer/Click to keep agent dependencies minimal.
    custom_project_root = None
    input_json_direct = None
    input_json_file = None

    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--root" and i + 1 < len(args):
            custom_project_root = args[i + 1]
            i += 1
        elif args[i] == "--json" and i + 1 < len(args):
            input_json_direct = args[i + 1]
            i += 1
        elif args[i] == "--json-file" and i + 1 < len(args):
            input_json_file = args[i + 1]
            i += 1
        elif args[i] in ["-h", "--help"]:
            print("ExWork Agent v2.3 Standalone Runner")
            print(
                "Usage: python exworkagent.py [--root <project_root_path>] [--json <json_string> | --json-file <path_to_json_file>]"
            )
            print("If no --json or --json-file, reads JSON from stdin.")
            sys.exit(0)
        else:
            print(f"Unknown argument: {args[i]}. Use --help for usage.")
            sys.exit(1)
        i += 1

    final_json_input = None
    if input_json_direct:
        final_json_input = input_json_direct
    elif input_json_file:
        try:
            final_json_input = Path(input_json_file).read_text(encoding="utf-8")
        except Exception as e_file:
            logger.critical(
                f"Error reading JSON from file '{input_json_file}': {e_file}"
            )
            sys.stdout.write(
                json.dumps(
                    {
                        "overall_success": False,
                        "status_message": f"Error reading JSON file: {e_file}",
                    }
                )
                + "\n"
            )
            sys.exit(1)

    main_exwork_agent(
        json_input_str=final_json_input, cli_project_root=custom_project_root
    )
