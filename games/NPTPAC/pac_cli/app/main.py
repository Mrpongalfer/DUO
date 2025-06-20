#!/usr/bin/env python3
# PAC - Prompt Assembler CLI / Nexus Operations Console
# Main application file (Typer/Rich based)
# Version: 2.0
# Generated on: 2025-05-11T16:04:38.845390+00:00


# --- Local Core Imports ---
# Ensure pac_cli/app is discoverable (e.g. via PYTHONPATH, or if run with 'python -m app.main' from pac_cli)
# Poetry's 'poetry run npac' or the launcher script should handle this.
# --- Local Core Imports ---
# --- Robust Import Logic for CLI/Module/Script Execution ---
import importlib.util
import json  # For loading/parsing JSON from Ex-Work templates or agent output
import logging
import os
import shlex  # For agent command construction if needed, though AgentRunner handles it
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.json import JSON  # For pretty printing JSON output from agents

from games.NPTPAC.pac_cli.app.commands import (
    lily_cmds,  # Import the Lily module
    ner_cmds,  # Import the module
)

try:
    from games.NPTPAC.pac_cli.app.commands import lily_cmds
    from games.NPTPAC.pac_cli.app.commands.ner_cmds import ner_app
    from games.NPTPAC.pac_cli.app.core.agent_runner import ExWorkAgentRunner, ScribeAgentRunner
    from games.NPTPAC.pac_cli.app.core.config_manager import ConfigManager
    from games.NPTPAC.pac_cli.app.core.llm_interface import LLMInterface
    from games.NPTPAC.pac_cli.app.core.ner_handler import NERHandler
    from games.NPTPAC.pac_cli.app.utils import ui_utils
except ImportError:
    try:
        from commands import lily_cmds
        from commands.ner_cmds import ner_app
        from games.nexus_omniengine_v3.core.agent_runner import ExWorkAgentRunner, ScribeAgentRunner
        from games.nexus_omniengine_v3.core.config_manager import ConfigManager
        from games.nexus_omniengine_v3.core.llm_interface import LLMInterface
        from games.nexus_omniengine_v3.core.ner_handler import NERHandler
        from utils import ui_utils
    except ImportError:
        # Try adding parent directory to sys.path for direct script execution
        sys.path.append(str(Path(__file__).resolve().parent))
        sys.path.append(str(Path(__file__).resolve().parent.parent))
        try:
            ConfigManager = importlib.util.find_spec("core.config_manager")
            if ConfigManager is not None:
                from commands import lily_cmds
                from commands.ner_cmds import ner_app
                from games.nexus_omniengine_v3.core.agent_runner import ExWorkAgentRunner, ScribeAgentRunner
                from games.nexus_omniengine_v3.core.config_manager import ConfigManager
                from games.nexus_omniengine_v3.core.llm_interface import LLMInterface
                from games.nexus_omniengine_v3.core.ner_handler import NERHandler
                from utils import ui_utils
            else:
                raise ImportError
        except ImportError as e:
            print(
                "[FATAL] Could not import required modules. Please run this script from the 'pac_cli' directory using either 'python3 -m app.main' or 'python3 app/main.py'. If the problem persists, check your PYTHONPATH and ensure all dependencies are installed.",
                file=sys.stderr,
            )
            print(f"Import error details: {e}", file=sys.stderr)
            sys.exit(1)


# --- Application Setup & Configuration ---
APP_NAME: str = "Nexus Prompt Assembler CLI (PAC)"
APP_VERSION: str = "2.0"  # From npt_generator.py

# NPT_BASE_DIR is critical. Launcher script (npac) sets this environment variable.
# Fallback if run directly (e.g., python app/main.py during dev)
NPT_BASE_DIR_ENV_VAR_NAME_IN_PAC: str = (
    "NPT_BASE_DIR"  # Literal string name from generator
)
NPT_BASE_DIR: Path
try:
    NPT_BASE_DIR = Path(os.environ[NPT_BASE_DIR_ENV_VAR_NAME_IN_PAC]).resolve()
except KeyError:
    # Fallback for direct execution (e.g. from IDE without launcher)
    NPT_BASE_DIR = (
        Path(__file__).resolve().parent.parent.parent
    )  # app -> pac_cli -> NPT_BASE_DIR
    # This print uses f-string interpolation correctly within main.py's scope
    print(
        f"[WARN] {NPT_BASE_DIR_ENV_VAR_NAME_IN_PAC} env var not set. Defaulting NPT_BASE_DIR to: {NPT_BASE_DIR}",
        file=sys.stderr,
    )

NER_DIR_NAME_CONST_IN_PAC: str = "ner_repository"
PAC_CONFIG_DIR_NAME_CONST_IN_PAC: str = "config"
SETTINGS_FILENAME_CONST_IN_PAC: str = "settings.toml"

# --- Logging Setup ---
# TODO, Architect: Enhance this logging setup.
# - Read log level and log file path from PAC's settings.toml.
# - Allow configuring different log formats.
# - Potentially use Rich a more Rich-integrated logger.
# For now, basic stderr logging, configurable level by environment for dev.
LOG_LEVEL_ENV_VAR = "PAC_LOG_LEVEL"
DEFAULT_PAC_LOG_LEVEL = "INFO"
pac_log_level_str = os.environ.get(LOG_LEVEL_ENV_VAR, DEFAULT_PAC_LOG_LEVEL).upper()
numeric_log_level = getattr(logging, pac_log_level_str, logging.INFO)

