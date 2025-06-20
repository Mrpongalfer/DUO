
echo "INFO: Saving TUI Block 1 code to src/ekko/tui/main.py..." && \
# Create/Overwrite the main TUI file using a HERE document
cat << 'EOF' > src/ekko/tui/main.py && \

#!/usr/bin/env python3
File: src/ekko/tui/main.py
Ekko TUI Block 1 - Basic Layout & System Monitor

import os
import sys
import logging
import time # Needed for network rate calculation timing
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, cast
--- Dependency Imports ---

try:
import psutil # For system stats
except ImportError:
logging.basicConfig(level=logging.CRITICAL)
logging.critical("psutil library not found! Cannot run system monitor.")
print("ERROR: psutil library not found. Please activate the Ekko venv and run 'pip install psutil'", file=sys.stderr)
sys.exit("Dependency Error: psutil missing")

try:
import asyncio # Needed for sleep in example action
from rich.text import Text
from textual.app import App, ComposeResult
from textual.containers import Container, Vertical, Horizontal, VerticalScroll # Added VerticalScroll
from textual.reactive import reactive
from textual.widgets import Header, Footer, Static, Label, LoadingIndicator, Placeholder, Log # Added Log/Placeholder
from textual.binding import Binding
except ImportError as e:
logging.basicConfig(level=logging.CRITICAL)
logging.critical(f"Textual import failed: {e}")
print("ERROR: Textual library not found or failed import.", file=sys.stderr)
print("Ensure setup script ran and venv is active.", file=sys.stderr)
sys.exit(f"Dependency Error: {e}")
--- Logging Setup ---

LOG_FILE = Path(file).parent.parent.parent / "ekko_tui_debug.log"
try:
LOG_FILE.parent.mkdir(parents=True, exist_ok=True) # Ensure log directory exists
logging.basicConfig(
level=logging.DEBUG, filename=LOG_FILE, filemode='a',
format='%(asctime)s-%(levelname)s-%(name)s-%(module)s:%(lineno)d - %(message)s',
datefmt='%Y-%m-%d %H:%M:%S'
)
except Exception as log_e:
logging.basicConfig(level=logging.WARNING, format='%(levelname)s: %(message)s')
logging.error(f"Failed config file logging: {log_e}. Using basic console log.")

logger = logging.getLogger("EkkoTUI")
--- Custom Widgets ---

class SystemMonitor(Static):
"""A widget to display updating system resource usage."""
cpu_usage = reactive(0.0, layout=True)
mem_total_gb = reactive(0.0, init=False); mem_available_gb = reactive(0.0, init=False); mem_percent = reactive(0.0, layout=True)
disk_path = reactive("/", init=False); disk_total_gb = reactive(0.0, init=False); disk_used_gb = reactive(0.0, init=False); disk_percent = reactive(0.0, layout=True)
net_counters_prev = reactive(cast(Optional[Dict[str, float]], None), init=False); last_net_update_time = reactive(cast(Optional[float], None), init=False)
net_rate = reactive(cast(Optional[Dict[str, float]], None), layout=True)

def __init__(self, update_interval: float = 2.0, disk_path: str = "/", **kwargs):
    super().__init__(**kwargs); self._update_interval = update_interval; self.disk_path = disk_path; logger.info(f"SysMon init: Interval={update_interval}s, Disk={disk_path}")
def on_mount(self) -> None:
    logger.info("SysMon mounted. Starting timer."); try: self._net_counters_prev = psutil.net_io_counters(pernic=False)._asdict(); self.last_net_update_time = time.monotonic(); except Exception: pass; self.update_stats(); self.set_interval(self._update_interval, self.update_stats)
