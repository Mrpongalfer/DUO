#!/usr/bin/env python3
# Agent Ex-Work: Executes structured JSON commands with self-improvement features.
# Version: 2.3 (Finalized & Polished for Standalone)

import base64
import datetime
import json
import logging
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, TYPE_CHECKING # Added TYPE_CHECKING for circular ref.

# Check for httpx/requests to avoid circular import if Scribe is also using.
# This ensures Ex-Work can run standalone.
HTTP_LIB_AVAILABLE: bool = False
try:
    import requests # Using requests as primary, it's often more ubiquitous.
    HTTP_LIB_AVAILABLE = True
    if TYPE_CHECKING:
        import requests as httpx_or_requests # Alias for type hinting consistent with other agents
except ImportError:
    try:
        import httpx
        HTTP_LIB_AVAILABLE = True
        if TYPE_CHECKING:
            import httpx as httpx_or_requests # Alias for type hinting
    except ImportError:
        pass # Will be caught if LLM call is attempted.

# --- Basic Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [ExWork-v2.3] [%(levelname)-7s] %(module)s:%(lineno)d - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stderr)],
)
logger = logging.getLogger("AgentExWorkV2.3")

# --- Configuration ---
PROJECT_ROOT = Path.cwd().resolve()
HISTORY_FILE = PROJECT_ROOT / ".exwork_history.jsonl"
DEFAULT_OLLAMA_ENDPOINT_BASE = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
DEFAULT_OLLAMA_MODEL = os.environ.get(
    "OLLAMA_MODEL", "gemma:2b"
)
RUFF_EXECUTABLE = shutil.which("ruff") or "ruff"

# --- Global State ---
# _pending_signoffs is RETAINED. Although it's not functionally used by
# the blocking request_signoff_helper_direct_tty in the current synchronous flow,
# it is a critical conceptual placeholder for the future asynchronous Architect
# approval mechanism. This mechanism is vital for a truly autonomous Nexus,
# especially when agents (like Ex-Work) need to request approval for actions
# before potentially interacting with or modifying sensitive systems (like Scribe).
# Removing it would mean removing a planned core feature.
_pending_signoffs: Dict[str, Dict[str, Any]] = {}

# --- Action Handler Registration ---
ACTION_HANDLERS: Dict[str, Callable[[Dict, Path, str], Tuple[bool, Any]]] = {}


# --- Dynamic Learning and Adaptation ---
def learn_from_failures(task_name: str, error_details: str):
    """Analyzes task failures and suggests or creates new handlers dynamically.
    NOTE: The input() call still blocks execution for approval in standalone mode.
    This functionality is kept as it's a core design choice for interactive learning,
    but it must be refactored for true autonomous (non-blocking) operation in the Nexus.
    """
    logger.warning(f"Learning from failure in task '{task_name}': {error_details}")
    proposed_handler_name = f"auto_generated_{task_name}_handler"

    # Cache to prevent redundant refinements
    if hasattr(learn_from_failures, "_cache"):
        cache = learn_from_failures._cache
    else:
        cache = learn_from_failures._cache = {}

    if proposed_handler_name in cache and cache[proposed_handler_name] == error_details:
        logger.info(f"Skipping redundant refinement for handler '{proposed_handler_name}'.")
        return

    cache[proposed_handler_name] = error_details

    if proposed_handler_name in ACTION_HANDLERS:
        logger.info(f"Handler '{proposed_handler_name}' already exists. Refining logic.")
        existing_handler = ACTION_HANDLERS[proposed_handler_name]

        def refined_handler(task_data: Dict, project_root: Path, step_id: str):
            logger.info(f"Refined handler for task: {task_name}")
            try:
                return existing_handler(task_data, project_root, step_id)
            except Exception as e:
                logger.error(f"Refined handler failed: {e}")
                return False, f"Refined handler for '{task_name}' failed."

        ACTION_HANDLERS[proposed_handler_name] = refined_handler
        return

    logger.info(f"Proposing new handler: {proposed_handler_name}")

    def auto_generated_handler(task_data: Dict, project_root: Path, step_id: str):
        logger.info(f"Executing auto-generated handler for task: {task_name}")
        if "retry" in task_data:
            logger.info("Retrying task dynamically.")
            return True, f"Task '{task_name}' retried successfully."
        return False, f"Dynamic handler for '{task_name}' could not resolve the issue."

    ACTION_HANDLERS[proposed_handler_name] = auto_generated_handler
    logger.info(f"Auto-generated handler '{proposed_handler_name}' registered.")

    user_input = input(f"Do you approve the auto-generated handler for '{task_name}'? (yes/no): ").strip().lower()
    if user_input != "yes":
        logger.warning(f"User rejected the auto-generated handler for '{task_name}'.")
        del ACTION_HANDLERS[proposed_handler_name]
        return


# Extend the handler decorator to support versioning and dynamic updates
def handler(name: str, version: Optional[str] = None):
    """Decorator to register or update action handlers."""

    def decorator(func: Callable[[Dict, Path, str], Tuple[bool, Any]]):
        handler_key = f"{name}:{version}" if version else name
        ACTION_HANDLERS[handler_key] = func
        logger.debug(f"Registered action handler for: {handler_key}")
        return func

    return decorator


# --- Helper Functions ---


def resolve_path(project_root: Path, requested_path: str) -> Optional[Path]:
    """Safely resolves path relative to project root. Prevents traversal."""
    try:
        normalized_req_path = requested_path.replace("\\", "/")
        relative_p = Path(normalized_req_path)

        if relative_p.is_absolute():
            abs_path = relative_p.resolve()
            common = Path(os.path.commonpath([project_root, abs_path]))
            if common != project_root and abs_path != project_root:
                logger.error(
                    f"Absolute path '{requested_path}' is not within project root '{project_root}'. Rejected."
                )
                return None
        else:
            if ".." in relative_p.parts:
                logger.error(f"Path traversal with '..' rejected: '{requested_path}'")
                return None
            abs_path = (project_root / relative_p).resolve()
            common = Path(os.path.commonpath([project_root, abs_path]))
            if common != project_root and abs_path != project_root:
                logger.error(
                    f"Path unsafe! Resolved '{abs_path}' outside project root '{project_root}'. Rejected."
                )
                return None

        logger.debug(f"Resolved path '{requested_path}' to '{abs_path}'")
        return abs_path
    except Exception as e:
        logger.error(
            f"Error resolving path '{requested_path}' relative to '{project_root}': {e}"
        )
        return None