logging.basicConfig(
    level=numeric_log_level,
    format="%(asctime)s [%(name)-12s] [%(levelname)-7s] %(module)s:%(lineno)d - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stderr)],  # Output to stderr
)
logger = logging.getLogger("PAC")  # Main PAC application logger
# Example: logger.info("PAC application starting...")

# --- Global Instances (initialized in main_callback) ---
config_manager: Optional[ConfigManager] = None
ner_handler: Optional[NERHandler] = None
ex_work_runner: Optional[ExWorkAgentRunner] = None
scribe_runner: Optional[ScribeAgentRunner] = None
llm_interface: Optional[LLMInterface] = None
console = ui_utils.console  # Use the shared console from ui_utils

# --- Typer Application Definition ---
app = typer.Typer(
    name="npac",
    help=f"{APP_NAME} v{APP_VERSION} - Omnitide Nexus Command Console.",  # Uses APP_NAME, APP_VERSION from this file
    rich_markup_mode="markdown",
    no_args_is_help=True,
    add_completion=True,  # Enable shell completion support
)


# --- Main Callback (Initialization & Context Setup) ---
@app.callback(invoke_without_command=True)
def main_callback(
    ctx: typer.Context,
    # Add global options if needed, e.g., --verbose, --config-file override
    # verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output (DEBUG logging)."),
    # config_override: Optional[Path] = typer.Option(None, "--pac-config", help="Override path to PAC settings.toml file.")
):
    """
    Main callback for PAC. Initializes core components and sets up context.
    Ensures NPT base and NER directories exist before any command runs.
    """
    global config_manager, ner_handler, ex_work_runner, scribe_runner, llm_interface

    # if verbose: # Example for a global --verbose flag
    #     logging.getLogger("PAC").setLevel(logging.DEBUG)
    #     logging.getLogger("app").setLevel(logging.DEBUG) # Assuming submodules use this prefix
    #     logger.debug("Verbose mode enabled by CLI flag.")

    # Display a startup banner (optional, using APP_NAME and APP_VERSION defined above)
    # Commented out for cleaner startup, but you can enable it.
    # ui_utils.console.rule(f"[bold magenta]{APP_NAME} v{APP_VERSION}[/bold magenta]")

    if ctx.invoked_subcommand is None and not any(
        arg in sys.argv for arg in ["--help", "--version"]
    ):
        # Default action if no subcommand: show system check or a welcome message.
        # For now, Typer's no_args_is_help=True will show help.
        # Consider calling 'system check' or a custom dashboard here.
        logger.debug("No subcommand invoked, Typer will show help.")
        pass  # Typer shows help

    # Critical: Ensure NPT_BASE_DIR is valid
    if not NPT_BASE_DIR.is_dir():
        console.print(
            f"[bold red]CRITICAL ERROR: NPT Base Directory not found at '{NPT_BASE_DIR}'![/bold red]"
        )
        console.print(
            "This directory is essential. Check NPT_BASE_DIR env var or bootstrap process."
        )
        raise typer.Exit(code=101)

    # Initialize ConfigManager
    try:
        # pac_settings_file_to_use = config_override if config_override else SETTINGS_FILENAME_CONST_IN_PAC
        # config_manager = ConfigManager(npt_base_dir=NPT_BASE_DIR, config_filename=pac_settings_file_to_use)
        config_manager = ConfigManager(
            npt_base_dir=NPT_BASE_DIR, config_filename=SETTINGS_FILENAME_CONST_IN_PAC
        )
        logger.info(
            f"ConfigManager initialized. Settings loaded from: {config_manager.settings_file_path}"
        )
    except Exception as e:
        console.print(
            f"[bold red]CRITICAL ERROR: Failed to initialize PAC ConfigManager: {e}[/bold red]"
        )
        logger.critical(f"Failed to initialize ConfigManager: {e}", exc_info=True)
        raise typer.Exit(code=102)

    # NER Path (can be overridden by config "general.default_ner_path")
    ner_path_str_from_config = config_manager.get(
        "general.default_ner_path", str(NPT_BASE_DIR / NER_DIR_NAME_CONST_IN_PAC)
    )
    ner_actual_path = Path(ner_path_str_from_config).resolve()
    if not ner_actual_path.is_dir():
        console.print(
            f"[bold red]CRITICAL ERROR: NER Directory not found at '{ner_actual_path}'![/bold red]"
        )
        console.print(
            "(Path from config 'general.default_ner_path' or default NPT structure)."
        )
        console.print(
            f"Please check path in {config_manager.settings_file_path} or ensure NER exists."
        )
        raise typer.Exit(code=103)

    # Initialize core handlers/runners
    try:
        ner_handler = NERHandler(
            ner_root_path=ner_actual_path, config_manager=config_manager
        )
        ex_work_runner = ExWorkAgentRunner(
            config_manager=config_manager
        )  # Gets agent path from config
        scribe_runner = ScribeAgentRunner(
            config_manager=config_manager
        )  # Gets agent path from config
        llm_interface = LLMInterface(
            config_manager=config_manager, ex_work_runner=ex_work_runner
        )
    except Exception as e:
        console.print(
            f"[bold red]CRITICAL ERROR: Failed to initialize core PAC handlers (NER, Agents, LLM): {e}[/bold red]"
        )
        logger.critical(f"Failed to initialize core handlers: {e}", exc_info=True)
        raise typer.Exit(code=104)

    # Make instances available to subcommands via Typer context
    ctx.meta["config_manager"] = config_manager
    ctx.meta["ner_handler"] = ner_handler
    ctx.meta["ex_work_runner"] = ex_work_runner
    ctx.meta["scribe_runner"] = scribe_runner
    ctx.meta["llm_interface"] = llm_interface

    logger.info(
        f"PAC Core Components Initialized. NPT Base: {NPT_BASE_DIR}, NER Root: {ner_actual_path}"
    )
    # Log agent paths from config for easier debugging if they are not found later
    logger.debug(
        f"Configured Ex-Work Agent Path: {config_manager.get('agents.ex_work_agent_path', 'Not Set')}"
    )
    logger.debug(
        f"Configured Scribe Agent Path: {config_manager.get('agents.scribe_agent_path', 'Not Set')}"
    )


