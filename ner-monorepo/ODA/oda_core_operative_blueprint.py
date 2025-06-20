#!/usr/bin/env python3
# Omnitide Development Agent (ODA) v0.1 - Core Operative Blueprint
# MVP Implementation focused on Python CLI Scaffolding
# Author: Drake v0.1 (Primed via Edict Ritual)
# Timestamp: 2025-05-08

import json  # Or YAML, depending on chosen Primed State format
import os
import shutil
import stat
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import typer
from jinja2 import Environment, FileSystemLoader  # Import Jinja2
from rich.console import Console
from rich.prompt import Confirm, Prompt


# PrimedOperationalState Class (as defined in previous response Part 1)
class PrimedOperationalState:
    # --- Assume class is defined here exactly as in Part 1 ---
    def __init__(self, config_path: Path):
        self.config_path = config_path
        self._config_data: Dict[str, Any] = {}
        self._load_config()

    def _load_config(self):
        console.print(
            f"[cyan]ODA: Loading Primed Operational State from '{self.config_path}'...[/cyan]"
        )
        if not self.config_path.is_file():
            console.print(
                f"[bold red]FATAL ERROR:[/bold red] Primed State file not found at '{self.config_path}'. ODA cannot operate."
            )
            console.print(
                "Please run the ODA Prime Ritual first or create the file manually."
            )
            raise typer.Exit(code=1)
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                # Using JSON load as example
                self._config_data = json.load(f)
            console.print("[green]✓[/green] Primed State loaded successfully.")
            self._validate_loaded_config()
        except Exception as e:
            console.print(
                f"[bold red]FATAL ERROR:[/bold red] Failed to load or parse Primed State file '{self.config_path}': {e}"
            )
            raise typer.Exit(code=1)

    def _validate_loaded_config(self):
        # Simplified validation for MVP
        if (
            "architect_identity" not in self._config_data
            or "tpc_standards" not in self._config_data
        ):
            console.print(
                "[yellow]Warning:[/yellow] Primed State appears incomplete. Using defaults where possible."
            )
        # In full impl, validate against a schema derived from Edicts

    def get_param(self, section: str, key: str, default: Any = None) -> Any:
        return self._config_data.get(section, {}).get(key, default)

    def get_section(self, section: str, default: Optional[Dict] = None) -> Dict:
        """Retrieve an entire configuration section."""
        if default is None:
            default = {}  # Ensure default is always a dict if None
        return self._config_data.get(section, default)

    # --- End of PrimedOperationalState ---


# InteractionManager Class (as defined in previous response Part 1)
class InteractionManager:
    # --- Assume class is defined here exactly as in Part 1 ---
    def __init__(self, console: Console, primed_state: PrimedOperationalState):
        self.console = console
        self.primed_state = primed_state
        self.communication_style = self.primed_state.get_param(
            "interaction_protocols", "style", "direct"
        )

    def greet(self):
        arch_name = self.primed_state.get_param(
            "architect_identity", "name", "Architect"
        )
        self.console.print(
            f"[bold cyan]ODA v0.1 (Primed)[/bold cyan]: Ready for directives, Supreme Master Architect {arch_name}."
        )

    def elicit_requirement(
        self,
        prompt_text: str,
        choices: Optional[List[str]] = None,
        default: Any = None,
        password: bool = False,
    ) -> Any:
        if choices:
            # Ensure default is one of the choices if provided
            valid_default = default if default in choices else None
            return Choice.ask(prompt_text, choices=choices, default=valid_default)
        else:
            return Prompt.ask(prompt_text, default=default, password=password)

    def confirm_action(self, prompt_text: str, default: bool = True) -> bool:
        # Use primed state to decide if confirmation is needed
        if not self.primed_state.get_param(
            "interaction_protocols", "confirm_major_actions", True
        ):
            return True  # Auto-confirm if configured
        return Confirm.ask(prompt_text, default=default)

    def present_information(self, text: str, style: str = "info"):
        prefix_map = {
            "info": "[cyan]i[/cyan]",
            "warning": "[yellow]⚠[/yellow]",
            "error": "[red]✗[/red]",
            "success": "[green]✓[/green]",
        }
        prefix = prefix_map.get(style, "[cyan]i[/cyan]")
        self.console.print(f"{prefix} {text}")

    def process_feedback(self, feedback_text: str):
        # MVP: Just log to console
        log_file = Path("oda_feedback_log.txt")
        try:
            with log_file.open("a", encoding="utf-8") as f:
                from datetime import datetime

                f.write(f"{datetime.now().isoformat()} - FEEDBACK: {feedback_text}\n")
            self.present_information("Feedback logged.", style="success")
        except Exception as e:
            self.present_information(f"Failed to log feedback: {e}", style="error")

    # --- End of InteractionManager ---


