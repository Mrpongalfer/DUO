#!/usr/bin/env python3
# Omnitide Interactive CLI - Main Application
# For The Supreme Master Architect Alix Feronti

import typer
from typing_extensions import Annotated
import json
import os
from pathlib import Path
import sys

# Assuming omnitide_cli_config_manager.py is in the same directory or Python path
# For package structure, adjust import if needed: from . import config_manager as cli_config_mgr
try:
    from . import config_manager as cli_config_mgr  # Relative import for package
except (
    ImportError
):  # Fallback for running directly or if structure is flat during bootstrap
    import config_manager as cli_config_mgr


# --- Global Config Variable ---
# This will be loaded once when the CLI starts or when config commands are run.
APP_CONFIG = cli_config_mgr.load_config()

# --- Typer Application Initialization ---
app = typer.Typer(
    name="omnitide-cli",
    help="Omnitide Nexus Interactive CLI: Orchestrate Scribe and ExWork agents, and more.",
    add_completion=True,
    no_args_is_help=True,
)

config_app = typer.Typer(name="config", help="Manage Omnitide CLI configuration.")
app.add_typer(config_app)

templates_app = typer.Typer(name="templates", help="Manage and use Omnitide templates.")
app.add_typer(templates_app)

scribe_app = typer.Typer(name="scribe", help="Run Scribe validation tasks.")
app.add_typer(scribe_app)

exwork_app = typer.Typer(name="exwork", help="Run ExWork execution tasks.")
app.add_typer(exwork_app)

workflow_app = typer.Typer(
    name="workflow", help="Run combined Scribe & ExWork workflows."
)
app.add_typer(workflow_app)

logs_app = typer.Typer(name="logs", help="View execution logs and reports.")
app.add_typer(logs_app)


# --- Helper Function for Path Validation ---
def _validate_agent_path(agent_name: str, path_str: str) -> Optional[Path]:
    """Validates if an agent script path exists and is a file."""
    # Resolve path relative to omniapp root if not absolute
    omniapp_root = Path(
        APP_CONFIG.get("omniapp_root_dir", Path.cwd())
    )  # Get omniapp_root from config or assume CWD
    p = Path(path_str)
    if not p.is_absolute():
        # If omniapp_root is not an empty string and path_str is relative
        if str(omniapp_root) != ".":  # Check if omniapp_root is actually set
            p = (omniapp_root / p).resolve()
        else:  # if omniapp_root is essentially CWD or not set, resolve path_str directly
            p = p.resolve()

    if not p.is_file():
        typer.secho(
            f"ERROR: {agent_name} script not found at '{p}'. Resolved from input '{path_str}'. Configure path using 'omnitide-cli config set {agent_name.lower().replace(' ', '_').replace('agent','').strip()}_agent_path <path>'.",
            fg=typer.colors.RED,
        )
        return None
    return p


def _get_python_executable() -> str:
    """Gets the current Python interpreter's executable path."""
    # Prefer python from current venv if active
    venv_python = os.environ.get("VIRTUAL_ENV")
    if venv_python:
        python_exe = Path(venv_python) / "bin" / "python"
        if python_exe.is_file():
            return str(python_exe)
    return sys.executable or "python3"  # Fallback


# --- Configuration Commands (config_app) ---
@config_app.command("show", help="Show current Omnitide CLI configuration.")
def config_show():
    """Displays the current configuration."""
    global APP_CONFIG
    APP_CONFIG = cli_config_mgr.load_config()  # Ensure latest
    typer.secho("Current Omnitide CLI Configuration:", fg=typer.colors.CYAN)
    config_to_display = APP_CONFIG.copy()
    # Add omniapp_root_dir for display if it was used implicitly
    config_to_display.setdefault(
        "omniapp_root_dir (effective)",
        str(Path(APP_CONFIG.get("omniapp_root_dir", Path.cwd())).resolve()),
    )
    typer.echo(json.dumps(config_to_display, indent=2))
    typer.secho(
        f"\nConfig file location: {cli_config_mgr.CONFIG_FILE_PATH}",
        fg=typer.colors.YELLOW,
    )


@config_app.command(
    "set",
    help="Set a configuration value (e.g., omnitide-cli config set scribe_agent_path agents/scribe.py).",
)
def config_set(
    key: Annotated[
        str,
        typer.Argument(
            help=f"Configuration key. Choices (among others): {', '.join(cli_config_mgr.DEFAULT_CONFIG.keys())}"
        ),
    ],
    value: Annotated[str, typer.Argument(help="Value for the configuration key.")],
):
    """Sets a specific configuration key-value pair."""
    global APP_CONFIG
    if (
        key not in APP_CONFIG
        and key not in cli_config_mgr.DEFAULT_CONFIG
        and key != "omniapp_root_dir"
    ):
        # Allow setting new keys, but warn if not in defaults (except omniapp_root_dir)
        typer.secho(
            f"Warning: '{key}' is not a predefined configuration key. Adding it.",
            fg=typer.colors.YELLOW,
        )

    APP_CONFIG[key] = value
    cli_config_mgr.save_config(APP_CONFIG)
    typer.secho(
        f"Configuration updated: '{key}' set to '{value}'.", fg=typer.colors.GREEN
    )