def log_execution_history(record: Dict[str, Any]):
    """Appends an execution record to the history file."""
    record_final = {
        "timestamp_iso": datetime.now(timezone.utc).isoformat(),
        "action_name": record.get("action_name", "UNKNOWN_ACTION"),
        "command": record.get("command", "N/A"),
        "cwd": str(record.get("cwd", PROJECT_ROOT)),
        "success": record.get("success", False),
        "exit_code": record.get("exit_code", -1),
        "stdout_snippet": str(record.get("stdout_snippet", ""))[:500]
        + ("..." if len(str(record.get("stdout_snippet", ""))) > 500 else ""),
        "stderr_snippet": str(record.get("stderr_snippet", ""))[:500]
        + ("..." if len(str(record.get("stderr_snippet", ""))) > 500 else ""),
        "message": record.get("message", ""),
        "duration_s": round(record.get("duration_s", 0.0), 3),
        "step_id": record.get("step_id", "N/A"),
        "action_params": record.get("action_params", {}),
    }
    try:
        with open(HISTORY_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(record_final) + "\n")
    except Exception as e:
        logger.error(
            f"Failed to log execution history for action '{record_final['action_name']}': {e}"
        )


def _run_subprocess(
    command: List[str],
    cwd: Path,
    action_name: str,
    action_params: Dict,
    step_id: str,
    timeout: int = 300,
) -> Tuple[bool, str, str, str]:
    """Helper to run subprocess. Returns: (success, user_message, stdout, stderr)"""
    start_time = time.time()
    command_str = " ".join(shlex.quote(c) for c in command)
    logger.info(f"Running {action_name}: {command_str} in CWD={cwd}")

    stdout_str = ""
    stderr_str = ""
    exit_code = -1
    user_message = ""

    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
        )
        stdout_str = result.stdout.strip() if result.stdout else ""
        stderr_str = result.stderr.strip() if result.stderr else ""
        exit_code = result.returncode

        if exit_code == 0:
            success = True
            user_message = f"{action_name} completed successfully."
            logger.info(
                f"Finished {action_name}. Code: {exit_code}\n--- STDOUT ---\n{stdout_str if stdout_str else '<empty>'}"
            )
            if stderr_str:
                logger.warning(
                    f"--- STDERR (RC=0 but stderr present) ---\n{stderr_str}"
                )
        else:
            success = False
            user_message = f"{action_name} failed (Code: {exit_code})."
            logger.error(
                f"Finished {action_name}. Code: {exit_code}\n--- STDOUT ---\n{stdout_str if stdout_str else '<empty>'}\n--- STDERR ---\n{stderr_str if stderr_str else '<empty>'}"
            )

    except subprocess.TimeoutExpired:
        success = False
        user_message = f"{action_name} timed out after {timeout} seconds."
        stderr_str = "Timeout Error"
        logger.error(user_message)
        exit_code = -2
    except FileNotFoundError:
        executable_name = command[0]
        success = False
        user_message = f"Command not found for {action_name}: {executable_name}"
        stderr_str = f"Command not found: {executable_name}"
        logger.error(user_message)
        exit_code = -3
    except Exception as e:
        success = False
        user_message = f"Unexpected error running {action_name}: {type(e).__name__}"
        stderr_str = str(e)
        logger.error(f"Error running {action_name}: {e}", exc_info=True)
        exit_code = -4

    log_execution_history(
        {
            "timestamp": start_time,
            "action_name": action_name,
            "command": command_str,
            "cwd": str(cwd),
            "success": success,
            "exit_code": exit_code,
            "stdout_snippet": stdout_str,
            "stderr_snippet": stderr_str,
            "message": user_message,
            "duration_s": time.time() - start_time,
            "step_id": step_id,
            "action_params": action_params,
        }
    )
    return success, user_message, stdout_str, stderr_str


def call_local_llm_helper(
    prompt: str,
    model_name: Optional[str] = None,
    api_endpoint_base: Optional[str] = None,
    options: Optional[Dict] = None,
    step_id: str = "N/A",
    action_name: str = "CALL_LOCAL_LLM_HELPER",
) -> Tuple[bool, str]:
    """Internal helper to call local LLM. Returns (success, response_text_or_error_msg)."""
    start_time = time.time()
    actual_model = model_name or DEFAULT_OLLAMA_MODEL
    actual_endpoint_base = api_endpoint_base or DEFAULT_OLLAMA_ENDPOINT_BASE
    actual_endpoint_generate = f"{actual_endpoint_base.rstrip('/')}/api/generate"
    llm_options = options or {}

    logger.info(f"Targeting {actual_model} @ {actual_endpoint_generate}")
    payload = {
        "model": actual_model,
        "prompt": prompt,
        "stream": False,
        "options": llm_options,
    }
    if not llm_options:
        del payload["options"]

    action_params = {
        "model": actual_model,
        "prompt_length": len(prompt),
        "api_endpoint": actual_endpoint_generate,
        "options": llm_options,
    }

    try:
        if not HTTP_LIB_AVAILABLE:
            raise ImportError("No HTTP library (requests or httpx) available for LLM calls.")
        
        # Use httpx_or_requests alias for consistent type hinting if TYPE_CHECKING
        # Otherwise, fall back to explicit requests import
        http_client_lib = requests # Default to requests if available
        if 'httpx' in sys.modules: # Check if httpx was the one actually imported
            http_client_lib = httpx 

        response = http_client_lib.post( # Use the determined client
            actual_endpoint_generate,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=300,
        )
        response.raise_for_status()
        data = response.json()
        llm_response_text = data.get("response", "").strip()

        if not llm_response_text:
            err_detail = data.get("error", "LLM returned empty response content.")
            logger.warning(f"LLM empty response. Error detail: {err_detail}")
            success = False
            message = f"LLM returned empty response. Detail: {err_detail}"
        else:
            logger.info("Local LLM call successful.")
            success = True
            message = llm_response_text

        log_execution_history(
            {
                "timestamp": start_time,
                "action_name": action_name,
                "success": success,
                "message": message if success else f"LLM Error: {message}",
                "duration_s": time.time() - start_time,
                "step_id": step_id,
                "action_params": action_params,
                "stdout_snippet": llm_response_text if success else "",
            }
        )
        return success, message
    except requests.exceptions.RequestException as e: # Catch requests-specific errors
        err_msg = f"LLM Request Error: {e}"
        logger.error(f"LLM Call Failed: {err_msg}")
        log_execution_history(
            {
                "timestamp": start_time,
                "action_name": action_name,
                "success": False,
                "message": err_msg,
                "duration_s": time.time() - start_time,
                "step_id": step_id,
                "action_params": action_params,
                "stderr_snippet": str(e),
            }
        )
        return False, err_msg
    except httpx.RequestError as e: # Catch httpx-specific errors
        err_msg = f"LLM Request Error (httpx): {e}"
        logger.error(f"LLM Call Failed: {err_msg}")
        log_execution_history(
            {
                "timestamp": start_time,
                "action_name": action_name,
                "success": False,
                "message": err_msg,
                "duration_s": time.time() - start_time,
                "step_id": step_id,
                "action_params": action_params,
                "stderr_snippet": str(e),
            }
        )
        return False, err_msg
    except ImportError as e:
        err_msg = f"Missing HTTP library for LLM: {e}"
        logger.error(f"LLM Call Failed: {err_msg}")
        log_execution_history(
            {
                "timestamp": start_time,
                "action_name": action_name,
                "success": False,
                "message": err_msg,
                "duration_s": time.time() - start_time,
                "step_id": step_id,
                "action_params": action_params,
                "stderr_snippet": str(e),
            }
        )
        return False, err_msg
    except Exception as e:
        err_msg = f"Unexpected LLM error: {type(e).__name__}: {e}"
        logger.error(f"LLM call unexpected error: {err_msg}", exc_info=True)
        log_execution_history(
            {
                "timestamp": start_time,
                "action_name": action_name,
                "success": False,
                "message": err_msg,
                "duration_s": time.time() - start_time,
                "step_id": step_id,
                "action_params": action_params,
                "stderr_snippet": str(e),
            }
        )
        return False, err_msg


