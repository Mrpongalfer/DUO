#!/usr/bin/env python3
# chimera_ops_cli.py (Skeleton v1.1 - Includes SetupState Fix)
# Personal Assistant / Ops Wizard CLI Tool

import json
import os
import platform
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Core dependencies (should be installed by run_ops_cli.sh)
try:
    import typer
    from dotenv import dotenv_values, find_dotenv, set_key, unset_key
    from rich.console import Console
    from rich.panel import Panel
    from rich.syntax import Syntax
    from rich.table import Table
    from rich.theme import Theme

    # Defer keyring and inquirerpy import until needed in specific commands
except ImportError as e:
    # Fallback print if rich failed somehow
    print(f"[ERROR] Core dependency missing: {e}. Exiting.", file=sys.stderr)
    print("       Ensure './run_ops_cli.sh' completed successfully.", file=sys.stderr)
    sys.exit(1)


# --- Configuration & Constants ---
APP_NAME = "Chimera Ops Assistant"
VERSION = "0.1.1"
MIN_PYTHON_VERSION = (3, 9)

PROJECT_ROOT = Path(__file__).parent.resolve()
CONFIG_DIR = Path.home() / ".config" / "chimera-ops"
PROJECT_CONFIG_FILE = CONFIG_DIR / "projects.json"  # Stores info about managed projects
STATE_FILE_PATH = CONFIG_DIR / "cli_state.json"  # Persist CLI tool state if needed
DEFAULT_TEMPLATE_DIR = CONFIG_DIR / "templates"  # For cookiecutter
DEFAULT_PROJECTS_DIR = Path.home() / "Projects"  # Default location for new projects

# --- Rich Console Setup ---
custom_theme = Theme(
    {
        "info": "dim cyan",
        "warning": "yellow",
        "danger": "bold red",
        "success": "bright_green",
        "prompt": "bold cyan",
        "path": "italic blue",
        "header": "bold magenta",
        "highlight": "bold yellow",
        "command": "bold blue",
        "arg": "italic green",
    }
)
console = Console(theme=custom_theme)


# --- Helper Functions ---
def print_header(text):
    console.print(Panel(f"[header]{text}[/]", expand=False, border_style="info"))


def print_success(text):
    console.print(f"[success]✔ {text}[/]")


def print_warning(text):
    console.print(f"[warning]⚠ {text}[/]")


def print_info(text):
    console.print(f"[info]ℹ {text}[/]")


def print_danger(text):
    console.print(f"[danger]✖ {text}[/]")


def command_exists(cmd):
    return shutil.which(cmd) is not None


def run_subprocess(
    command: List[str],
    cwd: Optional[Path] = None,
    check: bool = True,
    env: Optional[Dict] = None,
    capture: bool = True,
) -> Optional[subprocess.CompletedProcess]:
    """Runs a subprocess, capturing output and handling errors."""
    full_env = os.environ.copy()
    if env:
        full_env.update(env)
    try:
        cmd_str = " ".join(shlex.quote(str(s)) for s in command)
        console.print(f"[info]Running: {cmd_str} {f'(in {cwd})' if cwd else ''}[/]")
        process = subprocess.run(
            command,
            cwd=cwd,
            capture_output=capture,  # Capture if requested
            text=True,
            check=check,
            env=full_env,
        )
        # Only print if captured and not empty
        stdout = process.stdout.strip() if process.stdout else None
        stderr = process.stderr.strip() if process.stderr else None
        if capture:
            # Limit output length potentially
            if stdout:
                console.print(
                    f"[dim]Stdout:\n{stdout[:1000]}{'...' if len(stdout)>1000 else ''}[/]"
                )
            if stderr:
                console.print(
                    f"[warning]Stderr:\n{stderr[:1000]}{'...' if len(stderr)>1000 else ''}[/]"
                )
        return process
    except FileNotFoundError:
        console.print(f"[danger]Error: Command not found: {command[0]}[/]")
    except subprocess.CalledProcessError as e:
        console.print(f"[danger]Error executing: {' '.join(command)}[/]")
        console.print(f"[danger]Return Code: {e.returncode}[/]")
        stdout = e.stdout.strip() if e.stdout else None
        stderr = e.stderr.strip() if e.stderr else None
        if stdout:
            console.print(
                f"[danger]Stdout:\n{stdout[:1000]}{'...' if len(stdout)>1000 else ''}[/]"
            )
        if stderr:
            console.print(
                f"[danger]Stderr:\n{stderr[:1000]}{'...' if len(stderr)>1000 else ''}[/]"
            )
    except Exception as e:
        console.print(f"[danger]Unexpected error running command: {e}[/]")
    return None