app.add_typer(ner_cmds.ner_app)  # Add the ner_app instance FROM ner_cmds.py


app.add_typer(lily_cmds.lily_app)  # Add the lily_app instance FROM lily_cmds.py


# --- ONAP Command Group (Implementation using NERHandler & LLMInterface) ---
# (Re-define onap_app if it wasn't added earlier, or get from app.add_typer)
onap_app = typer.Typer(
    name="onap",
    help="Assemble and manage Omnitide Nexus Activation Protocol components.",
    no_args_is_help=True,
)
app.add_typer(onap_app)  # Ensure it's added to main app


@onap_app.command(
    "assemble",
    help="Interactively assemble an ONAP prompt from NER/01_ONAP_R3_COMPONENTS.",
)
def onap_assemble_cmd(
    ctx: typer.Context,
    # TODO, Architect: Add --profile <name> to load/save assembly configurations
    copy_to_clipboard: bool = typer.Option(
        True, "--clip/--no-clip", "-x", help="Copy assembled prompt to clipboard."
    ),
    output_file: Optional[Path] = typer.Option(
        None,
        "--out",
        "-o",
        help="Save assembled prompt to file.",
        resolve_path=True,
        dir_okay=False,
        writable=True,
    ),
):
    """Assembles ONAP prompt components from NER and provides output options."""
    current_ner_handler: NERHandler = ctx.meta["ner_handler"]
    onap_components_dir_relative = "01_ONAP_R3_COMPONENTS"  # Standardized path

    onap_items_data = current_ner_handler.list_items_in_category(
        onap_components_dir_relative
    )
    onap_files = sorted(
        [
            item["name"]
            for item in onap_items_data
            if item["type"] == "file" and item["name"].lower().endswith((".md", ".txt"))
        ]
    )

    if not onap_files:
        ui_utils.console.print(
            f"[yellow]No ONAP component files (.md, .txt) found in NER at '{onap_components_dir_relative}'.[/yellow]"
        )
        return

    ui_utils.console.print(
        f"Found {len(onap_files)} ONAP component(s) in '{onap_components_dir_relative}'."
    )
    selected_parts_names = ui_utils.fzf_select(
        onap_files,
        prompt="Select ONAP parts to assemble (multi-select with Tab, Enter to confirm):",
        multi=True,
    )

    if not selected_parts_names:
        ui_utils.console.print("[yellow]No ONAP parts selected for assembly.[/yellow]")
        return

    assembled_prompt_content = []
    ui_utils.console.print(
        "\nAssembling from selected ONAP parts (in order of selection):"
    )
    for (
        part_name
    ) in selected_parts_names:  # fzf usually returns in selection order if --no-sort
        part_relative_path_to_ner = f"{onap_components_dir_relative}/{part_name}"
        ui_utils.console.print(f"  -> [cyan]{part_name}[/cyan]")
        content = current_ner_handler.get_item_content(part_relative_path_to_ner)
        if content:
            assembled_prompt_content.append(content)
        else:
            ui_utils.console.print(
                f"    [yellow]Warning: Could not read content for {part_name}.[/yellow]"
            )

    if not assembled_prompt_content:
        ui_utils.console.print(
            "[red]No content assembled (all selected files were empty or unreadable).[/red]"
        )
        return

    # TODO, Architect: Consider a more sophisticated separator or structure from NER itself.
    final_prompt_str = "\n\n---\nPROMPT_PART_SEPARATOR\n---\n\n".join(
        assembled_prompt_content
    )
    final_prompt_str += "\n\n--- End of Assembled Omnitide Nexus Activation Context ---"

    ui_utils.display_panel(
        final_prompt_str,
        title="Assembled ONAP Prompt",
        border_style="green",
        expand=False,
        padding_val=(1, 1),
    )

    if copy_to_clipboard:
        # TODO, Architect: Implement a robust cross-platform clipboard copy utility in ui_utils
        # For now, conceptual call:
        # if ui_utils.copy_to_clipboard(final_prompt_str):
        #    ui_utils.console.print("[green]Prompt copied to clipboard.[/green]")
        # else:
        #    ui_utils.console.print("[yellow]Failed to copy to clipboard. Manual copy may be needed.[/yellow]")
        ui_utils.console.print(
            "[italic yellow]TODO: Implement clipboard copy.[/italic yellow]"
        )

    if output_file:
        try:
            output_file.parent.mkdir(
                parents=True, exist_ok=True
            )  # Ensure parent dir exists
            output_file.write_text(final_prompt_str, encoding="utf-8")
            ui_utils.console.print(
                f"[green]Assembled ONAP prompt saved to: {output_file.resolve()}[/green]"
            )
        except OSError as e:
            ui_utils.console.print(
                f"[red]Error saving assembled ONAP prompt to '{output_file}': {e}[/red]"
            )
            logger.error(
                f"Error saving ONAP prompt to file {output_file}: {e}", exc_info=True
            )