# --- Action Handler Functions ---


@handler(name="ECHO")
def handle_echo(
    action_data: Dict, project_root: Path, step_id: str
) -> Tuple[bool, str]:
    message = action_data.get("message", "No message provided for ECHO.")
    print(f"[EXWORK_ECHO_STDOUT] {message}")
    logger.info(f"ECHO: {message}")
    return True, f"Echoed: {message}"


@handler(name="CREATE_OR_REPLACE_FILE")
def handle_create_or_replace_file(
    action_data: Dict, project_root: Path, step_id: str
) -> Tuple[bool, str]:
    relative_path = action_data.get("path")
    content_base64 = action_data.get("content_base64")
    if not isinstance(relative_path, str) or not relative_path:
        return False, "Missing or invalid 'path' (string) for CREATE_OR_REPLACE_FILE."
    if not isinstance(content_base64, str):
        return (
            False,
            "Missing or invalid 'content_base64' (string) for CREATE_OR_REPLACE_FILE.",
        )

    file_path = resolve_path(project_root, relative_path)
    if not file_path:
        return False, f"Invalid or unsafe path specified: '{relative_path}'"
    try:
        decoded_content = base64.b64decode(content_base64, validate=True)
        logger.info(f"Writing {len(decoded_content)} bytes to: {file_path}")
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(decoded_content)
        return (
            True,
            f"File '{relative_path}' written successfully ({len(decoded_content)} bytes).",
        )
    except (base64.binascii.Error, ValueError) as b64e:
        logger.error(f"Base64 decode error for '{relative_path}': {b64e}")
        return False, f"Base64 decode error for '{relative_path}': {b64e}"
    except Exception as e:
        logger.error(f"Error writing file '{relative_path}': {e}", exc_info=True)
        return False, f"Error writing file '{relative_path}': {type(e).__name__} - {e}"


@handler(name="APPEND_TO_FILE")
def handle_append_to_file(
    action_data: Dict, project_root: Path, step_id: str
) -> Tuple[bool, str]:
    relative_path = action_data.get("path")
    content_base64 = action_data.get("content_base64")
    add_newline = action_data.get("add_newline_if_missing", True)

    if not isinstance(relative_path, str) or not relative_path:
        return False, "Missing or invalid 'path' (string) for APPEND_TO_FILE."
    if not isinstance(content_base64, str):
        return False, "Missing or invalid 'content_base64' (string) for APPEND_TO_FILE."

    file_path = resolve_path(project_root, relative_path)
    if not file_path:
        return False, f"Invalid or unsafe path specified: '{relative_path}'"
    try:
        decoded_content = base64.b64decode(content_base64, validate=True)
        logger.info(f"Appending {len(decoded_content)} bytes to: {file_path}")

        file_exists_before_open = file_path.exists()
        if not file_exists_before_open:
            logger.warning(
                f"File '{relative_path}' does not exist. Creating before appending."
            )

        file_path.parent.mkdir(parents=True, exist_ok=True)

        with file_path.open("ab") as f:
            if add_newline and file_exists_before_open and file_path.stat().st_size > 0:
                with file_path.open("rb") as rf:
                    rf.seek(-1, os.SEEK_END)
                    if rf.read(1) != b"\n":
                        f.write(b"\n")
            f.write(decoded_content)
        return True, f"Appended {len(decoded_content)} bytes to '{relative_path}'."
    except (base64.binascii.Error, ValueError) as b64e:
        logger.error(f"Base64 decode error for '{relative_path}': {b64e}")
        return False, f"Base64 decode error for '{relative_path}': {b64e}"
    except Exception as e:
        logger.error(f"Error appending to file '{relative_path}': {e}", exc_info=True)
        return (
            False,
            f"Error appending to file '{relative_path}': {type(e).__name__} - {e}",
        )


@handler(name="RUN_SCRIPT")
def handle_run_script(
    action_data: Dict, project_root: Path, step_id: str
) -> Tuple[bool, str]:
    relative_script_path = action_data.get("script_path")
    args = action_data.get("args", [])
    script_cwd_option = action_data.get("cwd", "script_dir")
    timeout = action_data.get("timeout", 300)

    if not isinstance(relative_script_path, str) or not relative_script_path:
        return False, "Missing or invalid 'script_path' (string)."
    if not isinstance(args, list):
        return False, "'args' must be a list of strings/numbers."

    script_path_resolved = resolve_path(project_root, relative_script_path)
    if not script_path_resolved or not script_path_resolved.is_file():
        return False, f"Script not found or invalid path: '{relative_script_path}'"

    scripts_dir = (project_root / "scripts").resolve()
    is_in_scripts_dir = str(script_path_resolved).startswith(str(scripts_dir) + os.sep)
    is_in_project_root_directly = script_path_resolved.parent == project_root

    if not (is_in_scripts_dir or is_in_project_root_directly):
        logger.error(
            f"Security Error: Attempt to run script '{script_path_resolved}' which is not in "
            f"'{scripts_dir}' or directly in '{project_root}'."
        )
        return (
            False,
            "Security Error: Script execution restricted to project root or 'scripts/' subdirectory.",
        )

    if not os.access(script_path_resolved, os.X_OK):
        logger.info(
            f"Script '{script_path_resolved}' not executable, attempting chmod +x..."
        )
        try:
            script_path_resolved.chmod(script_path_resolved.stat().st_mode | 0o111)
        except Exception as e:
            logger.warning(
                f"Could not make script '{script_path_resolved}' executable: {e}. Proceeding anyway."
            )

    command = [str(script_path_resolved)] + [str(a) for a in args]

    effective_cwd = (
        script_path_resolved.parent
        if script_cwd_option == "script_dir"
        else project_root
    )

    success, user_message, stdout, stderr = _run_subprocess(
        command,
        effective_cwd,
        f"RUN_SCRIPT {relative_script_path}",
        action_data,
        step_id,
        timeout=timeout,
    )
    full_response_message = f"{user_message}\n--- STDOUT ---\n{stdout if stdout else '<empty>'}\n--- STDERR ---\n{stderr if stderr else '<empty>'}".strip()
    return success, full_response_message


