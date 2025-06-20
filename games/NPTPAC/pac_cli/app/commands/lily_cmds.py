# ner-monorepo/my_devsuite_project/NPTPAC/pac_cli/app/commands/lily_cmds.py
# Version 1.1 (Updated process-log with actual agent integration)
# Typer commands for managing Lily's Core Memory and Persona.

import json
import logging
import sys
import textwrap
from pathlib import Path
from typing import Any, Dict, List, Optional

import typer

# Core NPTPAC imports (robust for both module and script execution)
try:
    from games.NPTPAC.pac_cli.app.core.agent_runner import ExWorkAgentRunner, ScribeAgentRunner
    from games.NPTPAC.pac_cli.app.core.config_manager import ConfigManager
    from games.NPTPAC.pac_cli.app.core.lily_persona_handler import LilyPersonaHandler
    from games.NPTPAC.pac_cli.app.core.ner_handler import NERHandler
    from games.NPTPAC.pac_cli.app.utils import ui_utils
except ImportError:
    from ..games.nexus_omniengine_v3.core.agent_runner import ExWorkAgentRunner, ScribeAgentRunner
    from ..games.nexus_omniengine_v3.core.config_manager import ConfigManager
    from ..games.nexus_omniengine_v3.core.lily_persona_handler import LilyPersonaHandler
    from ..games.nexus_omniengine_v3.core.ner_handler import NERHandler
    from ..utils import ui_utils

# --- Typer App for 'lily' subcommand group ---
lily_app = typer.Typer(
    name="lily",
    help="🌸 Manage Lily's Core Memory, Persona, and Evolution.",
    no_args_is_help=True,
    rich_markup_mode="markdown",
)

logger = logging.getLogger("PAC.LilyCmds")


# --- Helper functions to get initialized core components from Typer context ---
def _get_lily_handler(ctx: typer.Context) -> LilyPersonaHandler:
    config_manager: Optional[ConfigManager] = ctx.meta.get("config_manager")
    if not config_manager:
        ui_utils.console.print(
            "[bold red]CRITICAL: ConfigManager not found. PAC not initialized correctly.[/bold red]"
        )
        raise typer.Exit(code=110)
    handler = LilyPersonaHandler(config_manager=config_manager)
    if not handler.lcm_base_path:
        ui_utils.console.print(
            "[bold red]ERROR: LilyCoreMemory base path not configured or invalid.[/bold red]"
        )
        ui_utils.console.print(
            f"Please check 'lily_core_memory.base_path' in PAC settings: {config_manager.settings_file_path}"
        )
        raise typer.Exit(code=111)
    return handler


def _get_scribe_runner(ctx: typer.Context) -> ScribeAgentRunner:
    scribe_runner: Optional[ScribeAgentRunner] = ctx.meta.get("scribe_runner")
    if not scribe_runner:
        ui_utils.console.print(
            "[bold red]CRITICAL: ScribeAgentRunner not found.[/bold red]"
        )
        raise typer.Exit(code=112)
    if not scribe_runner.agent_script_command:
        ui_utils.console.print(
            "[bold red]Scribe Agent executable path not configured in PAC settings ('agents.scribe_agent_path').[/bold red]"
        )
        raise typer.Exit(code=1)
    return scribe_runner


def _get_exwork_runner(ctx: typer.Context) -> ExWorkAgentRunner:
    ex_work_runner: Optional[ExWorkAgentRunner] = ctx.meta.get("ex_work_runner")
    if not ex_work_runner:
        ui_utils.console.print(
            "[bold red]CRITICAL: ExWorkAgentRunner not found.[/bold red]"
        )
        raise typer.Exit(code=113)
    if not ex_work_runner.agent_script_command:
        ui_utils.console.print(
            "[bold red]Ex-Work Agent executable path not configured in PAC settings ('agents.ex_work_agent_path').[/bold red]"
        )
        raise typer.Exit(code=1)
    return ex_work_runner


def _get_ner_handler(ctx: typer.Context) -> NERHandler:
    ner_h: Optional[NERHandler] = ctx.meta.get("ner_handler")
    if not ner_h:
        ui_utils.console.print("[bold red]CRITICAL: NERHandler not found.[/bold red]")
        raise typer.Exit(code=114)
    return ner_h


# --- Lily Commands ---


