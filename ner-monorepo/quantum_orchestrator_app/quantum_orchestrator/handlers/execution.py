"""
Execution handlers for the Quantum Orchestrator.

Provides handlers for running scripts and Python code in a controlled environment.
"""

import os
import subprocess
import sys
import tempfile
import time
import json
from typing import Any, Dict

from quantum_orchestrator.handlers import handler
from quantum_orchestrator.utils.logging_utils import get_logger
from quantum_orchestrator.utils.security import sanitize_command, is_allowed_command
from quantum_orchestrator.utils.path_resolver import resolve_path
from quantum_orchestrator.games.nexus_omniengine_v3.core.config import Config

logger = get_logger(__name__)
config = Config()


@handler(
    name="run_script",
    description="Runs a script file or command with arguments",
    parameters={
        "command": {"type": "string", "description": "Command to run"},
        "args": {"type": "array", "description": "Command arguments", "default": []},
        "cwd": {"type": "string", "description": "Working directory", "default": "./"},
        "timeout": {
            "type": "number",
            "description": "Timeout in seconds",
            "default": 60,
        },
        "env": {
            "type": "object",
            "description": "Environment variables",
            "default": {},
        },
    },
    returns={
        "success": {
            "type": "boolean",
            "description": "Whether the command executed successfully",
        },
        "stdout": {"type": "string", "description": "Standard output from command"},
        "stderr": {"type": "string", "description": "Standard error from command"},
        "exit_code": {"type": "number", "description": "Exit code of the command"},
        "execution_time": {
            "type": "number",
            "description": "Execution time in seconds",
        },
        "error": {"type": "string", "description": "Error message if execution failed"},
    },
)
def run_script(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run a script file or command with arguments.

    Args:
        params: Dictionary containing command, args, cwd, timeout, and env

    Returns:
        Dict containing execution results
    """
    try:
        command = params.get("command", "")
        args = params.get("args", [])
        cwd = params.get("cwd", "./")
        timeout = params.get(
            "timeout", config.get("handlers", "execution", {}).get("timeout", 60)
        )
        env_vars = params.get("env", {})

        # Validate command
        if not command:
            return {"success": False, "error": "No command provided"}

        # Check if command is allowed
        allowed_commands = config.get("handlers", "execution", {}).get(
            "allowed_commands", ["python", "python3", "pip", "pip3"]
        )

        if not is_allowed_command(command, allowed_commands):
            return {
                "success": False,
                "error": f"Command not allowed: {command}. Allowed commands: {', '.join(allowed_commands)}",
            }

        # Sanitize command and arguments
        safe_command = sanitize_command(command)
        safe_args = [sanitize_command(arg) for arg in args if arg]

        # Resolve working directory
        if cwd:
            cwd = resolve_path(cwd)
            if not os.path.exists(cwd):
                os.makedirs(cwd, exist_ok=True)

        # Prepare environment
        env = os.environ.copy()
        for key, value in env_vars.items():
            env[key] = str(value)

        # Start execution time
        start_time = time.time()

        # Run command with timeout
        cmd = [safe_command] + safe_args
        logger.info(f"Running command: {' '.join(cmd)}")

        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=cwd,
                env=env,
                text=True,
            )

            stdout, stderr = process.communicate(timeout=timeout)
            exit_code = process.returncode

        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
            exit_code = -1
            return {
                "success": False,
                "stdout": stdout,
                "stderr": stderr,
                "exit_code": exit_code,
                "execution_time": time.time() - start_time,
                "error": f"Command timed out after {timeout} seconds",
            }

        # Calculate execution time
        execution_time = time.time() - start_time

        # Determine success based on exit code
        success = exit_code == 0

        logger.info(
            f"Command completed with exit code {exit_code} in {execution_time:.2f} seconds"
        )

        return {
            "success": success,
            "stdout": stdout,
            "stderr": stderr,
            "exit_code": exit_code,
            "execution_time": execution_time,
            "error": None if success else f"Command failed with exit code {exit_code}",
        }

    except Exception as e:
        logger.error(f"Error running script: {str(e)}")
        return {"success": False, "error": f"Error running script: {str(e)}"}


@handler(
    name="run_python_code",
    description="Runs Python code in a sandboxed environment",
    parameters={
        "code": {"type": "string", "description": "Python code to execute"},
        "timeout": {
            "type": "number",
            "description": "Timeout in seconds",
            "default": 60,
        },
        "env": {
            "type": "object",
            "description": "Environment variables",
            "default": {},
        },
        "inputs": {
            "type": "object",
            "description": "Input values to make available to the code",
            "default": {},
        },
    },
    returns={
        "success": {
            "type": "boolean",
            "description": "Whether the code executed successfully",
        },
        "result": {"type": "object", "description": "Result returned by the code"},
        "stdout": {"type": "string", "description": "Standard output from the code"},
        "stderr": {"type": "string", "description": "Standard error from the code"},
        "execution_time": {
            "type": "number",
            "description": "Execution time in seconds",
        },
        "error": {"type": "string", "description": "Error message if execution failed"},
    },
)
def run_python_code(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run Python code in a sandboxed environment.

    Args:
        params: Dictionary containing code, timeout, env, and inputs

    Returns:
        Dict containing execution results
    """
    try:
        code = params.get("code", "")
        timeout = params.get(
            "timeout", config.get("handlers", "execution", {}).get("timeout", 60)
        )
        env_vars = params.get("env", {})
        inputs = params.get("inputs", {})

        # Validate code
        if not code:
            return {"success": False, "error": "No code provided"}

        # Create a temporary file for the code
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as tmp:
            # Write code that captures stdout/stderr and returns result
            tmp.write(
                """
import sys
import os
import json
import traceback
from io import StringIO

# Set environment variables
{env_setup}

# Capture stdout and stderr
stdout_capture = StringIO()
stderr_capture = StringIO()
sys_stdout = sys.stdout
sys_stderr = sys.stderr
sys.stdout = stdout_capture
sys.stderr = stderr_capture

# Make inputs available
inputs = {inputs}

# Execute the code in a new namespace
namespace = {{"inputs": inputs}}
result = None
success = True
error = None

try:
    # Add the code to execute
    exec('''
{code}
''', namespace)

    # Check if result was defined
    if 'result' in namespace:
        result = namespace['result']

except Exception as e:
    success = False
    error = str(e)
    traceback.print_exc(file=sys.stderr)

# Restore stdout and stderr
sys.stdout = sys_stdout
sys.stderr = sys_stderr

# Prepare output
output = {{
    "success": success,
    "result": result,
    "stdout": stdout_capture.getvalue(),
    "stderr": stderr_capture.getvalue(),
    "error": error
}}

# Print output as JSON (will be captured by the parent process)
print("ORCHESTRATOR_RESULT_BEGIN")
print(json.dumps(output))
print("ORCHESTRATOR_RESULT_END")
""".format(
                    env_setup="\n".join(
                        [f"os.environ['{k}'] = '{v}'" for k, v in env_vars.items()]
                    ),
                    inputs=json.dumps(inputs),
                    code=code.replace("\\", "\\\\").replace("'''", "\\'\\'\\'"),
                )
            )

            tmp_path = tmp.name

        # Start execution time
        start_time = time.time()

        # Run the temporary script with timeout
        try:
            cmd = [sys.executable, tmp_path]
            logger.info(f"Running Python code with timeout {timeout} seconds")

            process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )

            stdout, stderr = process.communicate(timeout=timeout)
            exit_code = process.returncode

        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()

            # Calculate execution time
            execution_time = time.time() - start_time

            return {
                "success": False,
                "stdout": stdout,
                "stderr": stderr,
                "execution_time": execution_time,
                "error": f"Code execution timed out after {timeout} seconds",
            }
        finally:
            # Clean up the temporary file
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

        # Calculate execution time
        execution_time = time.time() - start_time

        # Parse result from stdout
        result = None
        if (
            "ORCHESTRATOR_RESULT_BEGIN" in stdout
            and "ORCHESTRATOR_RESULT_END" in stdout
        ):
            try:
                result_json = (
                    stdout.split("ORCHESTRATOR_RESULT_BEGIN")[1]
                    .split("ORCHESTRATOR_RESULT_END")[0]
                    .strip()
                )
                result = json.loads(result_json)

                # Extract stdout/stderr and remove JSON output
                if "stdout" in result:
                    stdout = result["stdout"]
                if "stderr" in result:
                    stderr = result["stderr"]

                # Return the parsed result
                return {
                    "success": result.get("success", exit_code == 0),
                    "result": result.get("result"),
                    "stdout": stdout,
                    "stderr": stderr,
                    "execution_time": execution_time,
                    "error": result.get("error"),
                }
            except (json.JSONDecodeError, Exception):
                pass

        # Fallback if output parsing fails
        return {
            "success": exit_code == 0,
            "result": None,
            "stdout": stdout,
            "stderr": stderr,
            "execution_time": execution_time,
            "error": (
                f"Code failed with exit code {exit_code}" if exit_code != 0 else None
            ),
        }

    except Exception as e:
        logger.error(f"Error running Python code: {str(e)}")
        return {"success": False, "error": f"Error running Python code: {str(e)}"}