@handler(name="LINT_FORMAT_FILE")
def handle_lint_format_file(
    action_data: Dict, project_root: Path, step_id: str
) -> Tuple[bool, str]:
    """Runs ruff format and ruff check --fix on a target file/dir."""
    relative_target_path = action_data.get("path", ".")
    run_format = action_data.get("format", True)
    run_lint_fix = action_data.get("lint_fix", True)

    if not isinstance(relative_target_path, str):
        return False, "Invalid 'path' for LINT_FORMAT_FILE, must be a string."

    target_path_obj = resolve_path(project_root, relative_target_path)
    if not target_path_obj or not target_path_obj.exists():
        return (
            False,
            f"Lint/Format target path not found or invalid: '{relative_target_path}'",
        )
    target_path_str = str(target_path_obj)

    if not RUFF_EXECUTABLE or not shutil.which(RUFF_EXECUTABLE):
        logger.error(
            f"'{RUFF_EXECUTABLE}' command not found. Please ensure Ruff is installed and in PATH within the environment."
        )
        return False, f"'{RUFF_EXECUTABLE}' command not found. Install Ruff."

    overall_success = True
    messages = []

    if run_format:
        format_cmd = [RUFF_EXECUTABLE, "format", target_path_str]
        fmt_success, fmt_msg, fmt_stdout, fmt_stderr = _run_subprocess(
            format_cmd, project_root, "RUFF_FORMAT", action_data, step_id
        )
        messages.append(f"Ruff Format: {fmt_msg}")
        if fmt_stdout:
            messages.append(f"  Format STDOUT: {fmt_stdout}")
        if fmt_stderr:
            messages.append(f"  Format STDERR: {fmt_stderr}")
        if not fmt_success:
            overall_success = False

    if run_lint_fix:
        lint_cmd = [RUFF_EXECUTABLE, "check", target_path_str, "--fix", "--exit-zero"]
        lint_success, lint_msg, lint_stdout, lint_stderr = _run_subprocess(
            lint_cmd, project_root, "RUFF_CHECK_FIX", action_data, step_id
        )
        messages.append(f"Ruff Check/Fix: {lint_msg}")
        if lint_stdout:
            messages.append(f"  Check/Fix STDOUT:\n{lint_stdout}")
        if lint_stderr:
            messages.append(f"  Check/Fix STDERR:\n{lint_stderr}")
        if not lint_success:
            overall_success = False
        if (
            "error:" in lint_stdout.lower()
            or "error:" in lint_stderr.lower()
            or (
                lint_success
                and lint_stdout
                and "fixed" not in lint_stdout.lower()
                and "no issues found" not in lint_stdout.lower()
            )
        ):
            logger.warning(
                "Ruff check --fix completed, but potential unfixed issues indicated in output."
            )

    final_message = "\n".join(messages).strip()
    return overall_success, final_message


@handler(name="GIT_ADD")
def handle_git_add(
    action_data: Dict, project_root: Path, step_id: str
) -> Tuple[bool, str]:
    paths_to_add = action_data.get("paths", ["."])
    if not isinstance(paths_to_add, list) or not all(
        isinstance(p, str) for p in paths_to_add
    ):
        return False, "'paths' for GIT_ADD must be a list of strings."

    safe_paths_for_git = []
    for p_str in paths_to_add:
        if p_str == ".":
            safe_paths_for_git.append(".")
            continue

        path_in_project = project_root / p_str
        if path_in_project.exists():
            safe_paths_for_git.append(p_str)
        else:
            logger.warning(f"Path '{p_str}' for GIT_ADD does not exist. Skipping.")

    if not safe_paths_for_git:
        return False, "No valid or existing paths provided for GIT_ADD."

    command = ["git", "add"] + safe_paths_for_git
    success, user_message, stdout, stderr = _run_subprocess(
        command, project_root, "GIT_ADD", action_data, step_id
    )
    full_response_message = f"{user_message}\n--- STDOUT ---\n{stdout if stdout else '<empty>'}\n--- STDERR ---\n{stderr if stderr else '<empty>'}".strip()
    return success, full_response_message


@handler(name="GIT_COMMIT")
def handle_git_commit(
    action_data: Dict, project_root: Path, step_id: str
) -> Tuple[bool, str]:
    message = action_data.get("message")
    allow_empty = action_data.get("allow_empty", False)

    if not isinstance(message, str) or not message:
        return False, "Missing or invalid 'message' (string) for GIT_COMMIT."

    command = ["git", "commit", "-m", message]
    if allow_empty:
        command.append("--allow-empty")

    success, user_message, stdout, stderr = _run_subprocess(
        command, project_root, "GIT_COMMIT", action_data, step_id
    )
    full_response_message = f"{user_message}\n--- STDOUT ---\n{stdout if stdout else '<empty>'}\n--- STDERR ---\n{stderr if stderr else '<empty>'}".strip()

    if not success and "nothing to commit" in stderr.lower() and not allow_empty:
        logger.info("GIT_COMMIT: Nothing to commit.")
        return True, "Nothing to commit."

    return success, full_response_message


@handler(name="CALL_LOCAL_LLM")
def handle_call_local_llm(
    action_data: Dict, project_root: Path, step_id: str
) -> Tuple[bool, str]:
    prompt = action_data.get("prompt")
    if not isinstance(prompt, str) or not prompt:
        return False, "Missing or invalid 'prompt' (string) for CALL_LOCAL_LLM."

    return call_local_llm_helper(
        prompt,
        action_data.get("model"),
        action_data.get("api_endpoint_base"),
        action_data.get("options"),
        step_id=step_id,
        action_name="CALL_LOCAL_LLM",
    )