# ToolOrchestrator Class (as defined in previous response Part 1)
class ToolOrchestrator:
    # --- Assume class is defined here exactly as in Part 1, using run_command ---
    def __init__(self, console: Console, primed_state: PrimedOperationalState):
        self.console = console
        self.primed_state = primed_state

    def run_command(
        self, command: List[str], cwd: Path, desc: str, sensitive_output: bool = False
    ) -> Tuple[bool, str, str]:
        self.console.print(
            f"[cyan]-> ODA Executing:[/cyan] '{' '.join(command)}' in '{cwd}' ({desc})..."
        )
        timeout = self.primed_state.get_param(
            "operational_philosophy", "default_timeout", 300
        )

        try:
            process = subprocess.Popen(
                command,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                shell=False,
            )
            stdout, stderr = process.communicate(timeout=timeout)

            if process.returncode == 0:
                self.console.print(f"[green]✓[/green] ODA Execution Success: {desc}")
                if stdout and stdout.strip() and not sensitive_output:
                    self.console.print(f"   [dim Output:]\n{stdout.strip()}[/dim]")
                return True, stdout or "", stderr or ""
            else:
                self.console.print(
                    f"[red]✗[/red] ODA Execution Failed: {desc} (Code: {process.returncode})"
                )
                stdout_clean = stdout.strip() if stdout else ""
                stderr_clean = stderr.strip() if stderr else ""
                if stdout_clean:
                    self.console.print(f"   [dim red]STDOUT:\n{stdout_clean}[/dim red]")
                if stderr_clean:
                    self.console.print(f"   [dim red]STDERR:\n{stderr_clean}[/dim red]")
                return False, stdout_clean, stderr_clean
        except subprocess.TimeoutExpired:
            self.console.print(
                f"[red]✗[/red] ODA Execution Timeout: {desc} exceeded {timeout} seconds."
            )
            return False, "", "Timeout occurred"
        except FileNotFoundError:
            self.console.print(
                f"[red]✗[/red] ODA Execution Error: Command '{command[0]}' not found."
            )
            return False, "", f"Command not found: {command[0]}"
        except Exception as e:
            self.console.print(
                f"[red]✗[/red] ODA Execution Error: Unexpected issue running {desc}: {e}"
            )
            return False, "", str(e)

    # --- End of ToolOrchestrator ---