# TODO, Architect: Add ONAP command: `onap send <assembled_prompt_file_or_template_name> [--llm-profile <name>]`
# This would use the llm_interface.send_prompt().

# --- Ex-Work Command Group (Implementation using ExWorkAgentRunner) ---
exwork_app = typer.Typer(
    name="exwork", help="Orchestrate Agent Ex-Work tasks.", no_args_is_help=True
)
app.add_typer(exwork_app)


@exwork_app.command(
    "run", help="Run an Ex-Work instruction block from template, file, or string."
)
def exwork_run_cmd(
    ctx: typer.Context,
    template_name: Optional[str] = typer.Option(
        None,
        "--template",
        "-t",
        help="Name of Ex-Work template from NER (e.g., 'basic_echo' or 'basic_echo.exwork.json').",
        show_default=False,
    ),
    json_file: Optional[Path] = typer.Option(
        None,
        "--file",
        "-f",
        help="Path to an Ex-Work JSON instruction file.",
        resolve_path=True,
        exists=True,
        dir_okay=False,
        show_default=False,
    ),
    json_string: Optional[str] = typer.Option(
        None,
        "--json",
        "-j",
        help="Direct Ex-Work JSON instruction string.",
        show_default=False,
    ),
    project_path_str: str = typer.Option(
        ".",
        "--project-path",
        "-P",
        help="Project context path for Ex-Work execution (CWD for agent).",
        show_default=True,
    ),
    # TODO, Architect: Add --param "key=value" --param "key2=value2" for dynamic parameterization
    # param_overrides: Optional[List[str]] = typer.Option(None, "--param", help="Override template parameters, format: 'key=value'. Repeat for multiple.")
):
    """Loads and runs an Ex-Work JSON instruction block."""
    runner: ExWorkAgentRunner = ctx.meta["ex_work_runner"]
    current_ner_handler: NERHandler = ctx.meta["ner_handler"]
    config_mgr: ConfigManager = ctx.meta[
        "config_manager"
    ]  # For default project path if needed

    if not runner.agent_script_command:  # Checks if ExWork agent path is configured
        ui_utils.console.print(
            "[bold red]Ex-Work Agent not configured in PAC settings (agents.ex_work_agent_path). Cannot run.[/bold red]"
        )
        raise typer.Exit(code=1)

    instruction_json_str: Optional[str] = None
    instruction_source_description: str = "Unknown Source"

    project_path = Path(project_path_str).resolve()
    if not project_path.is_dir():
        ui_utils.console.print(
            f"[bold red]Ex-Work project path '{project_path}' is not a valid directory.[/bold red]"
        )
        raise typer.Exit(code=1)

    if template_name:
        base_name = (
            template_name
            if template_name.endswith(".exwork.json")
            else f"{template_name}.exwork.json"
        )
        # Standard path for Ex-Work templates in NER
        template_rel_path_in_ner = (
            f"06_AGENT_BLUEPRINTS/ex_work_agent/templates/{base_name}"
        )
        instruction_json_str = current_ner_handler.get_item_content(
            template_rel_path_in_ner
        )
        if not instruction_json_str:
            ui_utils.console.print(
                f"[red]Ex-Work template '{base_name}' not found in NER at '{template_rel_path_in_ner}'.[/red]"
            )
            # TODO, Architect: Offer fzf selection from available Ex-Work templates if not found.
            raise typer.Exit(code=1)
        instruction_source_description = f"NER Template: {template_rel_path_in_ner}"
        ui_utils.console.print(
            f"Loaded Ex-Work instruction from {instruction_source_description}"
        )
        # TODO, Architect: Implement dynamic parameter parsing and replacement here.
        # 1. Parse instruction_json_str to get "parameters" field (list of dicts).
        # 2. For each param, use ui_utils.get_text_input to prompt user, using "prompt" and "default" from param def.
        # 3. Replace "{placeholder_name}" in instruction_json_str with user-provided values.
        #    Be careful with JSON string escaping if doing direct string replacement. Better to parse JSON,
        #    walk the structure, and replace values, then re-serialize to JSON.
        ui_utils.console.print(
            "[italic yellow]TODO: Implement dynamic parameter replacement for template placeholders (e.g., {my_var}).[/italic yellow]"
        )

    elif json_file:
        instruction_json_str = json_file.read_text("utf-8")
        instruction_source_description = f"File: {json_file}"
        ui_utils.console.print(
            f"Loaded Ex-Work instruction from {instruction_source_description}"
        )
    elif json_string:
        instruction_json_str = json_string
        instruction_source_description = "Direct JSON String Input"
        ui_utils.console.print("Using Ex-Work instruction from direct JSON string.")
    else:
        # TODO, Architect: If no source, default to interactive selection of a template from NER.
        ui_utils.console.print(
            "[red]No Ex-Work instruction source. Use --template, --file, or --json, or implement interactive template selection.[/red]"
        )
        raise typer.Exit(code=1)

    if not instruction_json_str:  # Should be caught above, but defensive.
        ui_utils.console.print(
            f"[red]Failed to load Ex-Work instruction content from '{instruction_source_description}'.[/red]"
        )
        raise typer.Exit(code=1)

    # Validate basic JSON structure
    try:
        parsed_instr_for_validation = json.loads(instruction_json_str)
        if (
            not isinstance(parsed_instr_for_validation, dict)
            or "actions" not in parsed_instr_for_validation
        ):
            raise ValueError("JSON must be an object with an 'actions' key.")
    except (json.JSONDecodeError, ValueError) as e:
        ui_utils.console.print(
            f"[bold red]Invalid JSON structure for Ex-Work instruction from '{instruction_source_description}': {e}[/bold red]"
        )
        ui_utils.display_syntax(
            instruction_json_str, "json", title="Invalid Ex-Work JSON Content"
        )
        raise typer.Exit(code=1)

    desc_preview = parsed_instr_for_validation.get("description", "N/A")
    num_actions_preview = len(parsed_instr_for_validation.get("actions", []))
    ui_utils.display_panel(
        f"Source: {instruction_source_description}\nDescription: {desc_preview}\nActions: {num_actions_preview}\nProject CWD: {project_path}",
        title="Confirm Ex-Work Execution",
        border_style="yellow",
    )

    if not ui_utils.get_user_confirmation(
        "Proceed with Ex-Work execution?", default_yes=False
    ):
        ui_utils.console.print("Ex-Work execution cancelled by Architect.")
        raise typer.Exit(code=0)  # Graceful exit

    ui_utils.console.print("Executing Ex-Work agent...")
    # ExWorkAgentRunner.execute_instruction_block returns (bool_success, dict_output_payload)
    success, output_payload = runner.execute_instruction_block(
        instruction_json_str, project_path
    )

    # ui_utils.print_agent_output handles displaying the structured JSON output from Ex-Work nicely.
    ui_utils.print_agent_output(
        "Ex-Work",
        success,
        output_payload,
        output_payload.get(
            "raw_stdout_if_error"
        ),  # Conceptual, runner returns parsed dict
        output_payload.get("raw_stderr_if_error"),
    )

    if not success or (
        isinstance(output_payload, dict)
        and not output_payload.get("overall_success", True)
    ):
        ui_utils.console.print(
            "[bold red]Ex-Work execution reported failure.[/bold red]"
        )
        # TODO, Architect: Implement call to DIAGNOSE_ERROR action of Ex-Work here if desired,
        # using output_payload (or its relevant parts) as input to the diagnosis prompt.
        # diagnosis_success, diagnosis_result = runner.execute_instruction_block(construct_diagnose_error_json(...), project_path)
        raise typer.Exit(code=1)
    else:
        ui_utils.console.print(
            "[bold green]Ex-Work execution reported success.[/bold green]"
        )