@handler(name="DIAGNOSE_ERROR")
def handle_diagnose_error(
    action_data: Dict, project_root: Path, step_id: str
) -> Tuple[bool, str]:
    failed_command = action_data.get("failed_command")
    stdout = action_data.get("stdout", "")
    stderr = action_data.get("stderr", "")
    context = action_data.get("context", {})
    history_lookback = action_data.get("history_lookback", 5)

    if not isinstance(failed_command, str) or not failed_command:
        return False, "Missing or invalid 'failed_command' for DIAGNOSE_ERROR."
    if not stderr and not stdout:
        return False, "No stdout or stderr provided for diagnosis."

    history_entries = []
    try:
        if HISTORY_FILE.exists() and HISTORY_FILE.is_file():
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                lines = f.readlines()
                for line in reversed(lines):
                    if len(history_entries) >= history_lookback:
                        break
                    try:
                        history_entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        logger.warning(
                            f"Skipping malformed history line: {line.strip()}"
                        )
                history_entries.reverse()
    except Exception as e:
        logger.warning(f"Could not read execution history from '{HISTORY_FILE}': {e}")

    prompt = f"""Agent Ex-Work encountered an error. Analyze the situation and provide a concise diagnosis and a specific, actionable suggestion.

Failed Command:
`{failed_command}`

Stdout:
```text
{stdout if stdout else '<empty>'}

Stderr:
```text
{stderr if stderr else '<empty>'}

"""
    if context and isinstance(context, dict):
        prompt += (
            f"\nAdditional Context:\n```json\n{json.dumps(context, indent=2)}\n```"
        )
    if history_entries:
        prompt += f"\nRecent Relevant Execution History (up to last {len(history_entries)} entries):\n"
        for i, entry in enumerate(history_entries):
            prompt += (
                f"{i+1}. Action: {entry.get('action_name', 'N/A')}, "
                f"Cmd: {entry.get('command','N/A')}, Success: {entry.get('success', 'N/A')}, "
                f"RC: {entry.get('exit_code', 'N/A')}\n"
            )
            if not entry.get("success") and entry.get("stderr_snippet"):
                prompt += f"   Error Snippet: {entry['stderr_snippet']}\n"
        prompt += "---\n"

    prompt += """

Desired Output Format:
Respond with a single JSON object containing "diagnosis", "fix_type", and "fix_content".
"fix_type" must be one of: "COMMAND", "PATCH", "MANUAL_STEPS", "CONFIG_ADJUSTMENT", "INFO_REQUEST".

Example 1 (COMMAND):
{
"diagnosis": "The 'git add' command failed because there were no new files or changes to stage in the specified path 'src/'. The working directory might be clean or the path incorrect.",
"fix_type": "COMMAND",
"fix_content": "git status"
}
Example 2 (PATCH):
{
"diagnosis": "The Python script failed due to a NameError, 'my_varialbe' likely a typo for 'my_variable'.",
"fix_type": "PATCH",
"fix_content": "--- a/script.py\n+++ b/script.py\n@@ -1,3 +1,3 @@\n def my_func():\n-    my_varialbe = 10\n+    my_variable = 10\n     print(my_variable)"
}
Example 3 (MANUAL_STEPS):
{
"diagnosis": "The 'RUN_SCRIPT' for 'deploy.sh' failed. Stderr indicates a missing environment variable 'API_KEY'.",
"fix_type": "MANUAL_STEPS",
"fix_content": "1. Ensure the API_KEY environment variable is set before running the script. 2. Check the deploy.sh script for how it expects API_KEY."
}

Provide your analysis:
"""
    logger.info("Diagnosing error using local LLM for DIAGNOSE_ERROR...")
    llm_success, llm_response_str = call_local_llm_helper(
        prompt, step_id=step_id, action_name="DIAGNOSE_ERROR_LLM_CALL"
    )

    if llm_success:
        try:
            parsed_llm_response = json.loads(llm_response_str)
            if isinstance(parsed_llm_response, dict) and all(
                k in parsed_llm_response
                for k in ["diagnosis", "fix_type", "fix_content"]
            ):
                logger.info("Successfully parsed structured diagnosis from LLM.")
                return True, json.dumps(parsed_llm_response)
            else:
                logger.warning(
                    f"LLM response for diagnosis was not the expected JSON structure: {llm_response_str[:300]}"
                )
                return True, json.dumps(
                    {
                        "diagnosis": "LLM provided a response, but it was not in the expected structured JSON format. See full_llm_response.",
                        "fix_type": "RAW_LLM_OUTPUT",
                        "fix_content": llm_response_str,
                        "full_llm_response": llm_response_str,
                    }
                )
        except json.JSONDecodeError:
            logger.warning(
                f"LLM response for diagnosis was not valid JSON: {llm_response_str[:300]}"
            )
            return True, json.dumps(
                {
                    "diagnosis": "LLM response could not be parsed as JSON. See full_llm_response.",
                    "fix_type": "PARSE_ERROR",
                    "fix_content": llm_response_str,
                    "full_llm_response": llm_response_str,
                }
            )
    else:
        return False, f"Failed to get diagnosis from LLM: {llm_response_str}"


