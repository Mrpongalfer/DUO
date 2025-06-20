#!/usr/bin/env python3
# native_workflow_runner.py
# Description: A simple NATIVE Python script to run Scribe and ExWork in tandem,
#              bypassing Docker for an immediate local test.
#              Created for The Architect by NAA/Drake.
# Usage: python3 run_native_nai_workflow.py

import json
import shlex  # For quoting arguments if needed, though direct list is safer
import subprocess
import sys
from pathlib import Path

# --- IMPORTANT: CONFIGURE THESE PATHS FOR YOUR HOST SYSTEM ---
# Assuming this script, scribe_agent.py, and ex_work_agentv2.py are in the same directory.
# If not, provide absolute paths or correct relative paths.
SCRIPT_DIR = Path(__file__).parent.resolve()
PYTHON_EXECUTABLE = sys.executable  # Uses the Python running this script

# Path to your Scribe agent script (ensure it has the tomllib/tomli fix if you're on Python < 3.11)
SCRIBE_AGENT_SCRIPT = (
    SCRIPT_DIR / "scribe_agent.v1.1.py"
)  # Assuming you renamed v1.1 to this
# Or use: SCRIBE_AGENT_SCRIPT = SCRIPT_DIR / "scribe_agent.v1.1.py"

# Path to your ExWork agent script
EXWORK_AGENT_SCRIPT = SCRIPT_DIR / "ex_work_agentv2.py"

# --- Test Project Configuration (EDIT THESE FOR YOUR HOST) ---
# Absolute path to the root of your test project on your HOST machine
TEST_PROJECT_DIR = Path("/home/pong/Projects/NAI")  # ### EXAMPLE - CHANGE THIS ###

# Absolute path to the file containing the NEW code Scribe should apply
# This file should exist on your HOST machine.
NEW_CODE_FILE_PATH = (
    TEST_PROJECT_DIR / "new_code_for_calculator.py"
)  # ### EXAMPLE - CHANGE THIS ###

# Relative path WITHIN the TEST_PROJECT_DIR where Scribe should apply the new code
TARGET_FILE_IN_PROJECT = "src/calculator.py"  # ### EXAMPLE - CHANGE THIS ###

# Absolute path to your .scribe.toml configuration file on your HOST machine
# Ensure 'allowed_target_bases' in this TOML is configured for your HOST paths (e.g., ["/home/pong/Projects/NAI/test_projects"])
SCRIBE_CONFIG_FILE_PATH = (
    SCRIPT_DIR / ".scribe.toml"
)  # ### EXAMPLE - Assumes .scribe.toml is with this script. CHANGE IF ELSEWHERE ###
# --- END OF REQUIRED CONFIGURATION ---


def run_command(
    command_list: list, stdin_data: Optional[str] = None, cwd: Optional[Path] = None
) -> tuple[int, str, str]:
    """Runs a command, returns (return_code, stdout, stderr)."""
    print(
        f"\n[RUNNER] Executing: {' '.join(shlex.quote(str(c)) for c in command_list)}"
    )
    if cwd:
        print(f"[RUNNER] In CWD: {cwd}")
    if stdin_data:
        print(
            f"[RUNNER] With STDIN: {stdin_data[:100]}{'...' if len(stdin_data) > 100 else ''}"
        )

    try:
        process = subprocess.Popen(
            command_list,
            stdin=subprocess.PIPE if stdin_data else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=cwd,
            encoding="utf-8",
            errors="replace",
        )
        stdout, stderr = process.communicate(
            input=stdin_data, timeout=600
        )  # 10 min timeout
        print(f"[RUNNER] Finished. RC: {process.returncode}")
        if stdout:
            print(f"[RUNNER] STDOUT:\n{stdout.strip()}")
        if stderr:
            print(f"[RUNNER] STDERR:\n{stderr.strip()}")
        return process.returncode, stdout or "", stderr or ""
    except subprocess.TimeoutExpired:
        print("[RUNNER] Command timed out!")
        return -1, "", "Command timed out after 10 minutes."
    except FileNotFoundError:
        print(f"[RUNNER] ERROR: Executable not found: {command_list[0]}")
        return -2, "", f"Executable not found: {command_list[0]}"
    except Exception as e:
        print(f"[RUNNER] Error running command: {e}")
        return -3, "", f"Error running command: {e}"


def create_minimal_test_files_if_not_exist():
    """Creates the calculator.py and new_code_for_calculator.py if they don't exist."""
    TEST_PROJECT_DIR.mkdir(parents=True, exist_ok=True)
    src_dir = TEST_PROJECT_DIR / "src"
    src_dir.mkdir(parents=True, exist_ok=True)

    calc_py = src_dir / "calculator.py"
    new_code_py = TEST_PROJECT_DIR / "new_code_for_calculator.py"
    proj_toml = TEST_PROJECT_DIR / "pyproject.toml"

    if not calc_py.exists():
        print(f"[SETUP] Creating initial {calc_py}...")
        calc_py.write_text(
            """# calculator.py (Initial Version)
def add(x: int, y: int) -> int:
# A simple function
    return x+y

class Greeter:
    def __init__(self, name:str):
        self.name =name
    def greet(self):
        print(f"Hello, {self.name}" )
"""
        )
    if not new_code_py.exists():
        print(f"[SETUP] Creating {new_code_py}...")
        new_code_py.write_text(
            """# new_code_for_calculator.py
# V1.1 - Updated by Scribe Test
def add(x: int, y: int) -> int:
    \"\"\"Adds two integers and returns the result.\"\"\"
    return x + y

def subtract(a: int, b: int) -> int:
    \"\"\"Subtracts second integer from the first.\"\"\"
    return a - b

class Greeter:
    def __init__(self, name: str):
        self.name: str = name # Explicit type hint for instance var

    def greet(self) -> None: # Added return type hint
        print(f"Hello, {self.name}!") # Added exclamation
"""
        )
    if not proj_toml.exists():
        print(f"[SETUP] Creating minimal {proj_toml}...")
        proj_toml.write_text(
            """[project]
name = "my_native_scribe_test_project"
version = "0.1.0"
description = "A minimal project for native Scribe testing."
"""
        )
    print("[SETUP] Test files ensured.")