# TODO, Architect: Add more Ex-Work commands:
# - exwork list-templates [--category <...>]
# - exwork validate-template <template_path_or_ner_ref> (needs JSON schema for Ex-Work instructions)
# - exwork new-template [--actions <...>] [--editor] (interactive template builder)

# --- Scribe Command Group (Implementation using ScribeAgentRunner) ---
scribe_app = typer.Typer(
    name="scribe", help="Orchestrate Project Scribe validations.", no_args_is_help=True
)
app.add_typer(scribe_app)


@scribe_app.command("validate", help="Run Project Scribe validation gauntlet.")
def scribe_validate_cmd(
    ctx: typer.Context,
    target_dir_str: str = typer.Option(
        ...,
        "--project-path",
        "-P",
        help="Target project directory for Scribe validation (must exist).",
        resolve_path=True,
        exists=True,
        file_okay=False,
        dir_okay=True,
        rich_help_panel="Scribe Inputs",
    ),
    code_file_str: str = typer.Option(
        ...,
        "--code-file",
        "-c",
        help="Path to the (temporary or actual) code file Scribe should apply/validate (must exist).",
        resolve_path=True,
        exists=True,
        dir_okay=False,
        rich_help_panel="Scribe Inputs",
    ),
    target_file_rel: str = typer.Option(
        ...,
        "--target-file",
        "-t",
        help="Relative path (from --project-path) where code from --code-file applies or is located.",
        rich_help_panel="Scribe Inputs",
    ),
    profile_name: Optional[str] = typer.Option(
        None,
        "--profile",
        help="Scribe profile name from NER (e.g., 'default' or 'default.scribe.toml'). If None, Scribe uses its internal default.",
        show_default=False,
        rich_help_panel="Scribe Configuration",
    ),
    commit: bool = typer.Option(
        False,
        "--commit",
        help="Attempt Git commit if Scribe validation passes.",
        rich_help_panel="Scribe Behavior",
    ),
    skip_deps: bool = typer.Option(
        False,
        "--skip-deps",
        help="Pass --skip-deps to Scribe agent.",
        rich_help_panel="Scribe Behavior",
    ),
    skip_tests: bool = typer.Option(
        False,
        "--skip-tests",
        help="Pass --skip-tests to Scribe agent.",
        rich_help_panel="Scribe Behavior",
    ),
    skip_review: bool = typer.Option(
        False,
        "--skip-review",
        help="Pass --skip-review to Scribe agent.",
        rich_help_panel="Scribe Behavior",
    ),
):
    # Runs the Scribe agent with specified parameters.
    runner: ScribeAgentRunner = ctx.meta["scribe_runner"]
    current_ner_handler: NERHandler = ctx.meta["ner_handler"]
    config_mgr: ConfigManager = ctx.meta["config_manager"]

    if not runner.agent_script_command:
        ui_utils.console.print(
            "[bold red]Scribe Agent not configured in PAC settings (agents.scribe_agent_path). Cannot run.[/bold red]"
        )
        raise typer.Exit(code=1)

    target_dir = Path(target_dir_str)  # Already resolved and checked by Typer
    code_file = Path(code_file_str)  # Already resolved and checked by Typer

    scribe_profile_abs_path: Optional[Path] = None
    if profile_name:
        base_name = (
            profile_name if profile_name.endswith(".toml") else f"{profile_name}.toml"
        )
        # Standard path for Scribe profiles in NER
        profile_rel_path_in_ner = (
            f"06_AGENT_BLUEPRINTS/scribe_agent/profiles/{base_name}"
        )
        potential_profile_path = current_ner_handler.ner_root / profile_rel_path_in_ner
        if potential_profile_path.is_file():
            scribe_profile_abs_path = potential_profile_path.resolve()
            ui_utils.console.print(
                f"Using Scribe profile from NER: [blue]{scribe_profile_abs_path}[/blue]"
            )
        else:
            ui_utils.console.print(
                f"[yellow]Scribe profile '{base_name}' not found in NER at '{profile_rel_path_in_ner}'.[/yellow]"
            )
            ui_utils.console.print(
                "Scribe agent will use its internal default profile or search its CWD."
            )
            # TODO, Architect: Offer fzf selection from available Scribe profiles in NER if not found.

    ui_utils.console.print(
        f"Requesting Scribe validation for project: [cyan]{target_dir}[/cyan], target file relative: [cyan]{target_file_rel}[/cyan]"
    )

    # ScribeAgentRunner.run_validation returns (bool_success, dict_output_payload from Scribe)
    success, output_payload = runner.run_validation(
        target_dir=target_dir,
        code_file=code_file,
        target_file_relative=target_file_rel,
        scribe_profile_path=scribe_profile_abs_path,
        commit=commit,
        skip_deps=skip_deps,
        skip_tests=skip_tests,
        skip_review=skip_review,
    )

    # ui_utils.print_agent_output handles structured display of Scribe's JSON report
    ui_utils.print_agent_output(
        "Scribe",
        success,
        output_payload,
        output_payload.get("raw_stdout_if_error"),  # Conceptual
        output_payload.get("raw_stderr_if_error"),
    )

    # Scribe's JSON output should contain an "overall_status" field.
    scribe_overall_status = output_payload.get(
        "overall_status", "FAILURE" if not success else "UNKNOWN_STATUS_FROM_SCRIBE"
    )

    if not success or scribe_overall_status != "SUCCESS":
        ui_utils.console.print(
            f"[bold red]Scribe validation reported failure or non-SUCCESS status ('{scribe_overall_status}').[/bold red]"
        )
        # TODO, Architect: If Scribe output contains structured errors (e.g., lint issues), PAC could offer
        # to automatically create an Ex-Work instruction to try and fix them.
        raise typer.Exit(code=1)
    else:
        ui_utils.console.print(
            f"[bold green]Scribe validation reported overall status: {scribe_overall_status}.[/bold green]"
        )