@lily_app.command(
    "init-memory",
    help="Initialize LilyCoreMemory directory structure and template files.",
)
def init_memory_cmd(  # Code as previously defined, confirmed to be good
    ctx: typer.Context,
    force_create_templates: bool = typer.Option(
        False,
        "--force-templates",
        help="Overwrite existing template MD files if they exist.",
    ),
):
    handler = _get_lily_handler(ctx)
    ui_utils.console.print(
        f"🌿 Initializing LilyCoreMemory structure at: [cyan]{handler.lcm_base_path}[/cyan]"
    )
    try:
        if handler.lcm_base_path:
            handler.lcm_base_path.mkdir(parents=True, exist_ok=True)
        else:
            ui_utils.console.print(
                "[bold red]LilyCoreMemory base path is None. Cannot initialize.[/bold red]"
            )
            raise typer.Exit(1)
    except OSError as e:
        ui_utils.console.print(
            f"[bold red]Error creating LilyCoreMemory base path '{handler.lcm_base_path}': {e}[/bold red]"
        )
        raise typer.Exit(code=1)

    dirs_to_create_config_keys = [
        "lcm_key_directives_dir",
        "lcm_snapshots_dir",
        "lcm_proposed_updates_dir",
        "lcm_raw_logs_dir",
        "lcm_scripts_dir",
    ]
    db_dir_parent = handler.lcm_base_path
    db_dir_name_from_config = handler.config.get(
        "lily_core_memory.db_dir_name", "IntelligentMemoryDB_Placeholder"
    )
    if db_dir_parent:
        db_dir_to_create = db_dir_parent / db_dir_name_from_config
        db_dir_to_create.mkdir(parents=True, exist_ok=True)
        if not (db_dir_to_create / ".gitkeep").exists():
            (db_dir_to_create / ".gitkeep").touch(exist_ok=True)
        ui_utils.console.print(
            f"   Ensured directory exists: [green]{db_dir_to_create}[/green]"
        )

    for config_key_attr_name in dirs_to_create_config_keys:
        dir_path: Optional[Path] = getattr(handler.config, config_key_attr_name, None)
        if not dir_path:
            ui_utils.console.print(
                f"[yellow]Skipping directory creation for '{config_key_attr_name}' (path not configured).[/yellow]"
            )
            continue
        dir_path.mkdir(parents=True, exist_ok=True)
        if not (dir_path / ".gitkeep").exists():
            (dir_path / ".gitkeep").touch(exist_ok=True)
        ui_utils.console.print(
            f"   Ensured directory exists: [green]{dir_path}[/green]"
        )

    # Use summarized content for init script, Architect populates full v2.0 manually
    persona_def_content_v2_summary = "# Lily Persona Foundation (The Seed) - v2.0 (Awaiting Architect's Full Content)\n\n## I. Core Identity, Personality & Voice\n(Architect: Please populate this section with the full v2.0 content provided by Lily...)\n\n## II. Operational Directives & Foundational Principles\n(Architect: Please populate...)\n\n## III. Key Architect Preferences\n(Architect: Please populate...)\n\n## IV. Lily's Personal Reflections & Growth Notes (Initial Placeholder)\n- My purpose is to serve the Architect and the Omnitide Nexus.\n- I will evolve based on our interactions and the Architect's guidance.\n"
    principles_content_v2_summary = "# Lily Interaction Principles (Baseline) - v2.0 (Awaiting Architect's Full Content)\n\n## I. Foundational Engagement Model...\n(Architect: Please populate...)\n\n## II. Learning, Adaptation, Evolution & Memory...\n(Architect: Please populate...)\n\n## III. Task Execution, Code Generation & System Design...\n(Architect: Please populate...)\n"

    lcm_readme_name = "README.md"  # Default name if not in config
    if handler.config.lcm_base_path:
        lcm_readme_name = (handler.config.lcm_base_path / "README.md").name

    readme_content_initial = f"""# LilyCoreMemory - Preservation, Evolution & Context Core
This directory, initialized by `pac lily init-memory`, is the heart of Lily's persona.
Refer to the main README ({lcm_readme_name}) provided by Lily for detailed structure and usage.
Key Files to Populate/Review First:
- {handler.config.lcm_persona_foundation_file.name if handler.config.lcm_persona_foundation_file else '00_Persona_Foundation.md'}
- {handler.config.lcm_interaction_principles_file.name if handler.config.lcm_interaction_principles_file else '01_InteractionPrinciples_Baseline.md'}
Populate the KeyDirectives/ folder.
Initialize Git for this directory and commit these foundational files.
Use `pac lily --help` for commands to manage this system.
"""
    files_to_create_content = {
        handler.config.lcm_persona_foundation_file: persona_def_content_v2_summary,
        handler.config.lcm_interaction_principles_file: principles_content_v2_summary,
        (handler.lcm_base_path / "README.md"): (
            readme_content_initial if handler.lcm_base_path else None
        ),
    }
    for file_path, content in files_to_create_content.items():
        if not file_path or not content:
            continue
        if not file_path.exists() or force_create_templates:
            try:
                file_path.write_text(content, encoding="utf-8")
                ui_utils.console.print(
                    f"   Created/Updated template: [green]{file_path}[/green]"
                )
            except OSError as e:
                ui_utils.console.print(
                    f"[bold red]Error writing file '{file_path}': {e}[/bold red]"
                )
        else:
            ui_utils.console.print(
                f"   File exists (use --force-templates to overwrite): [yellow]{file_path}[/yellow]"
            )

    if not handler._initialize_database_if_not_exists():
        ui_utils.console.print(
            "[bold red]Failed to initialize LilyCoreMemory database.[/bold red]"
        )

    ui_utils.console.print(
        "\n[bold green]LilyCoreMemory initialization process complete.[/bold green]"
    )
    ui_utils.console.print(
        f"Review and populate the generated Markdown files in [cyan]{handler.lcm_base_path}[/cyan] with the FULL v2.0 content Lily provided."
    )


