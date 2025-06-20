# pac_cli/app/core/agent_runner.py
import subprocess
import json
import shlex
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import logging
import os # For environment variables

# Assuming ConfigManager is available for agent paths
# from .config_manager import ConfigManager 
# Assuming LLMInterface might be used by agents or for processing their output
# from .llm_interface import LLMInterface

logger = logging.getLogger(__name__)

class AgentExecutionError(Exception):
    """Custom exception for agent execution failures.".""
    def __init__(self, message: str, stdout: Optional[str] = None, stderr: Optional[str] = None, return_code: Optional[int] = None):
        super().__init__(message)
        self.stdout = stdout
        self.stderr = stderr
        self.return_code = return_code

class BaseAgentRunner:
    """Base class for running external agents like Ex-Work and Scribe.".""
    def __init__(self, agent_name: str, agent_script_path_str: Optional[str], config_manager: Any): # config_manager is type 'ConfigManager'
        self.agent_name = agent_name
        self.agent_script_path_str = agent_script_path_str # Full command string, e.g., "python /path/to/agent.py"
        self.config_manager = config_manager
        self.agent_script_command: List[str] = []

        if not self.agent_script_path_str:
            logger.error(f"Path for {self.agent_name} is not configured. It cannot be run.")
            # Agent runner will be unusable, but don't crash PAC init for this.
            # Calls to run() should handle this.
        else:
            self.agent_script_command = shlex.split(self.agent_script_path_str)
            # Basic validation of the command (e.g., script exists if it's a path)
            if not self.agent_script_command:
                 logger.error(f"Agent command string '{self.agent_script_path_str}' for {self.agent_name} is empty after shlex.split.")
            # Further validation could occur here (e.g. if self.agent_script_command[0] == "python", check if self.agent_script_command[1] exists)

    def _prepare_env(self, project_env_vars: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Prepares the environment for the agent subprocess.".""
        # TODO, Architect: More sophisticated venv activation/management if agents need specific project venvs.
        # For now, assumes agents can run in PAC's venv or find their own way if they are complex.
        # The copied agents (Scribe, Ex-Work) will have their deps in PAC's venv.
        env = os.environ.copy()
        if project_env_vars:
            env.update(project_env_vars)

        # Pass NPT_BASE_DIR to agents so they know their context if needed
        if self.config_manager and self.config_manager.npt_base_dir:
            env["NPT_BASE_DIR"] = str(self.config_manager.npt_base_dir)
        return env

    def run(self,
            args: Optional[List[str]] = None, # For agents that take CLI args
            stdin_data: Optional[str] = None,    # For agents that take stdin
            cwd: Optional[Path] = None,
            project_env_vars: Optional[Dict[str, str]] = None, # Project-specific env vars
            timeout_seconds: Optional[int] = None
           ) -> Tuple[bool, Dict[str, Any], Optional[str], Optional[str]]:
        """
        Runs the configured agent.
        Returns: (success_bool, output_json_dict_or_error_payload, raw_stdout, raw_stderr)
        ".""
        if not self.agent_script_command:
            error_msg = f"{self.agent_name} path not configured or invalid. Cannot execute."
            logger.error(error_msg)
            return False, {"error": error_msg, "details": "Agent path missing in PAC config."}, None, None

        effective_cwd = cwd or (self.config_manager.npt_base_dir if self.config_manager else Path.cwd())
        effective_timeout = timeout_seconds or self.config_manager.get(f"agents.{self.agent_name.lower()}_timeout", 300) # Default 5 mins

        command_to_run = self.agent_script_command + (args if args else [])
        command_str_display = " ".join(shlex.quote(c) for c in command_to_run)

        logger.info(f"Executing {self.agent_name}: {command_str_display}")
        logger.info(f"  CWD: {effective_cwd}")
        if stdin_data:
            logger.info(f"  STDIN (first 100 chars): {stdin_data[:100].strip()}...")

        process_env = self._prepare_env(project_env_vars)

        try:
            process = subprocess.run(
                command_to_run,
                input=stdin_data.encode('utf-8') if stdin_data is not None else None,
                capture_output=True,
                text=True,
                cwd=effective_cwd,
                env=process_env,
                timeout=effective_timeout,
                check=False # We handle return codes
            )

            stdout_str = process.stdout.strip() if process.stdout else ""
            stderr_str = process.stderr.strip() if process.stderr else ""

            logger.debug(f"{self.agent_name} RC: {process.returncode}")
            if stdout_str: logger.debug(f"{self.agent_name} STDOUT:\n{stdout_str}")
            if stderr_str: logger.debug(f"{self.agent_name} STDERR:\n{stderr_str}")

            if process.returncode == 0:
                try:
                    # Assume successful agents output JSON to stdout
                    output_data = json.loads(stdout_str) if stdout_str else {}
                    # Ex-Work specific: check its internal overall_success if present
                    if isinstance(output_data, dict) and 'overall_success' in output_data and not output_data['overall_success']:
                        logger.warning(f"{self.agent_name} reported internal failure (overall_success: false) despite RC=0.")
                        return False, output_data, stdout_str, stderr_str
                    return True, output_data, stdout_str, stderr_str
                except json.JSONDecodeError:
                    logger.warning(f"{self.agent_name} STDOUT was not valid JSON. Treating as success with raw output.")
                    # For Scribe, its JSON output is critical. For Ex-Work, maybe less so if a simple action.
                    # This behavior might need agent-specific handling.
                    return True, {"raw_output": stdout_str, "warning": "Output not JSON"}, stdout_str, stderr_str
            else: # Agent returned non-zero exit code
                error_payload = {
                    "error": f"{self.agent_name} failed with exit code {process.returncode}.",
                    "return_code": process.returncode,
                    "stdout": stdout_str,
                    "stderr": stderr_str
                }
                logger.error(f"{error_payload['error']} stderr: {stderr_str}")
                return False, error_payload, stdout_str, stderr_str

        except subprocess.TimeoutExpired:
            error_msg = f"{self.agent_name} execution timed out after {effective_timeout} seconds."
            logger.error(error_msg)
            return False, {"error": "TimeoutExpired", "details": error_msg}, None, error_msg
        except FileNotFoundError:
            error_msg = f"{self.agent_name} script '{self.agent_script_command[0] if self.agent_script_command else 'UNKNOWN'}' not found. Check path."
            logger.error(error_msg)
            return False, {"error": "AgentScriptNotFound", "details": error_msg}, None, error_msg
        except Exception as e:
            error_msg = f"Unexpected error running {self.agent_name}: {type(e).__name__} - {e}"
            logger.error(error_msg, exc_info=True)
            return False, {"error": "UnexpectedExecutionError", "details": error_msg, "exception_type": type(e).__name__}, None, str(e)

class ExWorkAgentRunner(BaseAgentRunner):
    def __init__(self, config_manager: Any): # ConfigManager type
        agent_path = config_manager.get("agents.ex_work_agent_path")
        super().__init__("Ex-Work Agent", agent_path, config_manager)

    def execute_instruction_block(self, instruction_json_str: str, project_path: Path, timeout_seconds: Optional[int] = None) -> Tuple[bool, Dict[str, Any]]:
        """Sends a JSON instruction block to Ex-Work via stdin and gets JSON response.".""
        if not self.agent_script_command: return False, {"error": "Ex-Work agent not configured."}

        success, output_data, raw_stdout, raw_stderr = self.run(
            stdin_data=instruction_json_str,
            cwd=project_path,
            timeout_seconds=timeout_seconds
        )
        # Ex-Work's output_data should already be the parsed JSON response.
        # If !success, output_data contains the error payload from BaseAgentRunner.
        return success, output_data

class ScribeAgentRunner(BaseAgentRunner):
    def __init__(self, config_manager: Any): # ConfigManager type
        agent_path = config_manager.get("agents.scribe_agent_path")
        super().__init__("Scribe Agent", agent_path, config_manager)

    def run_validation(self,
                       target_dir: Path,
                       code_file: Path, # Absolute path to temp code file
                       target_file_relative: str, # Relative to target_dir
                       scribe_profile_path: Optional[Path] = None, # Absolute path to .scribe.toml
                       commit: bool = False,
                       skip_deps: bool = False,
                       skip_tests: bool = False,
                       skip_review: bool = False,
                       timeout_seconds: Optional[int] = None
                      ) -> Tuple[bool, Dict[str, Any]]:
        """Constructs Scribe CLI args and runs it.".""
        if not self.agent_script_command: return False, {"error": "Scribe agent not configured."}

        args = [
            "--target-dir", str(target_dir),
            "--code-file", str(code_file),
            "--target-file", target_file_relative,
            # TODO, Architect: Scribe's language & python_version args might be useful here from PAC config
        ]
        if scribe_profile_path:
            args.extend(["--config-file", str(scribe_profile_path)])
        if commit: args.append("--commit")
        if skip_deps: args.append("--skip-deps")
        if skip_tests: args.append("--skip-tests")
        if skip_review: args.append("--skip-review")

        # Scribe outputs its JSON report to stdout.
        success, output_data, raw_stdout, raw_stderr = self.run(
            args=args,
            cwd=target_dir, # Scribe operates within the target project directory
            timeout_seconds=timeout_seconds
        )
        return success, output_data