def update_stats(self) -> None:
    try:
        self.cpu_usage = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory(); self.mem_total_gb = mem.total/(1024**3); self.mem_available_gb = mem.available/(1024**3); self.mem_percent = mem.percent
        try: disk = psutil.disk_usage(self.disk_path); self.disk_total_gb=disk.total/(1024**3); self.disk_used_gb=disk.used/(1024**3); self.disk_percent=disk.percent
        except Exception as disk_e: logger.error(f"Disk {self.disk_path} error: {disk_e}"); self.disk_percent = -1.0
        net_now_dict = psutil.net_io_counters(pernic=False)._asdict(); net_now = {"bytes_sent": net_now_dict["bytes_sent"], "bytes_recv": net_now_dict["bytes_recv"]}
        current_time = time.monotonic()
        if self.net_counters_prev and self.last_net_update_time:
            interval = current_time - self.last_net_update_time
            if interval > 0.1: sent_rate=(net_now["bytes_sent"]-self.net_counters_prev["bytes_sent"])/interval; recv_rate=(net_now["bytes_recv"]-self.net_counters_prev["bytes_recv"])/interval; self.net_rate={"sent_kbps":sent_rate/1024,"recv_kbps":recv_rate/1024}
        else: self.net_rate = {"sent_kbps": 0.0, "recv_kbps": 0.0}
        self.net_counters_prev = net_now; self.last_net_update_time = current_time
        logger.debug(f"Stats: CPU={self.cpu_usage:.1f} Mem={self.mem_percent:.1f}")
    except psutil.Error as e: logger.error(f"psutil error: {e}")
    except Exception as e: logger.error(f"Stat update error: {e}", exc_info=True)
def _get_style(self, p: float) -> str: return "bold red" if p<0 else "bold green" if p<70 else "bold yellow" if p<90 else "bold red"
def render(self) -> Text:
    cpu_style=self._get_style(self.cpu_usage); mem_style=self._get_style(self.mem_percent); disk_style=self._get_style(self.disk_percent)
    disk_str=f"{self.disk_used_gb:.1f}/{self.disk_total_gb:.1f}G ({self.disk_percent:.1f}%)" if self.disk_percent>=0 else "[red]Error[/]"
    net_str="[dim]Net: N/A[/]"
    if self.net_rate: net_str = f"Net: ↑[green]{self.net_rate['sent_kbps']:>6.1f}[/]↓[cyan]{self.net_rate['recv_kbps']:>6.1f}[/] KB/s"
    return Text.assemble(("CPU:",cpu_style),(f"{self.cpu_usage:>5.1f}%","default"),(" | MEM:",mem_style),(f"{self.mem_percent:>5.1f}%","default"),(" | DISK:",disk_style),(f"{disk_str}","default"),("\n", "default"),(net_str, "default"))

--- Main TUI Application ---

class EkkoTUI(App[None]):
TITLE = "Project Ekko Control Plane v0.1"; SUB_TITLE = "AI Dev & Deploy Orchestrator"
CSS = """Screen{layout:grid;grid-size:2;grid-columns:auto 1fr;grid-rows:auto 1fr auto;} Header{grid-column:1 / 3;grid-row:1;} Footer{grid-column:1 / 3;grid-row:3;} #sidebar{grid-column:1;grid-row:2;width:30;border-right:thick $accent;padding:1;overflow-y:auto;} #main-area{grid-column:2;grid-row:2;padding:0 1;layout:vertical;} #system-monitor{height:3;margin-bottom:1;border:round $accent;padding:0 1;} #main-content-scroll{height:1fr;} #main-content{padding:1;border:round $accent;margin-bottom:1;} #log-pane{height:10;border:round $accent;margin-top:1;display:block;} #loading{width:100%;height:1;display:none;margin-top:1;text-align:center;} .view{display:none;padding:1;} .view.visible{display:block;}"""
BINDINGS = [ Binding("d","toggle_dark","Dark Mode"), Binding("q","request_quit","Quit"), Binding("ctrl+l","clear_log","Clear Log"), Binding("l","toggle_log","Toggle Log"), Binding("1","show_view('status-view')","Status"), Binding("2","show_view('git-view')","Git"), Binding("3","show_view('scribe-view')","Scribe"), Binding("4","show_view('ansible-view')","Ansible") ]
show_log_pane = reactive(True)