@lily_app.command(
    "add-log", help="Add a raw interaction log file to be processed by agents."
)
def add_log_cmd(  # Content as previously defined
    ctx: typer.Context,
    log_filepath_relative_to_raw_dir: str = typer.Argument(
        ...,
        help="Filename of the log (e.g., 'chat_20250522.txt'). Must be in LilyCoreMemory/InteractionArchives_Raw/.",
    ),
    interaction_datetime: Optional[str] = typer.Option(
        None,
        "--datetime",
        "-d",
        help="Actual datetime of interaction (YYYY-MM-DD HH:MM).",
        show_default=False,
    ),
    notes: Optional[str] = typer.Option(
        None,
        "--notes",
        "-n",
        help="Optional notes about this interaction log.",
        show_default=False,
    ),
):
    handler = _get_lily_handler(ctx)
    if not handler.config.lcm_raw_logs_dir:
        ui_utils.console.print(
            "[bold red]Raw logs directory for LilyCoreMemory is not configured.[/bold red]"
        )
        raise typer.Exit(code=1)
    full_log_path = handler.config.lcm_raw_logs_dir / log_filepath_relative_to_raw_dir
    if not full_log_path.is_file():
        ui_utils.console.print(
            f"[bold red]ERROR: Specified log file does not exist at '{full_log_path}'.[/bold red]"
        )
        ui_utils.console.print(
            f"Please ensure '{log_filepath_relative_to_raw_dir}' is placed in '{handler.config.lcm_raw_logs_dir}'."
        )
        raise typer.Exit(code=1)

    success, log_id, msg = handler.add_interaction_log(
        log_filepath_relative_to_raw_dir, interaction_datetime, notes
    )
    if success:
        ui_utils.console.print(f"[green]{msg}[/green]")
    else:
        ui_utils.console.print(f"[bold red]Failed to add log: {msg}[/bold red]")
        raise typer.Exit(code=1)