# TODO, Architect: Add more Scribe commands:
# - scribe list-profiles
# - scribe view-report <run_id_or_file> (Scribe would need to save reports with run_id for this)
# - scribe new-profile [--from-default] [--editor]

# --- Workflow Command Group (Conceptual Stubs) ---
workflow_app = typer.Typer(
    name="workflow",
    help="Define and execute multi-step NPT workflows.",
    no_args_is_help=True,
)
app.add_typer(workflow_app)


@workflow_app.command("run", help="Run a defined NPT workflow from a NER file.")
def workflow_run_cmd(
    ctx: typer.Context,
    workflow_file_ner_path: str = typer.Argument(
        ...,
        help="Relative path to the workflow definition file in NER (e.g., '07_SECURITY_TOOLS/red_team/scans/full_recon.workflow.json').",
    ),
):
    # Loads and executes a NPT workflow definition."."
    current_ner_handler: NERHandler = ctx.meta["ner_handler"]
    # ExWork, Scribe runners, LLM interface are also in ctx.meta

    ui_utils.console.print(
        f"Attempting to run workflow from NER file: [cyan]{workflow_file_ner_path}[/cyan]"
    )
    workflow_content_str = current_ner_handler.get_item_content(workflow_file_ner_path)

    if not workflow_content_str:
        ui_utils.console.print(
            f"[red]Workflow file not found or empty in NER: '{workflow_file_ner_path}'[/red]"
        )
        raise typer.Exit(code=1)

    ui_utils.console.print(
        "[italic yellow]TODO, Architect: Implement Workflow Engine Logic for PAC.[/italic yellow]"
    )
    ui_utils.console.print("Workflow Engine tasks would include:")
    ui_utils.console.print(
        "  1. Parsing the workflow definition (JSON or YAML from `workflow_content_str`)."
    )
    ui_utils.console.print(
        "     - Define schema: sequence of steps, step types (exwork, scribe, ner, llm, user_prompt, conditional), parameters, data passing."
    )
    ui_utils.console.print("  2. Validating the workflow structure.")
    ui_utils.console.print("  3. Iterating through steps:")
    ui_utils.console.print(
        "     - Dynamically resolving parameters (user input, previous step output)."
    )
    ui_utils.console.print(
        "     - Calling appropriate PAC core functions (ExWork/Scribe runners, NERHandler, LLMInterface, UIUtils for prompts)."
    )
    ui_utils.console.print(
        "     - Handling step success/failure and conditional branching (e.g., 'if scribe_fails then run exwork_diagnose')."
    )
    ui_utils.console.print(
        "     - Managing overall workflow state and producing a final report."
    )

    ui_utils.display_syntax(
        workflow_content_str,
        Path(workflow_file_ner_path).suffix[1:].lower() or "json",
        title=f"Workflow Content: {Path(workflow_file_ner_path).name}",
    )
    logger.warning(
        "Workflow execution is a stub. Full implementation required by Architect."
    )