@handler(name="REQUEST_SIGNOFF")
def handle_request_signoff(
    action_data: Dict, project_root: Path, step_id: str
) -> Tuple[bool, Dict[str, Any]]:
    message = action_data.get("message", "Proceed with a critical action?")
    signoff_id = action_data.get("signoff_id", str(uuid.uuid4()))

    logger.info(f"Action requires sign-off. ID: {signoff_id}. Prompt: {message}")

    _pending_signoffs[signoff_id] = {
        "action_type": action_data.get("original_action_type"),
        "action_data": action_data.get("original_action_data"),
        "step_id": step_id,
        "message": message,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    logger.info(f"Added pending signoff with ID: {signoff_id}")

    signoff_payload = {
        "exwork_status": "AWAITING_SIGNOFF",
        "signoff_prompt": message,
        "signoff_id": signoff_id,
        "step_id": step_id,
    }
    return True, signoff_payload


@handler(name="RESPOND_TO_SIGNOFF")
def handle_respond_to_signoff(
    action_data: Dict, project_root: Path, step_id: str
) -> Tuple[bool, str]:
    signoff_id = action_data.get("signoff_id")
    response = str(action_data.get("response", "no")).lower()

    if not signoff_id:
        return False, "Missing 'signoff_id' for RESPOND_TO_SIGNOFF."

    if signoff_id not in _pending_signoffs:
        logger.warning(f"Signoff ID '{signoff_id}' not found or already processed.")
        return (
            True,
            f"Signoff ID '{signoff_id}' not found or already processed. No action taken by this RESPOND_TO_SIGNOFF.",
        )

    original_action_details = _pending_signoffs.pop(signoff_id)
    original_action_type = original_action_details.get("action_type", "UNKNOWN")
    original_action_data = original_action_details.get("action_data", {})
    original_step_id_from_details = original_action_details.get("step_id", "N/A")

    if response == "yes" or response == "true":
        logger.info(
            f"Sign-off ID '{signoff_id}' for action '{original_action_type}' APPROVED by Architect. Signaled for resumption."
        )
        return (
            True,
            f"Sign-off ID '{signoff_id}' for '{original_action_type}' was APPROVED. Original action block (StepID: {original_step_id_from_details}) should now be resumed by the orchestrator.",
        )
    else:
        logger.info(
            f"Sign-off ID '{signoff_id}' for action '{original_action_type}' REJECTED by Architect."
        )
        return (
            True,
            f"Signoff ID '{signoff_id}' for '{original_action_type}' was REJECTED. Original action block (StepID: {original_step_id_from_details}) should be considered failed.",
        )


@handler(name="APPLY_PATCH")
def handle_apply_patch(
    action_data: Dict, project_root: Path, step_id: str
) -> Tuple[bool, str]:
    relative_path = action_data.get("path")
    patch_content = action_data.get("patch_content")

    if not isinstance(relative_path, str) or not relative_path:
        return False, "Missing or invalid 'path' (string) for APPLY_PATCH."
    if not isinstance(patch_content, str) or not patch_content:
        return False, "Missing or invalid 'patch_content' (string) for APPLY_PATCH."

    file_path = resolve_path(project_root, relative_path)
    if not file_path or not file_path.is_file():
        return False, f"Target file for patch not found or invalid: '{relative_path}'"

    signoff_message = (
        f"You are about to apply the following patch to the file:\n"
        f"  '{relative_path}'\n\n"
        f"--- PATCH CONTENT ---\n"
        f"{patch_content}\n"
        f"--- END PATCH CONTENT ---\n\n"
        f"This action can modify your code. Please review carefully."
    )

    is_approved, signoff_response_msg = request_signoff_helper_direct_tty(
        signoff_message, step_id
    )

    if not is_approved:
        return (
            False,
            f"Patch application for '{relative_path}' rejected by user. Reason: {signoff_response_msg}",
        )

    logger.info(f"User approved patch application for '{relative_path}'.")

    patch_file_path: Optional[Path] = None
    backup_file_path: Optional[Path] = None
    applied_successfully = False
    full_output_message = ""

    try:
        backup_file_path = file_path.with_suffix(file_path.suffix + ".exwork_patch_bak")
        if backup_file_path.exists():
            backup_file_path.unlink()
        shutil.copy2(file_path, backup_file_path)
        logger.info(f"Created backup: {backup_file_path}")

        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".patch", dir=project_root, encoding="utf-8"
        ) as tmp_patch_file:
            tmp_patch_file.write(patch_content)
            patch_file_path = Path(tmp_patch_file.name)

        logger.info(f"Applying patch from {patch_file_path} to {file_path}")
        patch_exe = shutil.which("patch")
        if not patch_exe:
            raise FileNotFoundError("`patch` command not found in PATH.")

        command = [
            patch_exe,
            "--forward",
            "-p1",
            str(file_path),
            "-i",
            str(patch_file_path),
        ]

        success, msg, stdout, stderr = _run_subprocess(
            command, project_root, "APPLY_PATCH_CMD", action_data, step_id
        )

        full_output_message = f"{msg}\n--- STDOUT ---\n{stdout if stdout else '<empty>'}\n--- STDERR ---\n{stderr if stderr else '<empty>'}".strip()

        if success:
            logger.info(f"Patch applied successfully to '{relative_path}'.")
            if backup_file_path and backup_file_path.exists():
                backup_file_path.unlink()
            applied_successfully = True
            return (
                True,
                f"Patch applied successfully to '{relative_path}'.\n{full_output_message}",
            )
        else:
            logger.error(
                f"Failed to apply patch to '{relative_path}'. Output:\n{full_output_message}"
            )
            if backup_file_path and backup_file_path.exists():
                logger.info(
                    f"Attempting to restore from backup: {backup_file_path} to {file_path}"
                )
                try:
                    shutil.move(str(backup_file_path), file_path)
                    logger.info(f"Successfully restored '{file_path}' from backup.")
                    return (
                        False,
                        f"Failed to apply patch. Original file restored from backup.\nPatch Output:\n{full_output_message}",
                    )
                except Exception as restore_e:
                    logger.error(
                        f"CRITICAL: Failed to restore '{file_path}' from backup '{backup_file_path}': {restore_e}"
                    )
                    return (
                        False,
                        f"Failed to apply patch AND FAILED TO RESTORE FROM BACKUP. File '{relative_path}' may be corrupted. Backup at: {backup_file_path}\nPatch Output:\n{full_output_message}",
                    )
            else:
                return (
                    False,
                    f"Failed to apply patch. No backup was found to restore.\nPatch Output:\n{full_output_message}",
                )

    except FileNotFoundError as fnf_e:
        logger.error(f"Error applying patch to '{relative_path}': {fnf_e}")
        if backup_file_path and backup_file_path.exists() and file_path.exists():
            shutil.move(str(backup_file_path), file_path)
        return (
            False,
            f"Error applying patch: {fnf_e}. Ensure 'patch' command is installed.",
        )
    except Exception as e:
        logger.error(
            f"Unexpected error during patch application for '{relative_path}': {e}",
            exc_info=True,
        )
        if backup_file_path and backup_file_path.exists() and file_path.exists():
            shutil.move(str(backup_file_path), file_path)
        return False, f"Unexpected error applying patch: {type(e).__name__} - {e}"
    finally:
        if patch_file_path and patch_file_path.exists():
            try:
                patch_file_path.unlink()
            except Exception as e_clean:
                logger.warning(
                    f"Could not delete temp patch file {patch_file_path}: {e_clean}"
                )