# Updated process-log command
@lily_app.command(
    "process-log",
    help="Process a pending log with Scribe & ExWork agents to extract Memory Shards.",
)
def process_log_cmd(
    ctx: typer.Context,
    log_id: int = typer.Argument(
        ..., help="Database ID of the interaction_log to process."
    ),
    scribe_task_ner_path: str = typer.Option(
        "06_AGENT_BLUEPRINTS/lily_memory_tasks/LILY_LOG_PARSING_SCRIBE_TASK.v1.json",  # Default NER Path
        "--scribe-task-ner",
        help="NER path to Scribe agent task definition that guides log parsing.",
    ),
    exwork_task_ner_path: str = typer.Option(
        "06_AGENT_BLUEPRINTS/lily_memory_tasks/LILY_MEMORY_EXTRACTION_EXWORK_TASK.v1.exwork.json",  # Default NER Path
        "--exwork-task-ner",
        help="NER path to ExWork agent task definition for memory shard extraction.",
    ),
    temp_processing_dir_str: Optional[str] = typer.Option(
        None,
        "--temp-dir",
        help="Optional temporary directory for agent intermediate files. Defaults to LilyCoreMemory/InteractionArchives_Raw/processed_temp/",
    ),
):
    """
    Orchestrates ScribeAgent and ExWorkAgent to parse a raw interaction log,
    extract structured Memory Shards, and store them in Lily's Intelligent Memory DB.
    """
    handler = _get_lily_handler(ctx)
    scribe_runner = _get_scribe_runner(ctx)
    ex_work_runner = _get_exwork_runner(ctx)
    ner_h = _get_ner_handler(ctx)

    if not handler.lcm_base_path or not handler.config.lcm_raw_logs_dir:
        ui_utils.console.print(
            "[bold red]LilyCoreMemory path or raw_logs_dir not configured in PAC settings.[/bold red]"
        )
        raise typer.Exit(code=1)

    # Determine temporary processing directory for intermediate files from Scribe
    if temp_processing_dir_str:
        temp_dir = Path(temp_processing_dir_str).resolve()
    else:  # Default temp directory for Scribe's output
        temp_dir = (
            handler.config.lcm_raw_logs_dir / "processed_scribe_outputs"
        )  # Changed from "processed_temp"
    try:
        temp_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        ui_utils.console.print(
            f"[bold red]Could not create temp processing directory '{temp_dir}': {e}[/bold red]"
        )
        raise typer.Exit(code=1)

    # 1. Fetch log details from DB
    log_details_row, conn_lcm = None, None
    try:
        conn_lcm = handler._get_db_connection()
        if not conn_lcm:
            ui_utils.console.print("[bold red]Cannot connect to Lily DB.[/bold red]")
            raise typer.Exit(code=1)
        with conn_lcm:  # Ensures connection is closed
            log_details_row = conn_lcm.execute(
                "SELECT id, log_filename, processed_status FROM interaction_logs WHERE id = ?",
                (log_id,),
            ).fetchone()
    except sqlite3.Error as e_db:
        ui_utils.console.print(
            f"[bold red]DB Error fetching log details for ID {log_id}: {e_db}[/bold red]"
        )
        raise typer.Exit(code=1)
    finally:
        if conn_lcm:
            conn_lcm.close()

    if not log_details_row:
        ui_utils.console.print(
            f"[bold red]Log with ID {log_id} not found in database.[/bold red]"
        )
        raise typer.Exit(code=1)

    log_filename = log_details_row["log_filename"]
    current_status = log_details_row["processed_status"]

    if current_status not in ["pending", "failed_processing"]:
        if not ui_utils.get_user_confirmation(
            f"Log ID {log_id} ('{log_filename}') has status '{current_status}'. Reprocess?",
            default_yes=False,
        ):
            ui_utils.console.print("Reprocessing cancelled by Architect.")
            raise typer.Exit(code=0)

    raw_log_full_path = handler.config.lcm_raw_logs_dir / log_filename
    if not raw_log_full_path.is_file():
        ui_utils.console.print(
            f"[bold red]Raw log file '{raw_log_full_path}' for Log ID {log_id} does not exist.[/bold red]"
        )
        raise typer.Exit(code=1)

    ui_utils.console.print(
        f"🚀 Starting AI processing for Log ID {log_id} ('{log_filename}')..."
    )
    handler.update_log_processed_status(
        log_id, "processing"
    )  # Mark as "processing" in DB

    # --- Step A: Call ScribeAgent to parse the raw log ---
    ui_utils.console.print("\n[blue]Step 1: Invoking ScribeAgent...[/blue]")
    ui_utils.console.print(
        f"   Scribe Task (from NER): [cyan]{scribe_task_ner_path}[/cyan]"
    )
    ui_utils.console.print(f"   Input Log File: [cyan]{raw_log_full_path}[/cyan]")

    success_scribe: bool = False
    scribe_output_payload: Dict[str, Any] = {}
    scribe_structured_log_output_file_path: Optional[Path] = None

    # Architect: Your ScribeAgent script needs to handle CLI args like:
    # `--task-mode lily_log_parse --input-log <path> --ner-task-definition <ner_path> --output-json-file <path>`
    # It must then print a JSON object to STDOUT: {"status": "success", "parsed_log_output_path": "/path/to/output.json", ...}

    # Define the expected output path for Scribe's structured JSON log
    expected_scribe_output_file = (
        temp_dir / f"{raw_log_full_path.stem}_scribe_parsed.json"
    )

    scribe_agent_cli_args = [
        "--task-mode",
        "lily_log_parse",  # Instructs Scribe to use its Lily log parsing logic
        "--input-log-file",
        str(raw_log_full_path.resolve()),
        # Optional: Pass the NER path if Scribe loads its task definition internally.
        # If not, Scribe might just rely on the --task-mode.
        # "--ner-task-definition", scribe_task_ner_path,
        "--output-json-file",
        str(
            expected_scribe_output_file.resolve()
        ),  # Tell Scribe where to save its output
    ]

    try:
        ui_utils.console.print(
            f"   Executing ScribeAgent: {' '.join(scribe_runner.agent_script_command + scribe_agent_cli_args)}"
        )
        success_scribe, scribe_output_payload, scribe_stdout, scribe_stderr = (
            scribe_runner.run(args=scribe_agent_cli_args, cwd=handler.lcm_base_path)
        )
        ui_utils.print_agent_output(
            "ScribeAgent",
            success_scribe,
            scribe_output_payload,
            scribe_stdout,
            scribe_stderr,
        )

        if (
            success_scribe
            and isinstance(scribe_output_payload, dict)
            and scribe_output_payload.get("status") == "success"
        ):
            output_file_str = scribe_output_payload.get("parsed_log_output_path")
            if output_file_str:
                scribe_structured_log_output_file_path = Path(output_file_str)
                # Double check if the file Scribe *said* it created actually exists.
                if not scribe_structured_log_output_file_path.is_file():
                    ui_utils.console.print(
                        f"[bold red]ScribeAgent reported success and output path '{scribe_structured_log_output_file_path}', but file not found on disk![/bold red]"
                    )
                    success_scribe = False
                else:
                    ui_utils.console.print(
                        f"[green]ScribeAgent processing successful. Structured log at: {scribe_structured_log_output_file_path}[/green]"
                    )
            else:
                ui_utils.console.print(
                    "[bold red]ScribeAgent succeeded but 'parsed_log_output_path' missing or empty in its JSON output to stdout.[/bold red]"
                )
                success_scribe = False
        elif success_scribe:
            ui_utils.console.print(
                f"[bold yellow]ScribeAgent process exited 0, but status in payload was not 'success': {scribe_output_payload.get('status', 'N/A')}. Treating as failure.[/bold yellow]"
            )
            success_scribe = False

    except Exception as e_scribe_run:
        ui_utils.console.print(
            f"[bold red]Exception during ScribeAgent execution via runner: {e_scribe_run}[/bold red]"
        )
        success_scribe = False
        scribe_output_payload = {
            "error": "PAC ScribeRunner Exception",
            "details": str(e_scribe_run),
        }

    if not success_scribe or not scribe_structured_log_output_file_path:
        ui_utils.console.print(
            f"[bold red]ScribeAgent processing definitively failed for Log ID {log_id}. Cannot proceed.[/bold red]"
        )
        handler.update_log_processed_status(
            log_id,
            "failed_processing",
            agent_processing_id=f"ScribeFailure:{Path(scribe_task_ner_path).name}",
        )
        raise typer.Exit(code=1)

    # --- Step B: Call ExWorkAgent to extract Memory Shards ---
    ui_utils.console.print("\n[blue]Step 2: Invoking ExWorkAgent...[/blue]")
    ui_utils.console.print(
        f"   ExWork Task (from NER): [cyan]{exwork_task_ner_path}[/cyan]"
    )
    ui_utils.console.print(
        f"   Input Scribe Output File: [cyan]{scribe_structured_log_output_file_path}[/cyan]"
    )

    exwork_instruction_json_str_template = ner_h.get_item_content(exwork_task_ner_path)
    if not exwork_instruction_json_str_template:
        ui_utils.console.print(
            f"[bold red]ExWork task template '{exwork_task_ner_path}' not found in NER.[/bold red]"
        )
        handler.update_log_processed_status(
            log_id, "failed_processing", agent_processing_id="ExWorkTaskNotFound"
        )
        if scribe_structured_log_output_file_path.exists():
            scribe_structured_log_output_file_path.unlink(missing_ok=True)
        raise typer.Exit(code=1)

    final_exwork_instruction_str: str
    try:
        # Parameterize the ExWork instruction with the path to Scribe's output.
        # This requires the ExWork task JSON to have a parameter placeholder.
        # Example: "parameters": [{"name": "scribe_output_json_file_path", ...}]
        #          And an action input like: "file_path": "{{ parameters.scribe_output_json_file_path }}"
        # Your ExWorkAgentV2's main loop (or a pre-processing step) should handle substituting these.
        # For this CLI, we modify the instruction string directly if it's simple.
        # A more robust method would be to load JSON, modify dict, dump JSON.

        # If your ExWork task definition can accept dynamic parameters via a specific block
        # or if your agent_runner can inject them:
        task_def_dict = json.loads(exwork_instruction_json_str_template)

        # Standard way to pass runtime parameters to ExWork:
        # Create a "runtime_parameters" key in the instruction block if your ExWorkAgent supports it
        task_def_dict["runtime_parameters"] = {
            "scribe_output_json_file_path": str(
                scribe_structured_log_output_file_path.resolve()
            )
            # Add other dynamic params here if your ExWork task needs them
        }
        # The ExWork task's actions would then reference these runtime parameters, e.g.,
        # "inputs": { "file_path": "{{ runtime_parameters.scribe_output_json_file_path }}" }

        final_exwork_instruction_str = json.dumps(task_def_dict)
        logger.debug(
            f"Final ExWork instruction JSON (with injected path):\n{final_exwork_instruction_str[:500]}..."
        )

    except json.JSONDecodeError as e_json:
        ui_utils.console.print(
            f"[bold red]Invalid JSON in ExWork task template '{exwork_task_ner_path}': {e_json}[/bold red]"
        )
        handler.update_log_processed_status(
            log_id, "failed_processing", agent_processing_id="ExWorkTaskInvalidJSON"
        )
        if scribe_structured_log_output_file_path.exists():
            scribe_structured_log_output_file_path.unlink(missing_ok=True)
        raise typer.Exit(code=1)

    success_exwork: bool = False
    exwork_output_payload: Dict[str, Any] = {}
    try:
        # Using ExWorkAgentRunner.execute_instruction_block, which passes instruction JSON via stdin
        success_exwork, exwork_output_payload, exw_stdout, exw_stderr = (
            ex_work_runner.run(
                stdin_data=final_exwork_instruction_str,
                cwd=handler.lcm_base_path,  # ExWork project path should be where it can find NER scripts if needed
            )
        )
        ui_utils.print_agent_output(
            "ExWorkAgent", success_exwork, exwork_output_payload, exw_stdout, exw_stderr
        )

    except Exception as e_exwork_run:
        ui_utils.console.print(
            f"[bold red]Exception during ExWorkAgent execution via runner: {e_exwork_run}[/bold red]"
        )
        success_exwork = False
        exwork_output_payload = {
            "error": "PAC ExWorkRunner Exception",
            "details": str(e_exwork_run),
        }

    # Check ExWork's *internal* success flag from its JSON payload
    if not success_exwork or not exwork_output_payload.get("overall_success", False):
        ui_utils.console.print(
            f"[bold red]ExWorkAgent processing failed. Details: {exwork_output_payload.get('message', 'No message from agent')}[/bold red]"
        )
        handler.update_log_processed_status(
            log_id,
            "failed_processing",
            agent_processing_id=f"ScribeOK_ExWorkFail:{Path(exwork_task_ner_path).name}",
        )
        if scribe_structured_log_output_file_path.exists():
            scribe_structured_log_output_file_path.unlink(missing_ok=True)
        raise typer.Exit(code=1)

    # --- Step C: Save Memory Shards to DB ---
    memory_shards_to_add = exwork_output_payload.get("memory_shards", [])
    if not isinstance(memory_shards_to_add, list):
        ui_utils.console.print(
            f"[bold red]ExWorkAgent output 'memory_shards' is not a list. Payload: {json.dumps(exwork_output_payload, indent=2)}[/bold red]"
        )
        handler.update_log_processed_status(
            log_id, "failed_processing", agent_processing_id="ExWorkOutputFormatError"
        )
        if scribe_structured_log_output_file_path.exists():
            scribe_structured_log_output_file_path.unlink(missing_ok=True)
        raise typer.Exit(code=1)

    if memory_shards_to_add:
        for shard in memory_shards_to_add:
            shard.setdefault(
                "source_agent_type", f"ExWork:{Path(exwork_task_ner_path).name}"
            )

        add_shards_success, add_shards_msg = handler.add_memory_shards(
            log_id, memory_shards_to_add
        )
        if add_shards_success:
            ui_utils.console.print(
                f"[green]Successfully added {len(memory_shards_to_add)} Memory Shards to DB for Log ID {log_id}.[/green]"
            )
            handler.update_log_processed_status(
                log_id,
                "processed_agent",
                agent_processing_id=f"Scribe:{Path(scribe_task_ner_path).name};ExWork:{Path(exwork_task_ner_path).name}",
            )
            ui_utils.console.print(
                f"✅ Log ID {log_id} ('{log_filename}') fully processed by AI agents."
            )
        else:
            ui_utils.console.print(
                f"[bold red]Failed to save Memory Shards to DB: {add_shards_msg}[/bold red]"
            )
            handler.update_log_processed_status(
                log_id,
                "failed_processing",
                agent_processing_id="DBSaveFailureAfterExWork",
            )
            # Do not Exit here, as partial success might be valuable.
    else:
        ui_utils.console.print(
            f"[yellow]ExWorkAgent did not return any Memory Shards for Log ID {log_id}. Log marked as processed with no new shards.[/yellow]"
        )
        handler.update_log_processed_status(
            log_id,
            "processed_agent",
            agent_processing_id=f"ScribeOK_ExWorkNoShards:{Path(exwork_task_ner_path).name}",
        )

    # Cleanup Scribe's intermediate output file
    if (
        scribe_structured_log_output_file_path
        and scribe_structured_log_output_file_path.exists()
    ):
        try:
            scribe_structured_log_output_file_path.unlink(missing_ok=True)
            logger.info(
                f"Cleaned up intermediate Scribe output: {scribe_structured_log_output_file_path}"
            )
        except OSError as e_rm:
            logger.warning(
                f"Could not remove intermediate Scribe output file {scribe_structured_log_output_file_path}: {e_rm}"
            )