def ensure_config_dir():  # Added function definition
    """Ensures the ~/.config/chimera-ops directory exists."""
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        print_danger(f"Failed to create config directory {CONFIG_DIR}: {e}")
        print_warning(
            f"Proceeding without guaranteed config directory at {CONFIG_DIR}. State/Project config may not persist."
        )
    except NameError:
        print(
            f"[ERROR] Failed to create config directory {CONFIG_DIR} (console unavailable)",
            file=sys.stderr,
        )


# --- State Management Class (Corrected) ---
class SetupState:
    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.data: Dict[str, Any] = self._load()
        self.data.setdefault("config", {})  # Holds general CLI config/state
        self.data.setdefault("projects", {})  # Holds info about managed projects
        self.data.setdefault(
            "status",
            {  # Holds status for *current* setup op if needed
                "last_command_success": None
            },
        )

    def _load(self) -> Dict[str, Any]:
        """Loads state from JSON file."""
        if self.file_path.exists():
            try:
                with open(self.file_path, "r") as f:
                    state_data = json.load(f)
                if (
                    isinstance(state_data, dict)
                    and "config" in state_data
                    and "projects" in state_data
                ):
                    return state_data
                else:
                    console.print(
                        f"[warning]State file '{self.file_path}' invalid format. Re-initializing.[/]"
                    )
                    return {"_schema_version": 1, "config": {}, "projects": {}}
            except (json.JSONDecodeError, IOError) as e:
                console.print(
                    f"[warning]State file '{self.file_path}' issue: {e}. Starting fresh.[/]"
                )
        return {"_schema_version": 1, "config": {}, "projects": {}}

    def save(self):
        """Saves current state to JSON file."""
        try:
            ensure_config_dir()  # Call helper function first
            with open(self.file_path, "w") as f:
                json.dump(self.data, f, indent=2)
        except IOError as e:
            console.print(f"[danger]Error saving state file '{self.file_path}': {e}")
        except Exception as e:
            console.print(f"[danger]Unexpected error saving state: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """Gets a value from state using dot notation for keys (e.g., 'config.DOMAIN')."""
        try:
            keys = key.split(".")
            value = self.data
            for k in keys:
                if not isinstance(value, dict):
                    return default
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default

    def set(self, key: str, value: Any):
        """Sets a value in state using dot notation (e.g., 'config.DOMAIN'), auto-saves."""
        try:
            keys = key.split(".")
            d = self.data
            for k in keys[:-1]:
                d = d.setdefault(k, {})
                if not isinstance(d, dict):
                    console.print(
                        f"[warning]Overwriting non-dict state at '{k}' for '{key}'[/]"
                    )
                    parent_d = self.data
                    # Need to re-find parent dict
                    for pk in keys[: keys.index(k)]:
                        parent_d = parent_d[pk]
                    parent_d[k] = {}
                    d = parent_d[k]
            d[keys[-1]] = value
            self.save()
        except Exception as e:
            console.print(f"[danger]Error setting state for key '{key}': {e}")

    # --- Project specific helpers ---
    def get_project_data(self, name: str, default: Any = None) -> Any:
        return self.get(f"projects.{name}", default if default is not None else {})

    def set_project_data(self, name: str, data: Dict[str, Any]):
        if not isinstance(data, dict):
            print_danger(f"Project data for '{name}' must be a dictionary.")
            return
        self.set(f"projects.{name}", data)

    def list_project_names(self) -> List[str]:
        return list(self.get("projects", {}).keys())

    def remove_project(self, name: str) -> bool:
        projects = self.get("projects", {})
        if isinstance(projects, dict) and name in projects:
            del projects[name]
            self.set("projects", projects)
            return True  # Re-set parent dict to trigger save
        return False

    # --- General CLI config helpers ---
    def get_cli_config(self, key: str, default: Any = None) -> Any:
        return self.get(f"config.{key}", default)

    def set_cli_config(self, key: str, value: Any):
        self.set(f"config.{key}", value)


# --- Typer Application Setup ---
app = typer.Typer(
    name="chimera-ops",
    help=f"{APP_NAME} v{VERSION} - Your Personal Ops Assistant.",
    add_completion=False,
    rich_markup_mode="rich",
)

# --- Global State ---
cli_state = SetupState(STATE_FILE_PATH)


# --- Typer Callback ---
@app.callback()
def main_callback(ctx: typer.Context):
    """Main callback to load state into context."""
    ctx.ensure_object(dict)
    ctx.obj["state"] = cli_state
    if sys.version_info < MIN_PYTHON_VERSION:
        print_danger(
            f"Python {'.'.join(map(str, MIN_PYTHON_VERSION))}+ required. Found {platform.python_version()}."
        )
        raise typer.Exit(code=1)


# --- Command Stubs ---
# (Stubs for: new, config, secret, deploy, ci-setup, ssh, status, list, check, scaffold, generate-env, edit-env, docker, migrate, setup-tunnel, setup-runner)

# --- Imports needed ---
import datetime
import subprocess  # For ping check
from pathlib import Path
from typing import Optional, List, Dict, Any  # Keep imports as needed
import typer  # Already imported likely

# Import Cookiecutter - place near top or ensure it's available
try:
    from cookiecutter.main import cookiecutter
    from cookiecutter.exceptions import CookiecutterException
except ImportError:
    console.print(
        "[danger]ERROR: Cookiecutter library not found. Run './run_ops_cli.sh'.[/]"
    )
    CookiecutterException = Exception

    def cookiecutter(*args, **kwargs):
        raise ImportError("Cookiecutter failed import.")


@app.command(name="new")
def new_project_cmd(
    ctx: typer.Context,
    project_name: str = typer.Argument(
        ..., help="Directory name for the new project (e.g., my-cool-app)."
    ),
    template: str = typer.Option(
        "default",
        "--template",
        "-t",
        help="Cookiecutter template: 'default', Git URL (HTTPS or SSH), or local path.",
    ),
    target_dir: Optional[Path] = typer.Option(
        None,
        "--dir",
        "-d",
        help=f"Parent directory for the project (defaults to: {DEFAULT_PROJECTS_DIR}).",
        resolve_path=True,
        show_default=False,
    ),
):
    """
    Scaffolds a new project using a Cookiecutter template and registers it.

    Default template uses cookiecutter-pypackage via GitHub SSH.
    Requires network access and Git command line tool.
    Ensure your SSH key is added to GitHub for non-public/default templates via SSH.
    """
    state: SetupState = ctx.obj["state"]
    print_header(f"Scaffolding New Project: [highlight]'{project_name}'[/]")

    # --- Determine Output Directory ---
    # (Logic unchanged)
    output_parent_dir = target_dir if target_dir else DEFAULT_PROJECTS_DIR
    try:
        output_parent_dir.mkdir(parents=True, exist_ok=True)
        print_info(f"Target parent directory: [path]{output_parent_dir.resolve()}[/]")
    except OSError as e:
        print_danger(
            f"Failed to access/create output directory '{output_parent_dir}': {e}"
        )
        raise typer.Exit(code=1)

    project_path = output_parent_dir / project_name

    # --- Check for Collisions ---
    # (Logic unchanged)
    if project_path.exists():
        print_danger(f"Project directory already exists: [path]{project_path}[/]")
        raise typer.Exit(code=1)
    if state.get_project_data(project_name):
        print_danger(
            f"Project name '{project_name}' is already registered by this tool."
        )
        raise typer.Exit(code=1)

    # --- Determine Template ---
    # --- MODIFIED DEFAULT TEMPLATE URL ---
    DEFAULT_TEMPLATE_URL = (
        "git@github.com:cookiecutter/cookiecutter-pypackage.git"  # Use SSH URL
    )
    template_source = ""
    is_url_template = False
    is_ssh_url = False

    if template.lower() == "default":
        template_source = DEFAULT_TEMPLATE_URL
        print_info(f"Using default template (SSH): {template_source}")
        is_url_template = True
        is_ssh_url = True
    elif template.startswith("https://") or template.startswith("git@"):
        template_source = template
        print_info(f"Using provided URL template: {template_source}")
        is_url_template = True
        if template.startswith("git@"):
            is_ssh_url = True
    elif Path(template).is_dir():
        template_source = template
        print_info(f"Using provided local template path: {template_source}")
        is_url_template = False
    else:
        print_danger(
            f"Invalid template specified: '{template}'. Must be 'default', Git URL (HTTPS/SSH), or local path."
        )
        raise typer.Exit(code=1)

    # --- Network/SSH Pre-check ---
    if is_url_template:
        target_host = ""
        try:  # Extract host for check
            if "://" in template_source:
                target_host = template_source.split("://")[1].split("/")[0]
            elif "@" in template_source:
                target_host = template_source.split("@")[1].split(":")[0]
        except IndexError:
            pass

        if target_host:
            # If SSH URL, check SSH connection instead of ping
            if is_ssh_url:
                print_info(
                    f"Performing quick SSH connection check to host: {target_host}..."
                )
                # Use ssh -T git@host -o ConnectTimeout=5 -o BatchMode=yes -o LogLevel=ERROR
                # BatchMode=yes prevents password prompts if key is wrong/missing
                # LogLevel=ERROR suppresses motd etc. Exit code 0 = success, 255 = error.
                ssh_check_command = [
                    "ssh",
                    "-T",
                    f"git@{target_host}",
                    "-o",
                    "ConnectTimeout=5",
                    "-o",
                    "BatchMode=yes",
                    "-o",
                    "LogLevel=ERROR",
                ]
                ssh_result = run_subprocess(
                    ssh_check_command, check=False, capture=True
                )  # Allow non-zero exit
                if (
                    ssh_result is not None and ssh_result.returncode == 1
                ):  # Exit code 1 often means successful auth but no shell access (expected for git@ user)
                    print_success(
                        f"SSH connection check to '{target_host}' seems successful (auth likely okay)."
                    )
                elif (
                    ssh_result is not None and ssh_result.returncode == 0
                ):  # Should not happen for git@ user typically
                    print_success(
                        f"SSH connection check to '{target_host}' successful."
                    )
                else:
                    print_warning(
                        f"SSH connection check to '{target_host}' failed (Exit Code: {ssh_result.returncode if ssh_result else 'N/A'})."
                    )
                    print_warning(
                        "Ensure your SSH key is added to GitHub/GitLab and network allows SSH (port 22)."
                    )
                    if not typer.confirm(
                        "Attempt to run Cookiecutter anyway?", default=False
                    ):
                        raise typer.Exit()
            else:  # Fallback to ping for HTTPS URLs
                print_info(
                    f"Performing quick network check (ping) for host: {target_host}..."
                )
                ping_command = ["ping", "-c", "1", "-W", "2", target_host]
                ping_result = run_subprocess(ping_command, check=False, capture=False)
                if ping_result is None or ping_result.returncode != 0:
                    print_warning(
                        f"Network check failed: Unable to ping '{target_host}'. Cookiecutter might fail."
                    )
                    if not typer.confirm(
                        "Attempt to run Cookiecutter anyway?", default=True
                    ):
                        raise typer.Exit()
                else:
                    print_success(f"Network check to '{target_host}' successful.")
        else:
            print_warning(
                f"Could not determine host from template URL '{template_source}' for network check."
            )

    # --- Run Cookiecutter ---
    console.print("\n[info]Running Cookiecutter...[/]")
    console.print(
        "[info]Using Git to clone template. May prompt for SSH key passphrase if set."
    )
    console.print("[info]May also prompt for template variables interactively.[/]")
    try:
        if not command_exists("git"):
            print_danger("Git command not found.")
            raise typer.Exit(code=1)

        generated_path_str = cookiecutter(
            template=template_source, output_dir=str(output_parent_dir.resolve())
        )
        generated_path = Path(generated_path_str)
        print_success("Cookiecutter scaffolding complete.")
        print_info(f"Project generated at: [path]{generated_path}[/]")

        # --- Register Project in State ---
        actual_project_name = generated_path.name
        reg_name = (
            project_name  # Use the name user provided for registration by default
        )
        if actual_project_name != project_name:
            print_warning(
                f"Generated dir name ('{actual_project_name}') != input name ('{project_name}'). Registering as '{reg_name}'."
            )

        print_info(f"Registering project '{reg_name}' in state file...")
        project_config_data = {
            "path": str(generated_path),
            "template": template_source,
            "created_at": datetime.datetime.now().isoformat(),
            "deployment_targets": {"default": "TODO: Configure target details"},
        }
        state.add_or_update_project(reg_name, project_config_data)
        print_success(f"Project '{reg_name}' successfully registered.")
        console.print(
            f"[info]Run 'status {reg_name}' or 'config {reg_name} show' to see details.[/]"
        )

    except CookiecutterException as e:
        print_danger(f"Cookiecutter failed: {e}")
        print_warning(
            "Check network, template URL/path, Git installation, and SSH key setup on GitHub/GitLab."
        )
        raise typer.Exit(code=1)
    except ImportError:
        print_danger("Cookiecutter library is not installed or could not be imported.")
        raise typer.Exit(code=1)
    except Exception as e:
        print_danger(f"An unexpected error occurred during Cookiecutter execution: {e}")
        console.print_exception(show_locals=False)
        raise typer.Exit(code=1)


# --- End of new_project_cmd function ---


@app.command()
def config(
    ctx: typer.Context,
    project_name: str = typer.Argument(...),
    action: str = typer.Argument("show"),
    key: Optional[str] = typer.Argument(None),
    value: Optional[str] = typer.Argument(None),
):
    """Manages project-specific configuration (non-secret). ACTION: show, get <k>, set <k> <v>, list"""
    print_header(f"Configure Project: {project_name}")
    print_warning("CMD 'config': Not implemented yet.")


@app.command()
def secret(
    ctx: typer.Context,
    project_name: str = typer.Argument(...),
    action: str = typer.Argument("list"),
    key: Optional[str] = typer.Argument(None),
):
    """Manages secrets via OS keychain. ACTION: list, set <k>, get <k>, delete <k>"""
    print_header(f"Manage Secrets: {project_name}")
    print_warning("CMD 'secret': Not implemented yet.")


@app.command()
def deploy(
    ctx: typer.Context,
    project_name: str = typer.Argument(...),
    target: str = typer.Option("default"),
):
    """Deploys a project to a configured target."""
    print_header(f"Deploy Project: {project_name} -> {target}")
    print_warning("CMD 'deploy': Not implemented yet.")


@app.command(name="ci-setup")
def ci_setup_cmd(
    ctx: typer.Context,
    project_name: str = typer.Argument(...),
    platform: str = typer.Option("github"),
):
    """Generates baseline CI/CD pipeline configurations."""
    print_header(f"Setup CI/CD: {project_name} on {platform}")
    print_warning("CMD 'ci-setup': Not implemented yet.")


@app.command()
def ssh(ctx: typer.Context, alias: str = typer.Argument(...)):
    """Connects to a configured server via SSH."""
    print_header(f"SSH Connect: {alias}")
    print_warning("CMD 'ssh': Not implemented yet.")


# Replace the existing status function in chimera_ops_cli.py with this:


@app.command()
def status(
    ctx: typer.Context,
    project_name: Optional[str] = typer.Argument(
        None, help="Show status for a specific project, or overview if omitted."
    ),
):
    """Shows overview or project-specific status and configuration."""
    state: SetupState = ctx.obj["state"]  # Get state from context

    if project_name:
        # --- Show status for a specific project ---
        print_header(f"Status Report for Project: [highlight]'{project_name}'[/]")
        project_data = state.get_project_data(project_name)

        if not project_data or not isinstance(project_data, dict):
            print_danger(f"Project '{project_name}' not found or has no configuration.")
            print_info("Use 'list' to see managed projects or 'new' to create it.")
            raise typer.Exit(code=1)

        config_table = Table(
            title="Project Configuration", show_header=True, header_style="bold blue"
        )
        config_table.add_column("Configuration Key", style="command")
        config_table.add_column("Value", style="arg")

        if not project_data:
            config_table.add_row("[dim]No configuration data found.[/]", "")
        else:
            for key, value in sorted(project_data.items()):
                # Simple check if key suggests sensitivity (improve later if needed)
                is_secret_key = any(
                    k in key.lower() for k in ["key", "token", "password", "secret"]
                )
                display_value = (
                    "[dim][hidden by CLI][/]"
                    if is_secret_key
                    else str(value) if value is not None else "[dim]Not Set[/]"
                )
                config_table.add_row(key, display_value)
        console.print(config_table)

        # Placeholder for project-specific status flags if added later
        # status_flags = state.get(f"projects.{project_name}.status", {})
        # ... display status flags ...

        print_info(f"\nUse 'config {project_name} <action>' to manage config.")
        print_info(f"Use 'secret {project_name} <action>' to manage secrets.")

    else:
        # --- Show overview status ---
        print_header("Status Report Overview")

        # Managed Projects
        projects = state.list_project_names()
        project_table = Table(title="Managed Projects")
        project_table.add_column("Project Name", style="command")
        if projects:
            for proj in sorted(projects):
                project_table.add_row(proj)
        else:
            project_table.add_row("[dim]No projects managed yet (use 'new').[/]")
        console.print(project_table)

        # CLI Configuration (if any stored in state['config'])
        cli_config_data = state.get("config", {})
        config_table = Table(title="CLI Configuration")
        config_table.add_column("Key", style="command")
        config_table.add_column("Value", style="arg")
        if not cli_config_data:
            config_table.add_row("[dim]No CLI configuration set.[/]", "")
        else:
            for key, value in sorted(cli_config_data.items()):
                config_table.add_row(
                    key, str(value) if value is not None else "[dim]Not Set[/]"
                )
        console.print(config_table)

        # Show key paths
        path_table = Table(title="Key Paths")
        path_table.add_column("Item", style="command")
        path_table.add_column("Path", style="path")
        path_table.add_row("Config Directory", str(CONFIG_DIR))
        path_table.add_row("Projects Config", str(PROJECT_CONFIG_FILE))
        path_table.add_row("CLI State File", str(STATE_FILE_PATH))
        path_table.add_row("Default Projects Dir", str(DEFAULT_PROJECTS_DIR))
        console.print(path_table)


# Replace the existing list_projects_cmd function in chimera_ops_cli.py with this:


@app.command(name="list")
def list_projects_cmd(ctx: typer.Context):
    """Lists all projects currently managed by chimera-ops."""
    state: SetupState = ctx.obj["state"]  # Get state from Typer context
    print_header("Managed Projects")
    projects = state.list_project_names()  # Get list from state manager

    if not projects:
        console.print(
            "[info]No projects managed yet. Use the 'new' command to create one.[/]"
        )
        return

    table = Table(show_header=True, header_style="bold blue")
    table.add_column("Project Name", style="command")
    for proj_name in sorted(projects):  # Sort alphabetically
        table.add_row(proj_name)

    console.print(table)


@app.command()
def check(ctx: typer.Context):
    """Checks for required tools (Docker, Git, Node, etc.)."""
    state: SetupState = ctx.obj["state"]
    print_warning("CMD 'check': Not implemented yet.")


@app.command()
def scaffold(ctx: typer.Context):
    """Creates the project directory structure (backend/, frontend/, etc.)."""
    state: SetupState = ctx.obj["state"]
    print_warning("CMD 'scaffold': Not implemented yet.")


@app.command(name="generate-env")
def generate_env_cmd(ctx: typer.Context, project_name: str = typer.Argument(...)):
    """Generates the specified project's .env file with placeholders."""
    state: SetupState = ctx.obj["state"]
    print_warning("CMD 'generate-env': Not implemented yet.")


@app.command(name="edit-env")
def edit_env_cmd(ctx: typer.Context, project_name: str = typer.Argument(...)):
    """Opens the specified project's .env file in $EDITOR."""
    state: SetupState = ctx.obj["state"]
    # Implementation from #71 needs project path integration
    print_warning("CMD 'edit-env': Not fully implemented yet.")


@app.command()
def docker(
    ctx: typer.Context,
    args: List[str] = typer.Argument(
        ...,
        help="Docker subcommand and args (e.g., 'network create pub', 'compose up -d')",
    ),
):
    """Runs docker/docker-compose commands. Needs sudo handling."""
    state: SetupState = ctx.obj["state"]
    print_warning("CMD 'docker': Not implemented yet.")


@app.command()
def migrate(ctx: typer.Context, project_name: str = typer.Argument(...)):
    """Runs database migrations using Alembic via Docker for a project."""
    state: SetupState = ctx.obj["state"]
    print_warning("CMD 'migrate': Not implemented yet.")


@app.command(name="setup-tunnel")
def setup_tunnel_cmd(ctx: typer.Context, project_name: str = typer.Argument(...)):
    """Guides Cloudflare Tunnel setup for a project."""
    state: SetupState = ctx.obj["state"]
    print_warning("CMD 'setup-tunnel': Not implemented yet.")


@app.command(name="setup-runner")
def setup_runner_cmd(ctx: typer.Context, project_name: str = typer.Argument(...)):
    """Sets up the GitHub Actions self-hosted runner for a project."""
    state: SetupState = ctx.obj["state"]
    print_warning("CMD 'setup-runner': Not implemented yet.")


# --- Typer Exit command (handled by Typer itself via default --help, but can add explicit) ---
# @app.command(name="exit")
# def exit_cmd():
#     """Exits the setup CLI."""
#     console.print("[info]Exiting...")
#     raise typer.Exit()

# --- Script Entry Point ---
if __name__ == "__main__":
    try:
        ensure_config_dir()  # Ensure config dir exists before Typer/State runs
        app()
    except Exception:
        console = Console(theme=custom_theme)  # Ensure console exists for error
        console.print(
            "[bold red]A critical unexpected error occurred launching or running the CLI:[/]"
        )
        console.print_exception(show_locals=False)
        sys.exit(1)
