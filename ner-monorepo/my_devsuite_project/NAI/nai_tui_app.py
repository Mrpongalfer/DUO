import json  # For parsing Scribe's JSON report
import os
import shlex
import subprocess
from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import (
    Container,
    Horizontal,  # Added VerticalScroll
    VerticalScroll,
)
from textual.reactive import reactive
from textual.widgets import (
    Button,
    DirectoryTree,
    Footer,
    Header,
    Input,
    Label,
    Log,
    Markdown,
    Static,
    TabPane,
    Tabs,
    TextArea,
)

# --- Configuration ---
# Ensure these paths match your Dockerfile COPY commands and actual script names
SCRIBE_AGENT_PATH = "/app/scribe_agent.v1.1.py"  # Matches your provided constant
EXWORK_AGENT_PATH = "/app/ex_work_agentv2.py"  # Matches your provided constant
WORKSPACE_ROOT_IN_CONTAINER = Path("/workspace")


# --- Helper for running agent commands ---
def run_agent_command(
    command_list: list[str], cwd: Path, json_input: str | None = None
) -> tuple[int, str, str]:
    """
    Runs an agent command as a subprocess.
    Returns: (return_code, stdout, stderr)
    """
    # Using a logger here would be good for debugging this helper if issues arise
    # logger = logging.getLogger("NAI_AgentRunner") # Requires logging setup for the TUI app
    # logger.debug(f"Running command: {' '.join(shlex.quote(c) for c in command_list)} in {cwd}")
    try:
        process = subprocess.Popen(
            command_list,
            stdin=subprocess.PIPE if json_input else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,  # Decodes output as text
            cwd=cwd,
            env=os.environ.copy(),
            encoding="utf-8",  # Be explicit about encoding
            errors="replace",  # Handle potential encoding errors in output
        )
        stdout, stderr = process.communicate(
            input=json_input,
            timeout=600,  # 10 min timeout, consider making this configurable
        )
        # logger.debug(f"Command finished. RC: {process.returncode}, STDOUT: {stdout[:200]}..., STDERR: {stderr[:200]}...")
        return (
            process.returncode,
            stdout or "",
            stderr or "",
        )  # Ensure stdout/stderr are strings
    except subprocess.TimeoutExpired:
        # logger.error("Command timed out after 10 minutes.")
        return (
            -1,
            "",
            "Command timed out after 10 minutes.",
        )  # Use a distinct RC for timeout
    except Exception as e:
        # logger.error(f"Error running command: {e}", exc_info=True)
        return (
            -2,
            "",
            f"Error running command: {type(e).__name__} - {e}",
        )  # Use a distinct RC for other errors


