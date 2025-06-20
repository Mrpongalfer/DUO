#!/bin/bash
# bootstrap_omniapp.sh - Interactively sets up the Omniapp Suite Project
# Version: 1.2 (Focus on CLI, WebUI, ExWork, Scribe; Interactive file sourcing)
# For The Supreme Master Architect Alix Feronti

set -e # Exit on any error

# --- Configuration ---
DEFAULT_OMNIAPP_DIR="/home/pong/Projects/omniapp"
PYTHON_CMD_FOR_VENV="python3.11" # Python for the project's virtual environment

# --- Color Codes & Helper Functions ---
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; CYAN='\033[0;36m'; NC='\033[0m';
print_error() { echo -e "${RED}ERROR: $1${NC}"; }
print_success() { echo -e "${GREEN}SUCCESS: $1${NC}"; }
print_warning() { echo -e "${YELLOW}WARNING: $1${NC}"; }
print_info() { echo -e "${BLUE}INFO: $1${NC}"; }
print_header() { echo -e "\n${CYAN}==== $1 ====${NC}"; }

prompt_yes_no() {
    while true; do
        read -r -p "$1 [Y/n]: " response
        response=${response,,}
        if [[ "$response" =~ ^(yes|y|"")$ ]]; then REPLY="yes"; return 0;
        elif [[ "$response" =~ ^(no|n)$ ]]; then REPLY="no"; return 0;
        else print_error "Invalid input."; fi
    done
}

# Function to write content to a file, creating parent dirs
# $1: file_path, $2: content_variable_name (name of var holding content), $3: overwrite_flag ("yes" or "no", default "no")
write_file_content() {
    local file_path="$1"
    local content_var_name="$2"
    local overwrite_flag="${3:-no}"
    local content

    eval "content=\$$content_var_name" 

    if [ -f "$file_path" ] && [ "$overwrite_flag" != "yes" ]; then
        prompt_yes_no "File '$file_path' already exists. Overwrite?"
        if [[ "$REPLY" == "no" ]]; then
            print_info "Skipping file: $file_path"
            return 0
        fi
    fi
    
    mkdir -p "$(dirname "$file_path")"
    echo -e "$content" > "$file_path"
    if [ $? -eq 0 ]; then print_info "Created/Updated file: $file_path"; else print_error "Failed to write file: $file_path"; return 1; fi
}

# Function to copy a file, creating parent dirs
# $1: source_file_path, $2: dest_file_path, $3: file_description (for prompts), $4: optional_flag (if "optional", don't exit on skip)
copy_file_interactive() {
    local source_file_path="$1"
    local dest_file_path="$2"
    local file_description="$3"
    local optional_flag="$4" # "optional" or ""

    if [ ! -f "$source_file_path" ]; then
        print_error "Source file for ${file_description} not found at '${source_file_path}'."
        if [[ "$optional_flag" == "optional" ]]; then
            prompt_yes_no "Skip copying ${file_description} and proceed (functionality might be affected)?"
            if [[ "$REPLY" == "no" ]]; then print_info "Aborting bootstrap as per user choice on missing essential source file."; exit 1; fi
            return 1 # Indicates copy was skipped due to missing source
        else
            print_info "Aborting bootstrap due to missing essential source file: ${file_description}."
            exit 1
        fi
    fi

    if [ -f "$dest_file_path" ]; then
        prompt_yes_no "Destination file '$dest_file_path' for ${file_description} already exists. Overwrite?"
        if [[ "$REPLY" == "no" ]]; then
            print_info "Skipping copy of ${file_description} to $dest_file_path"
            return 0 
        fi
    fi
    
    mkdir -p "$(dirname "$dest_file_path")"
    if cp "$source_file_path" "$dest_file_path"; then
        print_info "Copied ${file_description} to: $dest_file_path"
    else
        print_error "Failed to copy ${file_description} from '${source_file_path}' to '${dest_file_path}'"
        return 2 # Indicates copy failure
    fi
    return 0 # Success
}

# --- Main Script ---
print_header "Omniapp Suite Bootstrapper v1.2 (CLI, WebUI, Agents Focus)"

# 1. Determine Omniapp Directory & Source Directory for Existing Agent Components
OMNIAPP_DIR=""
EXISTING_AGENTS_SRC_DIR="/home/pong/Projects/projectsupload/omnitide_launcher_project" # For ExWork, Scribe, Templates

read -r -p "Enter the desired main directory for Omniapp Suite [${DEFAULT_OMNIAPP_DIR}]: " OMNIAPP_DIR_INPUT
OMNIAPP_DIR=${OMNIAPP_DIR_INPUT:-$DEFAULT_OMNIAPP_DIR}

if [ -d "$OMNIAPP_DIR" ]; then
    print_info "Omniapp directory '$OMNIAPP_DIR' already exists."
    prompt_yes_no "Proceed with bootstrapping into this existing directory? (You'll be prompted before overwriting specific files)"
    [[ "$REPLY" == "no" ]] && { print_info "Bootstrapping aborted."; exit 0; }
else
    prompt_yes_no "Omniapp directory '$OMNIAPP_DIR' does not exist. Create it now?"
    if [[ "$REPLY" == "yes" ]]; then
        mkdir -p "$OMNIAPP_DIR" || { print_error "Could not create directory '$OMNIAPP_DIR'."; exit 1; }
        print_success "Created Omniapp directory: $OMNIAPP_DIR"
    else
        print_info "Bootstrapping aborted."; exit 0;
    fi
fi
cd "$OMNIAPP_DIR"
OMNIAPP_DIR=$(pwd) # Get absolute path

print_info "This script will copy ExWork Agent, Scribe Agent, and Omnitide Templates from a source directory you provide."
DEFAULT_AGENTS_SRC_DIR_GUESS="/home/pong/Projects/projectsupload/omnitide_launcher_project" # Common location from our discussions
if [ ! -d "$DEFAULT_AGENTS_SRC_DIR_GUESS" ]; then
    DEFAULT_AGENTS_SRC_DIR_GUESS="$(dirname "$OMNIAPP_DIR")/omnitide_launcher_project" # Alternative guess
    if [ ! -d "$DEFAULT_AGENTS_SRC_DIR_GUESS" ]; then
        DEFAULT_AGENTS_SRC_DIR_GUESS="$(dirname "$OMNIAPP_DIR")" # Fallback to parent
    fi
fi

read -r -e -p "Enter the SOURCE directory where your existing ExWork Agent, Scribe Agent, and omnitide_templates.json are located [${DEFAULT_AGENTS_SRC_DIR_GUESS}]: " EXISTING_AGENTS_SRC_DIR_INPUT
EXISTING_AGENTS_SRC_DIR=${EXISTING_AGENTS_SRC_DIR_INPUT:-$DEFAULT_AGENTS_SRC_DIR_GUESS}
if [[ -n "$EXISTING_AGENTS_SRC_DIR" ]]; then
    EXISTING_AGENTS_SRC_DIR=$(realpath "$EXISTING_AGENTS_SRC_DIR" 2>/dev/null || echo "$EXISTING_AGENTS_SRC_DIR")
fi

COPY_EXISTING_AGENTS=false
if [ -d "$EXISTING_AGENTS_SRC_DIR" ]; then
    print_success "Will attempt to copy agent components from: ${EXISTING_AGENTS_SRC_DIR}"
    COPY_EXISTING_AGENTS=true
else
    print_warning "Specified source directory for agent components is not valid or not provided: '${EXISTING_AGENTS_SRC_DIR}'"
    prompt_yes_no "Continue without copying these agent components? (The 'agents' directory will be created but may be empty or have placeholders.)"
    if [[ "$REPLY" == "no" ]]; then
        print_info "Bootstrapping aborted."; exit 1;
    fi
fi

# 2. Define File Contents (for NEWLY generated files or those I provide as templates)