# ProjectScaffolder Class (Now with MVP implementations)
class ProjectScaffolder:
    """Handles the logic for scaffolding new projects."""

    def __init__(
        self,
        interaction_mgr: InteractionManager,
        tool_orchestrator: ToolOrchestrator,
        primed_state: PrimedOperationalState,
    ):
        self.im = interaction_mgr
        self.tools = tool_orchestrator
        self.state = primed_state
        # Template path derived from primed state
        template_source_type = self.state.get_param("template_sources", "type", "local")
        if template_source_type != "local":
            # For MVP, only support local. Full impl would handle Git etc.
            self.im.present_information(
                "Only 'local' template source type supported in MVP.", style="error"
            )
            raise typer.Exit(1)
        template_path_str = self.state.get_param(
            "template_sources", "path", "./oda_templates"
        )
        self.template_base_path = Path(template_path_str).resolve()
        if not self.template_base_path.is_dir():
            self.im.present_information(
                f"Template base path does not exist or is not a directory: {self.template_base_path}",
                style="error",
            )
            self.im.present_information(
                "Please run ForgeTemplateInitializer or configure the correct path.",
                style="info",
            )
            raise typer.Exit(1)
        # Initialize Jinja environment here for efficiency
        self.jinja_env = Environment(
            loader=FileSystemLoader(self.template_base_path),
            autoescape=True,
            trim_blocks=True,
            lstrip_blocks=True,
        )

    # _get_template_path, _render_template_to_project, _copy_static_template, _make_project_file_executable (Implementations)
    def _get_template_path(self, relative_path: str) -> Path:
        """Resolves the path to a template file within the configured base path."""
        # Security check: Ensure relative_path doesn't try to escape the base path
        # Using resolve() helps, but explicit check is good
        target_path = (self.template_base_path / relative_path).resolve()
        if not str(target_path).startswith(str(self.template_base_path.resolve())):
            self.im.present_information(
                f"Security Alert: Invalid template path detected: {relative_path}",
                style="error",
            )
            raise ValueError(f"Attempted path traversal: {relative_path}")

        if not target_path.exists():
            self.im.present_information(
                f"Required template file not found: {target_path}", style="error"
            )
            raise FileNotFoundError(f"Required template not found: {target_path}")

        return target_path

    def _render_template_to_project(
        self,
        template_rel_path: str,
        context: Dict[str, Any],
        output_rel_path: str,
        project_root: Path,
    ):
        """Renders a template file into the target project directory."""
        output_abs_path = project_root / output_rel_path
        try:
            # Jinja env initialized in __init__ now uses the base path loader
            template = self.jinja_env.get_template(
                template_rel_path
            )  # Use relative path here
            rendered_content = template.render(context)

            output_abs_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_abs_path, "w", encoding="utf-8") as f:
                f.write(rendered_content)
            self.im.present_information(
                f"Generated: {output_abs_path.relative_to(project_root)}",
                style="success",
            )
            return True
        except FileNotFoundError:
            # Jinja's get_template will raise TemplateNotFound, a subclass of OSError/IOError
            self.im.present_information(
                f"Template not found by Jinja: {template_rel_path}", style="error"
            )
            return False
        except Exception as e:
            self.im.present_information(
                f"Failed to render template {template_rel_path} to {output_rel_path}: {e}",
                style="error",
            )
            return False

    def _copy_static_template(
        self, template_rel_path: str, output_rel_path: str, project_root: Path
    ):
        """Copies a static file from the template source to the project."""
        output_abs_path = project_root / output_rel_path
        try:
            template_abs_path = self._get_template_path(
                template_rel_path
            )  # Resolves and checks existence

            output_abs_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(template_abs_path, output_abs_path)
            self.im.present_information(
                f"Copied:    {output_abs_path.relative_to(project_root)}",
                style="success",
            )
            return True
        except FileNotFoundError as e:
            # Should be caught by _get_template_path, but handle defensively
            self.im.present_information(
                f"Static template not found: {template_rel_path} -> {e}", style="error"
            )
            return False
        except Exception as e:
            self.im.present_information(
                f"Failed to copy static template {template_rel_path} to {output_rel_path}: {e}",
                style="error",
            )
            return False

    def _make_project_file_executable(self, file_rel_path: Path, project_root: Path):
        """Makes a file within the generated project executable."""
        abs_path = project_root / file_rel_path
        if not abs_path.exists():
            self.im.present_information(
                f"Cannot make executable, file not found: {file_rel_path}",
                style="warning",
            )
            return
        try:
            st = os.stat(abs_path)
            # Ensure user has execute permission before adding group/other
            os.chmod(
                abs_path,
                st.st_mode
                | stat.S_IEXEC
                | (stat.S_IXGRP if (st.st_mode & stat.S_IRGRP) else 0)
                | (stat.S_IXOTH if (st.st_mode & stat.S_IROTH) else 0),
            )
            self.im.present_information(
                f"Made executable: {file_rel_path}", style="success"
            )
        except Exception as e:
            self.im.present_information(
                f"Failed to make {file_rel_path} executable: {e}", style="warning"
            )

    # scaffold_new_project, _elicit_project_requirements, _confirm_specifications, _prepare_project_directory (as in Part 1)
    def scaffold_new_project(self):
        self.im.present_information(
            "Initiating new project scaffolding sequence.", style="info"
        )
        project_details = self._elicit_project_requirements()
        if not project_details:
            self.im.present_information(
                "Project scaffolding aborted by Architect.", style="warning"
            )
            return
        if not self._confirm_specifications(project_details):
            self.im.present_information(
                "Project scaffolding aborted by Architect after review.",
                style="warning",
            )
            return
        project_root = self._prepare_project_directory(project_details)
        if not project_root:
            return

        # Core generation sequence
        if not self._generate_base_structure(project_root, project_details):
            return
        if not self._setup_environment(project_root, project_details):
            return  # Stop if env fails
        if not self._initialize_git_repo(project_root, project_details):
            pass  # Continue but warn
        if not self._setup_pre_commit(project_root, project_details):
            pass  # Continue but warn
        if not self._run_initial_validation(project_root, project_details):
            self.im.present_information(
                "Initial validation encountered issues.", style="warning"
            )  # Continue but warn

        self._present_final_output(project_root, project_details)

    def _elicit_project_requirements(self) -> Optional[Dict[str, Any]]:
        # Simplified for MVP - only offers Python CLI
        details = {}
        self.im.present_information(
            "Let's define the new project (MVP: Python CLI Only).", style="info"
        )
        details["project_name"] = self.im.elicit_requirement("Project Name?")
        default_slug = (
            details["project_name"].lower().replace(" ", "-").replace("_", "-")
        )
        default_slug = "".join(c for c in default_slug if c.isalnum() or c == "-")
        details["project_slug"] = self.im.elicit_requirement(
            "Project Slug?", default=default_slug or "my-python-cli"
        )

        details["author_name"] = self.im.elicit_requirement(
            "Author Name?",
            default=self.state.get_param("architect_identity", "name", ""),
        )
        details["author_email"] = self.im.elicit_requirement(
            "Author Email?",
            default=self.state.get_param("architect_identity", "email", ""),
        )
        details["description"] = self.im.elicit_requirement(
            "Brief Project Description?", default="A new Python CLI project."
        )
        details["project_version"] = self.im.elicit_requirement(
            "Initial Version?", default="0.1.0"
        )

        # Hardcoded for MVP
        details["language"] = "python"
        details["template_type"] = "cli"
        details["python_version"] = self.state.get_param(
            "tpc_standards", "default_python_version", "3.11"
        )  # Get from state or default
        details["project_module_name"] = details["project_slug"].replace("-", "_")

        # Corrected line:
        details["tpc_standards"] = self.state.get_section(
            "tpc_standards", default={}
        )  # Use default={} for safety

        return details

    def _confirm_specifications(self, details: Dict[str, Any]) -> bool:
        self.im.present_information(
            "\nPlease confirm the project specifications:", style="info"
        )
        self.console.print(f"  [bold]Name:[/bold] {details.get('project_name')}")
        self.console.print(f"  [bold]Slug:[/bold] {details.get('project_slug')}")
        self.console.print(
            f"  [bold]Author:[/bold] {details.get('author_name')} <{details.get('author_email')}>"
        )
        self.console.print(f"  [bold]Version:[/bold] {details.get('project_version')}")
        self.console.print(f"  [bold]Description:[/bold] {details.get('description')}")
        self.console.print(
            f"  [bold]Stack:[/bold] {details.get('language')} / {details.get('template_type')} (Python: {details.get('python_version')})"
        )

        return self.im.confirm_action(
            "Proceed with these specifications?", default=True
        )

    def _prepare_project_directory(self, details: Dict[str, Any]) -> Optional[Path]:
        # Reuse logic from Part 1 - Ensure it uses self.im
        output_base_dir = Path(".")  # Or make configurable via elicitation/primed state
        project_root = (output_base_dir / details["project_slug"]).resolve()
        if project_root.exists():
            if not self.im.confirm_action(
                f"Directory '{project_root}' already exists. Overwrite?", default=False
            ):
                self.im.present_information("Aborted.", style="warning")
                return None
            else:
                self.im.present_information(
                    f"Overwriting existing directory: {project_root}", style="warning"
                )
                try:
                    shutil.rmtree(project_root)
                except OSError as e:
                    self.im.present_information(
                        f"Failed to remove existing directory: {e}", style="error"
                    )
                    return None
        try:
            project_root.mkdir(parents=True, exist_ok=True)
            self.im.present_information(
                f"Created project directory: {project_root}", style="success"
            )
            return project_root
        except OSError as e:
            self.im.present_information(
                f"Failed to create project directory: {e}", style="error"
            )
            return None

    # _generate_base_structure (Implementation for Python CLI)
    def _generate_base_structure(
        self, project_root: Path, details: Dict[str, Any]
    ) -> bool:
        self.im.present_information(
            "Generating project structure and core files (Python CLI)...", style="info"
        )
        success = True
        context = details  # Pass all details to templates

        # --- Common Files ---
        common_templates = [
            ("common/README.md.jinja", "README.md"),
            ("common/LICENSE.md.jinja", "LICENSE"),
            ("common/.gitignore.jinja", ".gitignore"),
            ("common/.env.example.jinja", ".env.example"),
            ("common/.github/workflows/ci.yml.jinja", ".github/workflows/ci.yml"),
            ("common/bootstrap.sh.jinja", "bootstrap.sh"),
            ("common/docs/architecture.md.jinja", "docs/architecture.md"),
            ("common/docs/setup_guide.md.jinja", "docs/setup_guide.md"),
        ]
        for template_path, output_path in common_templates:
            if not self._render_template_to_project(
                template_path, context, output_path, project_root
            ):
                success = False

        if (project_root / "bootstrap.sh").exists():
            self._make_project_file_executable(Path("bootstrap.sh"), project_root)

        # --- Python Specific Files ---
        py_templates = [
            ("python/pyproject.toml.jinja", "pyproject.toml"),
            ("python/.pre-commit-config.yaml.jinja", ".pre-commit-config.yaml"),
            (
                "python/tests/test_example.py.jinja",
                f"tests/test_{context['project_module_name']}_example.py",
            ),
        ]
        # --- Python CLI Specific Files ---
        py_templates.extend(
            [
                (
                    "python/cli/__init__.py.jinja",
                    f"{context['project_module_name']}/__init__.py",
                ),
                (
                    "python/cli/main.py.jinja",
                    f"{context['project_module_name']}/main.py",
                ),
                (
                    "python/cli/commands.py.jinja",
                    f"{context['project_module_name']}/commands.py",
                ),
                ("python/Dockerfile.cli.jinja", "Dockerfile"),
                # Conditionally add docker-compose based on elicitation or primed state
                # if self.state.get_param("tpc_standards", "cli_include_compose", False):
                #      py_templates.append(("python/docker-compose.cli.yml.jinja", "docker-compose.yml"))
            ]
        )
        # Render all python templates
        for template_path, output_path in py_templates:
            if not self._render_template_to_project(
                template_path, context, output_path, project_root
            ):
                success = False

        if not success:
            self.im.present_information(
                "Errors occurred during file generation.", style="warning"
            )
        return success

    # _setup_environment (Implementation for Python/Poetry)
    def _setup_environment(self, project_root: Path, details: Dict[str, Any]) -> bool:
        self.im.present_information(
            "Setting up Python environment using Poetry...", style="info"
        )
        if not shutil.which("poetry"):
            self.im.present_information(
                "Poetry command not found. Cannot install dependencies.", style="error"
            )
            return False

        # Run poetry install
        ok, stdout, stderr = self.tools.run_command(
            ["poetry", "install"],
            cwd=project_root,
            desc="Install Python dependencies via Poetry",
        )

        return ok

    # _initialize_git_repo (Implementation)
    def _initialize_git_repo(self, project_root: Path, details: Dict[str, Any]) -> bool:
        # Check primed state if git is desired
        if not self.state.get_param("tpc_standards", "initialize_git", True):
            self.im.present_information(
                "Git initialization disabled by configuration.", style="info"
            )
            return True

        if not shutil.which("git"):
            self.im.present_information(
                "Git command not found. Skipping Git initialization.", style="warning"
            )
            return False

        self.im.present_information("Initializing Git repository...", style="info")
        if not self.tools.run_command(
            ["git", "init"], cwd=project_root, desc="Git Init"
        )[0]:
            return False
        if not self.tools.run_command(
            ["git", "add", "."], cwd=project_root, desc="Git Add All"
        )[0]:
            return False
        commit_msg = f"Initial commit by ODA v0.1 for {details['project_name']}"
        if not self.tools.run_command(
            ["git", "commit", "-m", commit_msg], cwd=project_root, desc="Initial Commit"
        )[0]:
            return False

        return True

    # _setup_pre_commit (Implementation)
    def _setup_pre_commit(self, project_root: Path, details: Dict[str, Any]) -> bool:
        if not self.state.get_param("tpc_standards", "require_pre_commit", True):
            self.im.present_information(
                "Pre-commit setup disabled by configuration.", style="info"
            )
            return True

        if not (project_root / ".pre-commit-config.yaml").exists():
            self.im.present_information(
                "No .pre-commit-config.yaml found, skipping hook installation.",
                style="info",
            )
            return True

        if not shutil.which("pre-commit"):
            self.im.present_information(
                "pre-commit command not found. Skipping hook installation.",
                style="warning",
            )
            return False

        if not (project_root / ".git").is_dir():
            self.im.present_information(
                "Not a Git repository. Cannot install pre-commit hooks.",
                style="warning",
            )
            return False

        self.im.present_information("Setting up pre-commit hooks...", style="info")
        cmd_prefix = []
        # Assume pre-commit is in PATH for MVP. Full impl needs better env handling.
        if details["language"] == "python" and shutil.which("poetry"):
            # This relies on pre-commit being installed within the poetry env or globally
            cmd_prefix = ["poetry", "run"]
            # A better check involves seeing if `poetry run pre-commit --version` works

        install_cmd = cmd_prefix + ["pre-commit", "install"]
        run_cmd = cmd_prefix + ["pre-commit", "run", "--all-files"]

        if not self.tools.run_command(
            install_cmd, cwd=project_root, desc="Pre-commit Install Hooks"
        )[0]:
            return False  # Fail if install fails

        self.im.present_information(
            "Running initial pre-commit checks...", style="info"
        )
        if not self.tools.run_command(
            run_cmd, cwd=project_root, desc="Pre-commit Run All Files"
        )[0]:
            self.im.present_information(
                "Initial pre-commit checks found issues. Please review project files.",
                style="warning",
            )
            # Don't fail the whole process for initial lint errors

        return True

    # _run_initial_validation (Implementation for Python CLI MVP)
    def _run_initial_validation(
        self, project_root: Path, details: Dict[str, Any]
    ) -> bool:
        self.im.present_information(
            "Running initial project validation (Tests & Audit)...", style="info"
        )
        success = True

        # Run Tests
        if shutil.which("poetry"):
            if not self.tools.run_command(
                ["poetry", "run", "pytest"],
                cwd=project_root,
                desc="Run Python Tests (pytest)",
            )[0]:
                success = False
                self.im.present_information("Pytest execution failed.", style="warning")
        else:
            self.im.present_information(
                "Poetry not found, skipping automated tests.", style="warning"
            )
            success = False  # Consider test execution essential

        # Run Audit
        if self.state.get_param("operational_patterns", "run_audit_on_scaffold", True):
            if shutil.which("poetry"):
                # Need pip-audit installed. Assume it is for MVP if check enabled.
                if self.tools.run_command(
                    [
                        "poetry",
                        "export",
                        "--without-hashes",
                        "-f",
                        "requirements.txt",
                        "--output",
                        "requirements.txt",
                    ],
                    cwd=project_root,
                    desc="Export deps for audit",
                    sensitive_output=True,
                )[0]:
                    cmd_prefix = []
                    if shutil.which("pip-audit"):
                        audit_cmd = ["pip-audit", "-r", "requirements.txt"]
                        # Run audit, report but don't fail overall process for audit findings
                        self.tools.run_command(
                            cmd_prefix + audit_cmd,
                            cwd=project_root,
                            desc="Run Dependency Security Audit (pip-audit)",
                        )
                    else:
                        self.im.present_information(
                            "pip-audit not found, skipping security audit.",
                            style="warning",
                        )
                    # Clean up
                    try:
                        (project_root / "requirements.txt").unlink()
                    except OSError:
                        pass  # Ignore if cleanup fails
                else:
                    self.im.present_information(
                        "Failed to export dependencies for audit.", style="warning"
                    )
            else:
                self.im.present_information(
                    "Poetry not found, skipping dependency audit.", style="warning"
                )

        # Add Docker build validation if desired
        # ... (similar logic as before) ...

        if not success:
            self.im.present_information(
                "One or more initial validation steps failed.", style="error"
            )
        return success

    # _present_final_output (Implementation)
    def _present_final_output(self, project_root: Path, details: Dict[str, Any]):
        self.console.rule("[bold green]ODA Project Scaffolding Complete![/bold green]")
        self.im.present_information(
            f"Project '{details['project_name']}' created successfully at:",
            style="success",
        )
        self.console.print(f"  [link=file://{project_root}]{project_root}[/link]")
        self.im.present_information("\nKey next steps:", style="info")
        self.console.print(
            f'  1. Navigate to the directory: [cyan]cd "{project_root.relative_to(Path.cwd())}"[/cyan]'
        )
        self.console.print(
            "  2. Review the project's [cyan]README.md[/cyan] for specific instructions."
        )
        self.console.print(
            "  3. Activate the virtual environment: [cyan]poetry shell[/cyan]"
        )
        self.console.print(
            "  4. Set required environment variables in [cyan].env[/cyan]."
        )
        self.console.print("  5. Begin developing!")
        # Log interaction success for adaptive learning
        # self._log_successful_scaffold(details)


