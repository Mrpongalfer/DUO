#!/usr/bin/env python3
# ~/ex-work-agent/ex_work_agent.py
# Agent Ex-Work: Executes structured JSON commands.

import json
import sys
import logging
import base64
import subprocess
import shlex
import time
from pathlib import Path
import os
import requests # For Ollama API calls
from typing import Optional, Dict, List, Any, Tuple

# --- Basic Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [ExWork] [%(levelname)-7s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("AgentExWork")

# --- Helper Functions ---

def resolve_path(project_root: Path, requested_path: str) -> Optional[Path]:
    """
    Safely resolves a requested path relative to the project root,
    preventing path traversal. Returns absolute Path or None if unsafe/error.
    """
    try:
        relative_p = Path(requested_path)
        if ".." in relative_p.parts or relative_p.is_absolute():
             logger.error(f"Path traversal/absolute path rejected: '{requested_path}'")
             return None
        abs_path = project_root.joinpath(relative_p).resolve()
        is_safe = False
        if hasattr(abs_path, 'is_relative_to'): # Python 3.9+
            is_safe = abs_path == project_root.resolve() or abs_path.is_relative_to(project_root.resolve())
        else: # Fallback check
             is_safe = str(abs_path).startswith(str(project_root.resolve()) + os.sep) or abs_path == project_root.resolve()
        if is_safe:
             logger.debug(f"Resolved path '{requested_path}' to '{abs_path}'")
             return abs_path
        else:
             logger.error(f"Path unsafe! Resolved '{abs_path}' outside project root '{project_root}'.")
             return None
    except Exception as e:
        logger.error(f"Error resolving path '{requested_path}' relative to '{project_root}': {e}")
        return None

def _run_subprocess(command: list[str], cwd: Path, action_name: str) -> tuple[bool, str, str, str]:
    """
    Helper function to run a subprocess safely within project root.
    Returns: (success_bool, message_str, stdout_str, stderr_str)
    """
    full_output_log = ""
    try:
        command_str = ' '.join(shlex.quote(c) for c in command)
        logger.info(f"Running {action_name}: {command_str} in CWD={cwd}")
        result = subprocess.run(command, cwd=cwd, capture_output=True, text=True, check=False, timeout=300)
        stdout = result.stdout.strip() if result.stdout else ""; stderr = result.stderr.strip() if result.stderr else ""
        full_output_log = f"Finished {action_name}. Code: {result.returncode}"
        if stdout: full_output_log += f"\n--- STDOUT ---\n{stdout}"
        if stderr: full_output_log += f"\n--- STDERR ---\n{stderr}";
        if result.returncode == 0: logger.info(full_output_log); return True, f"{action_name} completed successfully.", stdout, stderr
        else: logger.error(full_output_log); return False, f"{action_name} failed (Code: {result.returncode}).", stdout, stderr
    except Exception as e: logger.error(f"Error running {action_name}: {e}", exc_info=True); return False, f"Unexpected error: {e}", "", ""

# --- Action Handler Functions --- (Implemented) ---

def handle_echo(action_data: dict, project_root: Path) -> tuple[bool, str]:
    message = action_data.get("message", "No message"); print(f"[AGENT ECHO] {message}"); logger.info(f"ECHO: {message}"); return True, "Echo ok."
def handle_create_or_replace_file(action_data: dict, project_root: Path) -> tuple[bool, str]:
    relative_path = action_data.get("path"); content_base64 = action_data.get("content_base64")
    if not relative_path or content_base64 is None: return False, "Missing path/content_base64."
    file_path = resolve_path(project_root, relative_path);
    if not file_path: return False, f"Invalid path: {relative_path}"
    try: logger.info(f"Writing: {file_path}"); file_path.parent.mkdir(parents=True, exist_ok=True); file_path.write_bytes(base64.b64decode(content_base64, validate=True)); return True, f"File '{relative_path}' written."
    except Exception as e: logger.error(f"Error writing {relative_path}: {e}", exc_info=True); return False, f"Write error: {e}"
