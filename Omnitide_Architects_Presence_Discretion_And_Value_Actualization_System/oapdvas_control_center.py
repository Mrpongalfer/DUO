import asyncio
import subprocess
import os
import logging
import re
import collections
import psutil
from typing import Dict, Optional, Any

from textual.app import App
from textual.widgets import (
    Header,
    Footer,
    Static,
    Button,
    Input,
)  # Removed Panel import
from textual.containers import Container, Horizontal, Vertical
from textual.reactive import reactive
from textual.binding import Binding
from textual.screen import Screen
from rich.text import Text

# Ensure logging is configured for this module
logger = logging.getLogger("OAPDVAS_CONTROL_CENTER")
log_level = os.environ.get("OAPDVAS_CONTROL_CENTER_LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)


class OAPDVASControlCenter(App):
    # Reactive Attributes
    status_message = reactive("Initializing OAPDVAS Control Center...")
    total_actualized_value = reactive(0.0)
    recent_actualizations: reactive[collections.deque[str]] = reactive(
        collections.deque(maxlen=10)
    )
    module_data: reactive[Dict[str, Dict[str, Any]]] = reactive({})
    system_metrics: reactive[Dict[str, Any]] = reactive({})
    environment_git_status: reactive[Dict[str, str]] = reactive({})
    omni_guardian_alerts: reactive[collections.deque[str]] = reactive(
        collections.deque(maxlen=5)
    )
    log_lines: reactive[collections.deque[str]] = reactive(
        collections.deque(maxlen=500)
    )

    # Binding Definitions
    BINDINGS = [
        Binding("q", "quit_app", "Quit", show=True, key_display="Q"),
        Binding("s", "start_oapdvas", "Start All", show=True, key_display="S"),
        Binding("x", "stop_oapdvas", "Stop All", show=True, key_display="X"),
        Binding("r", "refresh_data", "Refresh", show=True, key_display="R"),
        Binding("m", "start_mongo", "Start Mongo", show=True, key_display="M"),
        Binding("k", "stop_mongo", "Stop Mongo", show=True, key_display="K"),
        Binding("p", "git_pull", "Git Pull", show=True, key_display="P"),
        Binding("c", "git_commit", "Git Commit", show=True, key_display="C"),
        Binding("u", "git_push", "Git Push", show=True, key_display="U"),
    ]

    # Constants
    LOG_DIR = "logs/"
    OAPDVAS_PROCESS_NAMES = [
        "main_oapdvas_service.py",
        "contextual_informational_access_and_synthesis.py",
        "automated_digital_resource_genesis_and_outreach.py",
        "harmonized_resource_velocity_optimizer.py",
        "cpddiap_core.py",
        "omni_guardian.py",
    ]
    MONGO_CONTAINER_NAME = "mongodb"
    OAPDVAS_CORE_CONTAINER_NAME = "oapdvas-core"
    START_SCRIPT_PATH = "./start_oapdvas.sh"

    def __init__(self):
        super().__init__()
        self.log_buffer = collections.deque(maxlen=500)
        self.total_actualized_value = 0.0
        self.recent_actualizations = collections.deque(maxlen=10)
        self.module_pids: Dict[str, Optional[int]] = {}
        self.log_file_pointers: Dict[str, Any] = {}
        self.current_git_branch = ""
        self.git_status_summary = ""
        logger.info("OAPDVASControlCenter initialized.")

    def render_system_metrics(self) -> Text:
        """Renders system metrics for the UI."""
        cpu = self.system_metrics.get("cpu_percent", "N/A")
        mem = self.system_metrics.get("mem_percent", "N/A")
        disk_usage = self.system_metrics.get("disk_usage", "N/A")
        net_io_sent = self.system_metrics.get("net_io_sent", "N/A")
        net_io_recv = self.system_metrics.get("net_io_recv", "N/A")

        return Text.from_markup(
            f"[bold green]CPU:[/][blue] {cpu:.1f}%[/]\n"
            f"[bold green]Memory:[/][blue] {mem:.1f}%[/]\n"
            f"[bold green]Disk Used:[/][blue] {disk_usage:.1f}%[/]\n"
            f"[bold green]Net Sent:[/][blue] {net_io_sent / (1024**2):.2f} MB[/]\n"
            f"[bold green]Net Recv:[/][blue] {net_io_recv / (1024**2):.2f} MB[/]"
        )

    def render_module_status(self) -> Text:
        """Renders OAPDVAS module statuses."""
        status_text = Text()
        for name in self.OAPDVAS_PROCESS_NAMES:
            status = self.module_data.get(name, {})
            pid = status.get("pid", "N/A")
            cpu_p = status.get("cpu_percent", "N/A")
            mem_p = status.get("mem_percent", "N/A")
            running_status = (
                "[bold green]Running[/]"
                if status.get("running", False)
                else "[bold red]Stopped[/]"
            )
            status_text.append(f"{name}:\n")
            status_text.append(
                f"  PID: {pid} | Status: {running_status} | CPU: {cpu_p:.1f}% | Mem: {mem_p:.1f}%\n",
                style="italic blue",
            )
        return status_text

    def render_revenue_actualization(self) -> Text:
        """Renders the revenue actualization summary."""
        discretion_status = "[bold green]Optimal[/]"  # Default, updated by log parsing
        # Simple check for warning based on logs
        # The line below checks if 'POSSIBLE_RESIDUAL_NOISE' is present anywhere in the collected log lines.
        # This gives a basic indicator of potential discretion issues.
        if any("POSSIBLE_RESIDUAL_NOISE" in line for line in self.log_lines):
            discretion_status = "[bold yellow]Monitoring[/]"

        # Corrected multi-line f-string syntax
        summary = Text.from_markup(
            f"""[bold white on blue]Total Actualized Value:[/][bold green] ${self.total_actualized_value:.2f}[/]\n
[bold white on green]Discretion Status:[/]{discretion_status}\n\n
[bold white on magenta]Recent Actualizations:[/]\n"""
        )
        for act in self.recent_actualizations:
            summary.append(f"- {act}\n", style="italic cyan")
        return summary

    def render_environment_git_status(self) -> Text:
        """Renders environment and Git status."""
        status = self.environment_git_status
        return Text.from_markup(
            f"[bold green]Shell:[/][blue] {status.get('shell', 'N/A')}[/]\n"
            f"[bold green]User:[/][blue] {status.get('user', 'N/A')}[/]\n"
            f"[bold green]Root:[/][blue] {status.get('is_root', 'N/A')}[/]\n"
            f"[bold green]Docker Daemon:[/][blue] {status.get('docker_daemon', 'N/A')}[/]\n"
            f"[bold green]MongoDB Container:[/][blue] {status.get('mongo_container', 'N/A')}[/]\n"
            f"[bold green]Git Branch:[/][blue] {status.get('git_branch', 'N/A')}[/]\n"
            f"[bold green]Git Status:[/][blue] {status.get('git_summary', 'N/A')}[/]"
        )

    def render_omni_guardian_alerts(self) -> Text:
        """Renders Omni-Guardian alerts and suggestions."""
        alerts = Text.from_markup("[bold white on yellow]Omni-Guardian Alerts:[/]\n")
        if not self.omni_guardian_alerts:
            alerts.append("[italic grey]No active alerts from Omni-Guardian.[/]\n")
        else:
            for alert in self.omni_guardian_alerts:
                alerts.append(f"[yellow]- {alert}[/]\n")
        return alerts

    # \-\-\- Layout Definition \-\-\-
    def compose(self):
        yield Header(show_clock=True)
        with Container(classes="app-grid"):
            with Horizontal(classes="top-panels"):
                with Vertical(classes="panel-column"):
                    # System Metrics Panel
                    self.metrics_panel_content = Static("", id="metrics_display")
                    yield self.metrics_panel_content
                    # Revenue Actualization Panel
                    self.revenue_panel_content = Static("", id="revenue_display")
                    yield self.revenue_panel_content
                with Vertical(classes="panel-column"):
                    # OAPDVAS Modules Panel
                    self.module_status_content = Static("", id="module_status_display")
                    yield self.module_status_content
                    # Environment & Git Panel
                    self.env_git_content = Static("", id="env_git_display")
                    yield self.env_git_content
                    # Omni-Guardian Alerts Panel
                    self.alerts_content = Static("", id="alerts_display")
                    yield self.alerts_content
            # Live OAPDVAS Log Stream (Bottom-Full Width)
            self.log_display = Static("", id="log_stream", expand=True)
            yield self.log_display
        yield Footer()

    # \-\-\- Lifecycle Methods \-\-\-
    def on_mount(self):
        self.set_interval(interval=1.0, callback=self.update_all_panels)
        self.set_interval(interval=0.2, callback=self.tail_and_parse_logs)
        self.update_all_panels()  # Initial update
        logger.info("OAPDVAS Control Center mounted. Starting periodic updates.")

    async def update_all_panels(self):
        # Update System Metrics
        self.update_system_metrics()
        self.query_one("#metrics_display").update(self.render_system_metrics())
        # Update Module Status
        await self.update_module_status()
        self.query_one("#module_status_display").update(self.render_module_status())
        # Update Revenue Actualization
        self.query_one("#revenue_display").update(self.render_revenue_actualization())
        # Update Environment & Git Status
        self.update_environment_git_status()
        self.query_one("#env_git_display").update(self.render_environment_git_status())
        # Update Omni\-Guardian Alerts
        self.query_one("#alerts_display").update(self.render_omni_guardian_alerts())
        # Update status message in footer or header if desired
        # self.status_message = "System operational." # Or dynamic status based on health checks

    def update_system_metrics(self):
        """Updates system metrics data."""
        cpu_percent = psutil.cpu_percent(interval=None)
        mem_info = psutil.virtual_memory()
        disk_usage = psutil.disk_usage("/").percent
        net_io = psutil.net_io_counters()
        self.system_metrics = {
            "cpu_percent": cpu_percent,
            "mem_percent": mem_info.percent,
            "disk_usage": disk_usage,
            "net_io_sent": net_io.bytes_sent,
            "net_io_recv": net_io.bytes_recv,
        }

    async def update_module_status(self):
        """Updates status and metrics for OAPDVAS modules."""
        updated_module_data = {}
        for process_name in self.OAPDVAS_PROCESS_NAMES:
            process_found = False
            for p in psutil.process_iter(
                ["pid", "name", "cmdline", "cpu_percent", "memory_percent"]
            ):
                try:
                    cmdline = p.cmdline()
                    if cmdline and process_name in " ".join(cmdline):
                        updated_module_data[process_name] = {
                            "pid": p.pid,
                            "running": True,
                            "cpu_percent": p.cpu_percent(interval=None),
                            "mem_percent": p.memory_percent(),
                        }
                        process_found = True
                        break
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            if not process_found:
                updated_module_data[process_name] = {
                    "pid": "N/A",
                    "running": False,
                    "cpu_percent": 0.0,
                    "mem_percent": 0.0,
                }
        self.module_data = updated_module_data

    def update_environment_git_status(self):
        """Updates environment and Git status."""
        shell = os.environ.get("SHELL", "Unknown")
        user = os.environ.get("USER", "Unknown")
        is_root = "Yes" if os.geteuid() == 0 else "No"
        # Docker Daemon Status
        docker_daemon_status = "Stopped"
        try:
            subprocess.run(
                ["docker", "info"], capture_output=True, text=True, check=True
            )
            docker_daemon_status = "Running"
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
        # MongoDB Container Status
        mongo_container_status = "Stopped"
        try:
            result = subprocess.run(
                [
                    "docker",
                    "inspect",
                    "-f",
                    "{{.State.Running}}",
                    self.MONGO_CONTAINER_NAME,
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            if result.stdout.strip() == "true":
                mongo_container_status = "Running"
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
        # Git Status
        git_branch = "N/A"
        git_summary = "N/A"
        try:
            # Get current branch
            branch_result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True,
                text=True,
                cwd=os.getcwd(),
                check=True,
            )
            git_branch = branch_result.stdout.strip()
            # Get git status summary
            status_result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                cwd=os.getcwd(),
                check=True,
            )
            if status_result.stdout.strip():
                git_summary = "Modified/Untracked Files"
            else:
                git_summary = "Clean"
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass  # Not a git repo, or git not found
        self.environment_git_status = {
            "shell": shell,
            "user": user,
            "is_root": is_root,
            "docker_daemon": docker_daemon_status,
            "mongo_container": mongo_container_status,
            "git_branch": git_branch,
            "git_summary": git_summary,
        }

    def tail_and_parse_logs(self):
        """Reads new log lines and updates UI elements."""
        log_files = [
            os.path.join(self.LOG_DIR, f)
            for f in os.listdir(self.LOG_DIR)
            if f.endswith(".log")
        ]
        for log_file_path in log_files:
            if log_file_path not in self.log_file_pointers:
                try:
                    self.log_file_pointers[log_file_path] = open(
                        log_file_path, "r", encoding="utf-8"
                    )
                    self.log_file_pointers[log_file_path].seek(0, 2)  # Go to end
                except IOError:
                    logger.warning(f"Could not open log file: {log_file_path}")
                    continue
            try:
                new_lines = self.log_file_pointers[log_file_path].readlines()
                for line in new_lines:
                    self.log_lines.append(line.strip())
                    # Simple parsing for actualization and alerts
                    if (
                        "Actualized value:" in line
                        or "Insight exchanged" in line
                        or "Resource exchanged" in line
                    ):
                        match = re.search(r"\(\$[\d\.]+\)\s*(MONERO|BTC|ETH)?", line)
                        if match:
                            amount = float(match.group(1).replace("</span>", ""))
                            self.total_actualized_value += amount
                            self.recent_actualizations.append(f"{line.strip()}")
                        elif (
                            "Resource flow to" in line
                            and "completed. Total imprint: ZERO" in line
                        ):
                            self.recent_actualizations.append(f"{line.strip()}")

                    if "CRITICAL:" in line or "ERROR:" in line or "WARNING:" in line:
                        # Basic Omni-Guardian Alert logic
                        if (
                            "omni_guardian.py" not in line
                        ):  # Avoid double-alerting if OG already logged it
                            self.omni_guardian_alerts.append(f"[red]{line.strip()}[/]")

                    if (
                        "Omni-Guardian: Suggesting" in line
                        or "Omni-Guardian: Attempting to fix" in line
                    ):
                        self.omni_guardian_alerts.append(f"[yellow]{line.strip()}[/]")

            except Exception as e:
                logger.error(
                    f"Error reading log file {log_file_path}: {e}", exc_info=True
                )

        # Update the Static widget display
        self.query_one("#log_stream").update(
            Text("\n".join(self.log_lines), justify="left")
        )
        # Auto-scroll to end if new lines were added
        # This requires more advanced textual control or RichLog which handles it.

    # --- Actions (Menu/Keybindings) ---
    async def action_start_oapdvas(self):
        """Starts all OAPDVAS modules."""
        self.app.bell()  # Signal user action
        if await self.confirm_action("Start all OAPDVAS modules?"):
            logger.info("Attempting to start all OAPDVAS modules...")
            try:
                # Use subprocess.Popen for non-blocking execution of the start script
                # We do not use await here, as start_oapdvas.sh is long-running
                process = subprocess.Popen(
                    [self.START_SCRIPT_PATH],
                    cwd=os.getcwd(),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                )
                logger.info(f"OAPDVAS start script initiated with PID: {process.pid}")
                self.status_message = "OAPDVAS starting..."
                # Read output from the script (non-blocking if desired, or let logs show it)
                # This could be handled by omni_guardian monitoring logs
            except Exception as e:
                logger.error(f"Failed to execute start script: {e}", exc_info=True)
                self.status_message = f"Failed to start OAPDVAS: {e}"
        else:
            self.status_message = "OAPDVAS start cancelled."

    async def action_stop_oapdvas(self):
        """Stops all OAPDVAS modules."""
        self.app.bell()
        if await self.confirm_action(
            "Stop all OAPDVAS modules? This will kill Python processes."
        ):
            logger.info("Attempting to stop all OAPDVAS modules...")
            try:
                # Use pkill -f python3 for simplicity, but be aware it's broad.
                # A more precise way would be to track PIDs from start_oapdvas.sh
                subprocess.run(
                    ["pkill", "-f", "python3"],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                # Wait a moment for processes to terminate
                await asyncio.sleep(2)
                logger.info("All OAPDVAS Python processes likely stopped.")
                self.status_message = "OAPDVAS stopped."
            except subprocess.CalledProcessError as e:
                logger.error(
                    f"Failed to kill Python processes: {e.stderr}", exc_info=True
                )
                self.status_message = f"Failed to stop OAPDVAS: {e.stderr}"
            except Exception as e:
                logger.error(f"Error stopping OAPDVAS: {e}", exc_info=True)
                self.status_message = f"Error stopping OAPDVAS: {e}"
        else:
            self.status_message = "OAPDVAS stop cancelled."

    async def action_start_mongo(self):
        """Starts the MongoDB container."""
        self.app.bell()
        if await self.confirm_action("Start MongoDB container?"):
            logger.info("Attempting to start MongoDB container...")
            try:
                subprocess.run(
                    ["docker", "start", self.MONGO_CONTAINER_NAME],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                logger.info("MongoDB container started.")
                self.status_message = "MongoDB started."
            except subprocess.CalledProcessError as e:
                logger.error(
                    f"Failed to start MongoDB container: {e.stderr}", exc_info=True
                )
                self.status_message = f"Failed to start MongoDB: {e.stderr}"
            except FileNotFoundError:
                logger.error(
                    "Docker command not found. Is Docker installed and in PATH?"
                )
                self.status_message = "Docker not found."
            except Exception as e:
                logger.error(f"Error starting MongoDB: {e}", exc_info=True)

    async def action_stop_mongo(self):
        """Stops the MongoDB container."""
        self.app.bell()
        if await self.confirm_action("Stop MongoDB container?"):
            logger.info("Attempting to stop MongoDB container...")
            try:
                subprocess.run(
                    ["docker", "stop", self.MONGO_CONTAINER_NAME],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                logger.info("MongoDB container stopped.")
                self.status_message = "MongoDB stopped."
            except subprocess.CalledProcessError as e:
                logger.error(
                    f"Failed to stop MongoDB container: {e.stderr}", exc_info=True
                )
                self.status_message = f"Failed to stop MongoDB: {e.stderr}"
            except FileNotFoundError:
                logger.error(
                    "Docker command not found. Is Docker installed and in PATH?"
                )
                self.status_message = "Docker not found."
            except Exception as e:
                logger.error(f"Error stopping MongoDB: {e}", exc_info=True)

    async def action_git_pull(self):
        """Performs a git pull on the project."""
        self.app.bell()
        if await self.confirm_action("Perform git pull?"):
            logger.info("Attempting git pull...")
            try:
                result = subprocess.run(
                    ["git", "pull"],
                    check=True,
                    capture_output=True,
                    text=True,
                    cwd=os.getcwd(),
                )
                logger.info(f"Git pull successful: {result.stdout.strip()}")
                self.status_message = "Git pull complete."
            except subprocess.CalledProcessError as e:
                logger.error(f"Git pull failed: {e.stderr}", exc_info=True)
                self.status_message = f"Git pull failed: {e.stderr}"
            except FileNotFoundError:
                logger.error("Git command not found. Is Git installed and in PATH?")
                self.status_message = "Git not found."
            except Exception as e:
                logger.error(f"Error during git pull: {e}", exc_info=True)

    async def action_git_commit(self):
        """Commits changes to git."""
        self.app.bell()
        message = await self.app.push_screen(
            TextInputScreen(title="Git Commit Message", prompt="Enter commit message:")
        )
        if message:
            logger.info(f"Attempting git commit with message: {message}")
            try:
                subprocess.run(["git", "add", "."], check=True, cwd=os.getcwd())
                result = subprocess.run(
                    ["git", "commit", "-m", message],
                    check=True,
                    capture_output=True,
                    text=True,
                    cwd=os.getcwd(),
                )
                logger.info(f"Git commit successful: {result.stdout.strip()}")
                self.status_message = "Git commit complete."
            except subprocess.CalledProcessError as e:
                logger.error(f"Git commit failed: {e.stderr}", exc_info=True)
                self.status_message = f"Git commit failed: {e.stderr}"
            except FileNotFoundError:
                logger.error("Git command not found.")
                self.status_message = "Git not found."
            except Exception as e:
                logger.error(f"Error during git commit: {e}", exc_info=True)

    async def action_git_push(self):
        """Pushes changes to git remote."""
        self.app.bell()
        if await self.confirm_action("Perform git push?"):
            logger.info("Attempting git push...")
            try:
                result = subprocess.run(
                    ["git", "push"],
                    check=True,
                    capture_output=True,
                    text=True,
                    cwd=os.getcwd(),
                )
                logger.info(f"Git push successful: {result.stdout.strip()}")
                self.status_message = "Git push complete."
            except subprocess.CalledProcessError as e:
                logger.error(f"Git push failed: {e.stderr}", exc_info=True)
                self.status_message = f"Git push failed: {e.stderr}"
            except FileNotFoundError:
                logger.error("Git command not found.")
                self.status_message = "Git not found."
            except Exception as e:
                logger.error(f"Error during git push: {e}", exc_info=True)

    async def confirm_action(self, message: str) -> bool:
        """Displays a confirmation dialog."""
        return await self.app.push_screen(ConfirmationScreen(message))

    async def action_quit_app(self):
        """Quits the application."""
        self.app.bell()
        if await self.confirm_action(
            "Are you sure you want to quit the OAPDVAS Control Center?"
        ):
            self.exit()


# --- Helper Screens for Dialogs ---
class ConfirmationScreen(Screen):
    def __init__(self, message: str):
        super().__init__()
        self.message = message

    def compose(self):
        from textual.containers import Vertical, Horizontal

        # Helper for a panel-like container
        def panel(widget, title=None, border_style=None):
            container = Vertical(widget, classes="panel-container")
            if title:
                container.border_title = title
            if border_style:
                container.border_title_color = border_style
            return container

        yield panel(
            Text(self.message, justify="center"),
            title="Confirm Action",
            border_style="bold green",
        )
        with Horizontal(classes="dialog-buttons"):
            yield Button("Yes", variant="success", id="confirm_yes")
            yield Button("No", variant="error", id="confirm_no")


class TextInputScreen(Screen):
    def __init__(self, title: str, prompt: str):
        super().__init__()
        self.title_text = title
        self.prompt_text = prompt
        self.input_field = Input(placeholder=self.prompt_text)

    def compose(self):
        from textual.containers import Vertical, Horizontal

        def panel(widget, title=None, border_style=None):
            container = Vertical(widget, classes="panel-container")
            if title:
                container.border_title = title
            if border_style:
                container.border_title_color = border_style
            return container

        yield panel(
            Vertical(
                Static(self.prompt_text),
                self.input_field,
                Horizontal(
                    Button("Confirm", variant="success", id="text_input_confirm"),
                    Button("Cancel", variant="error", id="text_input_cancel"),
                    classes="dialog-buttons",
                ),
            ),
            title=self.title_text,
            border_style="bold blue",
        )
        self.input_field.focus()

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "text_input_confirm":
            self.dismiss(self.input_field.value)
        else:
            self.dismiss(None)


# --- Main Execution ---
if __name__ == "__main__":
    app = OAPDVASControlCenter()
    app.run()