# --- README.md Content (Generated) ---
README_MD_CONTENT=$(cat <<'EOF_README'
# Omniapp Suite

Welcome to the Omniapp Suite, Architect!

This project consolidates various Omnitide Nexus tools, primarily focusing on:
- **Omnitide CLI:** A Python Typer-based command-line interface for orchestrating ExWork and Scribe.
- **Agents:** Core Scribe and ExWork agents (copied from your specified source).
- **Web UI:** A Flask-based web interface for interacting with the agents.
- **User Shell Setup:** Scripts to configure your Xonsh development environment.

## Setup

1.  This `bootstrap_omniapp.sh` script initializes the project structure.
2.  Ensure your Xonsh environment is configured (you can use `user_shell_setup/setup_omnitide_user_shell.sh`).
3.  Navigate to this directory (`omniapp`).
4.  Activate the direnv environment: `direnv allow .` (This will use the `.envrc` file).
5.  The direnv environment should create a Python virtual environment. Install dependencies: `pip install -r requirements.txt` while the venv is active.

## Usage
-   **Omnitide CLI:** `python omnitide_cli/omnitide_cli/main.py --help` (or `omni-cli --help` if `pyproject.toml` setup makes it a system command via `pip install -e ./omnitide_cli`)
-   **Web UI:** `python web_ui/app.py` (then open browser to http://127.0.0.1:5678)
-   **User Shell Setup:** `bash user_shell_setup/setup_omnitide_user_shell.sh` (Run this once to configure your user's Xonsh)

EOF_README
)

# --- .envrc Content (Generated) ---
DOT_ENVRC_CONTENT=$(cat <<EOF_ENVRC
# .envrc for Omniapp Suite
echo "Loading Omniapp Suite environment (${OMNIAPP_DIR})..."
layout python ${PYTHON_CMD_FOR_VENV}
export OMNIAPP_ROOT="\$(pwd)"
# Ensure agents and templates can be found by CLI/WebUI relative to OMNIAPP_ROOT
# The CLI/WebUI's config_manager will now store OMNIAPP_ROOT and derive paths.

echo "Python from venv: \$(which python)"
echo "Omniapp Suite environment loaded. Install requirements with: pip install -r requirements.txt"
EOF_ENVRC
)

# --- Main requirements.txt Content (Generated) ---
MAIN_REQUIREMENTS_TXT_CONTENT=$(cat <<'EOF_MAIN_REQS'
# Main requirements.txt for Omniapp Suite
# Generated by bootstrap_omniapp.sh (v1.2)

# For Omnitide CLI
typer[all]>=0.9.0,<1.0.0

# For Web UI
Flask>=2.0,<3.1.0

# For ExWork Agent (core dependencies it might need if run as a module)
requests>=2.25.0,<3.0.0
pycryptodomex>=3.10.0,<4.0.0 # For ExWork's ENCRYPT_DECRYPT_TARGET

# For Scribe Agent (core dependencies it might need if run as a module)
httpx>=0.23.0,<1.0.0
tomli>=1.0.0,<3.0.0; python_version < "3.11" # Scribe handles tomllib for Py3.11+

# Note: The ExWork and Scribe agents are typically standalone scripts
# and might have more extensive dependencies if they were designed as libraries.
# This requirements.txt primarily covers the orchestrators (CLI, WebUI)
# and essential direct dependencies of the agents themselves.
# Refer to the original agents' environments for their full dependency sets if issues arise.
EOF_MAIN_REQS
)

# --- Omnitide CLI (NEWLY GENERATED parts) ---
OMNITIDE_CLI_MAIN_PY_CONTENT=$(cat <<'EOF_CLI_MAIN'
#!/usr/bin/env python3
# Omnitide CLI - main.py (v1.2 Bootstrap)
import typer
from typing_extensions import Annotated
import json
from pathlib import Path
import subprocess
import shlex
import sys

# Relative import for config_manager
try:
    from . import config_manager
except ImportError:
    # Fallback for direct execution if not installed as package, assuming config_manager is sibling
    import config_manager


# --- Global Config Variable ---
APP_CONFIG = config_manager.load_config()

# --- Typer Application Initialization ---
app = typer.Typer(
    name="omnitide-cli",
    help="Omnitide Nexus Interactive CLI: Orchestrate Scribe and ExWork agents.",
    add_completion=True,
    no_args_is_help=True
)

config_app = typer.Typer(name="config", help="Manage CLI runtime configuration (reads/writes ~/.omnitide_cli_config.json).")
app.add_typer(config_app)

templates_app = typer.Typer(name="templates", help="List and inspect Omnitide templates.")
app.add_typer(templates_app)

scribe_app = typer.Typer(name="scribe", help="Run Scribe validation tasks.")
app.add_typer(scribe_app)

exwork_app = typer.Typer(name="exwork", help="Run ExWork execution tasks.")
app.add_typer(exwork_app)

# workflow_app = typer.Typer(name="workflow", help="Run combined Scribe & ExWork workflows.")
# app.add_typer(workflow_app)

# logs_app = typer.Typer(name="logs", help="View execution logs and reports.")
# app.add_typer(logs_app)

# --- Helper Functions ---
def _get_python_executable() -> str:
    return sys.executable or "python3"

def _get_agent_path(agent_script_name_key: str) -> Path:
    """Gets absolute path to an agent script using CLI config."""
    omniapp_root_str = APP_CONFIG.get("omnitide_app_root", str(Path.cwd()))
    agents_dir_str = APP_CONFIG.get("agents_dir", "agents")
    script_name = APP_CONFIG.get(agent_script_name_key, "")
    
    if not omniapp_root_str or not script_name:
        typer.secho(f"ERROR: omnitide_app_root or {agent_script_name_key} not configured. Run 'omnitide-cli config wizard'.", fg=typer.colors.RED)
        raise typer.Exit(1)
        
    return (Path(omniapp_root_str) / agents_dir_str / script_name).resolve()

def _get_project_cwd() -> Path:
    """Gets absolute path for project CWD using CLI config."""
    omniapp_root_str = APP_CONFIG.get("omnitide_app_root", str(Path.cwd()))
    default_project_cwd_str = APP_CONFIG.get("default_project_cwd", ".")
    
    project_cwd = Path(default_project_cwd_str)
    if not project_cwd.is_absolute():
        project_cwd = (Path(omniapp_root_str) / default_project_cwd_str).resolve()
    
    if not project_cwd.is_dir():
        typer.secho(f"ERROR: Project CWD '{project_cwd}' is not a valid directory. Configure via 'omnitide-cli config wizard'.", fg=typer.colors.RED)
        raise typer.Exit(1)
    return project_cwd

def _get_templates_file_path() -> Path:
    omniapp_root_str = APP_CONFIG.get("omnitide_app_root", str(Path.cwd()))
    agents_dir_str = APP_CONFIG.get("agents_dir", "agents")
    templates_file_name = APP_CONFIG.get("omnitide_templates_file", "omnitide_templates.json")
    
    templates_path = (Path(omniapp_root_str) / agents_dir_str / templates_file_name).resolve()
    if not templates_path.is_file():
        typer.secho(f"WARNING: Templates file not found at '{templates_path}'. Template features will be limited.", fg=typer.colors.YELLOW)
    return templates_path

# --- Config Commands (from omnitide_cli_config_manager.py context) ---
@config_app.command("show", help="Show current CLI runtime configuration.")
def config_show():
    global APP_CONFIG
    APP_CONFIG = config_manager.load_config() 
    typer.secho("Current Omnitide CLI Configuration:", fg=typer.colors.CYAN)
    typer.echo(json.dumps(APP_CONFIG, indent=2))
    typer.secho(f"\nConfig file location: {config_manager.CONFIG_FILE_PATH}", fg=typer.colors.YELLOW)

@config_app.command("set", help="Set a CLI runtime configuration value (e.g., omnitide-cli config set default_project_cwd /path/to/project).")
def config_set(
    key: Annotated[str, typer.Argument(help=f"Configuration key. Choices: {', '.join(config_manager.DEFAULT_CONFIG.keys())}")],
    value: Annotated[str, typer.Argument(help="Value for the key.")]
):
    global APP_CONFIG
    if key not in config_manager.DEFAULT_CONFIG:
        typer.secho(f"Error: Invalid key '{key}'. Valid: {', '.join(config_manager.DEFAULT_CONFIG.keys())}", fg=typer.colors.RED)
        raise typer.Exit(code=1)
    
    APP_CONFIG[key] = value
    config_manager.save_config(APP_CONFIG)
    typer.secho(f"Configuration updated: '{key}' = '{value}'. This is stored in {config_manager.CONFIG_FILE_PATH}.", fg=typer.colors.GREEN)

@config_app.command("wizard", help="Interactive wizard to configure essential paths for the CLI.")
def config_wizard(
    omniapp_root: Annotated[str, typer.Option(help="Path to the Omniapp Suite root directory.", default_factory=lambda: str(Path.cwd().parent))] = str(Path.cwd().parent)
):
    global APP_CONFIG
    typer.secho("Omnitide CLI Configuration Wizard", fg=typer.colors.MAGENTA)
    
    APP_CONFIG['omnitide_app_root'] = typer.prompt(
        "Path to Omniapp Suite root directory", 
        default=APP_CONFIG.get('omnitide_app_root', omniapp_root) # Use callback default if no config
    )
    APP_CONFIG['agents_dir'] = typer.prompt(
        "Agents directory (relative to Omniapp root)", 
        default=APP_CONFIG.get('agents_dir', 'agents')
    )
    APP_CONFIG['scribe_agent_script'] = typer.prompt(
        "Scribe Agent script name (in agents_dir)", 
        default=APP_CONFIG.get('scribe_agent_script', 'scribe.py')
    )
    APP_CONFIG['exwork_agent_script'] = typer.prompt(
        "ExWork Agent script name (in agents_dir)", 
        default=APP_CONFIG.get('exwork_agent_script', 'exworkagent.py')
    )
    APP_CONFIG['omnitide_templates_file'] = typer.prompt(
        "Omnitide Templates JSON file name (in agents_dir)",
        default=APP_CONFIG.get('omnitide_templates_file', 'omnitide_templates.json')
    )
    APP_CONFIG['default_project_cwd'] = typer.prompt(
        "Default Project Working Directory for agents (can be relative to Omniapp root, e.g., '.', or absolute)",
        default=APP_CONFIG.get('default_project_cwd', '.')
    )
    APP_CONFIG['default_scribe_config_toml'] = typer.prompt(
        "Default Scribe .scribe.toml file name (relative to project CWD or absolute)",
        default=APP_CONFIG.get('default_scribe_config_toml', '.scribe.toml')
    )
    
    config_manager.save_config(APP_CONFIG)
    typer.secho(f"Configuration wizard completed. Settings saved to {config_manager.CONFIG_FILE_PATH}.", fg=typer.colors.GREEN)

# --- ExWork Agent Commands ---
@exwork_app.command("run", help="Run an ExWork agent task.")
def exwork_run(
    payload_file: Annotated[Optional[Path], typer.Option("--file", "-f", help="Path to ExWork JSON payload file.", exists=True, file_okay=True, dir_okay=False, readable=True)] = None,
    payload_str: Annotated[Optional[str], typer.Option("--json", "-j", help="ExWork JSON payload as a string.")] = None,
    project_cwd_override: Annotated[Optional[Path], typer.Option("--cwd", help="Override project working directory for this run.")] = None
):
    if not payload_file && !payload_str:
        typer.secho("Error: Must provide ExWork payload via --file or --json.", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    if payload_file && payload_str:
        typer.secho("Error: Cannot use both --file and --json. Provide only one payload source.", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    current_payload_str = ""
    if payload_file:
        current_payload_str = payload_file.read_text(encoding="utf-8")
    elif payload_str:
        current_payload_str = payload_str
    
    try:
        json.loads(current_payload_str) # Validate JSON
    except json.JSONDecodeError as e:
        typer.secho(f"Error: Invalid ExWork JSON payload: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    exwork_script = _get_agent_path("exwork_agent_script")
    effective_cwd = _get_project_cwd()
    if project_cwd_override:
        if not project_cwd_override.is_dir():
            typer.secho(f"Error: Specified --cwd '{project_cwd_override}' is not a valid directory.", fg=typer.colors.RED)
            raise typer.Exit(1)
        effective_cwd = project_cwd_override.resolve()

    python_exe = _get_python_executable()
    command = [python_exe, str(exwork_script)]
    
    typer.secho(f"Executing ExWork Agent: {' '.join(shlex.quote(str(c)) for c in command)}", fg=typer.colors.BLUE)
    typer.secho(f"Working Directory: {effective_cwd}", fg=typer.colors.BLUE)
    typer.secho(f"Payload:\n{current_payload_str}", fg=typer.colors.BLUE)

    try:
        process = subprocess.Popen(
            command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, cwd=effective_cwd, encoding='utf-8'
        )
        stdout, stderr = process.communicate(input=current_payload_str, timeout=600) # 10 min timeout

        typer.secho("\n--- ExWork STDOUT ---", fg=typer.colors.CYAN)
        typer.echo(stdout if stdout else "<empty>")
        if stderr:
            typer.secho("\n--- ExWork STDERR ---", fg=typer.colors.YELLOW)
            typer.echo(stderr)
        
        typer.secho(f"\nExWork agent finished with exit code: {process.returncode}",
                    fg=(typer.colors.GREEN if process.returncode == 0 else typer.colors.RED))
        
        # Try to parse and display JSON summary from stdout if successful
        if process.returncode == 0 and stdout:
            try:
                summary = json.loads(stdout)
                typer.secho("\n--- Parsed ExWork Summary ---", fg=typer.colors.MAGENTA)
                typer.echo(json.dumps(summary, indent=2))
            except json.JSONDecodeError:
                typer.secho("(Could not parse stdout as JSON summary)", fg=typer.colors.YELLOW)

    except subprocess.TimeoutExpired:
        typer.secho("Error: ExWork agent timed out.", fg=typer.colors.RED)
    except Exception as e:
        typer.secho(f"Error running ExWork agent: {e}", fg=typer.colors.RED)

# --- Scribe Agent Commands (Placeholder) ---
@scribe_app.command("validate", help="Run Scribe validation on a target file.")
def scribe_validate(
    target_dir: Annotated[Path, typer.Option(help="Path to the target project directory.", exists=True, file_okay=False, resolve_path=True)],
    code_file: Annotated[Path, typer.Option(help="Path to the temporary file containing new/modified code.", exists=True, file_okay=True, resolve_path=True)],
    target_file_relative: Annotated[str, typer.Option(help="Relative path within target_dir for the code to be applied & validated.")]
    # Add other Scribe CLI options here as needed (e.g., --commit, --config-file, skips)
):
    typer.secho(f"Scribe validation requested (placeholder):", fg=typer.colors.BLUE)
    typer.echo(f"  Target Dir: {target_dir}")
    typer.echo(f"  Code File: {code_file}")
    typer.echo(f"  Target File Relative: {target_file_relative}")
    
    scribe_script = _get_agent_path("scribe_agent_script")
    python_exe = _get_python_executable()
    
    command = [
        python_exe, str(scribe_script),
        "--target-dir", str(target_dir),
        "--code-file", str(code_file),
        "--target-file", target_file_relative
        # Add other Scribe flags based on function arguments
    ]
    # ... (subprocess execution logic similar to exwork_run) ...
    typer.secho("Placeholder: Scribe execution logic to be implemented.", fg=typer.colors.YELLOW)


# --- Templates Commands (Placeholder) ---
@templates_app.command("list", help="List available Omnitide templates.")
def templates_list():
    templates_file = _get_templates_file_path()
    if not templates_file.is_file():
        typer.secho(f"Templates file '{templates_file}' not found. Configure via 'omnitide-cli config wizard'.", fg=typer.colors.RED)
        return
    try:
        with open(templates_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        typer.secho("Available Templates:", fg=typer.colors.CYAN)
        for i, template in enumerate(data.get("templates", [])):
            typer.echo(f"  {i+1}. ID: {template.get('id', 'N/A')} - Name: {template.get('name', 'Unnamed')}")
        # Add tools listing if desired
    except Exception as e:
        typer.secho(f"Error loading templates: {e}", fg=typer.colors.RED)

@app.callback()
def main_callback(ctx: typer.Context):
    """
    Omnitide Nexus Interactive CLI.
    Use 'omnitide-cli config wizard' on first use or to update essential paths.
    Paths are stored in ~/.omnitide_cli_config.json
    """
    global APP_CONFIG
    APP_CONFIG = config_manager.load_config()
    
    # Check if omniapp_root is set, if not, prompt user to run wizard
    # This check will run before any subcommand
    if not APP_CONFIG.get("omnitide_app_root") or \
       APP_CONFIG.get("omnitide_app_root") == config_manager.DEFAULT_CONFIG.get("omnitide_app_root"):
        # Check if the command being run is part of the 'config' group or if it's help
        is_config_command = ctx.invoked_subcommand and ctx.parent and ctx.parent.command.name == "config"
        is_help_command = any(arg in ["--help", "-h"] for arg in sys.argv)

        if not is_config_command and not is_help_command and ctx.invoked_subcommand is not None:
            typer.secho(
                "WARNING: Key paths (like Omniapp root) might not be configured properly in "
                f"{config_manager.CONFIG_FILE_PATH}",
                fg=typer.colors.YELLOW
            )
            typer.secho("Please run 'omnitide-cli config wizard' to set them up.", fg=typer.colors.YELLOW)
            # Optionally, could raise typer.Exit(1) here if paths are critical for all commands

if __name__ == "__main__":
    # Initial check to prompt for wizard if config file doesn't exist or is default
    # This helps first-time users.
    cfg_path = config_manager.CONFIG_FILE_PATH
    if not cfg_path.exists():
        typer.secho(f"Welcome! It seems this is your first time running Omnitide CLI or the config file is missing ({cfg_path}).", fg=typer.colors.MAGENTA)
        if typer.confirm("Would you like to run the initial configuration wizard now to set up essential paths?", default=True):
            # Directly call the Typer command for the wizard
            # This is a bit of a workaround to invoke a subcommand before the main app fully dispatched.
            # A cleaner way in complex apps might be a state check in the main callback.
            try:
                wizard_result = typer.main.get_command(app).commands['config'].commands['wizard'](['--omniapp-root', str(Path.cwd().parent)])
            except SystemExit: # Typer often calls sys.exit
                pass 
            # Re-load config after wizard
            APP_CONFIG = config_manager.load_config() 
            typer.secho("Wizard finished. Please re-run your intended command if it wasn't 'config wizard'.", fg=typer.colors.GREEN)
            # Depending on how Typer handles this, you might need to sys.exit() here if wizard was run.
            # For now, let it proceed to app()
    app()
EOF_CLI_MAIN
)

OMNITIDE_CLI_CONFIG_MANAGER_PY_CONTENT=$(cat <<'EOF_CLI_CONFIG_MGR'
# Omnitide CLI - config_manager.py (v1.2 Bootstrap)
import json
from pathlib import Path
from typing import Dict, Optional, Any

CONFIG_FILE_NAME = ".omnitide_cli_config.json" # Stored in user's home directory
CONFIG_FILE_PATH = Path.home() / CONFIG_FILE_NAME

DEFAULT_CONFIG = {
    "omnitide_app_root": "", # To be populated by bootstrap or wizard with OMNIAPP_DIR
    "agents_dir": "agents",  # Relative to omniapp_root
    "scribe_agent_script": "scribe.py", # Name of script within agents_dir
    "exwork_agent_script": "exworkagent.py", # Name of script within agents_dir
    "omnitide_templates_file": "omnitide_templates.json", # Name of file, expected in agents_dir relative to omniapp_root
    "default_project_cwd": ".", # Default CWD for agents, relative to omniapp_root or absolute
    "default_scribe_config_toml": ".scribe.toml" # Default name for Scribe's config, relative to project_cwd
}

def load_config() -> Dict[str, Any]:
    """Loads configuration from the JSON file, applying defaults for missing keys."""
    if CONFIG_FILE_PATH.exists():
        try:
            with open(CONFIG_FILE_PATH, "r", encoding="utf-8") as f:
                config_from_file = json.load(f)
            # Merge with defaults: ensure all default keys exist, file values override
            merged_config = DEFAULT_CONFIG.copy()
            merged_config.update(config_from_file) # Values from file take precedence
            return merged_config
        except (json.JSONDecodeError, IOError) as e:
            print(f"[CLI_CONFIG_ERROR] Error loading config file {CONFIG_FILE_PATH}: {e}. Using defaults.")
            return DEFAULT_CONFIG.copy()
    return DEFAULT_CONFIG.copy()

def save_config(config_data: Dict[str, Any]) -> None:
    """Saves configuration to the JSON file."""
    try:
        CONFIG_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=2)
        # print(f"[CLI_CONFIG_INFO] Configuration saved to {CONFIG_FILE_PATH}") # Can be verbose
    except IOError as e:
        print(f"[CLI_CONFIG_ERROR] Error saving CLI config file {CONFIG_FILE_PATH}: {e}")

def get_config_value(key: str, current_config: Optional[Dict[str, Any]] = None) -> Any:
    """Gets a specific value from the config, loading if necessary."""
    config_to_use = current_config if current_config is not None else load_config()
    return config_to_use.get(key, DEFAULT_CONFIG.get(key)) # Fallback to default dict if key somehow missing after load
EOF_CLI_CONFIG_MGR
)

# --- Web UI (NEWLY GENERATED parts) ---
WEB_UI_APP_PY_CONTENT=$(cat <<'EOF_WEBUI_APP'
#!/usr/bin/env python3
# Omni Web UI - Flask Backend (v1.2 Bootstrap)
import sys
import os
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
import subprocess
import json
from pathlib import Path
import shlex

# Add parent directory (omnitide_cli package dir) to sys.path to import config_manager
# This assumes omni_web_ui and omnitide_cli are siblings under omniapp root
OMNIAPP_ROOT_DIR_FROM_WEBUI = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(OMNIAPP_ROOT_DIR_FROM_WEBUI / "omnitide_cli")) # Add omnitide_cli package path

try:
    from omnitide_cli import config_manager as cli_config_mgr # Import from package
except ImportError:
    print("ERROR: Could not import omnitide_cli.config_manager for Web UI.")
    print(f"Ensure omnitide_cli module is in PYTHONPATH or structured correctly relative to {OMNIAPP_ROOT_DIR_FROM_WEBUI}")
    # Fallback definition for basic operation if import fails
    class cli_config_mgr:
        @staticmethod
        def load_config(): return {"omnitide_app_root": str(OMNIAPP_ROOT_DIR_FROM_WEBUI), "exwork_agent_script": "../agents/exworkagent.py", "agents_dir": "../agents"}
        @staticmethod
        def get_config_value(key, cfg=None): config = cfg or cli_config_mgr.load_config(); return config.get(key)


app = Flask(__name__)
app.secret_key = os.urandom(24)

def get_python_executable() -> str:
    return sys.executable or "python3"

@app.route('/')
def index():
    return render_template('index.html', title="Omnitide Web UI")

@app.route('/exwork', methods=['GET', 'POST'])
def run_exwork_ui_route():
    config = cli_config_mgr.load_config()
    omniapp_root = Path(config.get("omnitide_app_root", str(OMNIAPP_ROOT_DIR_FROM_WEBUI)))
    agents_dir = omniapp_root / config.get("agents_dir", "agents")
    exwork_script_name = config.get("exwork_agent_script", "exworkagent.py")
    exwork_agent_script = (agents_dir / exwork_script_name).resolve()
    
    default_project_cwd_str = config.get("default_project_cwd", ".")
    project_cwd = Path(default_project_cwd_str)
    if not project_cwd.is_absolute():
        project_cwd = (omniapp_root / default_project_cwd_str).resolve()

    if request.method == 'POST':
        exwork_json_payload_str = request.form.get('exwork_json_payload')
        if not exwork_json_payload_str:
            flash("ExWork JSON payload cannot be empty.", "error")
            return render_template('run_exwork_ui.html', title="Run ExWork", submitted_payload=exwork_json_payload_str)
        try:
            json.loads(exwork_json_payload_str)
        except json.JSONDecodeError as e:
            flash(f"Invalid JSON: {e}", "error")
            return render_template('run_exwork_ui.html', title="Run ExWork", submitted_payload=exwork_json_payload_str)

        if not exwork_agent_script.is_file():
            flash(f"ExWork Agent script not found at '{exwork_agent_script}'. Configure via 'omnitide-cli config wizard'.", "error")
            return render_template('run_exwork_ui.html', title="Run ExWork", submitted_payload=exwork_json_payload_str)
        if not project_cwd.is_dir():
            flash(f"Project CWD not found at '{project_cwd}'. Configure via 'omnitide-cli config wizard'.", "error")
            return render_template('run_exwork_ui.html', title="Run ExWork", submitted_payload=exwork_json_payload_str)

        python_exe = get_python_executable()
        command = [python_exe, str(exwork_agent_script)]
        
        results = {}
        try:
            process = subprocess.Popen(
                command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, cwd=str(project_cwd), encoding='utf-8', errors='replace'
            )
            stdout, stderr = process.communicate(input=exwork_json_payload_str, timeout=300)
            
            results = {"stdout": stdout, "stderr": stderr, "return_code": process.returncode, "ran_successfully": process.returncode == 0}
            if process.returncode == 0 and stdout:
                try: results["exwork_summary"] = json.loads(stdout)
                except json.JSONDecodeError: results["exwork_summary"] = "Could not parse ExWork stdout as JSON."
            
            if results["ran_successfully"]: flash("ExWork task completed successfully!", "success")
            else: flash(f"ExWork task failed (RC: {process.returncode}). Check output.", "error")

        except subprocess.TimeoutExpired:
            flash("ExWork agent timed out.", "error")
            results = {"error": "ExWork agent timed out."}
        except Exception as e:
            flash(f"Error running ExWork agent: {e}", "error")
            results = {"error": f"Error running ExWork agent: {e}"}
        
        return render_template('run_exwork_ui.html', title="Run ExWork", results=results, submitted_payload=exwork_json_payload_str)

    default_echo_payload = {"step_id": "web_echo_01", "actions": [{"type": "ECHO", "message": "Hello from Omnitide Web UI via ExWork!"}]}
    return render_template('run_exwork_ui.html', title="Run ExWork", submitted_payload=json.dumps(default_echo_payload, indent=2))

# Placeholder for Scribe UI route
@app.route('/scribe', methods=['GET', 'POST'])
def run_scribe_ui_route():
    # Logic for Scribe will be similar: get params from form, run scribe.py, display report.
    flash("Scribe UI functionality is not yet implemented.", "info")
    return render_template('run_scribe_ui.html', title="Run Scribe")


if __name__ == '__main__':
    cfg = cli_config_mgr.load_config()
    omniapp_r = cfg.get('omnitide_app_root', 'UNKNOWN (Run CLI config wizard)')
    print(f"INFO: Omnitide Web UI - Flask Application v1.2")
    print(f"INFO: Omniapp Root (from CLI config): {omniapp_r}")
    print(f"INFO: Flask dev server running on http://127.0.0.1:5678/")
    app.run(host='0.0.0.0', port=5678, debug=True)
EOF_WEBUI_APP
)

WEB_UI_BASE_HTML_CONTENT=$(cat <<'EOF_WEBUI_BASE_HTML'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Omnitide Nexus UI{% endblock %}</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
</head>
<body>
    <header>
        <h1>Omnitide Nexus - Web Interface</h1>
    </header>
    <nav>
        <a href="{{ url_for('index') }}">Home</a>
        <a href="{{ url_for('run_exwork_ui_route') }}">ExWork Tasks</a>
        <a href="{{ url_for('run_scribe_ui_route') }}">Scribe Validation</a>
    </nav>
    <div class="container">
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                <ul class=flashes>
                {% for category, message in messages %}
                    <li class="{{ category }}">{{ message }}</li>
                {% endfor %}
                </ul>
            {% endif %}
        {% endwith %}
        {% block content %}{% endblock %}
    </div>
    <footer>
        <p>&copy; 2025, For The Supreme Master Architect Alix Feronti</p>
    </footer>
</body>
</html>
EOF_WEBUI_BASE_HTML
)

WEB_UI_INDEX_HTML_CONTENT=$(cat <<'EOF_WEBUI_INDEX_HTML'
{% extends "base.html" %}
{% block title %}Home - Omnitide Web UI{% endblock %}
{% block content %}
    <h2>Welcome, Architect!</h2>
    <p>This is the central web interface for interacting with your Omnitide Nexus tools.</p>
    <p>Select an action from the navigation menu above to begin.</p>
    
    <h3>Available Tools:</h3>
    <ul>
        <li><a href="{{ url_for('run_exwork_ui_route') }}">Run ExWork Agent Task</a></li>
        <li><a href="{{ url_for('run_scribe_ui_route') }}">Run Scribe Agent Validation</a> (NYI)</li>
    </ul>
{% endblock %}
EOF_WEBUI_INDEX_HTML
)

WEB_UI_RUN_EXWORK_HTML_CONTENT=$(cat <<'EOF_WEBUI_RUN_EXWORK_HTML'
{% extends "base.html" %}
{% block title %}Run ExWork Task - Omnitide Web UI{% endblock %}
{% block content %}
    <h2>Run ExWork Agent Task</h2>
    <p>Enter your ExWork JSON payload below. Default is a simple echo example.</p>
    <form method="POST" class="exwork-form">
        <div class="form-group">
            <label for="exwork_json_payload">ExWork JSON Payload:</label>
            <textarea id="exwork_json_payload" name="exwork_json_payload" rows="15">{{ submitted_payload | e if submitted_payload else '' }}</textarea>
        </div>
        <div class="form-group">
            <input type="submit" value="Run ExWork Task">
        </div>
    </form>

    {% if results %}
        <hr>
        <h3>Execution Results:</h3>
        <p><strong>Return Code:</strong> <span class="{{ 'success-text' if results.ran_successfully else 'error-text' }}">{{ results.return_code }}</span></p>
        
        {% if results.exwork_summary %}
            <h4>ExWork Summary Output (Parsed JSON):</h4>
            <pre class="results-output">{{ results.exwork_summary | tojson(indent=2) }}</pre>
        {% elif results.stdout %}
             <h4>ExWork Raw STDOUT:</h4>
             <pre class="results-output">{{ results.stdout }}</pre>
        {% endif %}
        
        {% if results.stderr %}
            <h4>ExWork STDERR:</h4>
            <pre class="results-output error-output">{{ results.stderr }}</pre>
        {% endif %}

        {% if results.error %} {# For errors generated by the Flask app itself #}
            <h4 class="error-text">Application Error:</h4>
            <pre class="results-output error-output">{{ results.error }}</pre>
        {% endif %}
    {% endif %}
{% endblock %}
EOF_WEBUI_RUN_EXWORK_HTML
)

WEB_UI_RUN_SCRIBE_HTML_CONTENT=$(cat <<'EOF_WEBUI_RUN_SCRIBE_HTML'
{% extends "base.html" %}
{% block title %}Run Scribe Task - Omnitide Web UI{% endblock %}
{% block content %}
    <h2>Run Scribe Agent Validation</h2>
    <p class="warning-text">Scribe integration is not yet fully implemented in this Web UI.</p>
    
    <form method="POST" class="scribe-form">
        <div class="form-group">
            <label for="scribe_target_dir">Target Project Directory:</label>
            <input type="text" id="scribe_target_dir" name="scribe_target_dir" placeholder="/path/to/your/project" style="width:98%;">
        </div>
        <div class="form-group">
            <label for="scribe_code_file">Source Code File (to apply):</label>
            <input type="text" id="scribe_code_file" name="scribe_code_file" placeholder="/tmp/new_code.py" style="width:98%;">
        </div>
        <div class="form-group">
            <label for="scribe_target_file_relative">Destination File (relative in project):</label>
            <input type="text" id="scribe_target_file_relative" name="scribe_target_file_relative" placeholder="src/module.py" style="width:98%;">
        </div>
        <div class="form-group">
            <input type="submit" value="Run Scribe Validation (NYI)">
        </div>
    </form>

    {% if results %}
        <hr>
        <h3>Scribe Results (Placeholder):</h3>
        <pre class="results-output">{{ results | tojson(indent=2) }}</pre>
    {% endif %}
{% endblock %}
EOF_WEBUI_RUN_SCRIBE_HTML
)

WEB_UI_STYLE_CSS_CONTENT=$(cat <<'EOF_WEBUI_STYLE_CSS'
/* static/css/style.css for Omnitide Web UI */
body { 
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
    margin: 0; 
    padding: 0; 
    background-color: #1e1e2f; /* Dark background */
    color: #e0e0e0; /* Light text */
    line-height: 1.6;
}
header { 
    background-color: #2a2a3a; /* Slightly lighter dark */
    color: #ffffff; 
    padding: 1.2em 0; 
    text-align: center; 
    border-bottom: 3px solid #7b5cd9; /* Accent color */
}
header h1 {
    margin: 0;
    font-size: 2.2em;
    font-weight: 300;
}
nav { 
    background-color: #303040; /* Darker than header */
    padding: 0.8em; 
    text-align: center; 
    box-shadow: 0 2px 5px rgba(0,0,0,0.2);
}
nav a { 
    color: #d0d0ff; /* Light accent for links */
    margin: 0 20px; 
    text-decoration: none; 
    font-weight: bold; 
    font-size: 1.1em;
    transition: color 0.3s ease;
}
nav a:hover, nav a.active { 
    color: #ffffff;
    text-shadow: 0 0 5px #ffffff;
}
.container { 
    width: 85%; 
    max-width: 1200px;
    margin: 25px auto; 
    padding: 25px; 
    background-color: #252535; /* Content area background */
    border-radius: 8px; 
    box-shadow: 0 4px 15px rgba(0,0,0,0.3);
}
h2 { 
    color: #a0a0ff; /* Accent color for headings */
    border-bottom: 2px solid #4a4a6a;
    padding-bottom: 0.3em;
    margin-top: 0;
}
h3 { color: #b0b0cc; }
h4 { color: #c0c0dd; }

label {
    display: block;
    margin-bottom: 8px;
    font-weight: bold;
    color: #c0c0dd;
}
textarea, input[type="text"] { 
    width: calc(100% - 22px); /* Full width minus padding and border */
    min-height: 100px; 
    padding: 10px; 
    border: 1px solid #4a4a6a; 
    border-radius: 4px; 
    font-family: 'Courier New', Courier, monospace; 
    font-size: 0.95em; 
    margin-bottom:15px; 
    background-color: #1c1c2b; /* Darker input background */
    color: #e0e0e0; /* Light text for input */
    resize: vertical;
}
textarea#exwork_json_payload { min-height: 200px; }

input[type="submit"], button { 
    background-color: #7b5cd9; /* Accent color button */
    color: white; 
    padding: 12px 20px; 
    border: none; 
    border-radius: 5px; 
    cursor: pointer; 
    font-size: 1.05em;
    font-weight: bold;
    transition: background-color 0.3s ease;
}
input[type="submit"]:hover, button:hover { 
    background-color: #6a4bc0; /* Darker accent on hover */
}

pre.results-output { 
    background-color: #1a1a28; /* Very dark for code blocks */
    padding: 15px; 
    border-radius: 5px; 
    border: 1px solid #3a3a4a;
    white-space: pre-wrap; 
    word-wrap: break-word; 
    color: #c0c0ff; /* Light blueish text for output */
    max-height: 400px;
    overflow-y: auto;
}
pre.error-output { color: #ff8080; /* Reddish for errors */ }

.error-text, .flashes .error { color: #ff6060; font-weight: bold; background-color: rgba(255, 80, 80, 0.1); padding: 10px; border-left: 5px solid #ff6060; margin-bottom:15px; border-radius:4px;}
.success-text, .flashes .success { color: #60ff60; font-weight: bold; background-color: rgba(80, 255, 80, 0.1); padding: 10px; border-left: 5px solid #60ff60; margin-bottom:15px; border-radius:4px;}
.warning-text, .flashes .info { color: #ffd700; background-color: rgba(255, 215, 0, 0.1); padding: 10px; border-left: 5px solid #ffd700; margin-bottom:15px; border-radius:4px;}

ul.flashes { list-style-type: none; padding: 0; }
.form-group { margin-bottom: 20px; }

footer { 
    text-align:center; 
    padding: 20px 0;
    margin-top: 30px;
    color: #888898; 
    font-size:0.9em;
    border-top: 1px solid #303040;
}
EOF_WEBUI_STYLE_CSS
)

# Content for setup_omnitide_user_shell.sh (v2.3_interactive_plus from previous discussion)
# This is a long script, so its content will be embedded here.
SETUP_OMNITIDE_USER_SHELL_SH_EMBED_CONTENT=$(cat <<'EOF_XONSH_SETUP'
#!/bin/bash
# setup_omnitide_user_shell.sh - Interactively sets up user's Xonsh environment for Omnitide CLI development.
# Version: 2.3_interactive_plus
# Run AS THE REGULAR USER (e.g., pong), NOT with sudo.

set -e # Exit immediately if a command exits with a non-zero status.

# --- Configuration & Helper Functions ---
PYTHON_CMD_DEFAULT="python3.11" # Primary Python for user-level tools
SCRIPT_VERSION="2.3_interactive_plus"
OMNITIDE_PROJECT_DIR_NAME_DEFAULT="omnitide_launcher_project" # Used for guidance
REQUIREMENTS_FILE_NAME="requirements_omnitide_cli.txt" # Project requirements file

# Function to prompt for yes/no
prompt_yes_no() {
    while true; do
        read -r -p "$1 [Y/n]: " response
        response=${response,,} # tolower
        if [[ "$response" =~ ^(yes|y|"")$ ]]; then
            REPLY="yes"
            return 0
        elif [[ "$response" =~ ^(no|n)$ ]]; then
            REPLY="no"
            return 0
        else
            echo "Invalid input. Please enter 'yes' or 'no'."
        fi
    done
}

# Function to check if a command exists
command_exists() {
    command -v "$1" &> /dev/null
}

echo "--- Omnitide Interactive User Shell Setup Utility (v${SCRIPT_VERSION}) ---"
echo "This script will guide you through setting up Xonsh, essential tools,"
echo "and assist with preparing your environment for an Omnitide CLI project."
echo "--------------------------------------------------------------------"

# --- 0. Pre-flight Checks & Python Command Configuration ---
echo "[Phase 0/9] Performing pre-flight system checks and Python setup..."
PYTHON_CMD=""
prompt_yes_no "This script will use a Python interpreter (preferably 3.11+) for installing user-level packages like Xonsh. Do you want to specify the Python command now (e.g., python3.11, python3), or use the default '${PYTHON_CMD_DEFAULT}'?"
if [[ "$REPLY" == "yes" ]]; then
    read -r -p "Enter the Python command to use (e.g., python3.11): " PYTHON_CMD_INPUT
    PYTHON_CMD=${PYTHON_CMD_INPUT:-$PYTHON_CMD_DEFAULT}
else
    PYTHON_CMD=$PYTHON_CMD_DEFAULT
fi
echo "  Using Python command: '${PYTHON_CMD}'"

CAN_PROCEED=true
if ! command_exists "$PYTHON_CMD"; then
    echo -e "${RED}FATAL_ERROR: Python command '${PYTHON_CMD}' could not be found. This script requires a working Python (preferably 3.11+).${NC}"
    echo "Please install Python, ensure it's in your PATH with the specified command name, and re-run."
    CAN_PROCEED=false
fi
if ! command_exists "curl"; then
    echo -e "${RED}FATAL_ERROR: 'curl' could not be found. It's required for some installations (e.g., x-cmd).${NC}"
    echo "Please install curl (e.g., 'sudo apt update && sudo apt install curl') and re-run."
    CAN_PROCEED=false
fi
if ! command_exists "git"; then
    echo -e "${YELLOW}WARNING: 'git' command not found. While not strictly fatal for this script,"
    echo "           git is essential for most development workflows and some xontrib features.${NC}"
    prompt_yes_no "It is highly recommended to install git. Would you like to attempt to install it now using 'sudo apt install git' (requires sudo privileges)?"
    if [[ "$REPLY" == "yes" ]]; then
        if sudo apt update && sudo apt install -y git; then
            echo "  Git installed successfully."
        else
            echo -e "  ${RED}ERROR: Git installation failed. Please install it manually.${NC}"
        fi
    fi
fi

if ! $CAN_PROCEED; then
    echo "Pre-flight checks failed. Please address the FATAL_ERROR messages above."
    exit 1
fi
echo "[OK] Basic pre-flight checks passed."
echo "--------------------------------------------------------------------"

# --- 1. Clean Up Old Configs (Interactive) ---
echo "[Phase 1/9] Optional: Clean up previous Xonsh/X-cmd user configurations."
prompt_yes_no "Do you want to attempt to REMOVE existing user-level Xonsh/x-cmd configurations? (Select 'yes' for a fresh start, 'no' to keep existing configs. ${RED}THIS IS DESTRUCTIVE if you have custom setups you want to keep.${NC})"
if [[ "$REPLY" == "yes" ]]; then
    echo "  Proceeding with cleanup..."
    rm -rf ~/.xonshrc ~/.config/xonsh ~/.local/share/xonsh ~/.cache/xonsh ~/.x-cmd.root ~/.xontribs_python_path
    echo "  Removed common Xonsh/X-cmd user config locations and ~/.xontribs_python_path."
    echo "  [INFO] If you previously integrated Xonsh with other shells (.bashrc, .profile, .zshrc),"
    echo "         manual review of those files for leftover sourcing lines is recommended."
else
    echo "  Skipping cleanup of existing Xonsh/X-cmd configs."
fi
echo "[OK] Cleanup phase decision processed."
echo "--------------------------------------------------------------------"

# --- 2. Install/Upgrade Core Python Tools for User (pip, virtualenv) ---
echo "[Phase 2/9] Core Python Tools (pip, virtualenv) for ${PYTHON_CMD}."
echo "This will ensure pip and virtualenv are installed/upgraded for your user account via '${PYTHON_CMD}'."
prompt_yes_no "Proceed with checking/installing/upgrading pip and virtualenv?"
if [[ "$REPLY" == "yes" ]]; then
    "$PYTHON_CMD" -m ensurepip --upgrade || echo -e "${YELLOW}WARNING: '${PYTHON_CMD} -m ensurepip --upgrade' reported an issue. This might be okay if pip is already functional.${NC}"
    if "$PYTHON_CMD" -m pip install --user --upgrade pip virtualenv; then
        echo "[OK] pip and virtualenv checked/installed/upgraded successfully for ${PYTHON_CMD}."
    else
        echo -e "${RED}ERROR: Failed to install/upgrade pip or virtualenv using ${PYTHON_CMD}.${NC}"
        echo "         Please check your Python installation and pip. You can try running manually:"
        echo "         ${PYTHON_CMD} -m pip install --user --upgrade pip virtualenv"
        prompt_yes_no "Continue despite this error (not recommended unless pip/virtualenv are known to be working for '${PYTHON_CMD}')?"
        [[ "$REPLY" == "no" ]] && exit 1
    fi
else
    echo "  Skipping pip/virtualenv check/update. Ensure they are functional for ${PYTHON_CMD}."
fi
echo "--------------------------------------------------------------------"

# --- 3. Install/Upgrade Xonsh ---
echo "[Phase 3/9] Xonsh Shell Installation/Upgrade."
XONSH_USER_BIN_DIR="\${HOME}/.local/bin" # Use literal $HOME for echo, expansion for test
XONSH_EXE_PATH_TEST="${HOME}/.local/bin/xonsh" # For -f test
XONSH_INSTALLED=false
NEEDS_XONSH_INSTALL_OR_UPGRADE=false

if [ -f "$XONSH_EXE_PATH_TEST" ] || command_exists xonsh; then
    XONSH_INSTALLED=true
    echo "  Xonsh appears to be already installed."
    prompt_yes_no "Do you want to attempt to UPGRADE it using '${PYTHON_CMD} -m pip install --user --upgrade \"xonsh[full]\"'?"
    if [[ "$REPLY" == "yes" ]]; then
        NEEDS_XONSH_INSTALL_OR_UPGRADE=true
    else
        echo "  Skipping Xonsh upgrade."
    fi
else
    echo "  Xonsh not detected."
    prompt_yes_no "Do you want to INSTALL Xonsh for your user account using '${PYTHON_CMD} -m pip install --user --upgrade \"xonsh[full]\"'?"
    if [[ "$REPLY" == "yes" ]]; then
        NEEDS_XONSH_INSTALL_OR_UPGRADE=true
    else
        echo "  Xonsh installation skipped. Further Xonsh-specific setup will be aborted."
        echo "Setup terminated by user choice."
        exit 0
    fi
fi

if [[ "\$NEEDS_XONSH_INSTALL_OR_UPGRADE" == "true" ]]; then
    echo "  Installing/Upgrading Xonsh (this may take a moment)..."
    if "$PYTHON_CMD" -m pip install --user --upgrade "xonsh[full]"; then
        echo "[OK] Xonsh installed/upgraded successfully."
        XONSH_INSTALLED=true 
    else
        echo -e "${RED}FATAL_ERROR: Failed to install/upgrade Xonsh. Please check pip output and Python environment.${NC}"
        exit 1
    fi
fi

if \$XONSH_INSTALLED; then
    mkdir -p "${HOME}/.local/bin" 
    if [[ ":\$PATH:" != *":\${HOME}/.local/bin:"* ]]; then
        echo ""
        echo -e "${YELLOW}[IMPORTANT_ACTION_REQUIRED] '\${HOME}/.local/bin' is not found in your current PATH.${NC}"
        echo "  To make Xonsh directly callable, you MUST add it to your PATH."
        echo "  Add this line to your shell's startup file (e.g., ~/.bashrc, ~/.zshrc, or ~/.profile):"
        echo -e "      ${CYAN}export PATH=\"\\\$HOME/.local/bin:\\\$PATH\"${NC}"
        echo "  Then, source the file (e.g., 'source ~/.bashrc') or re-login / restart your terminal."
        prompt_yes_no "This script can attempt to add it to ~/.profile if you wish. Proceed?"
        if [[ "\$REPLY" == "yes" ]]; then
            if ! grep -qF "export PATH=\"\$HOME/.local/bin:\$PATH\"" ~/.profile; then
                echo -e '\n# Added by Omnitide User Shell Setup for Xonsh and user pip packages\nexport PATH="$HOME/.local/bin:$PATH"' >> ~/.profile
                echo "  Line added to ~/.profile. You'll need to re-login for it to take full effect."
            else
                echo "  Required PATH export line already exists in ~/.profile."
            fi
        fi
    fi
else
    echo "Xonsh is not installed. Cannot proceed with Xonsh specific setup."
    exit 1
fi
echo "[OK] Xonsh installation/check complete."
echo "--------------------------------------------------------------------"

# --- 4. Install Xontribs ---
echo "[Phase 4/9] Xonsh Extensions (Xontribs) Setup."
XONTRIBS_CORE_RECOMMENDED=("xontrib-direnv" "xontrib-fzf" "xontrib-up")
XONTRIBS_INSTALLED_FOR_RC=()

echo "The following xontribs are highly recommended:"
for XONTRIB in "\${XONTRIBS_CORE_RECOMMENDED[@]}"; do echo "  - \${XONTRIB}"; done
prompt_yes_no "Do you want to install/upgrade these recommended xontribs?"
if [[ "\$REPLY" == "yes" ]]; then
    if [[ " \${XONTRIBS_CORE_RECOMMENDED[*]} " =~ " xontrib-fzf " ]] && ! command_exists fzf; then
        echo -e "${YELLOW}WARNING: 'fzf' command (system dependency for xontrib-fzf) not found.${NC}"
        prompt_yes_no "           Install 'fzf' system-wide (e.g., 'sudo apt install fzf')? This script can try."
        if [[ "\$REPLY" == "yes" ]]; then
            if sudo apt update && sudo apt install -y fzf; then echo "  fzf installed."; else echo -e "  ${RED}ERROR: fzf system installation failed. Install manually.${NC}"; fi
        fi
    fi
    if [[ " \${XONTRIBS_CORE_RECOMMENDED[*]} " =~ " xontrib-direnv " ]] && ! command_exists direnv; then
        echo -e "${YELLOW}WARNING: 'direnv' command (system dependency for xontrib-direnv) not found.${NC}"
        prompt_yes_no "           Install 'direnv' system-wide (e.g., 'sudo apt install direnv')? This script can try."
        if [[ "\$REPLY" == "yes" ]]; then
             if sudo apt update && sudo apt install -y direnv; then echo "  direnv installed."; else echo -e "  ${RED}ERROR: direnv system installation failed. Install manually.${NC}"; fi
        fi
    fi
    
    echo "  Installing/upgrading recommended xontribs: \${XONTRIBS_CORE_RECOMMENDED[*]}..."
    if "$PYTHON_CMD" -m pip install --user --upgrade "\${XONTRIBS_CORE_RECOMMENDED[@]}"; then
        echo "[OK] Recommended xontribs installed/upgraded."
        XONTRIBS_INSTALLED_FOR_RC=("\${XONTRIBS_CORE_RECOMMENDED[@]}")
    else
        echo -e "${RED}ERROR: Failed to install one or more core xontribs. Check pip output.${NC}"
    fi
else
    echo "  Skipping installation of recommended xontribs."
fi
echo "[OK] Xontribs setup phase complete."
echo "--------------------------------------------------------------------"

# --- 5. Install x-cmd (Optional) ---
echo "[Phase 5/9] x-cmd Installation (Optional Tool)."
XCMD_EXE_PATH_TEST="\${HOME}/.x-cmd.root/bin/x"
XCMD_INSTALLED_FLAG=false
if [ -f "\$XCMD_EXE_PATH_TEST" ]; then
    echo "  x-cmd appears to be already installed."
    XCMD_INSTALLED_FLAG=true
    prompt_yes_no "Do you want to check for x-cmd updates ('\$XCMD_EXE_PATH_TEST update self')?"
    if [[ "\$REPLY" == "yes" ]]; then
        if "\$XCMD_EXE_PATH_TEST" update self; then echo "  x-cmd updated."; else echo "  x-cmd update command had issues or was already latest."; fi
    fi
else
    prompt_yes_no "x-cmd is a community-driven command-line tool enhancer. Install it now?"
    if [[ "\$REPLY" == "yes" ]]; then
        if bash -c "\$(curl -fsSL https://get.x-cmd.com)"; then
            echo "[OK] x-cmd installation script completed."
            if [ -f "\$XCMD_EXE_PATH_TEST" ]; then XCMD_INSTALLED_FLAG=true; else echo -e "${RED}ERROR: x-cmd executable not found after install.${NC}"; fi
        else
            echo -e "${RED}ERROR: x-cmd installation script failed.${NC}"
        fi
    else
        echo "  Skipping x-cmd installation."
    fi
fi
echo "[OK] x-cmd installation phase complete."
echo "--------------------------------------------------------------------"

# --- 6. Integrate x-cmd with Xonsh (If x-cmd installed) ---
echo "[Phase 6/9] x-cmd Xonsh Integration (if x-cmd is installed)."
if \$XCMD_INSTALLED_FLAG; then
    prompt_yes_no "Run 'x onsh --setup' to integrate x-cmd with Xonsh configuration?"
    if [[ "\$REPLY" == "yes" ]]; then
        if "\$XCMD_EXE_PATH_TEST" onsh --setup; then
            echo "[OK] 'x onsh --setup' completed."
        else
            echo -e "${YELLOW}WARNING: 'x onsh --setup' command reported an issue. This might be okay if already set up.${NC}"
        fi
    else
        echo "  Skipping 'x onsh --setup'."
    fi
else
    echo "  Skipping x-cmd Xonsh integration (x-cmd not installed)."
fi
echo "[OK] x-cmd Xonsh integration phase complete."
echo "--------------------------------------------------------------------"

# --- 7. Create/Update .xonshrc ---
echo "[Phase 7/9] Generating/Updating ~/.xonshrc file..."
XONSHRC_CONTENT="# ~/.xonshrc (Omnitide CLI Dev v\${SCRIPT_VERSION})
# Interactively generated. Loads essential plugins.

print(f\"INFO: Omnitide Dev .xonshrc v\${SCRIPT_VERSION} loading...\")

# Load selected xontribs (ensure system packages fzf, direnv are installed for these)
if \${#XONTRIBS_INSTALLED_FOR_RC[@]} -gt 0 ; then
    print(\"INFO: Loading selected xontribs...\")
    for xontrib_raw_name in \"\${XONTRIBS_INSTALLED_FOR_RC[@]}\"; do
        xontrib_load_name = xontrib_raw_name.replace('xontrib-', '')
        try:
            xontrib load @(xontrib_load_name)
            print(f\"  INFO: Successfully loaded xontrib: {xontrib_load_name}\")
        except Exception as e_xontrib:
            print(f\"  WARN: Could not load xontrib '{xontrib_load_name}': {{e_xontrib}}\")
    print(\"\")
else:
    print(\"INFO: No xontribs were selected for auto-loading in .xonshrc during setup.\")
    print(\"      You can load them manually via 'xontrib load <name>'.\")
fi

# Optional: Powerline prompt (Uncomment if xontrib-powerline or similar is installed)
# print(\"INFO: Attempting to load powerline prompt (optional)...\")
# try:
#     xontrib load powerline 
#     \$PROMPT = \$POWERLINE_PROMPT 
#     print(\"  INFO: Powerline prompt theme loaded.\")
# except Exception as e_powerline:
#     print(f\"  WARN: Could not load powerline xontrib or set prompt: {{e_powerline}}\")

# x-cmd integration is typically handled by files in ~/.config/xonsh/ via 'x onsh --setup'.

# Ensure prompt updates after all configurations.
if 'update_prompt' in globals() and callable(globals()['update_prompt']):
    print(\"INFO: Requesting final prompt update via globals()['update_prompt']()...\")
    globals()['update_prompt']()
elif hasattr(__builtins__, 'update_prompt') and callable(getattr(__builtins__, 'update_prompt')): # Fallback
    print(\"INFO: Requesting final prompt update via __builtins__.update_prompt()...\")
    getattr(__builtins__, 'update_prompt')()
else:
    print(\"INFO: 'update_prompt' function not found/callable. Prompt may update via other mechanisms.\")

print(f\"INFO: Omnitide Dev .xonshrc v\${SCRIPT_VERSION} loading complete.\")
"
# The XONSHRC_CONTENT needs to be written carefully to avoid issues with bash trying to expand $ and backticks.
# Using single quotes for cat EOF is safer for literal content.
# For the xontrib loop within .xonshrc, it's tricky to generate that part from bash into python.
# A simpler .xonshrc might be better if this becomes too complex.

# Simplified .xonshrc generation, user can add xontribs manually or script adds fixed ones
cat << EOF_XONSHRC > ~/.xonshrc
# ~/.xonshrc (Omnitide CLI Dev v${SCRIPT_VERSION})
# Interactively generated.

print(f"INFO: Omnitide Dev .xonshrc v${SCRIPT_VERSION} loading...")

# Load direnv, fzf, up if they were installed via this script
EOF_XONSHRC

# Append xontrib loading if they were installed
if [[ " ${XONTRIBS_INSTALLED_FOR_RC[*]} " =~ " xontrib-direnv " ]]; then
echo -e "print('  Loading xontrib-direnv...')\ntry: xontrib load direnv\nexcept: print('  WARN: Failed to load direnv xontrib.')" >> ~/.xonshrc
fi
if [[ " ${XONTRIBS_INSTALLED_FOR_RC[*]} " =~ " xontrib-fzf " ]]; then
echo -e "print('  Loading xontrib-fzf...')\ntry: xontrib load fzf\nexcept: print('  WARN: Failed to load fzf xontrib.')" >> ~/.xonshrc
fi
if [[ " ${XONTRIBS_INSTALLED_FOR_RC[*]} " =~ " xontrib-up " ]]; then
echo -e "print('  Loading xontrib-up...')\ntry: xontrib load up\nexcept: print('  WARN: Failed to load up xontrib.')" >> ~/.xonshrc
fi

cat <<EOF_XONSHRC_END >> ~/.xonshrc

# Optional: Powerline (manual uncomment)
# print("INFO: Attempting to load powerline prompt...")
# try:
#     xontrib load powerline
#     \$PROMPT = \$POWERLINE_PROMPT
# except Exception as e:
#     print(f"  WARN: Could not load powerline: {e}")

if 'update_prompt' in globals() and callable(globals()['update_prompt']):
    print("INFO: Requesting final prompt update...")
    globals()['update_prompt']()
else:
    print("INFO: 'update_prompt' not found/callable.")

print(f"INFO: Omnitide Dev .xonshrc v${SCRIPT_VERSION} loading complete.")
EOF_XONSHRC_END

echo "[OK] ~/.xonshrc created/updated."
echo "--------------------------------------------------------------------"

# --- 8. Guidance and Automation for Omnitide CLI Project Setup ---
echo "[Phase 8/9] Omnitide Project Environment Setup Assistance (using direnv)."
echo ""
CURRENT_DIR_FOR_PROJECT_SETUP=$(pwd)
prompt_yes_no "Is the current directory ('${CURRENT_DIR_FOR_PROJECT_SETUP}') the root of your Omniapp project where you want to set up a direnv environment?"
if [[ "\$REPLY" == "yes" ]]; then
    OMNIAPP_PROJECT_ROOT_CONFIRMED="\$CURRENT_DIR_FOR_PROJECT_SETUP"
    echo "  Current directory confirmed as project root: \${OMNIAPP_PROJECT_ROOT_CONFIRMED}"

    if ! command_exists direnv; then
        echo -e "  ${RED}ERROR: 'direnv' command is not available. This step requires 'direnv' (system-wide) and 'xontrib-direnv' (for Xonsh).${NC}"
    else
        echo "  Setting up direnv for project: \${OMNIAPP_PROJECT_ROOT_CONFIRMED}"
        ENVRC_FILE="\${OMNIAPP_PROJECT_ROOT_CONFIRMED}/.envrc"
        REQUIREMENTS_PROJECT_FILE="\${OMNIAPP_PROJECT_ROOT_CONFIRMED}/${REQUIREMENTS_FILE_NAME}" # Using global var

        if [ -f "\$ENVRC_FILE" ]; then
            echo "  Found existing .envrc file in project directory."
            prompt_yes_no "Overwrite existing .envrc with a standard Omniapp template?"
            if [[ "\$REPLY" == "no" ]]; then
                echo "  Keeping existing .envrc. Ensure it includes 'layout python ${PYTHON_CMD_FOR_VENV}' or similar."
                NEEDS_ENVRC_CREATION_PROJECT=false
            else
                NEEDS_ENVRC_CREATION_PROJECT=true
            fi
        else
            NEEDS_ENVRC_CREATION_PROJECT=true
        fi

        if \$NEEDS_ENVRC_CREATION_PROJECT; then
            echo "  Creating/Overwriting .envrc file with standard Python layout..."
            # Use the PYTHON_CMD_FOR_VENV defined at the top of this bootstrap script
            echo "# .envrc for Omniapp Suite (auto-generated by setup script)" > "\$ENVRC_FILE"
            echo "echo \"Loading Omniapp project environment (\${OMNIAPP_PROJECT_ROOT_CONFIRMED})...\"" >> "\$ENVRC_FILE"
            echo "layout python ${PYTHON_CMD_FOR_VENV}" >> "\$ENVRC_FILE"
            echo "export OMNIAPP_ROOT=\\\$(pwd)" >> "\$ENVRC_FILE" # direnv will set OMNIAPP_ROOT
            echo "echo \"Python from venv: \\\$(which python)\"" >> "\$ENVRC_FILE"
            echo "echo \"Omniapp project environment loaded.\"" >> "\$ENVRC_FILE"
            echo "  .envrc file created/updated in \${OMNIAPP_PROJECT_ROOT_CONFIRMED}."
        fi

        prompt_yes_no "Run 'direnv allow .' in this directory ('\${OMNIAPP_PROJECT_ROOT_CONFIRMED}') to approve and activate the environment?"
        if [[ "\$REPLY" == "yes" ]]; then
            echo "  Running 'direnv allow .'..."
            if (cd "\${OMNIAPP_PROJECT_ROOT_CONFIRMED}" && direnv allow .); then
                echo "  'direnv allow .' executed."
                
                if [ -f "\$REQUIREMENTS_PROJECT_FILE" ]; then
                    echo "  Found project requirements file: \${REQUIREMENTS_PROJECT_FILE}"
                    prompt_yes_no "Attempt to install project dependencies using 'pip install -r \${REQUIREMENTS_FILE_NAME}' into the direnv-managed venv now?"
                    if [[ "\$REPLY" == "yes" ]]; then
                        echo "  Attempting to install dependencies. This assumes direnv has activated the venv."
                        if (cd "\${OMNIAPP_PROJECT_ROOT_CONFIRMED}" && direnv exec . pip install -r "\${REQUIREMENTS_FILE_NAME}"); then
                             echo "  [OK] 'pip install -r \${REQUIREMENTS_FILE_NAME}' executed."
                        else
                             echo -e "  ${YELLOW}WARNING: 'pip install' via 'direnv exec' reported an issue. Manual installation might be needed after ensuring direnv environment is active.${NC}"
                        fi
                    fi
                else
                    echo -e "  ${YELLOW}WARNING: Project requirements file '\${REQUIREMENTS_PROJECT_FILE}' not found. Cannot offer to install dependencies.${NC}"
                    echo "            Please ensure '\${REQUIREMENTS_FILE_NAME}' (with content for CLI, WebUI, Agents) is in '\${OMNIAPP_PROJECT_ROOT_CONFIRMED}'."
                fi
            else
                echo -e "  ${RED}ERROR: 'direnv allow .' failed. Please run it manually in '\${OMNIAPP_PROJECT_ROOT_CONFIRMED}' from within Xonsh.${NC}"
            fi
        else
            echo "  Skipped 'direnv allow .'. You will need to run it manually in '\${OMNIAPP_PROJECT_ROOT_CONFIRMED}'."
        fi
    fi
else
    echo "  Skipping automated project setup for current directory."
    echo "  Remember to set up a 'direnv' environment for your Omniapp project manually later."
fi
echo "--------------------------------------------------------------------"


# --- 9. Final Instructions ---
echo "[Phase 9/9] Final Instructions & Summary"
echo ""
echo -e "${GREEN}--- Omnitide Interactive User Shell & Project Setup Finished ---${NC}"
echo "IMPORTANT NEXT STEPS:"
echo "1. If PATH was modified (e.g., for ~/.local/bin), ${YELLOW}CLOSE THIS TERMINAL and open a new one, or re-login.${NC}"
echo "2. Start Xonsh in your new terminal: ${CYAN}xonsh${NC}"
echo "3. If this is your FIRST time using direnv with Xonsh:"
echo "   Run this command ONCE *inside* Xonsh: ${CYAN}execx(\$(direnv hook xonsh), 'exec')${NC}"
echo "   Then, ${YELLOW}RESTART XONSH${NC} again (exit and type 'xonsh')."
echo "4. Navigate to your Omniapp project directory (e.g., '${CYAN}cd ${OMNIAPP_DIR:-/home/pong/Projects/omniapp}${NC}')."
echo "   - If you used Phase 8 for project setup:"
echo "     - Direnv should automatically activate the venv (you'll see a message)."
echo "     - If dependencies weren't installed, run: ${CYAN}pip install -r ${REQUIREMENTS_FILE_NAME}${NC}"
echo "   - If you SKIPPED Phase 8 project setup:"
echo "     - Create an '.envrc' file (see Phase 8 output for an example)."
echo "     - Run: ${CYAN}direnv allow .${NC}"
echo "     - Install dependencies: ${CYAN}pip install -r ${REQUIREMENTS_FILE_NAME}${NC}"
echo "5. Once the project environment is active and dependencies are installed, you should be able to use the Omnitide tools."
echo ""
echo "Review all script output for WARNINGS or ERRORS and address them as needed."
echo "--------------------------------------------------------------------"
exit 0

EOF_XONSH_SETUP
)


# 3. Create Directory Structure and Populate Files
print_header "Step 3: Creating Directory Structure and Populating Files in ${OMNIAPP_DIR}"

declare -A components_to_install
prompt_yes_no "Bootstrap Omnitide CLI component (generates new structure for Typer CLI)?" && components_to_install["cli"]="yes"
if [[ "${components_to_install[cli]}" == "yes" ]]; then
    prompt_yes_no "  Also generate a basic pyproject.toml for the Omnitide CLI component (for potential packaging/installation)?" && components_to_install["cli_pyproject"]="yes"
fi
prompt_yes_no "Bootstrap Agents (ExWork, Scribe, Templates - copies from your specified source directory)?" && components_to_install["agents"]="yes"
prompt_yes_no "Bootstrap Web UI component (generates new Flask app and HTML templates)?" && components_to_install["web_ui"]="yes"
prompt_yes_no "Include User Shell Setup scripts (for Xonsh - allows copying your version or uses embedded template)?" && components_to_install["user_shell"]="yes"

# Always create main configuration files at Omniapp root
write_file_content "${OMNIAPP_DIR}/README.md" "README_MD_CONTENT" "yes"
write_file_content "${OMNIAPP_DIR}/.envrc" "DOT_ENVRC_CONTENT" "yes"
write_file_content "${OMNIAPP_DIR}/requirements.txt" "MAIN_REQUIREMENTS_TXT_CONTENT" "yes"

# --- Omnitide CLI Component ---
if [[ "${components_to_install[cli]}" == "yes" ]]; then
    print_info "Setting up Omnitide CLI component..."
    CLI_BASE_DIR="${OMNIAPP_DIR}/omnitide_cli"
    CLI_PKG_DIR="${CLI_BASE_DIR}/omnitide_cli" # Python package dir
    mkdir -p "${CLI_PKG_DIR}/commands"
    touch "${CLI_PKG_DIR}/__init__.py"
    touch "${CLI_PKG_DIR}/commands/__init__.py"
    
    # Adjust config_manager.py DEFAULT_CONFIG to include omniapp_root if needed (or handle it in CLI logic)
    # The provided OMNITIDE_CLI_CONFIG_MANAGER_PY_CONTENT uses omnitide_app_root from its own config file.
    
    write_file_content "${CLI_PKG_DIR}/main.py" "OMNITIDE_CLI_MAIN_PY_CONTENT"
    write_file_content "${CLI_PKG_DIR}/config_manager.py" "OMNITIDE_CLI_CONFIG_MANAGER_PY_CONTENT"
    
    # Placeholder command modules - these would be expanded by the CLI's own functionality or manually
    INIT_CMDS_PY_CONTENT="# omnitide_cli/commands/__init__.py"
    EXWORK_CMDS_PY_CONTENT="# omnitide_cli/commands/exwork_cmds.py\nimport typer\n\napp = typer.Typer(name=\"exwork\", help=\"ExWork Agent Commands - NYI\")\n\n@app.command(\"run\")\ndef exwork_run_cmd():\n    typer.echo(\"ExWork run command placeholder\")\n"
    SCRIBE_CMDS_PY_CONTENT="# omnitide_cli/commands/scribe_cmds.py\nimport typer\n\napp = typer.Typer(name=\"scribe\", help=\"Scribe Agent Commands - NYI\")\n\n@app.command(\"validate\")\ndef scribe_validate_cmd():\n    typer.echo(\"Scribe validate command placeholder\")\n"
    # TODO: Add template_cmds.py, log_cmds.py placeholders later if confirmed

    write_file_content "${CLI_PKG_DIR}/commands/__init__.py" "INIT_CMDS_PY_CONTENT"
    write_file_content "${CLI_PKG_DIR}/commands/exwork_cmds.py" "EXWORK_CMDS_PY_CONTENT"
    write_file_content "${CLI_PKG_DIR}/commands/scribe_cmds.py" "SCRIBE_CMDS_PY_CONTENT"

    CLI_README_CONTENT="# Omnitide CLI\n\nA Python Typer-based CLI to orchestrate Omnitide agents and tasks.\n\n## Setup\nEnsure dependencies from the main \`omniapp/requirements.txt\` are installed in your virtual environment.\nIf using poetry for this sub-module (see pyproject.toml), navigate here and run \`poetry install\`.\n\n## Usage\nFrom the \`omniapp\` root (with venv active):\n\`python -m omnitide_cli.main --help\`\nOr if installed via poetry/pyproject.toml:\n\`omni-cli --help\`"
    write_file_content "${CLI_BASE_DIR}/README.md" "CLI_README_CONTENT" "yes"

    if [[ "${components_to_install[cli_pyproject]}" == "yes" ]]; then
        PYPROJECT_TOML_CONTENT=$(cat <<'EOF_PYPROJECT'
[tool.poetry]
name = "omnitide-cli"
version = "0.1.0"
description = "Omnitide Nexus CLI Orchestrator"
authors = ["Architect Alix Feronti <architect@omnitide.dev>"]
readme = "README.md"
packages = [{include = "omnitide_cli"}] # Assumes omnitide_cli dir is at same level as pyproject.toml

[tool.poetry.dependencies]
python = "^3.9" 
typer = {extras = ["all"], version = "^0.9.0"}
# Add other direct CLI dependencies here as it evolves, e.g.:
# requests = "^2.25"
# rich = "^13.0"

[tool.poetry.scripts]
omni-cli = "omnitide_cli.main:app"

[build-system]
requires = ["poetry-core>=1.0.0"]
build-backend = "poetry.core.masonry.api"
EOF_PYPROJECT
)
        write_file_content "${CLI_BASE_DIR}/pyproject.toml" "PYPROJECT_TOML_CONTENT"
    fi
fi

# --- Agents Component ---
if [[ "${components_to_install[agents]}" == "yes" ]]; then
    print_info "Setting up Agents component (ExWork, Scribe, Templates)..."
    AGENTS_DIR="${OMNIAPP_DIR}/agents"
    mkdir -p "${AGENTS_DIR}"
    
    agent_files_copied_count=0
    if $COPY_EXISTING_AGENTS; then
        if copy_file_interactive "${EXISTING_AGENTS_SRC_DIR}/exworkagent.py" "${AGENTS_DIR}/exworkagent.py" "ExWork Agent"; then
             chmod +x "${AGENTS_DIR}/exworkagent.py"
             agent_files_copied_count=$((agent_files_copied_count + 1))
        fi
        if copy_file_interactive "${EXISTING_AGENTS_SRC_DIR}/scribe.py" "${AGENTS_DIR}/scribe.py" "Scribe Agent"; then
            chmod +x "${AGENTS_DIR}/scribe.py"
            agent_files_copied_count=$((agent_files_copied_count + 1))
        fi
        if copy_file_interactive "${EXISTING_AGENTS_SRC_DIR}/omnitide_templates.json" "${AGENTS_DIR}/omnitide_templates.json" "Omnitide Templates JSON"; then
            agent_files_copied_count=$((agent_files_copied_count + 1))
        fi
    fi
    if [ $agent_files_copied_count -eq 0 ]; then
        print_warning "No agent files (ExWork, Scribe, Templates) were copied. The 'agents' directory is empty or only contains files not copied by this script."
        print_warning "Ensure your source directory ('${EXISTING_AGENTS_SRC_DIR}') contains the correct files or that you confirmed overwrites."
        # Create placeholder/empty templates if none copied and user confirms
        if [ ! -f "${AGENTS_DIR}/omnitide_templates.json" ]; then
            prompt_yes_no "Create an empty placeholder for 'omnitide_templates.json'?"
            if [[ "$REPLY" == "yes" ]]; then
                EMPTY_TEMPLATES_JSON_CONTENT='{\n  "version": "0.1.0",\n  "comment": "Placeholder Omnitide Templates. Populate with ExWork and Scribe templates.",\n  "templates": [],\n  "tools": []\n}'
                write_file_content "${AGENTS_DIR}/omnitide_templates.json" "EMPTY_TEMPLATES_JSON_CONTENT" "yes"
            fi
        fi
    fi
fi

# --- Web UI Component ---
if [[ "${components_to_install[web_ui]}" == "yes" ]]; then
    print_info "Setting up Web UI component (Flask)..."
    WEB_UI_DIR="${OMNIAPP_DIR}/web_ui"
    mkdir -p "${WEB_UI_DIR}/templates"
    mkdir -p "${WEB_UI_DIR}/static/css"
    
    write_file_content "${WEB_UI_DIR}/app.py" "WEB_UI_APP_PY_CONTENT"
    write_file_content "${WEB_UI_DIR}/templates/base.html" "WEB_UI_BASE_HTML_CONTENT"
    write_file_content "${WEB_UI_DIR}/templates/index.html" "WEB_UI_INDEX_HTML_CONTENT"
    write_file_content "${WEB_UI_DIR}/templates/run_exwork_ui.html" "WEB_UI_RUN_EXWORK_HTML_CONTENT"
    write_file_content "${WEB_UI_DIR}/templates/run_scribe_ui.html" "WEB_UI_RUN_SCRIBE_HTML_CONTENT"
    write_file_content "${WEB_UI_DIR}/static/css/style.css" "WEB_UI_STYLE_CSS_CONTENT"
fi

# --- User Shell Setup Component ---
handle_potentially_sourced_or_embedded_script() {
    local script_name_in_repo="$1" 
    local target_dir_rel="$2" 
    local embedded_content_var_name="$3" 
    local file_description="$4"
    local default_source_filename="$5" # Actual filename to look for in user's source dir

    mkdir -p "${OMNIAPP_DIR}/${target_dir_rel}"
    local target_path="${OMNIAPP_DIR}/${target_dir_rel}/${script_name_in_repo}" # How it's named in Omniapp

    local source_script_path=""
    local user_provided_path=false

    prompt_yes_no "For ${file_description} ('${script_name_in_repo}'), do you have an existing local version you'd like to copy into Omniapp?"
    if [[ "$REPLY" == "yes" ]]; then
        read -r -e -p "Enter full path to your existing '${default_source_filename}' for ${file_description}: " script_src_path_input
        if [[ -n "$script_src_path_input" ]]; then
            user_provided_path=true
            source_script_path="$script_src_path_input"
        fi
    fi

    if $user_provided_path && [ -f "$source_script_path" ]; then
        if copy_file_interactive "$source_script_path" "$target_path" "$file_description"; then
             if [[ "$target_path" == *".sh" ]]; then chmod +x "$target_path"; fi
        else # Copy failed or skipped by user
            print_warning "Copy of user-provided ${file_description} failed or was skipped."
            # Fallback to embedded only if copy explicitly failed after path was given & valid
            if [ -f "$source_script_path" ]; then # if source was valid but copy was skipped
                print_info "Keeping destination ${target_path} as is or empty."
            else # if source path was invalid initially
                 prompt_yes_no "Use embedded template content for ${file_description} ('${script_name_in_repo}') instead?"
                 if [[ "$REPLY" == "yes" ]]; then
                    eval "current_content=\$$embedded_content_var_name" 
                    write_file_content "$target_path" "current_content" "yes" 
                    if [[ "$target_path" == *".sh" ]]; then chmod +x "$target_path"; fi
                 else
                    print_info "Skipped ${file_description}."
                 fi
            fi
        fi
    else # User did not provide a path, or path was invalid
        if $user_provided_path && [[ -n "$source_script_path" ]]; then # Path was given but not found
            print_warning "Source for ${file_description} ('${source_script_path}') not found."
        fi
        prompt_yes_no "Use embedded template content for ${file_description} ('${script_name_in_repo}')?"
        if [[ "$REPLY" == "yes" ]]; then
            eval "current_content=\$$embedded_content_var_name" 
            write_file_content "$target_path" "current_content" "yes" 
            if [[ "$target_path" == *".sh" ]]; then chmod +x "$target_path"; fi
        else
            print_info "Skipped ${file_description}."
        fi
    fi
}

if [[ "${components_to_install[user_shell]}" == "yes" ]]; then
    print_info "Setting up User Shell Setup component..."
    handle_potentially_sourced_or_embedded_script "setup_omnitide_user_shell.sh" "user_shell_setup" \
        "SETUP_OMNITIDE_USER_SHELL_SH_EMBED_CONTENT" "Xonsh Setup Script" "setup_omnitide_user_shell.sh"
fi

print_success "Directory structure and component files processed based on your selections."

# 4. Final Setup Steps (Direnv, Dependencies)
print_header "Step 4: Final Environment Setup for ${OMNIAPP_DIR}"
if command -v direnv &> /dev/null; then
    prompt_yes_no "Found 'direnv'. Attempt to run 'direnv allow .' in '${OMNIAPP_DIR}' to activate the environment defined in .envrc?"
    if [[ "$REPLY" == "yes" ]]; then
        print_info "Running 'direnv allow .' in '${OMNIAPP_DIR}'..."
        if (cd "$OMNIAPP_DIR" && direnv allow .); then # Run in subshell to ensure direnv picks up CWD correctly
            print_success "'direnv allow .' executed. The environment should load/be created."
            print_info "You might need to 'cd' out and back into '${OMNIAPP_DIR}' for the environment (especially PATH changes for venv) to fully activate in your current shell."
            
            # Check if requirements.txt exists
            if [ -f "${OMNIAPP_DIR}/requirements.txt" ]; then
                prompt_yes_no "Install Python dependencies from '${OMNIAPP_DIR}/requirements.txt' into the direnv-managed virtual environment now? (This requires the venv to be active.)"
                if [[ "$REPLY" == "yes" ]]; then
                    print_info "Attempting to install dependencies using 'direnv exec ${OMNIAPP_DIR} pip install -r requirements.txt'..."
                    echo "If this step seems to hang or fails, try manually after 'cd ${OMNIAPP_DIR}' and ensuring venv is active:"
                    echo "  (your_venv_prompt)$ pip install -r requirements.txt"
                    if (cd "$OMNIAPP_DIR" && direnv exec . pip install -r requirements.txt); then
                        print_success "Dependencies installed successfully via 'direnv exec'."
                    else
                        print_error "Dependency installation via 'direnv exec' failed or reported issues. Please check output and try manually within the activated direnv environment."
                    fi
                else
                    print_info "Skipped automatic dependency installation. Remember to run 'pip install -r requirements.txt' later within the direnv environment of '${OMNIAPP_DIR}'."
                fi
            else
                print_warning "'${OMNIAPP_DIR}/requirements.txt' not found. Skipping dependency installation step."
            fi
        else
            print_error "'direnv allow .' failed. Please run it manually in '${OMNIAPP_DIR}' from within a shell where 'direnv hook' is active (like Xonsh after setup)."
        fi
    else
        print_info "Skipped 'direnv allow .'. Please run it manually in '${OMNIAPP_DIR}' after ensuring your shell's direnv hook is active."
    fi
else
    print_warning "'direnv' command not found. Cannot automatically set up project environment with direnv."
    print_info "To set up manually: create a Python virtual environment in '${OMNIAPP_DIR}', activate it, then run 'pip install -r requirements.txt'."
fi

# Offer to run the Xonsh setup script if it was included
if [[ "${components_to_install[user_shell]}" == "yes" ]] && [ -f "${OMNIAPP_DIR}/user_shell_setup/setup_omnitide_user_shell.sh" ]; then
    prompt_yes_no "Do you want to run the Xonsh user environment setup script ('${OMNIAPP_DIR}/user_shell_setup/setup_omnitide_user_shell.sh') now? (This configures your global Xonsh, not the project venv)"
    if [[ "$REPLY" == "yes" ]]; then
        bash "${OMNIAPP_DIR}/user_shell_setup/setup_omnitide_user_shell.sh"
    fi
fi


print_header "Omniapp Suite Bootstrap Complete!"
echo "Your project is set up in: ${OMNIAPP_DIR}"
echo "Please review the README.md in that directory for next steps on using the components."
echo "Key actions:"
echo "1. If Xonsh setup was run or PATH was modified, ${YELLOW}restart your terminal/shell session.${NC}"
echo "2. Navigate to the Omniapp directory: ${CYAN}cd ${OMNIAPP_DIR}${NC}"
echo "3. Ensure direnv activates the environment (you might see messages from .envrc)."
echo "   If it's your first time with direnv, you might need to run ${CYAN}direnv allow .${NC} first."
echo "4. If dependencies weren't installed during bootstrap, run: ${CYAN}pip install -r requirements.txt${NC} (while the venv is active)."
echo "--------------------------------------------------------------------"

exit 0