def handle_append_to_file(action_data: dict, project_root: Path) -> tuple[bool, str]:
    relative_path = action_data.get("path"); content_base64 = action_data.get("content_base64")
    if not relative_path or content_base64 is None: return False, "Missing path/content_base64."
    file_path = resolve_path(project_root, relative_path);
    if not file_path: return False, f"Invalid path: {relative_path}"
    try: logger.info(f"Appending: {file_path}"); file_path.parent.mkdir(parents=True, exist_ok=True); decoded_bytes = base64.b64decode(content_base64, validate=True)
        with file_path.open("ab") as f:
            if file_path.exists() and file_path.stat().st_size > 0:
                with file_path.open("rb") as rf: rf.seek(-1, os.SEEK_END);
                if rf.read(1) != b'\n': f.write(b'\n')
            f.write(decoded_bytes); return True, f"Appended to '{relative_path}'."
    except Exception as e: logger.error(f"Error appending {relative_path}: {e}", exc_info=True); return False, f"Append error: {e}"
def handle_run_script(action_data: dict, project_root: Path) -> tuple[bool, str]:
    relative_script_path = action_data.get("script_path"); args = action_data.get("args", [])
    if not relative_script_path: return False, "Missing script_path.";
    if not isinstance(args, list): return False, "Args not list."
    script_path = resolve_path(project_root, relative_script_path);
    if not script_path or not script_path.is_file(): return False, f"Script not found: {relative_script_path}"
    scripts_dir = (project_root / "scripts").resolve(); is_safe = False
    if hasattr(script_path, "is_relative_to"): is_safe = script_path.is_relative_to(scripts_dir)
    else: is_safe = str(script_path).startswith(str(scripts_dir) + os.sep)
    if not is_safe: return False, f"Security Error: Script must be in scripts/."
    command = [str(script_path)] + args; success, msg, _, _ = _run_subprocess(command, project_root, f"RUN_SCRIPT"); return success, msg
def handle_run_formatter(action_data: dict, project_root: Path) -> tuple[bool, str]:
    tool = action_data.get("tool", "ruff"); target = action_data.get("target", ".")
    if tool not in ["ruff", "black"]: return False, f"Invalid formatter: {tool}"
    target_path = str(project_root) if target == "." else str(resolve_path(project_root, target))
    if not target_path: return False, f"Invalid target path: {target}"
    command = [tool];
    if tool == "ruff": command.append("format")
    command.append(target_path); success, msg, _, _ = _run_subprocess(command, project_root, f"RUN_FORMATTER ({tool})"); return success, msg
def handle_git_add(action_data: dict, project_root: Path) -> tuple[bool, str]:
    paths = action_data.get("paths", ["."]); safe_paths = []
    if not isinstance(paths, list): return False, "'paths' must be list."
    for p in paths:
        if p == ".": safe_paths.append(p); continue
        p_path = Path(p);
        if ".." in p_path.parts or p_path.is_absolute(): logger.warning(f"Skip unsafe git add: {p}"); continue
        if (project_root / p).exists(): safe_paths.append(p)
        else: logger.warning(f"Skip non-existent git add: {p}")
    if not safe_paths: return False, "No valid paths for git add."
    command = ["git", "add"] + safe_paths; success, msg, _, _ = _run_subprocess(command, project_root, "GIT_ADD"); return success, msg
def handle_git_commit(action_data: dict, project_root: Path) -> tuple[bool, str]:
    message = action_data.get("message");
    if not message: return False, "Missing 'message' for commit."
    command = ["git", "commit", "-m", message]; success, msg, _, _ = _run_subprocess(command, project_root, "GIT_COMMIT"); return success, msg
def handle_call_local_llm(action_data: dict, project_root: Path) -> tuple[bool, str]:
    logger.info("Executing CALL_LOCAL_LLM..."); prompt = action_data.get("prompt"); default_model = "mistral-nemo:12b-instruct-2407-q4_k_m"; model_name = action_data.get("model", default_model); default_endpoint = "http://localhost:11434/api/generate"; api_endpoint = action_data.get("api_endpoint", default_endpoint); llm_options = action_data.get("options", {})
    if not prompt: return False, "Missing 'prompt'."
    if not isinstance(llm_options, dict): logger.warning("LLM options not dict."); llm_options = {}
    logger.info(f"Targeting {model_name} @ {api_endpoint}"); payload = {"model": model_name, "prompt": prompt, "stream": False, "options": llm_options };
    if not llm_options: del payload["options"]
    try:
        response = requests.post(api_endpoint, json=payload, headers={"Content-Type": "application/json"}, timeout=300); response.raise_for_status(); data = response.json()
        llm_response = data.get("response", "").strip();
        if not llm_response: err = data.get("error", "empty resp"); logger.warning(f"LLM empty resp. Err: {err}"); return False, f"LLM empty resp. Details: {err}"
        logger.info("Local LLM call successful."); return True, llm_response
    except requests.exceptions.RequestException as e: logger.error(f"LLM Call Failed: {e}"); return False, f"LLM Request Error: {e}"
    except Exception as e: logger.error(f"LLM call unexpected error: {e}", exc_info=True); return False, f"Unexpected LLM error: {e}"