def compose(self) -> ComposeResult:
    logger.info("Composing Ekko TUI..."); yield Header();
    with Container(id="sidebar"): yield Label("[b u]Ekko Control[/b u]"); yield Static("1: [green]Status[/green]"); yield Static("2: [dim]Git[/dim]"); yield Static("3: [dim]Scribe[/dim]"); yield Static("4: [dim]Ansible[/dim]"); yield Static("---"); yield Static("[i]Keys:[/i] L:Log D:Dark Q:Quit");
    with Container(id="main-area"): yield SystemMonitor(id="system-monitor");
        with VerticalScroll(id="main-content-scroll"): # Main content area
            yield Static("Welcome! System monitoring active.", id="status-view", classes="view visible"); yield Static("[bold yellow]Git Panel[/]", id="git-view", classes="view"); yield Static("[bold cyan]Scribe Panel[/]", id="scribe-view", classes="view"); yield Static("[bold magenta]Ansible Panel[/]", id="ansible-view", classes="view");
        yield LoadingIndicator(id="loading"); yield Log(id="log-pane", auto_scroll=True, max_lines=1000, markup=True);
    yield Footer()

def on_mount(self) -> None: log=self.query_one(Log); log.write_line("[b green]Ekko TUI Init.[/]"); log.write_line(f"[dim]Log: {LOG_FILE}[/]"); logger.info("Ekko TUI Mounted.")
def watch_show_log_pane(self, show:bool) -> None: self.set_class(show,"show-log"); self.query_one(Log).display=show; logger.debug(f"Log display: {show}")
def action_toggle_dark(self) -> None: self.dark = not self.dark; logger.debug("Toggled dark.")
def action_request_quit(self) -> None: logger.info("Quit request."); self.exit("User quit.")
def action_clear_log(self) -> None: self.query_one(Log).clear(); logger.info("Log cleared."); self.query_one(Log).write_line("[dim]Log Cleared.[/]")
def action_toggle_log(self) -> None: self.show_log_pane = not self.show_log_pane; logger.info(f"Log toggled: {self.show_log_pane}")
def action_show_view(self, view_id: str) -> None:
    logger.info(f"Switching view: {view_id}"); for v in self.query(".view"): v.display=(v.id==view_id); self.query_one(Log).write_line(f"View: [bold]{view_id}[/]"); self.run_worker(self._simulate_action(f"Loading {view_id}..."), exclusive=True)
async def _simulate_action(self, msg: str): loader=self.query_one(LoadingIndicator); log=self.query_one(Log); loader.display=True; log.write_line(f"[yellow]{msg}[/]"); logger.info(f"Simulate: {msg}"); await asyncio.sleep(0.5); loader.display=False; log.write_line(f"[green]OK: {msg}[/]"); logger.info("Simulate done.")

if name == "main": logger.info("--- Starting Ekko TUI ---"); app = EkkoTUI(); app.run(); logger.info("--- Ekko TUI Exited ---")

EOF
echo "INFO: Saved src/ekko/tui/main.py." &&

echo "INFO: Activating Ekko venv..." &&

source .venv/bin/activate &&

echo "INFO: Ensuring dependencies (including psutil)..." &&

python -m pip install -e ".[dev]" &&

echo "INFO: Running pre-commit checks..." &&

pre-commit run --all-files &&

echo "INFO: Renaming launch script run_nexusterm.sh to run_ekko_tui.sh..." &&

if [ -f run_nexusterm.sh ]; then mv run_nexusterm.sh run_ekko_tui.sh && git add run_nexusterm.sh run_ekko_tui.sh; else echo "[Warn] run_nexusterm.sh not found, assuming already renamed."; fi &&

echo "INFO: Committing TUI Block 1..." &&

git add src/ekko/tui/main.py .github/workflows/ci.yaml &&

git commit -m "feat(tui): Implement Ekko Block 1 - Layout & System Monitor widget" &&

echo "INFO: Deactivating venv." &&

deactivate &&

echo "" &&

echo ">>> SUCCESS: Ekko TUI Block 1 implemented and committed. <<<" &&

echo ">>> Run './run_ekko_tui.sh' to start the TUI. <<<" ||

( echo "ERROR: Failed during TUI implementation steps. Check output." && deactivate && exit 1 )
# ---------------------------------------------