def request_signoff_helper_direct_tty(message: str, step_id: str) -> Tuple[bool, str]:
    """
    Handles direct, blocking user signoff.
    NOTE: This is a blocking operation. For autonomous agents, this needs
    to be refactored to an asynchronous mechanism (e.g., webhook, external queue).
    """
    signoff_mode = os.environ.get("EXWORK_SIGNOFF_MODE", "tty").lower()
    start_time = time.time()
    logger.info(f"REQUESTING USER SIGNOFF (mode: {signoff_mode}): {message}")
    action_params = {"prompt_message": message, "signoff_mode": signoff_mode}
    response_str = "No response (error)."
    success = False

    try:
        if signoff_mode == "tty":
            sys.stderr.write(f"\n>>> AGENT SIGNOFF REQUIRED (StepID: {step_id}) <<<\n")
            sys.stderr.write(message + "\n")
            sys.stderr.write(">>> Proceed? (yes/no): ")
            sys.stderr.flush()
            response = ""
            try:
                with open("/dev/tty", "r") as tty_in:
                    response = tty_in.readline().strip().lower()
            except Exception as e_tty:
                logger.warning(
                    f"Could not read from /dev/tty for signoff ({e_tty}), falling back to sys.stdin (may block if stdin is piped for main JSON)."
                )
                print(">>> (Fallback to stdin) Proceed? (yes/no): ", end="", flush=True)
                response = sys.stdin.readline().strip().lower()
            if response == "yes" or response == "y":
                logger.info("Sign-off APPROVED by user.")
                success = True
                response_str = "User approved."
            else:
                logger.info(f"Sign-off REJECTED by user (response: '{response}').")
                success = False
                response_str = "User rejected."
        elif signoff_mode == "file":
            flag_dir = os.environ.get("EXWORK_SIGNOFF_FLAG_DIR", PROJECT_ROOT)
            flag_base = f"exwork_signoff_{step_id}"
            awaiting_flag = os.path.join(flag_dir, flag_base + ".awaiting")
            approved_flag = os.path.join(flag_dir, flag_base + ".approved")
            os.makedirs(flag_dir, exist_ok=True)
            with open(awaiting_flag, "w") as f:
                f.write(message)
            logger.info(f"Signoff awaiting file created: {awaiting_flag}. Waiting for approval file: {approved_flag}")
            sys.stderr.write(f"\n[INFO] Awaiting signoff: create '{approved_flag}' to approve.\n")
            timeout = int(os.environ.get("EXWORK_SIGNOFF_TIMEOUT", "600"))
            waited = 0
            poll_interval = 2
            while waited < timeout:
                if os.path.exists(approved_flag):
                    success = True
                    response_str = "User approved via file."
                    os.remove(approved_flag)
                    break
                time.sleep(poll_interval)
                waited += poll_interval
            else:
                success = False
                response_str = f"Timed out waiting for signoff file after {timeout} seconds."
            if os.path.exists(awaiting_flag):
                os.remove(awaiting_flag)
        elif signoff_mode == "auto":
            logger.info("Auto signoff mode: automatically approving.")
            success = True
            response_str = "Auto-approved (EXWORK_SIGNOFF_MODE=auto)."
        elif signoff_mode == "webhook":
            logger.warning("Webhook signoff mode not implemented. Failing signoff.")
            success = False
            response_str = "Webhook signoff not implemented."
        else:
            logger.error(f"Unknown signoff mode: {signoff_mode}")
            success = False
            response_str = f"Unknown signoff mode: {signoff_mode}"
    except Exception as e:
        logger.error(f"Sign-off interaction failed: {e}", exc_info=True)
        success = False
        response_str = f"Error during sign-off: {type(e).__name__}"

    log_execution_history(
        {
            "timestamp": start_time,
            "action_name": "SIGNOFF_REQUEST",
            "success": success,
            "message": response_str,
            "duration_s": time.time() - start_time,
            "step_id": step_id,
            "action_params": action_params,
            "stdout_snippet": response_str,
        }
    )
    return success, response_str


# --- Core Agent Logic ---


def process_instruction_block(
    instruction_json: str, project_root: Path
) -> Tuple[bool, List[Dict[str, Any]]]:
    """
    Parses a JSON instruction block and executes its sequence of actions.
    Returns (overall_success_of_block, list_of_action_results).
    """
    action_results_summary: List[Dict[str, Any]] = []
    overall_block_success = True

    try:
        instruction = json.loads(instruction_json)
    except json.JSONDecodeError as e:
        logger.error(f"FATAL: JSON Decode Failed for instruction block: {e}")
        logger.error(f"Raw input snippet: {instruction_json[:500]}...")
        action_results_summary.append(
            {
                "action_type": "BLOCK_PARSE_ERROR",
                "success": False,
                "message_or_payload": f"JSON Decode Error: {e}",
            }
        )
        return False, action_results_summary

    if not isinstance(instruction, dict):
        logger.error("FATAL: Instruction block is not a JSON object.")
        action_results_summary.append(
            {
                "action_type": "BLOCK_VALIDATION_ERROR",
                "success": False,
                "message_or_payload": "Instruction block not a dict.",
            }
        )
        return False, action_results_summary

    step_id = instruction.get("step_id", str(uuid.uuid4()))
    description = instruction.get("description", "No description provided.")
    actions = instruction.get("actions", [])

    logger.info(
        f"Processing Instruction Block - StepID: {step_id}, Desc: '{description}'"
    )
    if not isinstance(actions, list):
        logger.error(f"'{step_id}': 'actions' field must be a list. Skipping block.")
        action_results_summary.append(
            {
                "action_type": "BLOCK_VALIDATION_ERROR",
                "success": False,
                "message_or_payload": "'actions' field not a list.",
            }
        )
        return False, action_results_summary

    for i, action_data in enumerate(actions):
        if not isinstance(action_data, dict):
            logger.error(
                f"'{step_id}': Action {i+1} is not a valid JSON object. Skipping action."
            )
            action_results_summary.append(
                {
                    "action_type": "ACTION_VALIDATION_ERROR",
                    "success": False,
                    "message_or_payload": f"Action {i+1} not a dict.",
                }
            )
            overall_block_success = False
            continue

        action_type = action_data.get("type")
        action_num = i + 1
        logger.info(
            f"--- {step_id}: Action {action_num}/{len(actions)} (Type: {action_type}) ---"
        )

        handler_func = ACTION_HANDLERS.get(action_type)
        if handler_func:
            action_start_time = time.time()
            success, result_payload = handler_func(action_data, project_root, step_id)
            action_duration = time.time() - action_start_time

            action_summary = {
                "action_type": action_type,
                "success": success,
                "message_or_payload": result_payload,
                "duration_s": round(action_duration, 3),
                "action_num": action_num,
            }
            action_results_summary.append(action_summary)

            # Centralized logging: Only log here if handler itself doesn't log via _run_subprocess etc.
            if action_type not in ["RUN_SCRIPT", "LINT_FORMAT_FILE", "APPLY_PATCH", "GIT_ADD", "GIT_COMMIT", "CALL_LOCAL_LLM", "DIAGNOSE_ERROR", "REQUEST_SIGNOFF", "RESPOND_TO_SIGNOFF"]:
                log_execution_history(
                    {
                        "timestamp_iso": datetime.now(timezone.utc).isoformat(),
                        "action_name": action_type,
                        "success": success,
                        "message": (
                            result_payload
                            if isinstance(result_payload, str)
                            else json.dumps(result_payload)
                        ),
                        "duration_s": action_duration,
                        "step_id": step_id,
                        "action_num": action_num,
                        "action_params": action_data,
                    }
                )

            if not success:
                logger.error(
                    f"'{step_id}': Action {action_num} ({action_type}) FAILED. Result: {result_payload}"
                )
                overall_block_success = False
                logger.info(
                    f"Halting processing of action block '{step_id}' due to failure in action {action_num} ({action_type})."
                )
                break
            else:
                logger.info(
                    f"'{step_id}': Action {action_num} ({action_type}) SUCCEEDED. Duration: {action_duration:.3f}s"
                )
        else:
            logger.error(
                f"'{step_id}': Unknown action type encountered: '{action_type}'. Halting block."
            )
            action_results_summary.append(
                {
                    "action_type": action_type,
                    "success": False,
                    "message_or_payload": "Unknown action type.",
                    "action_num": action_num,
                }
            )
            overall_block_success = False
            break

    logger.info(
        f"--- Finished processing actions for StepID: {step_id}. Overall Block Success: {overall_block_success} ---"
    )
    return overall_block_success, action_results_summary


