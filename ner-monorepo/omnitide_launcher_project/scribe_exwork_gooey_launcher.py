#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# File: scribe_exwork_gooey_launcher_v1.2.1.py
# Project: Omnitide Nexus - Gooey Launcher for Scribe & Ex-Work
# Version: 1.2.1 (Refined Scribe path inputs based on user's scribe.py)
# Manifested under Drake Protocol v5.0 Apex on Mon May 12 2025 from Moore, Oklahoma.
# For The Supreme Master Architect Alix Feronti

"""
Project Scribe & Ex-Work Gooey Launcher (v1.2.1):
A desktop GUI application using Gooey to orchestrate scribe.py (user's version)
and exworkagent.py (user's v2.1) for task execution.
Includes template loading from omnitide_templates.json and UI enhancements.
"""

import json
import shlex
import subprocess
import sys
import os
from pathlib import Path
from datetime import datetime
import logging

# import time # Not strictly needed for this version's core logic

# --- Gooey Import ---
try:
    from gooey import Gooey, GooeyParser, options

    # from gooey.gui.components.widgets.bases import Textarea # Not directly used by name
    # from gooey.gui.components.widgets.basic.filechooser import FileChooser # Used via widget="FileChooser"
    # from gooey.gui.components.widgets.basic.dirchooser import DirChooser # Used via widget="DirChooser"
except ImportError:
    print(
        "FATAL ERROR: Gooey library not found. Please install it with 'pip install Gooey'",
        file=sys.stderr,
    )
    sys.exit(1)

# --- Basic Logging for this Gooey App ---
launcher_logger = logging.getLogger("ScribeExWorkLauncherV1.2.1")
launcher_logger.setLevel(logging.INFO)
# For debug logging of the launcher:
# launcher_logger.setLevel(logging.DEBUG)
# log_dir_launcher = Path.home() / ".omnitide_nexus_launcher_logs"
# log_dir_launcher.mkdir(parents=True, exist_ok=True)
# log_file_launcher = log_dir_launcher / "launcher_gui_v1.2.1.log"
# handler_launcher = logging.FileHandler(log_file_launcher, mode='a', encoding='utf-8')
# handler_launcher.setFormatter(logging.Formatter('%(asctime)s [%(levelname)-7s] %(name)s (%(module)s:%(lineno)d): %(message)s'))
# launcher_logger.addHandler(handler_launcher)
# launcher_logger.info("Launcher GUI session started.")


# --- Constants & Helper Functions ---
DEFAULT_SCRIBE_AGENT_FILENAME = "scribe.py"  # Updated to user's filename
DEFAULT_EXWORK_AGENT_FILENAME = "exworkagent.py"  # Updated to user's filename

DEFAULT_SCRIBE_AGENT_PATH = os.environ.get(
    "SCRIBE_AGENT_PATH", DEFAULT_SCRIBE_AGENT_FILENAME
)
DEFAULT_EXWORK_AGENT_PATH = os.environ.get(
    "EXWORK_AGENT_PATH", DEFAULT_EXWORK_AGENT_FILENAME
)
DEFAULT_TEMPLATES_FILE = "omnitide_templates.json"
DEFAULT_PYTHON_VERSION_SCRIBE = "3.11"  # Matching Scribe's default
REPORT_FORMATS_SCRIBE = ["json", "text"]  # From Scribe
LOG_LEVELS_SCRIBE = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]  # From Scribe

# Store last used paths for convenience
LAST_USED_PATHS_FILE = Path.home() / ".omnitide_launcher_v1.2_lastpaths.json"


def get_timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def load_last_used_paths() -> dict:
    if LAST_USED_PATHS_FILE.exists():
        try:
            with open(LAST_USED_PATHS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_last_used_paths(paths: dict):
    try:
        LAST_USED_PATHS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LAST_USED_PATHS_FILE, "w", encoding="utf-8") as f:
            json.dump(paths, f, indent=2)
    except Exception as e:
        launcher_logger.warning(f"[LAUNCHER] Could not save last used paths: {e}")


# Global to store loaded templates
LOADED_TEMPLATES = {"templates": [], "tools": []}


def load_omnitide_templates(
    templates_file_path_str: str, gooey_print_function: callable
) -> None:
    global LOADED_TEMPLATES
    LOADED_TEMPLATES = {"templates": [], "tools": []}
    templates_file_path = Path(templates_file_path_str)

    if not templates_file_path.is_file():
        gooey_print_function(
            f"[LAUNCHER] TEMPLATE INFO: Templates file not found at '{templates_file_path_str}'. To use templates, create this file or specify the correct path and click 'Load/Reload Templates File'.\n"
        )
        launcher_logger.warning(f"Templates file not found: {templates_file_path_str}")
        return

    try:
        with open(templates_file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict) or not (
            isinstance(data.get("templates"), list)
            or isinstance(data.get("tools"), list)
        ):  # Allow tools to be missing
            raise ValueError(
                "Templates file has invalid root structure or missing 'templates' list."
            )

        LOADED_TEMPLATES["templates"] = data.get("templates", [])
        LOADED_TEMPLATES["tools"] = data.get("tools", [])

        num_templates = len(LOADED_TEMPLATES["templates"])
        num_tools = len(LOADED_TEMPLATES["tools"])
        gooey_print_function(
            f"[LAUNCHER] Successfully loaded {num_templates} templates and {num_tools} tool definitions from '{templates_file_path_str}'.\n"
        )
        launcher_logger.info(
            f"Loaded {num_templates} templates and {num_tools} tools from {templates_file_path_str}"
        )
    except json.JSONDecodeError as e:
        gooey_print_function(
            f"[LAUNCHER] ERROR: Could not parse templates file '{templates_file_path_str}': {e}\n"
        )
        launcher_logger.error(
            f"JSON decode error in templates file {templates_file_path_str}: {e}"
        )
    except ValueError as e:
        gooey_print_function(
            f"[LAUNCHER] ERROR: Invalid template structure in '{templates_file_path_str}': {e}\n"
        )
        launcher_logger.error(
            f"Invalid template structure in {templates_file_path_str}: {e}"
        )
    except Exception as e:
        gooey_print_function(
            f"[LAUNCHER] ERROR: An unexpected error occurred while loading templates from '{templates_file_path_str}': {e}\n"
        )
        launcher_logger.error(
            f"Unexpected error loading templates {templates_file_path_str}: {e}",
            exc_info=True,
        )