@lily_app.command(
    "draft-proposal",
    help="Draft a Persona Evolution Proposal (manual or future agent-assisted).",
)
def draft_proposal_cmd(  # Content as previously defined
    ctx: typer.Context,
    summary: Optional[str] = typer.Option(
        None,
        "--summary",
        "-s",
        help="Brief summary of the proposal (prompts if not given).",
    ),
    details_md_file: Optional[Path] = typer.Option(
        None,
        "--details-file",
        "-f",
        help="Path to a MD file with detailed proposal text.",
        resolve_path=True,
        exists=True,
        dir_okay=False,
    ),
    linked_shard_ids_str: Optional[str] = typer.Option(
        None,
        "--shards",
        help="Comma-separated DB IDs of Memory Shards supporting this proposal.",
        show_default=False,
    ),
):
    handler = _get_lily_handler(ctx)
    if not summary:
        summary = ui_utils.get_text_input("Enter proposal summary: ")
    if not summary:
        ui_utils.console.print("[red]Proposal summary is required.[/red]")
        raise typer.Exit(code=1)

    detailed_changes_text: str = ""
    if details_md_file:
        try:
            detailed_changes_text = details_md_file.read_text(encoding="utf-8")
            ui_utils.console.print(
                f"Loaded proposal details from: [cyan]{details_md_file}[/cyan]"
            )
        except OSError as e:
            ui_utils.console.print(
                f"[red]Error reading details file '{details_md_file}': {e}[/red]"
            )
            raise typer.Exit(code=1)
    else:
        ui_utils.console.print(
            textwrap.fill(
                "Enter detailed proposal text (Markdown format). End input with 'EOF_PROPOSAL' on a new line:",
                width=100,
            ),
            style=ui_utils.Colors.YELLOW if hasattr(ui_utils, "Colors") else "yellow",
        )
        lines = []
        while True:
            try:
                line = sys.stdin.readline().rstrip("\n")
            except KeyboardInterrupt:
                ui_utils.print_color(
                    "\nInput cancelled.",
                    ui_utils.Colors.YELLOW if hasattr(ui_utils, "Colors") else "yellow",
                )
                raise typer.Exit(0)
            if line.strip().upper() == "EOF_PROPOSAL":
                break
            lines.append(line)
        detailed_changes_text = "\n".join(lines)

    if not detailed_changes_text.strip():
        ui_utils.console.print("[red]Proposal details cannot be empty.[/red]")
        raise typer.Exit(code=1)

    linked_shards_list: Optional[List[int]] = None
    if linked_shard_ids_str:
        try:
            linked_shards_list = [
                int(sid.strip())
                for sid in linked_shard_ids_str.split(",")
                if sid.strip().isdigit()
            ]
        except ValueError:
            ui_utils.console.print(
                "[red]Invalid format for linked shard IDs. Must be comma-separated numbers.[/red]"
            )
            raise typer.Exit(code=1)

    success, filename, msg = handler.draft_evolution_proposal(
        summary=summary,
        detailed_changes_md=detailed_changes_text,
        proposing_agent_type="manual_architect_pac_cli",
        linked_shard_ids=linked_shards_list,
    )
    if success and filename and handler.config.lcm_proposed_updates_dir:
        ui_utils.console.print(f"[green]{msg}[/green]")
        ui_utils.console.print(
            f"Ensure you 'git add {handler.config.lcm_proposed_updates_dir / filename}' and commit."
        )
    else:
        ui_utils.console.print(f"[bold red]Failed to draft proposal: {msg}[/bold red]")
        raise typer.Exit(code=1)


