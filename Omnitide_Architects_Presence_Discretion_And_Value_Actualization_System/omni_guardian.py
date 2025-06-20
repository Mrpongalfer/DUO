import asyncio
import subprocess
import os
import time
import logging
import re
import psutil
from typing import Dict, List, Tuple, Optional, Set, Any

# Logging Configuration
log_level = os.environ.get("OMNI_GUARDIAN_LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("OMNI_GUARDIAN")

# Constants & Configuration
LOG_DIR = "logs/"
OAPDVAS_PROCESS_NAMES = [
    "main_oapdvas_service.py",
    "contextual_informational_access_and_synthesis.py",
    "automated_digital_resource_genesis_and_outreach.py",
    "harmonized_resource_velocity_optimizer.py",
    "cpddiap_core.py",
]
MONGO_CONTAINER_NAME = "mongodb"
OAPDVAS_CORE_CONTAINER_NAME = "oapdvas-core"
START_SCRIPT_PATH = "./start_oapdvas.sh"
ARCHITECT_DIGITAL_VAULT = os.getenv(
    "ARCHITECT_DIGITAL_VAULT", "YOUR_DIGITAL_VAULT_ADDRESS_HERE"
)
MONITOR_INTERVAL_SECONDS = 5

if ARCHITECT_DIGITAL_VAULT == "YOUR_DIGITAL_VAULT_ADDRESS_HERE":
    logger.critical(
        "ARCHITECT_DIGITAL_VAULT is set to the placeholder! Please set your actual vault address."
    )


class OmniGuardian:
    def __init__(self, vault_address: str):
        self.vault_address = vault_address
        self.known_pids: Set[int] = set()
        self.actualized_revenue_tracker: float = 0.0
        self.log_file_pointers: Dict[str, Any] = {}
        logger.info("OmniGuardian initialized for vault: %s", self.vault_address)

    def _get_process_status(self, process_name: str) -> Optional[psutil.Process]:
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                if any(process_name in str(x) for x in proc.info.get("cmdline", [])):
                    return proc
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return None

    def _is_docker_daemon_running(self) -> bool:
        result = subprocess.run(["docker", "info"], capture_output=True, text=True)
        return result.returncode == 0

    def _is_container_running(self, container_name: str) -> bool:
        result = subprocess.run(
            ["docker", "inspect", "-f", "{{.State.Running}}", container_name],
            capture_output=True,
            text=True,
        )
        return result.stdout.strip() == "true"

    def _get_container_logs(self, container_name: str) -> str:
        result = subprocess.run(
            ["docker", "logs", "--tail", "50", container_name],
            capture_output=True,
            text=True,
        )
        return result.stdout + result.stderr

    def _run_shell_command(
        self, command: List[str], check_result: bool = True
    ) -> Tuple[bool, str]:
        try:
            result = subprocess.run(command, capture_output=True, text=True)
            if check_result:
                return result.returncode == 0, result.stdout + result.stderr
            else:
                return True, result.stdout + result.stderr
        except Exception as e:
            logger.error(f"Shell command failed: {command} | {e}")
            return False, str(e)

    def diagnose_and_remediate_issue(self, issue_type: str, context: Dict) -> Dict:
        logger.warning(
            f"Diagnosing and remediating issue: {issue_type} | Context: {context}"
        )
        if issue_type == "mongodb_down":
            logger.warning("Attempting to start MongoDB container...")
            success, output = self._run_shell_command(
                ["docker", "start", MONGO_CONTAINER_NAME]
            )
            if success:
                logger.info("MongoDB started.")
                return {"status": "fixed", "message": "MongoDB started."}
            else:
                return {
                    "status": "failed_fix",
                    "message": f"Failed to start MongoDB: {output}",
                }
        elif issue_type == "oapdvas_module_down":
            logger.warning(f"Attempting to restart {context.get('module_name')}...")
            success, output = self._run_shell_command([START_SCRIPT_PATH])
            if success:
                logger.info(f"{context.get('module_name')} restarted.")
                return {
                    "status": "fixed",
                    "message": f"{context.get('module_name')} restarted.",
                }
            else:
                return {
                    "status": "failed_fix",
                    "message": f"Failed to restart {context.get('module_name')}: {output}",
                }
        elif issue_type == "python_module_error":
            logger.warning("Attempting to re-export PYTHONPATH and activate venv...")
            # Not directly fixable from daemon context; log suggestion
            return {
                "status": "suggestion",
                "message": 'Manual action required: source venv/bin/activate && export PYTHONPATH="$PWD"',
            }
        elif issue_type == "nltk_data_error":
            logger.warning("Attempting to download missing NLTK data...")
            success, output = self._run_shell_command(
                ["python3", "-c", "import nltk; nltk.download('all', quiet=True)"]
            )
            if success:
                logger.info("NLTK data downloaded.")
                return {"status": "fixed", "message": "NLTK data downloaded."}
            else:
                return {
                    "status": "failed_fix",
                    "message": f"Failed to download NLTK data: {output}",
                }
        elif issue_type == "port_conflict":
            logger.warning(
                "Detected potential port conflict/firewall issue. Suggesting manual review."
            )
            return {
                "status": "suggestion",
                "message": "Port 8000 might be blocked. Check firewall or occupied ports (netstat -tulnp).",
            }
        else:
            return {
                "status": "no_fix",
                "message": "No automated fix available. Manual Architect intervention required.",
            }

    async def monitor_and_remediate(self):
        while True:
            # Monitor Docker/MongoDB
            if not self._is_docker_daemon_running():
                logger.critical("Docker daemon is not running! Please start Docker.")
            elif not self._is_container_running(MONGO_CONTAINER_NAME):
                self.diagnose_and_remediate_issue("mongodb_down", {})
            elif not self._is_container_running(OAPDVAS_CORE_CONTAINER_NAME):
                self.diagnose_and_remediate_issue(
                    "oapdvas_module_down", {"module_name": "main_oapdvas_service.py"}
                )
            # Monitor OAPDVAS Python Processes
            for process_name in OAPDVAS_PROCESS_NAMES:
                proc = self._get_process_status(process_name)
                if not proc:
                    self.diagnose_and_remediate_issue(
                        "oapdvas_module_down", {"module_name": process_name}
                    )
            # Parse logs for errors & actualized revenue
            for log_file in os.listdir(LOG_DIR):
                log_path = os.path.join(LOG_DIR, log_file)
                if not os.path.isfile(log_path):
                    continue
                if log_path not in self.log_file_pointers:
                    self.log_file_pointers[log_path] = 0
                try:
                    with open(log_path, "r") as f:
                        f.seek(self.log_file_pointers[log_path])
                        lines = f.readlines()
                        self.log_file_pointers[log_path] = f.tell()
                        for line in lines:
                            if (
                                "ModuleNotFoundError" in line
                                or "ConnectionFailure" in line
                                or "Error during" in line
                                or "failed_fix" in line
                            ):
                                self.diagnose_and_remediate_issue(
                                    "python_module_error", {"log": line}
                                )
                            if (
                                "nltk_data" in line
                                or "Resource punkt not found" in line
                            ):
                                self.diagnose_and_remediate_issue(
                                    "nltk_data_error", {"log": line}
                                )
                            m = re.search(r"Actualized value: ([\d.]+)", line)
                            if m:
                                value = float(m.group(1))
                                self.actualized_revenue_tracker += value
                except Exception as e:
                    logger.warning(f"Log parse error: {e}")
            # Conceptual CI/CD & Proactive Suggestions
            if int(time.time()) % 300 < MONITOR_INTERVAL_SECONDS:
                logger.info(
                    "Suggesting CI/CD pipeline optimization for OAPDVAS code changes."
                )
                logger.info(
                    "Proposing dynamic IP rotation for CPDDIAP via cloud proxy integration."
                )
            await asyncio.sleep(MONITOR_INTERVAL_SECONDS)


if __name__ == "__main__":
    guardian = OmniGuardian(ARCHITECT_DIGITAL_VAULT)
    asyncio.run(guardian.monitor_and_remediate())