# --- System/Admin Command Group ---
system_app = typer.Typer(
    name="system",
    help="PAC system management, configuration, and diagnostics.",
    no_args_is_help=True,
)
app.add_typer(system_app)


@system_app.command("config", help="View or modify PAC configuration settings.")
def system_config_cmd(
    ctx: typer.Context,
    key: Optional[str] = typer.Argument(
        None,
        help="Config key to get/set (e.g., 'general.user_name' or 'agents.ex_work_agent_path'). View all if no key.",
        show_default=False,
    ),
    value: Optional[str] = typer.Argument(
        None,
        help="Value to set for the key (if setting). To clear a key, set value to 'NULL' or 'DEFAULT'.",
        show_default=False,
    ),
):
    """Manages PACs settings.toml configuration."""
    cfg_mgr: ConfigManager = ctx.meta["config_manager"]

    if key and value:  # Set value
        # TODO, Architect: Implement type conversion for value if settings schema is introduced.
        # For now, all values from CLI are strings. ConfigManager might need to handle types.
        # Special values for 'value': "NULL" to remove, "DEFAULT" to reset to default.
        ui_utils.console.print(
            f"Setting config '{key}' to '{value}' in {cfg_mgr.settings_file_path}..."
        )
        if value.upper() == "NULL":
            # TODO: ConfigManager needs a 'delete_key' or 'set_to_none' method. This is conceptual.
            # cfg_mgr.delete_value(key)
            ui_utils.console.print(
                f"[yellow]TODO: Implement deletion for '{key}'. For now, set it to empty string or manually edit TOML.[/yellow]"
            )
            cfg_mgr.set_value(key, "")  # Placeholder
        elif value.upper() == "DEFAULT":
            # TODO: ConfigManager needs ability to reset a key to its internal default.
            ui_utils.console.print(
                f"[yellow]TODO: Implement reset to default for '{key}'.[/yellow]"
            )
        else:
            cfg_mgr.set_value(key, value)

        retrieved_value_after_set = cfg_mgr.get(key)  # Re-get to confirm
        ui_utils.console.print(
            f"Config '{key}' is now: '[cyan]{retrieved_value_after_set}[/cyan]'"
        )
    elif key:  # Get specific value
        retrieved_value = cfg_mgr.get(key)
        ui_utils.console.print(
            f"Config '{key}': [cyan]{retrieved_value if retrieved_value is not None else '[Not Set]'}[/cyan]"
        )
    else:  # View all current settings
        settings_str = json.dumps(
            cfg_mgr.settings, indent=2, default=str
        )  # Use json for pretty print of dict
        ui_utils.display_panel(
            JSON(settings_str),
            title=f"Current PAC Settings (from {cfg_mgr.settings_file_path})",
            border_style="magenta",
        )
    ui_utils.console.print(f"Settings file: [dim]{cfg_mgr.settings_file_path}[/dim]")