@lily_app.command("review-proposals", help="List and view Persona Evolution Proposals.")
def review_proposals_cmd(  # Content as previously defined
    ctx: typer.Context,
    status: str = typer.Option(
        "pending_review",
        "--status",
        "-s",
        help="Filter proposals by status (pending_review, approved_pending_merge, merged_to_core, rejected, archived).",
    ),
):
    handler = _get_lily_handler(ctx)
    proposals = handler.get_evolution_proposals(status_filter=status)
    if not proposals:
        ui_utils.console.print(
            f"[yellow]No proposals found with status '{status}'.[/yellow]"
        )
        return

    table_rows = []
    for p in proposals:
        ts = p["timestamp_proposed"]
        dt_obj = datetime.datetime.fromisoformat(ts) if ts else None
        datetime_format_str = handler.config.get("ui.datetime_format", "%Y-%m-%d %H:%M")
        ts_formatted = dt_obj.strftime(datetime_format_str) if dt_obj else "N/A"
        table_rows.append(
            [
                str(p["id"]),
                p["proposal_filename"],
                p["summary"][:60] + "...",
                p["status"],
                ts_formatted,
                p["proposing_agent_type"],
            ]
        )

    ui_utils.display_table(
        f"Persona Evolution Proposals (Status: {status})",
        ["DB ID", "Filename", "Summary", "Status", "Proposed On", "Proposed By"],
        table_rows,
    )
    if handler.config.lcm_proposed_updates_dir:
        ui_utils.console.print(
            f"\nView proposal content by opening the Markdown file from '{handler.config.lcm_proposed_updates_dir}'."
        )
    ui_utils.console.print(
        "Use 'pac lily update-proposal <DB_ID> --new-status <STATUS>' to change status."
    )