# --- Main TUI Application ---
class NexusAgentInterfaceApp(App[None]):  # Added type hint for App result
    """A Textual TUI for Scribe and ExWork agents."""

    TITLE = "Nexus Agent Interface (NAI) - V1.1"  # Updated title slightly
    SUB_TITLE = "Orchestrate Scribe & ExWork | Omnitide Nexus"
    CSS_PATH = "nai_tui_styles.css"

    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit NAI", show=True),
        Binding("ctrl+d", "toggle_dark", "Toggle Dark Mode", show=True),
        Binding("f1", "show_help_screen", "Help", show=True),
    ]

    # Reactive variables
    selected_project_path: reactive[Path | None] = reactive(None)
    current_project_display: reactive[str] = reactive("No Project Selected")
    action_in_progress: reactive[bool] = reactive(
        False
    )  # V1.1: Guard for button presses

    def on_mount(self) -> None:
        """Called when app is mounted."""
        log_widget = self.query_one(Log)
        log_widget.write_line("NAI TUI Initialized. Welcome, Architect!")
        log_widget.write_line(
            "1. Select a project from the 'Project Explorer' on the left."
        )
        log_widget.write_line(
            f"   (Explorer root is '{WORKSPACE_ROOT_IN_CONTAINER}' inside the container)."
        )
        log_widget.write_line("2. Navigate to the Scribe or ExWork tab to run actions.")

        try:
            self.query_one(DirectoryTree).path = WORKSPACE_ROOT_IN_CONTAINER
        except Exception as e:
            log_widget.write_line(
                f"[bold red]Error initializing DirectoryTree: {e}. Is /workspace mounted and accessible?[/]"
            )

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="main_layout_horizontal"):
            with VerticalScroll(
                id="sidebar_left", classes="sidebar"
            ):  # Added class for potential styling
                yield Label("Project Explorer (/workspace):")
                yield DirectoryTree(WORKSPACE_ROOT_IN_CONTAINER, id="project_tree")
                yield Static(self.current_project_display, id="current_project_label")

            with Container(
                id="main_content_area"
            ):  # Wrapped tabs and log in a main container
                with Tabs(id="agent_tabs"):
                    with TabPane("Scribe Agent", id="scribe_tab"):
                        yield Label("Scribe Agent Controls:", classes="tab_header")
                        with VerticalScroll():  # V1.1: Added VerticalScroll for Scribe inputs
                            yield Label(
                                "Target File (relative to project root, e.g., src/module.py):"
                            )
                            yield Input(
                                placeholder="e.g., src/main.py or calculator.py",  # Updated placeholder
                                id="scribe_target_file_input",
                            )
                            yield Label(
                                "Code File (full path in container to new/modified code):"
                            )
                            yield Input(
                                placeholder="e.g., /workspace/project/temp_code.py or /tmp/my_changes.py",  # Updated placeholder
                                id="scribe_code_file_input",
                            )
                            yield Label(
                                "Additional Scribe Flags (e.g., --commit --skip-tests --config-file /path/to/.scribe.toml):"
                            )
                            yield Input(
                                placeholder="e.g., --fix --log-level DEBUG",
                                id="scribe_flags_input",
                            )
                            yield Button(
                                "Run Scribe",  # Simplified text
                                id="run_scribe_button",
                                variant="primary",
                                classes="action_button",  # Added class
                            )
                    with TabPane("ExWork Agent", id="exwork_tab"):
                        yield Label("ExWork Agent Controls:", classes="tab_header")
                        yield Label("ExWork JSON Input:", classes="sub_header_label")
                        yield TextArea(
                            "",  # Start with empty text
                            language="json",
                            show_line_numbers=True,
                            id="exwork_json_input",
                            classes="json_input_area",
                        )
                        yield Label(
                            "Quick Actions (Examples - loads JSON below):",  # Clarified
                            classes="sub_header_label",
                        )
                        with Horizontal(
                            classes="quick_action_buttons"
                        ):  # Group buttons
                            yield Button(
                                "Create README",
                                id="exwork_action_create_readme",
                                variant="success",
                            )
                            yield Button(
                                "Git Add & Commit All",
                                id="exwork_action_git_commit_all",
                                variant="success",
                            )
                        yield Button(
                            "Execute Custom ExWork JSON",
                            id="run_exwork_button",
                            variant="primary",
                            classes="action_button",
                        )

                    with TabPane("Help / About", id="help_tab"):
                        yield Markdown(self.get_help_text(), id="help_markdown")

                yield Log(
                    id="output_log", highlight=True, classes="output_log_area"
                )  # Removed markup=True
        yield Footer()

    def get_help_text(self) -> str:
        # (Your existing get_help_text method is good, no changes needed unless you want to update it)
        return """
# Nexus Agent Interface (NAI) - Help V1.1

## Quick Start
1.  **Select Project:** Use the Project Explorer on the left to click on a directory within `/workspace`.
    This `/workspace` inside the TUI corresponds to the host directory you mounted when running Docker
    (e.g., `-v /path/to/your/projects:/workspace/your_project_name`).
2.  **Scribe Agent:**
    * Go to the "Scribe Agent" tab.
    * **Target File:** Enter the relative path within the selected project (e.g., `src/calculator.py`).
    * **Code File:** Enter the full path *inside the container* to the file containing the new code Scribe should apply (e.g., `/workspace/your_project_name/new_code_for_calculator.py`).
    * Enter any additional flags for Scribe (e.g., `--fix`, `--config-file /mnt/scribe_config/.scribe.toml`).
    * Click "Run Scribe." Output appears in the Log below.
3.  **ExWork Agent:**
    * Go to the "ExWork Agent" tab.
    * Paste your ExWork JSON instruction block into the text area or use a Quick Action.
    * Click "Execute Custom ExWork JSON." Output appears in the Log.

## Key Bindings
* `Ctrl+Q`: Quit NAI
* `Ctrl+D`: Toggle Dark/Light Mode
* `F1`: Show this Help Screen (or switch to Help Tab)

## Agents
* **ScribeAgent (`/app/scribe_agent.v1.1.py`):** Validates code quality, formatting, types, etc.
* **ExWorkAgent (`/app/ex_work_agentv2.py`):** Executes structured JSON commands.

*More features and Harley's flair coming soon!*
        """

    def on_directory_tree_directory_selected(
        self, event: DirectoryTree.DirectorySelected
    ) -> None:
        """Called when a directory is selected in the tree."""
        log_widget = self.query_one(Log)
        self.selected_project_path = event.path

        safe_path_repr = repr(event.path)  # V1.1: For safe logging
        log_widget.write_line(
            f"Project context selected: {safe_path_repr}"  # Simplified log message
        )

        try:
            display_name = event.path.name
        except Exception as e:
            display_name = "Error_Reading_Name"
            log_widget.write_line(
                f"[bold red]Error getting path name for display: {e}[/]"
            )

        self.current_project_display = (
            f"Project: {display_name}"  # Update reactive var, Static widget will follow
        )

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Event handler called when a button is pressed."""
        log_widget = self.query_one(Log)

        if self.action_in_progress:
            log_widget.write_line(
                "[bold yellow]! Action already in progress. Please wait for it to complete.[/]"
            )
            return

        self.action_in_progress = True  # Set lock

        try:
            # Project selection check for actions that require it
            if event.button.id in [
                "run_scribe_button",
                "run_exwork_button",
                "exwork_action_create_readme",
                "exwork_action_git_commit_all",
            ]:
                if self.selected_project_path is None:
                    log_widget.write_line(
                        "[bold red]ERROR: No project directory selected! "
                        "Please select a project from the explorer on the left.[/]"
                    )
                    return  # Return early from the try block

                log_widget.write_line(
                    f"--- Attempting action in project: {self.selected_project_path} ---"
                )

            # --- Scribe Agent Logic ---
            if event.button.id == "run_scribe_button":
                target_file_rel_path_input = self.query_one(
                    "#scribe_target_file_input", Input
                )
                code_file_abs_path_input = self.query_one(
                    "#scribe_code_file_input", Input
                )
                scribe_flags_input = self.query_one("#scribe_flags_input", Input)

                target_file_rel_path = target_file_rel_path_input.value.strip()
                code_file_abs_path = code_file_abs_path_input.value.strip()
                scribe_flags_str = scribe_flags_input.value.strip()

                log_widget.write_line(
                    f"[dim]Debug Scribe Inputs - Target File: '{target_file_rel_path}', Code File: '{code_file_abs_path}', Flags: '{scribe_flags_str}'[/dim]"
                )

                if not target_file_rel_path:
                    log_widget.write_line(
                        "[bold red]ERROR: Scribe 'Target File' path is required and cannot be empty![/]"
                    )
                    target_file_rel_path_input.focus()
                    return
                if not code_file_abs_path:
                    log_widget.write_line(
                        "[bold red]ERROR: Scribe 'Code File' path is required and cannot be empty![/]"
                    )
                    code_file_abs_path_input.focus()
                    return
                if (
                    not self.selected_project_path
                ):  # Should be caught above, but defensive
                    log_widget.write_line(
                        "[bold red]ERROR: No project selected for Scribe![/]"
                    )
                    return

                scribe_flags_list = shlex.split(scribe_flags_str)
                command_list = [
                    "python",
                    SCRIBE_AGENT_PATH,
                    "--target-dir",
                    str(self.selected_project_path),
                    "--code-file",
                    code_file_abs_path,
                    "--target-file",
                    target_file_rel_path,
                    "--report-format",
                    "json",  # Always get JSON for potential TUI parsing
                ] + scribe_flags_list

                log_widget.write_line(
                    f"[bold blue]Executing Scribe: {' '.join(shlex.quote(c) for c in command_list)}[/]"
                )
                log_widget.write_line(
                    "[italic]Scribe agent running... please wait.[/italic]"
                )

                return_code, stdout, stderr = await self.app.run_cpu_bound(
                    run_agent_command,
                    command_list,
                    self.selected_project_path,  # CWD for agent process
                )

                log_widget.write_line(
                    f"[bold]Scribe Agent Finished (Exit Code: {return_code})[/bold]"
                )
                if (
                    stderr
                ):  # Log stderr first as it often contains important error details
                    log_widget.write_line("[bold red]--- Scribe STDERR ---[/]")
                    log_widget.write_line(stderr)
                if stdout:
                    log_widget.write_line(
                        "[bold green]--- Scribe JSON Report (STDOUT) ---[/]"
                    )
                    log_widget.write_line(stdout)  # Dump raw JSON for now

                if return_code == 0:
                    try:
                        report_data = json.loads(stdout)
                        if report_data.get("overall_status") == "SUCCESS":
                            log_widget.write_line(
                                "[bold green]Scribe: Workflow SUCCESSFUL! ✨[/]"
                            )
                        else:
                            log_widget.write_line(
                                f"[bold orange_red1]Scribe: Workflow COMPLETED WITH ISSUES (Overall Status: {report_data.get('overall_status', 'UNKNOWN')}). Review report.[/]"
                            )
                    except json.JSONDecodeError:
                        log_widget.write_line(
                            "[bold red]Scribe: Output was not valid JSON. Operation status unclear based on report content.[/]"
                        )
                elif return_code == 2:  # Argparse error from Scribe
                    log_widget.write_line(
                        "[bold red]Scribe: FAILED due to argument error. Ensure Target File, Code File, and Target Dir are provided correctly and paths are valid.[/]"
                    )
                else:
                    log_widget.write_line(
                        f"[bold red]Scribe: Operation FAILED (Exit Code: {return_code})! Check STDERR and Scribe logs. ❗💔[/]"
                    )

            # --- ExWork Agent Logic ---
            elif event.button.id == "run_exwork_button":
                json_input_str = self.query_one("#exwork_json_input", TextArea).text
                if not json_input_str.strip():
                    log_widget.write_line(
                        "[bold red]ERROR: ExWork JSON input is empty![/]"
                    )
                    return
                if not self.selected_project_path:
                    return  # Already checked but defensive

                command_list = ["python", EXWORK_AGENT_PATH]
                log_widget.write_line(
                    f"[bold blue]Executing ExWork with provided JSON in {self.selected_project_path}...[/]"
                )
                log_widget.write_line(
                    "[italic]ExWork agent running... please wait.[/italic]"
                )

                return_code, stdout, stderr = await self.app.run_cpu_bound(
                    run_agent_command,
                    command_list,
                    self.selected_project_path,
                    json_input_str,
                )

                log_widget.write_line(
                    f"[bold]ExWork Agent Finished (Exit Code: {return_code})[/bold]"
                )
                if stderr:  # Log stderr first
                    log_widget.write_line("[bold red]--- ExWork STDERR ---[/]")
                    log_widget.write_line(stderr)
                if stdout:  # ExWork's primary output with results is stdout
                    log_widget.write_line(
                        "[bold green]--- ExWork JSON Response (STDOUT) ---[/]"
                    )
                    log_widget.write_line(stdout)

                if (
                    return_code == 0
                ):  # Check ExWork's own overall_success in its JSON output
                    try:
                        exwork_response_data = json.loads(stdout)
                        if exwork_response_data.get("overall_success", False):
                            log_widget.write_line(
                                "[bold green]ExWork: Operation SUCCEEDED! 🎉🚀[/]"
                            )
                        else:
                            log_widget.write_line(
                                "[bold orange_red1]ExWork: Operation COMPLETED WITH ISSUES (Overall Success: false). Review response.[/]"
                            )
                    except json.JSONDecodeError:
                        log_widget.write_line(
                            "[bold red]ExWork: Output was not valid JSON. Operation status unclear.[/]"
                        )
                else:
                    log_widget.write_line(
                        f"[bold red]ExWork: Operation FAILED (Exit Code: {return_code})! Check STDERR. ❗💔[/]"
                    )

            elif event.button.id == "exwork_action_create_readme":
                readme_content = "# My Awesome Project\n\nThis README was generated by NAI TUI + ExWork!\n\n## TODO\n- Fill this in!"
                readme_content_b64 = base64.b64encode(
                    readme_content.encode("utf-8")
                ).decode("utf-8")
                readme_json = f"""
                {{
                    "step_id": "NAICreateBasicREADME",
                    "description": "Create a basic README.md file via NAI.",
                    "actions": [
                        {{
                            "type": "CREATE_OR_REPLACE_FILE",
                            "path": "README_NAI.md",
                            "content_base64": "{readme_content_b64}"
                        }}
                    ]
                }}
                """
                self.query_one("#exwork_json_input", TextArea).text = (
                    readme_json.strip()
                )
                log_widget.write_line(
                    "Loaded 'Create README.md' ExWork JSON into input area. Click 'Execute Custom ExWork JSON'."
                )

            elif event.button.id == "exwork_action_git_commit_all":
                commit_json_template = """
                {
                    "step_id": "NAIGitAddCommitAll",
                    "description": "Stage all changes in the current project and commit with a default NAI message.",
                    "actions": [
                        {
                            "type": "GIT_ADD",
                            "paths": ["."]
                        },
                        {
                            "type": "GIT_COMMIT",
                            "message": "NAI TUI: Auto-commit all changes.",
                            "allow_empty": false
                        }
                    ]
                }
                """
                self.query_one("#exwork_json_input", TextArea).text = (
                    commit_json_template.strip()
                )
                log_widget.write_line(
                    "Loaded 'Git Add & Commit All' ExWork JSON into input area. Click 'Execute Custom ExWork JSON'."
                )

            log_widget.write_line("--- UI Action complete ---")

        finally:
            self.action_in_progress = False  # Reset lock

    def action_show_help_screen(self) -> None:
        """Action to switch to the help tab."""
        try:
            self.query_one(Tabs).active = "help_tab"
            self.query_one(Log).write_line("Switched to Help / About tab.")
        except Exception as e:
            self.query_one(Log).write_line(
                f"[bold red]Error switching to help tab: {e}[/]"
            )


if __name__ == "__main__":
    app = NexusAgentInterfaceApp()
    app.run()