def handle_request_signoff(action_data: dict, project_root: Path) -> tuple[bool, str]:
    message = action_data.get("message", "Proceed?"); logger.info(f"REQUESTING USER SIGNOFF: {message}")
    try: print(f"\n>>> AGENT APPROVAL: {message}"); print(">>> Proceed? (y/N): ", end='', flush=True); response = input().strip().lower()
        if response == 'y': logger.info("Sign-off APPROVED."); return True, "User approved."
        else: logger.info("Sign-off REJECTED."); return False, "User rejected."
    except Exception as e: logger.error(f"Sign-off error: {e}", exc_info=True); return False, "Error during sign-off."

# --- Action Dispatch Table ---
ACTION_HANDLERS = {
    "ECHO": handle_echo,
    "CREATE_OR_REPLACE_FILE": handle_create_or_replace_file,
    "APPEND_TO_FILE": handle_append_to_file,
    "RUN_SCRIPT": handle_run_script,
    "RUN_FORMATTER": handle_run_formatter,
    "GIT_ADD": handle_git_add,
    "GIT_COMMIT": handle_git_commit,
    "CALL_LOCAL_LLM": handle_call_local_llm,
    "REQUEST_SIGNOFF": handle_request_signoff,
}

# --- Core Agent Logic ---
def process_instruction(instruction_json: str, project_root: Path) -> bool:
    """Parses and executes a single JSON instruction block."""
    try: instruction = json.loads(instruction_json); step_id = instruction.get('step_id', 'Unknown'); logger.info(f"Received: {step_id}"); logger.debug(f"Full: {instruction}")
        description = instruction.get("description", "N/A"); logger.info(f"Desc: {description}"); actions = instruction.get("actions", [])
        if not isinstance(actions, list): logger.error("'actions' must be list."); return False
        for i, action in enumerate(actions):
            action_type = action.get("type"); action_num = i + 1; logger.info(f"--- Action {action_num}/{len(actions)} ({action_type}) ---")
            handler = ACTION_HANDLERS.get(action_type)
            if handler: success, message = handler(action, project_root);
                if not success: logger.error(f"Action {action_num} FAILED: {message}"); logger.error(f"Halting: {step_id}"); return False
                else: logger.info(f"Action {action_num} SUCCEEDED: {message}")
            else: logger.error(f"Unknown action type: '{action_type}'"); logger.error(f"Halting: {step_id}"); return False
        logger.info(f"--- Completed actions for step_id: {step_id} ---"); return True
    except json.JSONDecodeError as e: logger.error(f"JSON Decode Failed: {e}"); logger.error(f"Raw input snippet: {instruction_json[:500]}..."); return False
    except Exception as e: logger.error(f"Error processing instruction block: {e}", exc_info=True); return False

def main():
    """Main loop to read JSON instructions from stdin."""
    logger.info("--- Agent Ex-Work Initializing ---"); project_root = Path.cwd().resolve(); logger.info(f"Agent operating in Project Root: {project_root}")
    if not (project_root / '.git').is_dir(): logger.warning(".git missing - Ensure running from project root.")
    print("\nPaste JSON instruction block, press Enter, then send EOF (Ctrl+D or Ctrl+Z+Enter).")
    while True:
        print(f"\n{'-'*20} Ready for JSON (Project: {project_root.name}) {'-'*20}")
        try:
            json_input_lines = sys.stdin.readlines();
            if not json_input_lines: logger.info("EOF detected. Exiting agent."); break
            json_input = "".join(json_input_lines)
            if not json_input.strip(): logger.warning("Empty input."); continue
            logger.info(f"Processing {len(json_input)} bytes instruction...")
            process_instruction(json_input, project_root)
        except KeyboardInterrupt: logger.info("KeyboardInterrupt. Exiting."); break
        except Exception as e: logger.error(f"Critical main loop error: {e}", exc_info=True); time.sleep(2)

if __name__ == "__main__":
    main()