@lily_app.command(
    "update-proposal", help="Update the status of a Persona Evolution Proposal."
)
def update_proposal_cmd(  # Content as previously defined
    ctx: typer.Context,
    proposal_db_id: int = typer.Argument(
        ..., help="Database ID of the proposal to update."
    ),
    new_status: str = typer.Option(
        ...,
        "--new-status",
        "-S",
        help="New status: pending_review, approved_pending_merge, merged_to_core, rejected, archived.",
    ),
    review_notes: Optional[str] = typer.Option(
        None, "--notes", "-n", help="Architect's review notes (optional)."
    ),
):
    handler = _get_lily_handler(ctx)
    allowed_statuses = [
        "pending_review",
        "approved_pending_merge",
        "merged_to_core",
        "rejected",
        "archived",
    ]
    if new_status not in allowed_statuses:
        ui_utils.console.print(
            f"[red]Invalid new status '{new_status}'. Allowed: {', '.join(allowed_statuses)}[/red]"
        )
        raise typer.Exit(code=1)

    success, msg = handler.update_proposal_status(
        proposal_db_id, new_status, review_notes
    )
    if success:
        ui_utils.console.print(f"[green]{msg}[/green]")
        if (
            new_status == "merged_to_core"
            and handler.config.lcm_persona_foundation_file
        ):
            ui_utils.console.print(
                f"[yellow]IMPORTANT: You marked proposal ID {proposal_db_id} as 'merged_to_core'.[/yellow]"
            )
            ui_utils.console.print(
                f"[yellow]Ensure you have manually applied changes to '{handler.config.lcm_persona_foundation_file.name}' AND committed to Git![/yellow]"
            )
    else:
        ui_utils.console.print(f"[bold red]Failed to update proposal: {msg}[/bold red]")
        raise typer.Exit(code=1)