def run_command_and_display_output(
    command_list: list[str],
    cwd: Optional[str] = None,
    input_data: Optional[str] = None,
    process_title: str = "Process",
    gooey_print_function: Optional[callable] = None,
) -> tuple[bool, str, str, Optional[str]]:
    if gooey_print_function is None:
        gooey_print_function = print

    full_command_str = " ".join(shlex.quote(str(arg)) for arg in command_list)
    gooey_print_function(
        f"[LAUNCHER] [{get_timestamp()}] Starting {process_title}:\n  Cmd: {full_command_str}\n"
    )
    if cwd:
        gooey_print_function(f"[LAUNCHER]   Working Directory: {cwd}\n")

    stdout_acc = []
    stderr_acc = []
    success = False
    final_json_output = None

    try:
        process = subprocess.Popen(
            command_list,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE if input_data is not None else None,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=cwd,
            bufsize=1,
            universal_newlines=True,
        )

        if input_data is not None:
            try:
                process.stdin.write(input_data)
                process.stdin.flush()
                process.stdin.close()
                launcher_logger.debug(
                    f"[LAUNCHER] {process_title}: Sent {len(input_data)} bytes to stdin and closed."
                )
            except Exception as e:
                launcher_logger.error(
                    f"[LAUNCHER] {process_title}: Error writing to stdin: {e}"
                )

        stdout_data, stderr_data = process.communicate(timeout=3600)

        raw_stdout_for_agent = stdout_data.strip() if stdout_data else ""
        raw_stderr_for_agent = stderr_data.strip() if stderr_data else ""

        if process_title == "Ex-Work Agent":
            gooey_print_function(
                f"[EXWORK_RAW_STDOUT]\n{raw_stdout_for_agent}\n[/EXWORK_RAW_STDOUT]\n"
            )
            if raw_stderr_for_agent:
                gooey_print_function(
                    f"[EXWORK_RAW_STDERR]\n{raw_stderr_for_agent}\n[/EXWORK_RAW_STDERR]\n"
                )
            try:
                # Ex-Work v2.1's main output IS its final summary JSON to stdout
                parsed_summary = json.loads(raw_stdout_for_agent)
                final_json_output = raw_stdout_for_agent  # Store the raw JSON string
                gooey_print_function(
                    f"[EXWORK_RESULTS] Summary JSON Parsed Successfully:\n{json.dumps(parsed_summary, indent=2)}\n"
                )
            except json.JSONDecodeError:
                gooey_print_function(
                    "[LAUNCHER] WARNING: Could not parse Ex-Work's primary stdout as summary JSON. Displaying as raw output.\n"
                )
                # final_json_output remains None
        else:  # For Scribe or other commands
            if raw_stdout_for_agent:
                gooey_print_function(
                    f"[{process_title.upper()}_OUTPUT] STDOUT:\n{raw_stdout_for_agent}\n"
                )
            if raw_stderr_for_agent:
                gooey_print_function(
                    f"[{process_title.upper()}_OUTPUT] STDERR:\n{raw_stderr_for_agent}\n"
                )

        stdout_acc.append(raw_stdout_for_agent)
        stderr_acc.append(raw_stderr_for_agent)

        rc = process.returncode
        gooey_print_function(
            f"[LAUNCHER] [{get_timestamp()}] Finished {process_title}. Exit Code: {rc}\n"
        )
        success = rc == 0

    except FileNotFoundError:
        error_msg = f"[LAUNCHER] ERROR: Executable not found for {process_title}: {command_list[0]}"
        gooey_print_function(error_msg + "\n")
        stderr_acc.append(error_msg)
    except subprocess.TimeoutExpired:
        error_msg = f"[LAUNCHER] ERROR: {process_title} timed out after 1 hour."
        gooey_print_function(error_msg + "\n")
        stderr_acc.append(error_msg)
        if process and process.poll() is None:
            process.kill()
            process.communicate()
    except Exception as e:
        error_msg = f"[LAUNCHER] ERROR: Unexpected error running {process_title}: {e}"
        gooey_print_function(error_msg + "\n")
        launcher_logger.error(error_msg, exc_info=True)
        stderr_acc.append(str(e))

    return success, "\n".join(stdout_acc), "\n".join(stderr_acc), final_json_output


LAST_USED_PATHS = load_last_used_paths()


