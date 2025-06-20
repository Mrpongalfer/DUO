#!/usr/bin/env python3
# ./NAI/quick_run.py

import base64
import json
import shlex
import subprocess
import sys
from pathlib import Path

# These are paths INSIDE THE DOCKER CONTAINER
SCRIBE_SCRIPT_PATH_IN_CONTAINER = "/app/scribe_agent.py"
EXWORK_SCRIPT_PATH_IN_CONTAINER = "/app/ex_work_agentv2.py"
SCRIBE_CONFIG_PATH_IN_CONTAINER = (
    "/app/.scribe.toml"  # We'll mount NAI/.scribe.toml here
)
TEST_PROJECT_ROOT_IN_CONTAINER = Path(
    "/workspace/test_project"
)  # Mounted from ./NAI/quick_test_project

# Test file specifications (relative to TEST_PROJECT_ROOT_IN_CONTAINER)
NEW_CODE_FILE_IN_PROJECT = "new_code.py"  # Name of the file containing new code
TARGET_FILE_IN_PROJECT_RELATIVE = "src/module.py"  # Relative path for Scribe to target


def run_host_command(command_array, input_data=None, cwd=None):
    print(
        f"\n>>> RUNNING: {' '.join(shlex.quote(str(c)) for c in command_array)}",
        flush=True,
    )
    if cwd:
        print(f"    IN CWD: {cwd}", flush=True)
    try:
        process = subprocess.run(
            command_array,
            input=input_data,
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=300,  # 5 min timeout for each agent call
            check=False,  # We'll check returncode manually
        )
        print(f"<<< FINISHED: RC={process.returncode}", flush=True)
        if process.stdout:
            print("--- STDOUT ---", flush=True)
            print(process.stdout.strip(), flush=True)
            print("--- END STDOUT ---", flush=True)
        if process.stderr:
            print("--- STDERR ---", flush=True)
            print(process.stderr.strip(), flush=True)
            print("--- END STDERR ---", flush=True)
        return process.returncode, process.stdout, process.stderr
    except FileNotFoundError:
        print(f"ERROR: Command not found: {command_array[0]}", flush=True)
        return -127, "", f"Command not found: {command_array[0]}"
    except subprocess.TimeoutExpired:
        print("ERROR: Command timed out!", flush=True)
        return -126, "", "Command timed out."
    except Exception as e:
        print(f"ERROR running command: {e}", flush=True)
        return -125, "", str(e)


def perform_quick_run():
    print("--- OMNITIDE NEXUS: Quick Scribe + ExWork Tandem Test ---", flush=True)

    # --- 1. Run Scribe ---
    print("\n--- Stage 1: Invoking Scribe Agent ---", flush=True)
    scribe_cmd = [
        "python",
        SCRIBE_SCRIPT_PATH_IN_CONTAINER,
        "--target-dir",
        str(TEST_PROJECT_ROOT_IN_CONTAINER),
        "--code-file",
        str(TEST_PROJECT_ROOT_IN_CONTAINER / NEW_CODE_FILE_IN_PROJECT),
        "--target-file",
        TARGET_FILE_IN_PROJECT_RELATIVE,
        "--config-file",
        SCRIBE_CONFIG_PATH_IN_CONTAINER,
        "--report-format",
        "json",
        # For speed:
        "--skip-deps",  # Assumes Ruff/MyPy are globally installed via requirements.txt in Docker
        # The minimal .scribe.toml already skips AI tests and review
    ]
    scribe_rc, scribe_stdout, _ = run_host_command(
        scribe_cmd, cwd=TEST_PROJECT_ROOT_IN_CONTAINER
    )

    scribe_passed = False
    if scribe_rc == 0:
        try:
            report = json.loads(scribe_stdout)
            if report.get("overall_status") == "SUCCESS":
                print("[SUCCESS] Scribe validation passed!", flush=True)
                scribe_passed = True
            else:
                print(
                    f"[FAILURE] Scribe completed but reported issues: {report.get('overall_status')}",
                    flush=True,
                )
        except json.JSONDecodeError:
            print("[FAILURE] Scribe output was not valid JSON.", flush=True)
    else:
        print(f"[FAILURE] Scribe agent failed with exit code {scribe_rc}.", flush=True)

    if not scribe_passed:
        print(
            "--- Workflow Halted: Scribe did not pass. ExWork will not run. ---",
            flush=True,
        )
        sys.exit(1)

    # --- 2. Run ExWork ---
    print("\n--- Stage 2: Invoking ExWork Agent (Scribe Succeeded) ---", flush=True)
    success_message = (
        "Scribe validation successful! ExWork was triggered by quick_run.py!"
    )
    success_message_b64 = base64.b64encode(success_message.encode("utf-8")).decode(
        "utf-8"
    )

    exwork_payload = {
        "step_id": "QuickRunExWorkConfirmation",
        "description": "Confirms Scribe success and ExWork execution.",
        "actions": [
            {
                "type": "ECHO",
                "message": "ExWork: Received signal after Scribe success.",
            },
            {
                "type": "CREATE_OR_REPLACE_FILE",
                "path": "QUICK_RUN_SUCCESS.txt",  # Will be in TEST_PROJECT_ROOT_IN_CONTAINER
                "content_base64": success_message_b64,
            },
        ],
    }
    exwork_stdin_str = json.dumps(exwork_payload)
    exwork_cmd = ["python", EXWORK_SCRIPT_PATH_IN_CONTAINER]

    exwork_rc, exwork_stdout, _ = run_host_command(
        exwork_cmd, input_data=exwork_stdin_str, cwd=TEST_PROJECT_ROOT_IN_CONTAINER
    )

    if exwork_rc == 0:
        try:
            exwork_report = json.loads(exwork_stdout)
            if exwork_report.get("overall_success"):
                print("[SUCCESS] ExWork execution successful!", flush=True)
                print(
                    "Check for 'QUICK_RUN_SUCCESS.txt' in your quick_test_project directory.",
                    flush=True,
                )
            else:
                print(
                    "[FAILURE] ExWork completed but reported overall_success as false.",
                    flush=True,
                )
        except json.JSONDecodeError:
            print("[FAILURE] ExWork output was not valid JSON.", flush=True)
    else:
        print(f"[FAILURE] ExWork agent failed with exit code {exwork_rc}.", flush=True)
        sys.exit(1)

    print("\n--- Quick Scribe + ExWork Tandem Test Finished ---", flush=True)


if __name__ == "__main__":
    perform_quick_run()