@system_app.command(
    "check", help="Perform a system check for PAC environment and configurations."
)
def system_check_cmd(ctx: typer.Context):
    """Runs diagnostic checks on the PAC setup."""
    ui_utils.console.print(
        f"[bold underline]Performing PAC System Health Check (v{APP_VERSION})[/bold underline]\n"
    )
    cfg_mgr: ConfigManager = ctx.meta["config_manager"]
    ner_h: NERHandler = ctx.meta["ner_handler"]
    exw_r: ExWorkAgentRunner = ctx.meta["ex_work_runner"]
    scr_r: ScribeAgentRunner = ctx.meta["scribe_runner"]
    llm_i: LLMInterface = ctx.meta["llm_interface"]

    checks_data = []

    def add_check(item: str, value: Any, status_ok: bool, notes: str = ""):
        status_str = "[green]OK[/green]" if status_ok else "[red]FAIL[/red]"
        if not status_ok and not notes:
            notes = "Check configuration or path."
        checks_data.append([item, str(value), status_str, notes])

    # NPT Base and Config
    add_check("NPT Base Directory", NPT_BASE_DIR, NPT_BASE_DIR.is_dir())
    add_check(
        "PAC Settings File",
        cfg_mgr.settings_file_path,
        cfg_mgr.settings_file_path.is_file(),
        "If missing, defaults are used and new file created on save.",
    )

    # NER
    ner_path_from_cfg = cfg_mgr.get("general.default_ner_path", "Not Set")
    add_check(
        "NER Directory (from config)",
        ner_path_from_cfg,
        ner_h.ner_root.is_dir(),
        f"Actual path used: {ner_h.ner_root}",
    )
    ner_git_ok = (ner_h.ner_root / ".git").is_dir()
    add_check(
        "NER Git Repository",
        ".git folder exists",
        ner_git_ok,
        "If false, NER is not a Git repo.",
    )

    # Core Agents
    exw_path_cfg = cfg_mgr.get("agents.ex_work_agent_path")
    exw_script_cmd_list = shlex.split(exw_path_cfg) if exw_path_cfg else []
    exw_script_actual_path = (
        Path(exw_script_cmd_list[1])
        if len(exw_script_cmd_list) > 1
        and exw_script_cmd_list[0].endswith("python3")
        or exw_script_cmd_list[0].endswith("python")
        else Path(exw_script_cmd_list[0]) if exw_script_cmd_list else Path("")
    )
    add_check(
        "Ex-Work Agent Path (config)",
        exw_path_cfg or "Not Set",
        bool(exw_path_cfg),
        "Must be set for Ex-Work commands.",
    )
    if exw_path_cfg:
        add_check(
            "Ex-Work Script Executable/Exists",
            exw_script_actual_path,
            exw_script_actual_path.is_file()
            and (
                os.access(exw_script_actual_path, os.X_OK)
                or exw_script_cmd_list[0].endswith("python")
            ),
            "Check path and permissions.",
        )

    scr_path_cfg = cfg_mgr.get("agents.scribe_agent_path")
    scr_script_cmd_list = shlex.split(scr_path_cfg) if scr_path_cfg else []
    scr_script_actual_path = (
        Path(scr_script_cmd_list[1])
        if len(scr_script_cmd_list) > 1
        and scr_script_cmd_list[0].endswith("python3")
        or scr_script_cmd_list[0].endswith("python")
        else Path(scr_script_cmd_list[0]) if scr_script_cmd_list else Path("")
    )
    add_check(
        "Scribe Agent Path (config)",
        scr_path_cfg or "Not Set",
        bool(scr_path_cfg),
        "Must be set for Scribe commands.",
    )
    if scr_path_cfg:
        add_check(
            "Scribe Script Executable/Exists",
            scr_script_actual_path,
            scr_script_actual_path.is_file()
            and (
                os.access(scr_script_actual_path, os.X_OK)
                or scr_script_cmd_list[0].endswith("python")
            ),
            "Check path and permissions.",
        )

    # LLM Interface
    add_check(
        "LLM Provider (config)", llm_i.provider, True
    )  # Provider always has a value
    add_check(
        "LLM API Base URL (config)",
        llm_i.api_base_url or "Not Set",
        bool(llm_i.api_base_url or llm_i.provider == "generic"),
        "Needed for direct LLM calls.",
    )
    add_check(
        "LLM Default Model (config)",
        llm_i.default_model or "Not Set",
        bool(llm_i.default_model),
        "Needed for LLM calls.",
    )

    # Python Environment (PAC's venv)
    py_exe_in_venv = sys.executable
    add_check("PAC Python Executable", py_exe_in_venv, Path(py_exe_in_venv).is_file())
    # TODO, Architect: Add check for key dependencies like fzf, git from system PATH if PAC relies on them directly.

    ui_utils.display_table(
        f"{APP_NAME} System Health Check",
        ["Component", "Value/Path", "Status", "Notes"],
        checks_data,
    )
    ui_utils.console.print(
        "\n[italic]This check provides an overview. Ensure external tools (git, fzf) and agent dependencies are also met.[/italic]"
    )


# TODO, Architect: Add more system commands:
# - system logs view [--lines N] [--level <level>]
# - system self-update (if NPT hosted in a way that generator can be re-fetched and run)
# - system export-config / import-config

# --- Main Entry Point for PAC Application ---
if __name__ == "__main__":
    logger.info(
        f"Starting {APP_NAME} v{APP_VERSION} directly via __main__ (dev/debug mode)."
    )
    app()