def main_workflow():
    print("--- Starting Native Scribe + ExWork Workflow ---")

    # Ensure test files exist for a smoother first run
    create_minimal_test_files_if_not_exist()

    # --- Step 1: Run Scribe ---
    print("\n--- Stage 1: Running Scribe Agent ---")
    scribe_command = [
        PYTHON_EXECUTABLE,  # Use the Python that's running this script
        str(SCRIBE_AGENT_SCRIPT),
        "--target-dir",
        str(TEST_PROJECT_DIR),
        "--code-file",
        str(NEW_CODE_FILE_PATH),
        "--target-file",
        TARGET_FILE_IN_PROJECT,
        "--config-file",
        str(SCRIBE_CONFIG_FILE_PATH),
        "--report-format",
        "json",
        "--skip-tests",  # Keep it fast for this test
        "--skip-review",  # Keep it fast for this test
        # "--commit" # Optionally add if you want to test git commit (ensure .git repo in TEST_PROJECT_DIR)
    ]

    scribe_rc, scribe_stdout, scribe_stderr = run_command(
        scribe_command, cwd=TEST_PROJECT_DIR
    )

    scribe_overall_success = False
    if scribe_rc == 0:
        try:
            report_data = json.loads(scribe_stdout)
            if report_data.get("overall_status") == "SUCCESS":
                scribe_overall_success = True
                print("[SCRIBE RESULT] Scribe reported: Workflow SUCCESSFUL!")
            else:
                print(
                    f"[SCRIBE RESULT] Scribe reported: Workflow COMPLETED WITH ISSUES (Status: {report_data.get('overall_status')})"
                )
        except json.JSONDecodeError:
            print(
                "[SCRIBE RESULT] Scribe output was not valid JSON. Assuming failure based on non-zero RC or empty output."
            )
    else:
        print(f"[SCRIBE RESULT] Scribe FAILED with exit code: {scribe_rc}")

    if not scribe_overall_success:
        print(
            "\n--- Workflow Halted: Scribe did not succeed. ExWork step will be skipped. ---"
        )
        return

    # --- Step 2: Run ExWork (if Scribe succeeded) ---
    print("\n--- Stage 2: Running ExWork Agent (Scribe Succeeded!) ---")

    exwork_json_payload = {
        "step_id": "NativeExWorkPostScribe",
        "description": "ExWork action after successful native Scribe run.",
        "actions": [
            {
                "type": "ECHO",
                "message": "NATIVE WORKFLOW: Scribe SUCCESS, ExWork EXECUTION CONFIRMED!",
            },
            {
                "type": "CREATE_OR_REPLACE_FILE",
                "path": "NATIVE_SCRIBE_EXWORK_SUCCESS.txt",  # Will be created in TEST_PROJECT_DIR
                "content_base64": "TmF0aXZlIFNjcmliZSArIEV4V29yayB3b3JrZmxvdyBjb21wbGV0ZWQgc3VjY2Vzc2Z1bGx5IQ==",
                # Base64 for: "Native Scribe + ExWork workflow completed successfully!"
            },
        ],
    }
    exwork_stdin = json.dumps(exwork_json_payload)

    exwork_command = [PYTHON_EXECUTABLE, str(EXWORK_AGENT_SCRIPT)]

    exwork_rc, exwork_stdout, exwork_stderr = run_command(
        exwork_command, stdin_data=exwork_stdin, cwd=TEST_PROJECT_DIR
    )

    if exwork_rc == 0:
        try:
            exwork_output_data = json.loads(exwork_stdout)
            if exwork_output_data.get("overall_success"):
                print("[EXWORK RESULT] ExWork reported: Overall Success!")
            else:
                print("[EXWORK RESULT] ExWork reported: Completed with issues.")
        except json.JSONDecodeError:
            print("[EXWORK RESULT] ExWork output was not valid JSON.")
    else:
        print(f"[EXWORK RESULT] ExWork FAILED with exit code: {exwork_rc}")

    print("\n--- Native Scribe + ExWork Workflow Finished ---")


if __name__ == "__main__":
    # Basic check for script paths
    if not SCRIBE_AGENT_SCRIPT.is_file():
        print(
            f"FATAL ERROR: Scribe agent script not found at '{SCRIBE_AGENT_SCRIPT}'. Please check SCRIPT_DIR and filenames."
        )
        sys.exit(1)
    if not EXWORK_AGENT_SCRIPT.is_file():
        print(
            f"FATAL ERROR: ExWork agent script not found at '{EXWORK_AGENT_SCRIPT}'. Please check SCRIPT_DIR and filenames."
        )
        sys.exit(1)
    if not SCRIBE_CONFIG_FILE_PATH.is_file():
        print(
            f"WARNING: Scribe config file not found at '{SCRIBE_CONFIG_FILE_PATH}'. Scribe will use its defaults, which might not be suitable for native paths."
        )
        # Allow to continue, Scribe has internal defaults, but user should be aware.

    main_workflow()