# --- Main ODA Application Entry Point ---
console = Console()
oda_app = typer.Typer(help="Omnitide Development Agent v0.1 (Foundational)")
primed_state_instance: Optional[PrimedOperationalState] = None


@oda_app.callback()
def main(
    ctx: typer.Context,
    config_path: Path = typer.Option(
        "oda_primed_state.json",
        "--config",
        "-c",
        help="Path to the ODA Primed Operational State file.",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
    ),
):
    """Loads ODA's primed state."""
    global primed_state_instance
    try:
        primed_state_instance = PrimedOperationalState(config_path)
        ctx.obj = {
            "state": primed_state_instance,
            "im": InteractionManager(console, primed_state_instance),
            "tools": ToolOrchestrator(console, primed_state_instance),
        }
        # Only greet if not running the prime command itself maybe?
        # Or check if state indicates priming needed? For MVP, always greet.
        ctx.obj["im"].greet()
    except Exception as e:
        # Error handled within PrimedOperationalState loading usually
        console.print(f"[bold red]Failed ODA initialization: {e}[/bold red]")
        raise typer.Exit(code=2)


@oda_app.command(
    "init_project", help="Initiate the intelligent project scaffolding workflow."
)
def init_project_cmd(ctx: typer.Context):
    """Command to start scaffolding a new project."""
    if not ctx.obj or not ctx.obj.get("state"):
        console.print("[bold red]ODA State not initialized. Exiting.[/bold red]")
        raise typer.Exit(code=3)
    scaffolder = ProjectScaffolder(
        interaction_mgr=ctx.obj["im"],
        tool_orchestrator=ctx.obj["tools"],
        primed_state=ctx.obj["state"],
    )
    scaffolder.scaffold_new_project()