# --- Interactive Configuration and Execution ---
def interactive_mode():
    """Provides an interactive mode for configuring and executing tasks."""
    logger.info("Entering interactive mode for Ex-Work Agent.")

    while True:
        print("\n--- Ex-Work Agent Interactive Mode ---")
        print("1. Add a new task (triggers learning/handler creation)")
        print("2. View registered handlers")
        print("3. Execute tasks from a JSON file (processes as an instruction block)")
        print("4. Exit interactive mode")

        choice = input("Select an option (1-4): ").strip()

        if choice == "1":
            task_name = input("Enter task name: ").strip()
            parameters_str = input("Enter task parameters as JSON (e.g., {\"message\": \"hi\"}): ").strip()
            try:
                task_params = json.loads(parameters_str)
                logger.info(f"Adding task: {task_name} with parameters: {task_params}")
                learn_from_failures(task_name, f"Interactive task add for {task_name}")
            except json.JSONDecodeError:
                print("Invalid JSON format for parameters. Please try again.")
            except Exception as e:
                print(f"Error adding task: {e}")

        elif choice == "2":
            print("\n--- Registered Handlers ---")
            if not ACTION_HANDLERS:
                print("No handlers currently registered.")
            else:
                for handler_name in sorted(ACTION_HANDLERS.keys()):
                    print(f"- {handler_name}")

        elif choice == "3":
            file_path = input("Enter the path to the JSON instruction block file: ").strip()
            try:
                resolved_file_path = Path(file_path).resolve()
                if not resolved_file_path.is_file():
                    print(f"Error: File not found at '{file_path}'.")
                    continue
                with open(resolved_file_path, "r", encoding="utf-8") as f:
                    instruction_json_str = f.read()
                
                logger.info(f"Executing instruction block from {file_path}")
                overall_success, action_results = process_instruction_block(
                    instruction_json_str, PROJECT_ROOT
                )
                print(f"\n--- Execution Results for {file_path} ---")
                print(f"Overall Success: {overall_success}")
                for result in action_results:
                    print(f"  - Action [{result.get('action_num', 'N/A')}] {result.get('action_type')}: Success={result.get('success')}, Message={result.get('message_or_payload')}")
                print("---------------------------------------")

            except (FileNotFoundError, json.JSONDecodeError) as e:
                print(f"Error loading or parsing instruction file: {e}")
            except Exception as e:
                print(f"Unexpected error during file execution: {e}")

        elif choice == "4":
            print("Exiting interactive mode.")
            break

        else:
            print("Invalid choice. Please select a valid option.")

# --- Main Entry Point ---
def main():
    """Main entry point for the Ex-Work Agent."""
    
    # Initial checks for external executables
    if not shutil.which(RUFF_EXECUTABLE) and RUFF_EXECUTABLE == "ruff":
        logger.warning(
            f"Command '{RUFF_EXECUTABLE}' not found in PATH. `LINT_FORMAT_FILE` action may fail. Please install Ruff or set RUFF_EXECUTABLE env var."
        )
    if not shutil.which("patch"):
        logger.warning(
            "Command 'patch' not found in PATH. `APPLY_PATCH` action will fail. Please install 'patch'."
        )

    logger.info(f"--- Agent Ex-Work V2.3 Initialized in {PROJECT_ROOT} ---")

    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        interactive_mode()
    else:
        logger.info(
            "Running Ex-Work Agent in single-block stdin mode. Send EOF (Ctrl+D Linux/macOS, Ctrl+Z+Enter Windows) after JSON."
        )

        json_input_lines = []
        try:
            for line in sys.stdin:
                json_input_lines.append(line)
        except KeyboardInterrupt:
            logger.info("KeyboardInterrupt during stdin read. Exiting.")
            sys.stdout.write(
                json.dumps(
                    {
                        "overall_success": False,
                        "status_message": "Interrupted by user during input.",
                    }
                )
                + "\n"
            )
            sys.exit(1)
        except Exception as e:
            logger.error(f"Error reading from stdin: {e}", exc_info=True)
            sys.stdout.write(
                json.dumps(
                    {"overall_success": False, "status_message": f"Stdin read error: {e}"}
                )
                + "\n"
            )
            sys.exit(1)

        json_input = "".join(json_input_lines)

        if not json_input.strip():
            logger.warning("No input received from stdin. Exiting.")
            sys.stdout.write(
                json.dumps(
                    {"overall_success": False, "status_message": "No input from stdin."}
                )
                + "\n"
            )
            sys.exit(0)

        logger.info(f"Processing {len(json_input)} bytes of instruction...")
        start_process_time = time.time()

        overall_success, action_results = process_instruction_block(
            json_input, PROJECT_ROOT
        )

        end_process_time = time.time()
        duration = round(end_process_time - start_process_time, 3)

        final_status_message = f"Instruction block processing finished. Overall Success: {overall_success}. Duration: {duration}s"
        logger.info(final_status_message)

        output_payload = {
            "overall_success": overall_success,
            "status_message": final_status_message,
            "duration_seconds": duration,
            "action_results": action_results,
        }
        sys.stdout.write(json.dumps(output_payload) + "\n")
        sys.stdout.flush()

        if not overall_success:
            sys.exit(1)


if __name__ == "__main__":
    main()