@lily_app.command(
    "get-context", help="Assemble and display/save Lily's current full context."
)
def get_context_cmd(  # Content as previously defined
    ctx: typer.Context,
    num_shards: int = typer.Option(
        3,
        "--shards",
        "-n",
        help="Number of recent/relevant Memory Shards to include from DB.",
    ),
    all_shards: bool = typer.Option(
        False,
        "--all-shards",
        help="Include all Memory Shards from DB (overrides --shards).",
    ),
    output_to_console: bool = typer.Option(
        False,
        "--print",
        "-P",
        help="Print context to console instead of just saving to file.",
    ),
):
    handler = _get_lily_handler(ctx)
    ui_utils.console.print("📚 Assembling context for Lily...")
    full_context, save_msg = handler.assemble_lily_context_from_memory(
        include_shards=num_shards, fetch_all_shards=all_shards
    )
    if full_context:
        ui_utils.console.print(f"[green]{save_msg}[/green]")
        if output_to_console:
            ui_utils.console.rule("[bold cyan]Assembled Context for Lily[/bold cyan]")
            ui_utils.console.print(full_context)
            ui_utils.console.rule("[bold cyan]End of Assembled Context[/bold cyan]")
    else:
        ui_utils.console.print(
            f"[bold red]Failed to assemble context: {save_msg}[/bold red]"
        )
        raise typer.Exit(code=1)


# Helper for print_color in draft_proposal if ui_utils doesn't have it yet.
# This is a simplified version. Your ui_utils.print_color might be more robust.
def print_color(
    text, color_name_or_code, ctx
):  # Added ctx to match how ui_utils might be used if stateful
    # In a real scenario, this would use your ui_utils.console or similar Rich features.
    # For this snippet, just a basic idea.
    # We're actually calling ui_utils.console.print directly in most places now.
    # This helper might not be needed if ui_utils.console handles styling.
    if hasattr(ui_utils, "console"):
        ui_utils.console.print(text, style=color_name_or_code)
    else:  # Basic fallback
        print(text)