@oda_app.command("feedback", help="Provide feedback to ODA for adaptive learning.")
def feedback_cmd(
    ctx: typer.Context,
    feedback_text: str = typer.Argument(..., help="Your feedback message."),
):
    """Command to provide feedback."""
    if not ctx.obj or not ctx.obj.get("im"):
        console.print("[bold red]ODA State not initialized. Exiting.[/bold red]")
        raise typer.Exit(code=3)
    ctx.obj["im"].process_feedback(feedback_text)


@oda_app.command("prime", help="Run the Edict Priming Ritual (Conceptual placeholder).")
def prime_cmd(
    # Simplified for blueprint - requires actual implementation based on design doc
    config_output: Path = typer.Option(
        "oda_primed_state.json", help="Path to save the generated primed state file."
    )
):
    """Placeholder command representing the priming ritual."""
    console.print("[bold yellow]ODA Priming Ritual (Conceptual)[/bold yellow]")
    console.print("This command represents the Edict Priming process.")
    console.print(
        "In a full implementation, it would execute the logic from 'oda_prime_ritual_design.md'."
    )
    # TODO: Instantiate and run the actual 'ODAPrimer' class here.
    # It would need paths to the Edict files as input.
    console.print(
        f"[yellow]Action Required:[/yellow] Manually create '{config_output}' based on 'oda_prime_ritual_design.md' or implement the priming logic."
    )
    # Example: Create a basic dummy file for MVP testing
    dummy_state = {
        "oda_version": "0.1-primed-dummy",
        "architect_identity": {"name": "Architect (Dummy)", "email": ""},
        "tpc_standards": {
            "default_license": "MIT",
            "require_docker": True,
            "require_ci_cd": True,
            "require_pre_commit": True,
        },
        "interaction_protocols": {"confirm_major_actions": True},
        "operational_philosophy": {"default_timeout": 300},
        "template_sources": {"type": "local", "path": "./oda_templates"},
    }
    try:
        with open(config_output, "w") as f:
            json.dump(dummy_state, f, indent=2)
        console.print(
            f"[green]✓[/green] Created dummy state file at '{config_output}' for MVP testing."
        )
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to create dummy state file: {e}")


# Import platform at the end if used within functions that need it.

# Corrected main execution guard
if __name__ == "__main__":
    oda_app()