@config_app.command(
    "wizard", help="Interactive wizard to configure essential paths for Omnitide CLI."
)
def config_wizard(
    omniapp_root: Annotated[
        Optional[Path],
        typer.Option(
            help="Specify the Omniapp project root directory.", show_default=False
        ),
    ] = None,
):
    """Interactive wizard to set essential paths if config is fresh or needs update."""
    global APP_CONFIG
    typer.secho("Omnitide CLI Configuration Wizard", fg=typer.colors.MAGENTA)

    if omniapp_root:
        resolved_omniapp_root = omniapp_root.resolve()
    else:
        resolved_omniapp_root = Path(
            typer.prompt(
                "Enter the absolute path to your Omniapp project root directory",
                default=APP_CONFIG.get("omniapp_root_dir", str(Path.cwd().resolve())),
            )
        ).resolve()

    APP_CONFIG["omniapp_root_dir"] = str(resolved_omniapp_root)

    typer.secho(
        f"Omniapp project root set to: {resolved_omniapp_root}", fg=typer.colors.BLUE
    )

    # Default paths will be relative to this omniapp_root_dir
    APP_CONFIG["project_working_directory"] = str(
        resolved_omniapp_root
    )  # Default CWD for agents is project root

    APP_CONFIG["scribe_agent_path"] = typer.prompt(
        "Enter path to Scribe Agent script (relative to Omniapp root, e.g., agents/scribe.py)",
        default=APP_CONFIG.get("scribe_agent_path", "agents/scribe.py"),
    )
    APP_CONFIG["exwork_agent_path"] = typer.prompt(
        "Enter path to ExWork Agent script (relative to Omniapp root, e.g., agents/exworkagent.py)",
        default=APP_CONFIG.get("exwork_agent_path", "agents/exworkagent.py"),
    )
    APP_CONFIG["omnitide_templates_path"] = typer.prompt(
        "Enter path to omnitide_templates.json (relative to Omniapp root, e.g., agents/omnitide_templates.json)",
        default=APP_CONFIG.get(
            "omnitide_templates_path", "agents/omnitide_templates.json"
        ),
    )
    APP_CONFIG["scribe_config_toml_path"] = typer.prompt(
        "Enter default path to Scribe's .scribe.toml (can be relative to project_working_directory or absolute)",
        default=APP_CONFIG.get(
            "scribe_config_toml_path", ".scribe.toml"
        ),  # This is usually in the target project, not omniapp root.
    )

    # Validate paths after input, relative to omniapp_root_dir
    for key_path in [
        "scribe_agent_path",
        "exwork_agent_path",
        "omnitide_templates_path",
    ]:
        p_val = APP_CONFIG[key_path]
        abs_p = (
            resolved_omniapp_root / p_val
            if not Path(p_val).is_absolute()
            else Path(p_val)
        )
        if not abs_p.exists():
            typer.secho(
                f"Warning: Path for '{key_path}': '{abs_p}' does not currently exist.",
                fg=typer.colors.YELLOW,
            )

    cli_config_mgr.save_config(APP_CONFIG)
    typer.secho(
        "Configuration wizard completed. Settings saved to CLI config.",
        fg=typer.colors.GREEN,
    )


# --- Main CLI Callback & Initialization ---
@app.callback()
def main_cli_callback(ctx: typer.Context):
    """
    Omnitide Nexus Interactive CLI.
    Manages Scribe, ExWork, templates, and more.
    Run 'omnitide-cli config wizard' on first use or to update core paths.
    """
    global APP_CONFIG
    APP_CONFIG = cli_config_mgr.load_config()

    # If omniapp_root_dir is not set, or if critical paths are still default and might be incorrect.
    omniapp_root_configured = APP_CONFIG.get("omniapp_root_dir")
    is_likely_unconfigured = not omniapp_root_configured or APP_CONFIG.get(
        "scribe_agent_path"
    ) == cli_config_mgr.DEFAULT_CONFIG.get("scribe_agent_path")

    if (
        is_likely_unconfigured
        and ctx.invoked_subcommand not in ["config", None]
        and (
            not hasattr(ctx, "parent")
            or not ctx.parent
            or ctx.parent.invoked_subcommand != "config"
        )
    ):
        typer.secho(
            "WARNING: Omnitide CLI might be using default or unconfigured paths. "
            "Run 'omnitide-cli config wizard' to set up your Omniapp project root and agent paths.",
            fg=typer.colors.YELLOW,
        )


# --- Placeholder command modules (to be populated later) ---
# from .commands import exwork_cmds, scribe_cmds, template_cmds, log_cmds
# app.add_typer(exwork_cmds.app, name="exwork")
# app.add_typer(scribe_cmds.app, name="scribe")
# ...etc.


@app.command("hello", help="A simple hello command for testing.")
def hello_test(name: str = "Architect"):
    typer.echo(f"Hello {name}, Omnitide CLI is operational!")


if __name__ == "__main__":
    # This makes the CLI runnable directly for development.
    # For distribution, entry points via pyproject.toml would be used.

    # Initial check for config file and offer wizard
    if not cli_config_mgr.CONFIG_FILE_PATH.exists():
        typer.secho(
            f"No Omnitide CLI configuration file found at {cli_config_mgr.CONFIG_FILE_PATH}.",
            fg=typer.colors.YELLOW,
        )
        if typer.confirm(
            "Would you like to run the initial configuration wizard now?", default=True
        ):
            # Simulate calling 'config wizard'
            # In a real Typer app, you might structure this differently or let the user run it.
            # For bootstrap, ensuring it runs if needed is good.
            try:
                # This is a simplified way to call it.
                # Typer usually handles context.
                config_wizard(omniapp_root=None)  # Will prompt for omniapp_root
                APP_CONFIG = cli_config_mgr.load_config()  # Reload after wizard
                typer.secho(
                    "Initial configuration complete. Please re-run your intended command.",
                    fg=typer.colors.GREEN,
                )
                # It's cleaner to ask user to re-run than to try to re-invoke Typer's main loop here.
                sys.exit(0)
            except typer.Exit:
                pass  # User might have exited wizard
            except Exception as e:
                print_error(f"Error running config wizard automatically: {e}")

    app()