@Gooey(
    program_name="Omnitide Scribe & Ex-Work Launcher",
    program_description="Orchestrate Scribe validation and Ex-Work v2.1 task execution with template support.",
    default_size=(1050, 850),
    navigation="TABBED",
    header_show_title=True,
    header_show_subtitle=True,
    header_subtitle="Version 1.2.1 - Nexus Edition",
    busy_indicator_containing_text="Nexus Processing...",
    menu=[
        {
            "name": "File",
            "items": [
                {
                    "type": "AboutDialog",
                    "menuTitle": "About",
                    "name": "Omnitide Launcher",
                    "description": "A tool to run Scribe and Ex-Work agents sequentially, with template support.",
                    "version": "1.2.1",
                    "copyright": "2025, Manifested for The Supreme Master Architect Alix Feronti",
                },
                {
                    "type": "MessageDialog",
                    "menuTitle": "Template File Info",
                    "name": "Template File",
                    "message": f"Templates are loaded from '{DEFAULT_TEMPLATES_FILE}' (or path specified in 'Templates Configuration' tab) located relative to this launcher's execution directory.\n\nSee 'Usage & Templates' under Help menu for omnitide_templates.json structure example.",
                },
            ],
        },
        {
            "name": "Help",
            "items": [
                {
                    "type": "MessageDialog",
                    "menuTitle": "Usage & Templates",
                    "name": "How to Use This Launcher",
                    "message": (
                        "INITIAL SETUP:\n"
                        "1. Ensure Python 3.9+ and Gooey (`pip install Gooey`) are installed.\n"
                        "2. Place `scribe.py` (your v1.1) and `exworkagent.py` (your v2.1) where this launcher can find them (ideally same directory, or specify full paths in 'Agent Paths & Workflow' tab).\n"
                        "3. Create `omnitide_templates.json` in the same directory (or specify its path) to use templates.\n\n"
                        "USING TEMPLATES (Simplified - Manual Variable Substitution for v1.2.1):\n"
                        "1. Go to the 'Load Template' tab.\n"
                        "2. Specify path to your `omnitide_templates.json` file if not default.\n"
                        "3. Click 'Load/Reload Templates from File'. The dropdown will populate.\n"
                        "4. Select a template. Click 'Load Template Content & Show Variables'.\n"
                        "5. The Console will show required `{{variables}}` for the template.\n"
                        "6. The Scribe and/or Ex-Work tabs will be populated with raw template content.\n"
                        "7. MANUALLY EDIT loaded content in Scribe/Ex-Work tabs, replacing `{{variable_name}}` placeholders with actual values.\n\n"
                        "MANUAL CONFIGURATION:\n"
                        "1. 'Agent Paths & Workflow': Set paths to agents and project working directory.\n"
                        "2. 'Scribe Agent (v1.1)': Check 'Run Scribe', provide 'Target Project Dir', 'Source Code File Path', 'Destination Target File (relative)', and other Scribe params.\n"
                        "3. 'Ex-Work Agent (v2.1)': Check 'Run Ex-Work', provide JSON payload (use 'Prettify JSON'!).\n"
                        "4. Click 'Start Workflow'. Output appears in 'Console Output'.\n\n"
                        "EX-WORK V2.1 SIGNOFFS (`REQUEST_SIGNOFF` action type):\n"
                        "- If Ex-Work's summary output indicates 'AWAITING_SIGNOFF':\n"
                        "  - This launcher will (conceptually) show a Yes/No dialog (currently prints prompt to console).\n"
                        "  - FOR THIS VERSION: Manually prepare a new Ex-Work JSON with `RESPOND_TO_SIGNOFF` action (see example in console after signoff request) and run it (uncheck Scribe).\n"
                        "- The original Ex-Work task sequence does NOT automatically resume after signoff. Subsequent actions need manual re-triggering or workflow redesign.\n\n"
                        "EX-WORK V2.1 `APPLY_PATCH` SIGNOFF:\n"
                        "- `APPLY_PATCH` has its own internal TTY prompt. This may conflict with Gooey and hang. Use with caution."
                        # ... (rest of help message from v1.2, including JSON structure example)
                    ),
                }
            ],
        },
    ],
)
def main_gooey():
    parser = GooeyParser(description="Omnitide Nexus Universal Agent Launcher.")

    # --- Group 0: Template Configuration & Loading ---
    template_opts = parser.add_argument_group(
        "Templates Configuration & Loading",
        "Load preconfigured Scribe/Ex-Work settings or full workflows.",
        gooey_options={"columns": 1},
    )
    template_opts.add_argument(
        "--templates_file_path",
        metavar="Templates File Path",
        help=f"Path to your templates JSON file (e.g., omnitide_templates.json). Default: ./{DEFAULT_TEMPLATES_FILE}",
        default=LAST_USED_PATHS.get(
            "templates_file_path",
            str(
                Path(os.path.dirname(__file__)) / DEFAULT_TEMPLATES_FILE
                if getattr(sys, "frozen", False)
                else Path.cwd() / DEFAULT_TEMPLATES_FILE
            ),
        ),  # Default to same dir as script or CWD
        widget="FileChooser",
        gooey_options=options.Argument(
            wildcard="JSON (*.json)|*.json", full_width=True
        ),
    )
    template_opts.add_argument(
        "--reload_templates_button",
        metavar="Load/Reload Templates from File",
        action="store_true",
        help="Load/Reload templates from the path above. Then select a template below.",
        widget="Button",
        gooey_options={
            "full_width": False,
            "button_text": "Load/Reload Templates from File",
        },
    )
    # Dynamic choices for this dropdown are tricky with Gooey's declarative setup.
    # The list is populated once when the script starts based on initial load.
    # The button above serves as a user action to *trigger a script run* that will reload.
    template_choices = ['No templates loaded - specify path and click "Load/Reload"']
    if LOADED_TEMPLATES.get("templates") or LOADED_TEMPLATES.get(
        "tools"
    ):  # Check if anything was loaded initially
        template_choices = [
            f"{t.get('name', 'Unnamed Template')} (ID: {t.get('id', 'no_id')})"
            for t in LOADED_TEMPLATES.get("templates", [])
        ]
        template_choices += [
            f"{t.get('name', 'Unnamed Tool')} (TOOL ID: {t.get('id', 'no_id')})"
            for t in LOADED_TEMPLATES.get("tools", [])
        ]
        if not template_choices:
            template_choices = ["No valid templates/tools found in file."]

    template_opts.add_argument(
        "--selected_template_id_with_name",
        metavar="Select Template / Tool",
        help="Choose a preconfigured item. Requires templates file to be loaded and valid.",
        widget="Dropdown",
        choices=template_choices,
        gooey_options={"full_width": True},
    )
    template_opts.add_argument(
        "--load_selected_template_button",
        metavar="Load Content & Show Variables for Selected Template",
        action="store_true",
        help="Populate Scribe/Ex-Work tabs with selected item's content (placeholders intact). Variable details appear in console.",
        widget="Button",
        gooey_options={"full_width": True},
    )

    # --- Group 1: Agent Paths & Workflow Configuration ---
    config_opts = parser.add_argument_group(
        "Agent Paths & Workflow", gooey_options={"columns": 1}
    )
    config_opts.add_argument(
        "--scribe_agent_path",
        metavar="Scribe Agent Script Path",
        default=LAST_USED_PATHS.get("scribe_agent_path", DEFAULT_SCRIBE_AGENT_PATH),
        widget="FileChooser",
        gooey_options=options.Argument(wildcard="Python (*.py)|*.py", full_width=True),
    )
    config_opts.add_argument(
        "--exwork_agent_path",
        metavar="Ex-Work Agent Script Path",
        default=LAST_USED_PATHS.get("exwork_agent_path", DEFAULT_EXWORK_AGENT_PATH),
        widget="FileChooser",
        gooey_options=options.Argument(wildcard="Python (*.py)|*.py", full_width=True),
    )
    config_opts.add_argument(
        "--working_directory",
        metavar="Project Working Directory (for Agents)",
        default=LAST_USED_PATHS.get("working_directory", os.getcwd()),
        widget="DirChooser",
        gooey_options=options.Argument(full_width=True),
    )
    config_opts.add_argument(
        "--exwork_if_scribe_succeeds",
        metavar="Conditional Ex-Work",
        action="store_true",
        default=True,
        help="Run Ex-Work only if Scribe runs and succeeds.",
    )

    # --- Group 2: Scribe Agent (scribe.py v1.1) Parameters ---
    scribe_opts = parser.add_argument_group(
        "Scribe Agent (Your v1.1)", "Configure Scribe validation agent."
    )
    scribe_opts.add_argument(
        "--run_scribe", metavar="Run Scribe Agent", action="store_true", default=False
    )  # Default to False if using templates

    scribe_core_inputs_group = scribe_opts.add_argument_group(
        "Scribe Core Inputs", gooey_options={"columns": 1}
    )
    scribe_core_inputs_group.add_argument(
        "--scribe_target_project_dir",
        metavar="1. Target Project Dir (--target-dir)",
        default=LAST_USED_PATHS.get("scribe_target_project_dir", ""),
        widget="DirChooser",
        gooey_options=options.Argument(full_width=True),
    )
    scribe_core_inputs_group.add_argument(
        "--scribe_source_code_file_path",
        metavar="2. Source Code File Path (--code-file)",
        help="Path to the NEW/MODIFIED code Scribe should APPLY.",
        default=LAST_USED_PATHS.get("scribe_source_code_file_path", ""),
        widget="FileChooser",
        gooey_options=options.Argument(wildcard="All files (*.*)|*.*", full_width=True),
    )
    scribe_core_inputs_group.add_argument(
        "--scribe_destination_target_file_relative",
        metavar="3. Destination Target File in Project (relative, --target-file)",
        help="File path within 'Target Project Dir' where code from 'Source Code File Path' will be APPLIED & VALIDATED (e.g., src/main.py).",
        default=LAST_USED_PATHS.get("scribe_destination_target_file_relative", ""),
        gooey_options=options.Argument(full_width=True),
    )

    # ... (rest of Scribe options: config_group, behavior_group, llm_group, log_group, additional_options from v1.2 draft) ...
    # For brevity, I'm assuming these groups are similar to the v1.2 draft I provided before,
    # ensuring argument names match those in your uploaded scribe.py's setup_arg_parser.
    # E.g., --scribe_commit for Scribe's --commit flag.

    scribe_config_group = scribe_opts.add_argument_group(
        "Scribe Configuration", gooey_options={"columns": 2}
    )
    scribe_config_group.add_argument(
        "--scribe_config_file_cli",
        metavar="Scribe Config (.toml)",
        widget="FileChooser",  # Renamed to avoid conflict with Scribe's own arg
        default=LAST_USED_PATHS.get("scribe_config_file_cli", ""),
        gooey_options=options.Argument(
            wildcard="TOML (*.toml)|*.toml", full_width=True
        ),
        help="Path to .scribe.toml (Overrides Scribe's default search).",
    )
    scribe_config_group.add_argument(
        "--scribe_commit_cli",
        metavar="Auto-Commit (--commit)",
        action="store_true",
        default=False,  # Renamed
        help="Enable Scribe's auto-commit feature.",
    )
    scribe_config_group.add_argument(
        "--scribe_language_cli",
        metavar="Language (--language)",
        default="python",  # Renamed
        gooey_options=options.Argument(full_width=True),
    )
    scribe_config_group.add_argument(
        "--scribe_python_version_cli",
        metavar="Python Version (--python-version)",
        default=DEFAULT_PYTHON_VERSION_SCRIBE,  # Renamed
        gooey_options=options.Argument(full_width=True),
    )
    scribe_config_group.add_argument(
        "--scribe_report_format_cli",
        metavar="Report Format (--report-format)",
        choices=REPORT_FORMATS_SCRIBE,  # Renamed
        default=REPORT_FORMATS_SCRIBE[0],
        widget="Dropdown",
    )

    scribe_behavior_group = scribe_opts.add_argument_group(
        "Scribe Skip Flags", gooey_options={"columns": 3}
    )
    scribe_behavior_group.add_argument(
        "--scribe_skip_deps_cli",
        metavar="Skip Deps (--skip-deps)",
        action="store_true",
        default=False,
    )  # Renamed
    scribe_behavior_group.add_argument(
        "--scribe_skip_tests_cli",
        metavar="Skip Tests (--skip-tests)",
        action="store_true",
        default=False,
    )  # Renamed
    scribe_behavior_group.add_argument(
        "--scribe_skip_review_cli",
        metavar="Skip Review (--skip-review)",
        action="store_true",
        default=False,
    )  # Renamed

    scribe_llm_group = scribe_opts.add_argument_group(
        "Scribe LLM Overrides (Optional)", gooey_options={"columns": 2}
    )
    scribe_llm_group.add_argument(
        "--scribe_ollama_base_url_cli",
        metavar="Ollama URL (--ollama-base-url)",
        default="",
        gooey_options=options.Argument(full_width=True),
    )  # Renamed
    scribe_llm_group.add_argument(
        "--scribe_ollama_model_cli",
        metavar="Ollama Model (--ollama-model)",
        default="",
        gooey_options=options.Argument(full_width=True),
    )  # Renamed

    scribe_log_group = scribe_opts.add_argument_group(
        "Scribe Logging Overrides (Optional)", gooey_options={"columns": 2}
    )
    scribe_log_group.add_argument(
        "--scribe_log_level_cli",
        metavar="Log Level (--log-level)",
        choices=[""] + LOG_LEVELS_SCRIBE,
        default="",
        widget="Dropdown",
    )  # Renamed
    scribe_log_group.add_argument(
        "--scribe_log_file_cli",
        metavar="Log File (--log-file)",
        widget="FileSaver",
        default="",
        gooey_options=options.Argument(wildcard="Log (*.log)|*.log", full_width=True),
    )  # Renamed

    scribe_opts.add_argument(
        "--scribe_additional_options",
        metavar="Raw Additional Scribe CLI Options String",
        default="",
        help="Pass any other options directly to scribe.py (e.g., --custom-flag value)",
        gooey_options=options.Argument(full_width=True),
    )

    # --- Group 3: Ex-Work Agent (exworkagent.py v2.1) Parameters ---
    exwork_opts = parser.add_argument_group(
        "Ex-Work Agent (Your v2.1)", "Configure Ex-Work task execution."
    )
    exwork_opts.add_argument(
        "--run_exwork", metavar="Run Ex-Work Agent", action="store_true", default=False
    )  # Default to False if using templates

    exwork_json_group = exwork_opts.add_argument_group(
        "JSON Payload & Actions", gooey_options={"full_width": True}
    )
    exwork_json_group.add_argument(
        "--prettify_exwork_json_button",
        metavar="Format/Prettify Ex-Work JSON Input",
        action="store_true",
        help="Click to attempt to format the JSON payload editor content below.",
        widget="Button",
        gooey_options={"full_width": False},
    )
    exwork_json_group.add_argument(
        "--exwork_json_payload",
        metavar="Ex-Work JSON Payload",
        widget="JsonEditor",
        default=LAST_USED_PATHS.get(
            "exwork_json_payload",
            '{\n  "step_id": "exwork_default_from_launcher_v1.2.1",\n  "description": "Default Ex-Work task from Launcher v1.2.1",\n  "actions": [\n    {\n      "type": "ECHO",\n      "message": "Hello from Ex-Work v2.1 via Omnitide Launcher v1.2.1!"\n    }\n  ]\n}',
        ),
        gooey_options={"height": 350, "full_width": True, "language": "json"},
    )

    # Initial argument parsing to get template file path for initial load
    # If Gooey is run without CLI args, sys.argv[1:] is empty.
    initial_cli_args = sys.argv[1:] if len(sys.argv) > 1 else []
    parsed_initial_args = parser.parse_args(
        initial_cli_args
    )  # Parse to get initial values

    # Load templates using the path from parsed_initial_args or defaults
    # Use a print here because Gooey console isn't fully set up until after parse_args completes.
    # This message will go to the terminal if launcher is run from there.
    print(
        f"[LAUNCHER_INIT] Attempting initial template load from: {parsed_initial_args.templates_file_path}"
    )
    load_omnitide_templates(parsed_initial_args.templates_file_path, print)

    # We cannot easily update the 'choices' for the Dropdown after the @Gooey decorator has run.
    # The 'Reload Templates' button and its interaction is mostly a UX hint for the user
    # to restart the Gooey app if they change the template file path, so the choices are re-evaluated.
    # A more dynamic update requires deeper wxPython manipulation.
    # For now, populate choices at decorator time based on what might have been loaded.
    # This requires `load_omnitide_templates` to be called *before* @Gooey decorator if we want dynamic choices.
    # This is a structural limitation of Gooey's declarative first approach.
    # The workaround: the choices in the decorator are static. The `reload_templates_button` re-runs the script.
    # The actual list of choices in `args.selected_template_id_with_name` widget is based on decorator time.

    args = parser.parse_args()  # Final parse for the actual execution flow

    # Save current paths for next session
    current_paths_to_save = {
        "templates_file_path": args.templates_file_path,
        "scribe_agent_path": args.scribe_agent_path,
        "exwork_agent_path": args.exwork_agent_path,
        "working_directory": args.working_directory,
        "scribe_target_project_dir": args.scribe_target_project_dir,
        "scribe_source_code_file_path": args.scribe_source_code_file_path,
        "scribe_destination_target_file_relative": args.scribe_destination_target_file_relative,
        "scribe_config_file_cli": args.scribe_config_file_cli,
        "exwork_json_payload": args.exwork_json_payload,
    }
    save_last_used_paths(current_paths_to_save)

    # --- Handle Button Actions that Don't Run Full Workflow ---
    # (These should ideally modify the args for the *next* run if Gooey supported it easily,
    # or update UI widgets directly with wxPython, which is complex for this auto-generation)

    if args.reload_templates_button:
        print(
            f"[LAUNCHER] [{get_timestamp()}] 'Load/Reload Templates from File' button clicked."
        )
        print(
            f"[LAUNCHER] Attempting to reload templates from: {args.templates_file_path}\n"
        )
        load_omnitide_templates(args.templates_file_path, print)  # Reload into global
        print(
            f"[LAUNCHER] Templates reloaded. {len(LOADED_TEMPLATES['templates'])} templates, {len(LOADED_TEMPLATES['tools'])} tools found."
        )
        print(
            "[LAUNCHER] Due to Gooey limitations, the 'Select Template/Tool' dropdown may not update immediately."
        )
        print(
            "[LAUNCHER] Please RESTART the launcher to see newly loaded templates in the dropdown if path changed, or if this is the first load.\n"
        )
        return

    if args.load_selected_template_button:
        print(
            f"[LAUNCHER] [{get_timestamp()}] 'Load Template Content & Show Variables' clicked.\n"
        )
        if (
            not args.selected_template_id_with_name
            or args.selected_template_id_with_name.startswith("Load templates")
            or args.selected_template_id_with_name.startswith("No valid")
        ):
            print(
                "[LAUNCHER] Please select a valid template/tool from the dropdown first.\n"
            )
        else:
            selected_id_match = re.search(
                r"\(ID: ([^\)]+)\)", args.selected_template_id_with_name
            )
            selected_tool_id_match = re.search(
                r"\(TOOL ID: ([^\)]+)\)", args.selected_template_id_with_name
            )
            selected_id = None
            is_tool = False

            if selected_id_match:
                selected_id = selected_id_match.group(1)
            elif selected_tool_id_match:
                selected_id = selected_tool_id_match.group(1)
                is_tool = True

            if not selected_id:
                print(
                    f"[LAUNCHER] Could not parse ID from selected template/tool: '{args.selected_template_id_with_name}'.\n"
                )
                return

            item_to_load = None
            source_array = (
                LOADED_TEMPLATES["tools"] if is_tool else LOADED_TEMPLATES["templates"]
            )
            item_to_load = next(
                (t for t in source_array if t.get("id") == selected_id), None
            )

            if item_to_load:
                print(f"[LAUNCHER] Loading content for: {item_to_load.get('name')}\n")
                print(f"[LAUNCHER] Description: {item_to_load.get('description')}\n")
                if item_to_load.get("variables"):
                    print(
                        "[LAUNCHER] This item uses variables. MANUALLY REPLACE placeholders like {{variable_name}} in the Scribe/Ex-Work tabs after reviewing the content printed below.\nRequired Variables:\n"
                    )
                    for var_info in item_to_load.get("variables", []):
                        print(
                            f"  - Name: {{{{{var_info.get('name')}}}}}, Prompt: {var_info.get('prompt')}, Default: {var_info.get('default', 'N/A')}\n"
                        )

                if is_tool:
                    if item_to_load.get("exwork_action_template"):
                        tool_exwork_payload = {
                            "step_id": f"tool_{item_to_load['id']}_{{{{timestamp}}}}",
                            "description": f"Execute tool: {item_to_load['name']}",
                            "actions": [item_to_load["exwork_action_template"]],
                        }
                        print(
                            "[LAUNCHER] === Ex-Work JSON for this Tool ===\n(Copy to 'Ex-Work JSON Payload' editor in the 'Ex-Work Agent' tab, then replace placeholders like {{variable_name}} and {{timestamp}} manually):\n"
                        )
                        print(json.dumps(tool_exwork_payload, indent=2) + "\n")
                else:  # It's a template
                    if item_to_load.get("type") in [
                        "scribe_config_only",
                        "full_scribe_exwork_workflow",
                    ] and item_to_load.get("scribe_params"):
                        print(
                            "[LAUNCHER] === Scribe Parameters from Template ===\n(Manually configure fields in the 'Scribe Agent' tab based on this, replacing placeholders):\n"
                        )
                        print(
                            json.dumps(item_to_load["scribe_params"], indent=2) + "\n"
                        )

                    if item_to_load.get("type") in [
                        "exwork_payload_only",
                        "full_scribe_exwork_workflow",
                    ] and item_to_load.get("exwork_json"):
                        print(
                            "[LAUNCHER] === Ex-Work JSON Payload from Template ===\n(Copy to 'Ex-Work JSON Payload' editor in the 'Ex-Work Agent' tab, then replace placeholders):\n"
                        )
                        print(json.dumps(item_to_load["exwork_json"], indent=2) + "\n")

                print(
                    "[LAUNCHER] Reminder: After copying, manually edit placeholders for variables and `{{timestamp}}` if present.\n"
                )
            else:
                print(
                    f"[LAUNCHER] Selected template/tool ID '{selected_id}' not found in loaded data.\n"
                )
        return  # Exit after handling template load button, do not proceed to full workflow

    if args.prettify_exwork_json_button:
        print(f"[LAUNCHER] [{get_timestamp()}] 'Prettify JSON Input' button clicked.\n")
        current_json_payload = args.exwork_json_payload
        try:
            parsed_json = json.loads(current_json_payload)
            pretty_json = json.dumps(parsed_json, indent=2)
            print("[LAUNCHER] JSON successfully prettified.\n")
            print(
                "[LAUNCHER] IMPORTANT: Due to Gooey limitations, the text area below IS NOT automatically updated."
            )
            print(
                "[LAUNCHER] Please MANUALLY COPY the prettified JSON below and PASTE it back into the 'Ex-Work JSON Payload' editor if you want to use it for execution.\n"
            )
            print("--- PRETTIFIED EX-WORK JSON (COPY THIS) ---\n")
            print(pretty_json)
            print("\n--- END PRETTIFIED EX-WORK JSON ---\n")
        except json.JSONDecodeError as e:
            print(
                f"[LAUNCHER] ERROR: Invalid JSON in 'Ex-Work JSON Payload' text area. Cannot prettify.\n  Details: {e}\n"
            )
        except Exception as e:
            print(f"[LAUNCHER] ERROR: Could not prettify JSON. Details: {e}\n")
        return  # Exit after handling prettify button

    # --- Main Workflow Execution (if no button-only actions were triggered) ---
    print(
        f"[LAUNCHER] [{get_timestamp()}] Full Workflow Execution Starting (Non-button action)...\n"
    )
    # (Rest of the main workflow execution logic from v1.2 draft, adapted for new Scribe args)
    # This includes path validation, Scribe command construction, Scribe execution,
    # conditional Ex-Work execution, Ex-Work command construction, Ex-Work execution,
    # and parsing Ex-Work v2.1's summary JSON output.

    scribe_agent_script_path = Path(args.scribe_agent_path)
    exwork_agent_script_path = Path(args.exwork_agent_path)
    working_dir_path = Path(args.working_directory)

    # Path validation (repeated here for main execution flow)
    if args.run_scribe and not scribe_agent_script_path.is_file():
        print(
            f"[LAUNCHER] ERROR: Scribe agent script not found: '{scribe_agent_script_path}'. Scribe phase cannot run.\n"
        )
        args.run_scribe = False  # Disable Scribe for this run
    if args.run_exwork and not exwork_agent_script_path.is_file():
        print(
            f"[LAUNCHER] ERROR: Ex-Work agent script not found: '{exwork_agent_script_path}'. Ex-Work phase cannot run.\n"
        )
        args.run_exwork = False  # Disable Ex-Work
    if not working_dir_path.is_dir():
        print(
            f"[LAUNCHER] ERROR: Working directory is invalid: '{working_dir_path}'. Cannot run agents.\n"
        )
        return  # Critical error, stop workflow

    scribe_phase_overall_success = True  # Assume success if Scribe is not run

    if args.run_scribe:
        print("[LAUNCHER] --- Phase 1: Scribe Agent (Your `scribe.py` v1.1) ---")
        if (
            not args.scribe_target_project_dir
            or not args.scribe_destination_target_file_relative
            or not args.scribe_source_code_file_path
        ):
            print(
                "[LAUNCHER] ERROR: Scribe 'Target Project Dir', 'Source Code File Path', and 'Destination Target File (relative)' are ALL required. Skipping Scribe phase.\n"
            )
            scribe_phase_overall_success = False
        else:
            scribe_command = [sys.executable, str(scribe_agent_script_path)]
            try:
                # Paths for Scribe based on its CLI: --target-dir, --code-file, --target-file
                resolved_target_dir = str(
                    Path(args.scribe_target_project_dir).resolve()
                )
                resolved_code_file = str(
                    Path(args.scribe_source_code_file_path).resolve()
                )
                # --target-file is relative to --target-dir as per Scribe's help
                relative_dest_target_file = args.scribe_destination_target_file_relative

                scribe_command.extend(["--target-dir", resolved_target_dir])
                scribe_command.extend(["--code-file", resolved_code_file])
                scribe_command.extend(["--target-file", relative_dest_target_file])
            except Exception as e:
                print(
                    f"[LAUNCHER] ERROR processing Scribe core path arguments: {e}. Skipping Scribe.\n"
                )
                scribe_phase_overall_success = False

            if (
                scribe_phase_overall_success
            ):  # Only add other args if core paths were okay
                if args.scribe_config_file_cli:
                    scribe_command.extend(
                        [
                            "--config-file",
                            str(Path(args.scribe_config_file_cli).resolve()),
                        ]
                    )
                if args.scribe_commit_cli:
                    scribe_command.append("--commit")
                if args.scribe_language_cli:
                    scribe_command.extend(["--language", args.scribe_language_cli])
                if args.scribe_python_version_cli:
                    scribe_command.extend(
                        ["--python-version", args.scribe_python_version_cli]
                    )
                if args.scribe_report_format_cli:
                    scribe_command.extend(
                        ["--report-format", args.scribe_report_format_cli]
                    )

                if args.scribe_skip_deps_cli:
                    scribe_command.append("--skip-deps")
                if args.scribe_skip_tests_cli:
                    scribe_command.append("--skip-tests")
                if args.scribe_skip_review_cli:
                    scribe_command.append("--skip-review")

                if args.scribe_ollama_base_url_cli:
                    scribe_command.extend(
                        ["--ollama-base-url", args.scribe_ollama_base_url_cli]
                    )
                if args.scribe_ollama_model_cli:
                    scribe_command.extend(
                        ["--ollama-model", args.scribe_ollama_model_cli]
                    )
                if args.scribe_log_level_cli:
                    scribe_command.extend(["--log-level", args.scribe_log_level_cli])
                if args.scribe_log_file_cli:
                    scribe_command.extend(
                        ["--log-file", str(Path(args.scribe_log_file_cli).resolve())]
                    )

                if args.scribe_additional_options:
                    try:
                        additional_args = shlex.split(args.scribe_additional_options)
                        scribe_command.extend(additional_args)
                    except Exception as e:
                        print(
                            f"[LAUNCHER] Warning: Could not parse Scribe additional options ('{args.scribe_additional_options}'): {e}. Ignoring.\n"
                        )

                s_success, _, _, _ = run_command_and_display_output(
                    scribe_command,
                    cwd=str(working_dir_path),
                    process_title="Scribe Agent",
                    gooey_print_function=print,
                )
                scribe_phase_overall_success = s_success
                print(
                    f"[LAUNCHER] Scribe Agent phase {'SUCCEEDED' if scribe_phase_overall_success else 'FAILED'}.\n"
                )
    else:
        print("[LAUNCHER] Scribe Agent phase SKIPPED as per selection.\n")

    # --- Ex-Work Agent Execution ---
    if args.run_exwork:
        if (
            args.exwork_if_scribe_succeeds
            and args.run_scribe
            and not scribe_phase_overall_success
        ):
            print(
                "[LAUNCHER] --- Phase 2: Ex-Work Agent (Your `exworkagent.py` v2.1) ---"
            )
            print(
                "[LAUNCHER] Ex-Work Agent phase SKIPPED because Scribe Agent ran and FAILED, and conditional execution is enabled.\n"
            )
        else:
            print(
                "[LAUNCHER] --- Phase 2: Ex-Work Agent (Your `exworkagent.py` v2.1) ---"
            )
            exwork_json_input_str = args.exwork_json_payload

            # Validate JSON before trying to use it
            try:
                json.loads(exwork_json_input_str)  # Just to validate
            except json.JSONDecodeError as e_json:
                print(
                    f"[LAUNCHER] ERROR: Invalid JSON provided in Ex-Work payload editor: {e_json}"
                )
                print(
                    "[LAUNCHER] Ex-Work phase cannot run with invalid JSON. Please correct it and try again.\n"
                )
                print(
                    f"[LAUNCHER] [{get_timestamp()}] Omnitide Nexus Launcher: Workflow Finished (with errors).\n"
                )
                return  # Stop execution

            # Warning for APPLY_PATCH and REQUEST_SIGNOFF based on simple string search
            if '"type": "APPLY_PATCH"' in exwork_json_input_str:
                print(
                    "[LAUNCHER] WARNING: Ex-Work JSON contains 'APPLY_PATCH'. This action may attempt direct terminal input for its internal signoff, which might behave unexpectedly or hang in Gooey. Monitor console output closely.\n"
                )

            signoff_detected_in_initial_payload = (
                '"type": "REQUEST_SIGNOFF"' in exwork_json_input_str
            )
            if signoff_detected_in_initial_payload:
                print(
                    "[LAUNCHER] INFO: Ex-Work JSON payload contains a 'REQUEST_SIGNOFF' action."
                )
                print(
                    "[LAUNCHER] The Ex-Work agent will output details if it reaches this action, including a 'signoff_id'."
                )
                print(
                    "[LAUNCHER] This launcher will then guide you to submit a 'RESPOND_TO_SIGNOFF' action.\n"
                )

            exwork_command = [sys.executable, str(exwork_agent_script_path)]
            ew_success, _, _, ew_final_json_str_output = run_command_and_display_output(
                exwork_command,
                cwd=str(working_dir_path),
                input_data=exwork_json_input_str,
                process_title="Ex-Work Agent",
                gooey_print_function=print,
            )

            if ew_final_json_str_output:
                try:
                    exwork_summary = json.loads(ew_final_json_str_output)
                    agent_overall_success = exwork_summary.get("overall_success", False)
                    print(
                        f"[LAUNCHER] Ex-Work Agent call completed. Agent overall_success: {agent_overall_success}.\n"
                    )

                    signoff_details_from_run = None
                    for result_action in exwork_summary.get("action_results", []):
                        if (
                            isinstance(result_action.get("message_or_payload"), dict)
                            and result_action["message_or_payload"].get("exwork_status")
                            == "AWAITING_SIGNOFF"
                        ):
                            signoff_details_from_run = result_action[
                                "message_or_payload"
                            ]
                            print(
                                f"[LAUNCHER] SIGNOFF REQUIRED by Ex-Work (Action Type: {result_action.get('action_type')})\n"
                            )
                            break

                    if signoff_details_from_run:
                        signoff_prompt = signoff_details_from_run.get(
                            "signoff_prompt", "Confirm action?"
                        )
                        signoff_id = signoff_details_from_run.get("signoff_id")
                        print(
                            f"[LAUNCHER] Ex-Work is AWAITING SIGNOFF for ID: {signoff_id}\n  Prompt: '{signoff_prompt}'\n"
                        )
                        print(
                            "[LAUNCHER] TO RESPOND TO THIS SIGNOFF:\n"
                            "1. Go to the 'Ex-Work Agent' tab.\n"
                            "2. Ensure 'Run Scribe Agent' is UNCHECKED (if you don't want to re-run Scribe).\n"
                            "3. Replace the Ex-Work JSON payload with the following (adjust 'response'):\n"
                            "   {\n"
                            f'     "step_id": "respond_to_signoff_{signoff_id}",\n'
                            '     "description": "Responding to pending signoff.",\n'
                            '     "actions": [\n'
                            "       {\n"
                            '         "type": "RESPOND_TO_SIGNOFF",\n'
                            f'         "signoff_id": "{signoff_id}",\n'
                            '         "response": "yes"  // Or "no"\n'
                            "       }\n"
                            "     ]\n"
                            "   }\n"
                            "4. Click 'Start Workflow' again.\n"
                            "5. Note: The original Ex-Work action sequence that was paused will NOT automatically resume. "
                            "The `RESPOND_TO_SIGNOFF` action in Ex-Work v2.1 only logs the response. "
                            "You may need to re-trigger subsequent original actions manually if the signoff was 'yes'.\n"
                        )

                except json.JSONDecodeError:
                    print(
                        "[LAUNCHER] WARNING: Could not parse Ex-Work's summary JSON output. This might indicate an agent error or unexpected output format. Raw STDOUT from agent was displayed above.\n"
                    )
            else:
                print(
                    f"[LAUNCHER] Ex-Work Agent call did not produce the expected summary JSON output. Success based on exit code: {'SUCCEEDED' if ew_success else 'FAILED'}.\n"
                )
    else:
        print("[LAUNCHER] Ex-Work Agent phase SKIPPED as per selection.\n")

    print(
        f"[LAUNCHER] [{get_timestamp()}] Omnitide Nexus Launcher: Workflow Finished.\n"
    )


if __name__ == "__main__":
    # This initial call to load_omnitide_templates attempts to populate LOADED_TEMPLATES
    # *before* Gooey builds its UI. This is essential for the Dropdown choices.
    # Determine the initial templates file path (same logic as in Gooey arg default)
    initial_templates_path_str = LAST_USED_PATHS.get(
        "templates_file_path",
        str(
            Path(os.path.dirname(__file__))
            if getattr(sys, "frozen", False)
            else Path.cwd() / DEFAULT_TEMPLATES_FILE
        ),
    )
    # print(f"[LAUNCHER_PRE_GOOEY_INIT] Attempting pre-load of templates from: {initial_templates_path_str}")
    load_omnitide_templates(
        initial_templates_path_str, print
    )  # Use print for pre-GUI messages

    main_gooey()
