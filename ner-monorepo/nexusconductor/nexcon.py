#!/usr/bin/env python3
# nexcon.py - NexusConductor MVE v0.1
# Interactive CLI orchestrator for Scribe & Ex-Work

import click
import questionary  # type: ignore # (for richer prompts - pip install questionary)
import subprocess
import json
import os
import sys
import shlex
from pathlib import Path
import tempfile

# --- Configuration (MVE: Assume scribe.py and exworkagent.py are in PATH or same dir) ---
PYTHON_EXECUTABLE = sys.executable
SCRIBE_EXECUTABLE = "scribe"  # Adjust if not in PATH or provide full path
EXWORK_EXECUTABLE = "exworkagent"  # Adjust if not in PATH or provide full path


# --- Helper Functions ---
def _run_command(
    command_list, input_data=None, cwd=None, timeout=None
) -> subprocess.CompletedProcess:
    """Helper to run a command and return CompletedProcess."""
    log_info(f"Executing: {' '.join(shlex.quote(str(c)) for c in command_list)}")
    if input_data:
        log_info(
            f"With Input Data (first 100 chars): {input_data[:100]}{'...' if len(input_data) > 100 else ''}"
        )

    process = subprocess.run(
        command_list,
        input=input_data,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=cwd,
        timeout=timeout,
    )
    if process.stdout:
        log_debug(f"STDOUT:\n{process.stdout}")
    if process.stderr:
        log_debug(f"STDERR:\n{process.stderr}")
    return process


def run_scribe(
    target_file: Path, project_dir: Path, scribe_args_extra: list = None
) -> Optional[dict]:
    """Runs Scribe and returns its parsed JSON report, or None on critical failure."""
    if not target_file.exists():
        log_error(f"Scribe Target File not found: {target_file}")
        return None
    if not project_dir.exists():
        log_error(f"Scribe Project Directory not found: {project_dir}")
        return None

    # Determine target_file relative to project_dir for Scribe's --target-file
    try:
        relative_target_file = target_file.relative_to(project_dir)
    except ValueError:
        log_error(
            f"Target file {target_file} is not inside project directory {project_dir}."
        )
        return None

    command = [
        PYTHON_EXECUTABLE,
        SCRIBE_EXECUTABLE,
        "--target-dir",
        str(project_dir),
        "--code-file",
        str(target_file),  # Scribe applies this to target-file then validates
        "--target-file",
        str(relative_target_file),
        "--report-format",
        "json",
        "--skip-commit",  # nexcon will handle commits
    ]
    if scribe_args_extra:
        command.extend(scribe_args_extra)

    try:
        process = _run_command(command, timeout=600)  # Generous timeout for Scribe
        if process.stdout:
            try:
                report = json.loads(process.stdout)
                log_info(
                    f"Scribe completed. Overall status: {report.get('overall_status', 'UNKNOWN')}"
                )
                return report
            except json.JSONDecodeError:
                log_error("Failed to parse Scribe JSON report.")
                log_error(f"Scribe raw stdout: {process.stdout[:1000]}")
                return {
                    "overall_status": "FAILURE",
                    "error_message": "Scribe output was not valid JSON.",
                }
        else:
            log_error("Scribe produced no stdout. Critical execution error likely.")
            log_error(f"Scribe stderr: {process.stderr[:1000]}")
            return {
                "overall_status": "FAILURE",
                "error_message": f"Scribe execution error: {process.stderr.strip()}",
            }
    except FileNotFoundError:
        log_error(
            f"{SCRIBE_EXECUTABLE} not found. Ensure it's in PATH or path is correct."
        )
        return {
            "overall_status": "FAILURE",
            "error_message": "Scribe executable not found.",
        }
    except subprocess.TimeoutExpired:
        log_error("Scribe execution timed out.")
        return {
            "overall_status": "FAILURE",
            "error_message": "Scribe execution timed out.",
        }
    except Exception as e:
        log_error(f"Unexpected error running Scribe: {e}")
        return {
            "overall_status": "FAILURE",
            "error_message": f"Unexpected Scribe error: {str(e)}",
        }


def run_exwork(payload: dict, cwd: Optional[Path] = None) -> Optional[dict]:
    """Runs Agent Ex-Work with the given JSON payload and returns its summary, or None on critical failure."""
    payload_str = json.dumps(payload, indent=2)
    command = [PYTHON_EXECUTABLE, EXWORK_EXECUTABLE]
    try:
        process = _run_command(
            command, input_data=payload_str, cwd=cwd, timeout=600
        )  # Timeout for Ex-Work
        if process.stdout:
            try:
                summary = json.loads(process.stdout)
                log_info(
                    f"Ex-Work completed. Overall success: {summary.get('overall_success', False)}"
                )
                return summary
            except json.JSONDecodeError:
                log_error("Failed to parse Ex-Work JSON summary.")
                log_error(f"Ex-Work raw stdout: {process.stdout[:1000]}")
                return {
                    "overall_success": False,
                    "status_message": "Ex-Work output was not valid JSON.",
                }
        else:
            log_error("Ex-Work produced no stdout. Critical execution error likely.")
            log_error(f"Ex-Work stderr: {process.stderr[:1000]}")
            return {
                "overall_success": False,
                "status_message": f"Ex-Work execution error: {process.stderr.strip()}",
            }

    except FileNotFoundError:
        log_error(
            f"{EXWORK_EXECUTABLE} not found. Ensure it's in PATH or path is correct."
        )
        return {
            "overall_success": False,
            "status_message": "Ex-Work executable not found.",
        }
    except subprocess.TimeoutExpired:
        log_error("Ex-Work execution timed out.")
        return {
            "overall_success": False,
            "status_message": "Ex-Work execution timed out.",
        }
    except Exception as e:
        log_error(f"Unexpected error running Ex-Work: {e}")
        return {
            "overall_success": False,
            "status_message": f"Unexpected Ex-Work error: {str(e)}",
        }


def display_scribe_summary(scribe_report: Optional[dict]):
    if not scribe_report:
        click.secho("No Scribe report available.", fg="red")
        return

    status = scribe_report.get("overall_status", "UNKNOWN")
    fg_color = (
        "green" if status == "SUCCESS" else "yellow" if status == "WARNING" else "red"
    )
    click.echo(click.style("\n--- Scribe Validation Summary ---", bold=True))
    click.echo(f"Overall Status: {click.style(status, fg=fg_color, bold=True)}")

    if scribe_report.get("error_message"):  # For nexcon internal errors calling Scribe
        click.secho(f"  NexCon Error: {scribe_report['error_message']}", fg="red")

    ai_review_findings = scribe_report.get("ai_review_findings")
    if ai_review_findings:
        click.echo(f"  AI Review Findings: {len(ai_review_findings)}")
        for i, finding in enumerate(ai_review_findings[:3]):  # Show top 3
            click.echo(
                f"    - [{finding.get('severity','N/A').upper()}] {finding.get('location','N/A')}: {finding.get('description','N/A')[:80]}..."
            )
        if len(ai_review_findings) > 3:
            click.echo("    ... (more findings in full report)")

    # Summarize other key issues if present (e.g., linting, type errors from steps)
    issues_summary = []
    for step in scribe_report.get("steps", []):
        if step.get("status") == "FAILURE":
            step_msg = step.get("details", {}).get("message") or step.get(
                "error_message"
            )
            if step_msg:
                issues_summary.append(
                    f"  - Failed Step '{step.get('name')}': {str(step_msg)[:100]}..."
                )
        elif step.get("status") == "WARNING":
            step_msg = step.get("details", {}).get("message")
            if step_msg:
                issues_summary.append(
                    f"  - Warning Step '{step.get('name')}': {str(step_msg)[:100]}..."
                )

    if issues_summary:
        click.echo("  Key Issues/Warnings from Steps:")
        for issue_line in issues_summary[:5]:  # Show top 5
            click.echo(f"    {issue_line}")

    click.echo(
        "  (Full Scribe JSON report available if saved by Scribe or --output-file option was used with Scribe)"
    )
    click.echo(click.style("--- End Scribe Summary ---", bold=True))


# --- Click CLI Structure ---
@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    """
    NexusConductor (nexcon): Interactively orchestrates Project Scribe and Agent Ex-Work
    to enhance your development workflow.
    """
    log_info("NexusConductor MVE v0.1 activated.")
    if ctx.invoked_subcommand is None:
        # Default action: run polish command or show help
        click.echo(ctx.get_help())
        # Or, could directly invoke polish:
        # ctx.invoke(polish)


@cli.command()
@click.option(
    "--file",
    "-f",
    "target_file_path_str",
    type=click.Path(exists=True, dir_okay=False, resolve_path=True),
    help="Path to the Python file to polish.",
)
@click.option(
    "--project_dir",
    "-p",
    "project_dir_str",
    type=click.Path(exists=True, file_okay=False, resolve_path=True),
    help="Path to the project root directory.",
)
def polish(target_file_path_str, project_dir_str):
    """Interactively polishes a Python file using Scribe and AI-assisted fixes via Ex-Work."""
    click.secho("--- Interactive Code Polish Workflow ---", fg="cyan", bold=True)

    target_file = None
    if target_file_path_str:
        target_file = Path(target_file_path_str)
    else:
        target_file_str_q = questionary.path(
            "Enter path to Python file to polish:",
            validate=lambda p: Path(p).is_file() or "File not found.",
        ).ask()
        if not target_file_str_q:
            click.echo("File path is required. Aborting.")
            return
        target_file = Path(target_file_str_q).resolve()

    project_dir = None
    if project_dir_str:
        project_dir = Path(project_dir_str)
    else:
        # Try to infer project_dir (e.g., Git root or parent of file)
        # For MVE, just ask
        project_dir_str_q = questionary.path(
            f"Enter project directory for '{target_file.name}':",
            default=str(target_file.parent),
            validate=lambda p: Path(p).is_dir() or "Directory not found.",
        ).ask()
        if not project_dir_str_q:
            click.echo("Project directory is required. Aborting.")
            return
        project_dir = Path(project_dir_str_q).resolve()

    log_info(f"Target File: {target_file}")
    log_info(f"Project Dir: {project_dir}")

    current_file_content = target_file.read_text(encoding="utf-8")
    loop_count = 0
    max_loops = 3  # Max refinement loops

    while loop_count < max_loops:
        loop_count += 1
        click.secho(f"\n--- Scribe Validation Pass {loop_count} ---", fg="yellow")
        scribe_report = run_scribe(
            target_file, project_dir, scribe_args_extra=["--skip-tests"]
        )  # Skip tests for faster polish loop initially
        display_scribe_summary(scribe_report)

        if not scribe_report or scribe_report.get("overall_status") == "FAILURE":
            if not questionary.confirm(
                "Scribe validation indicated issues. Attempt AI-driven refinement via Ex-Work?"
            ).ask():
                click.echo("Skipping AI refinement. Manual review recommended.")
                break

            exwork_diag_payload = {
                "step_id": f"ai_diag_polish_{target_file.name}_{loop_count}",
                "actions": [
                    {
                        "type": "DIAGNOSE_ERROR",
                        "failed_command": f"Scribe validation for {target_file.name}",
                        "stderr": json.dumps(
                            scribe_report, indent=2
                        ),  # Pass full Scribe report
                        "context": {
                            "target_file": str(target_file),
                            "project_dir": str(project_dir),
                        },
                    }
                ],
            }
            click.secho(
                "\nRequesting AI diagnosis & fix suggestion from Ex-Work...",
                fg="magenta",
            )
            exwork_summary = run_exwork(exwork_diag_payload, cwd=project_dir)

            if exwork_summary and exwork_summary.get("overall_success"):
                try:
                    # ExWork's DIAGNOSE_ERROR returns its result as a JSON string in message_or_payload
                    diag_result_str = exwork_summary.get("action_results", [{}])[0].get(
                        "message_or_payload", "{}"
                    )
                    diag_result = json.loads(diag_result_str)

                    fix_type = diag_result.get("fix_type")
                    fix_content = diag_result.get("fix_content")
                    diagnosis_text = diag_result.get(
                        "diagnosis", "No diagnosis provided."
                    )

                    click.secho(f"\nAI Diagnosis: {diagnosis_text}", fg="blue")
                    if fix_type and fix_content:
                        click.secho(f"AI Fix Type: {fix_type}", fg="blue")
                        click.secho(
                            f"AI Fix Content:\n{'-'*20}\n{fix_content}\n{'-'*20}",
                            fg="blue",
                        )

                        if questionary.confirm("Apply this suggested fix?").ask():
                            if fix_type == "PATCH":
                                # For MVE: User manually applies patch or nexcon uses temp file + ExWork APPLY_PATCH
                                # For simplicity now, if it's a patch, we'll write to a temp file and use Ex-Work APPLY_PATCH
                                # ExWork's APPLY_PATCH needs non-TTY approval for full automation here.
                                # This is a known complexity from Ex-Work.
                                # A simpler MVE for nexcon would be: if fix_type is "FULL_CONTENT", replace file.
                                with tempfile.NamedTemporaryFile(
                                    mode="w", delete=False, suffix=".patch", dir="."
                                ) as tmp_patch_file:
                                    tmp_patch_file.write(fix_content)
                                    tmp_patch_file_path = tmp_patch_file.name

                                apply_patch_payload = {
                                    "step_id": f"apply_ai_patch_{loop_count}",
                                    "actions": [
                                        {
                                            "type": "APPLY_PATCH",  # This will use Ex-Work's TTY prompt for now.
                                            "path": str(
                                                target_file.relative_to(project_dir)
                                            ),  # Path relative to project_dir
                                            "patch_content": fix_content,  # Ex-Work APPLY_PATCH also takes patch_content
                                        }
                                    ],
                                }
                                click.secho(
                                    "Attempting to apply patch via Ex-Work (may require TTY confirmation)...",
                                    fg="magenta",
                                )
                                patch_apply_summary = run_exwork(
                                    apply_patch_payload, cwd=project_dir
                                )
                                if os.path.exists(tmp_patch_file_path):
                                    os.unlink(tmp_patch_file_path)

                                if (
                                    patch_apply_summary
                                    and patch_apply_summary.get("overall_success")
                                    and patch_apply_summary.get("action_results", [{}])[
                                        0
                                    ].get("success")
                                ):
                                    click.secho(
                                        "Patch applied successfully by Ex-Work. Re-validating with Scribe...",
                                        fg="green",
                                    )
                                    current_file_content = target_file.read_text(
                                        encoding="utf-8"
                                    )  # Re-read
                                    continue  # Go to next Scribe validation pass
                                else:
                                    click.secho(
                                        "Failed to apply patch via Ex-Work or patch application itself failed.",
                                        fg="red",
                                    )
                                    click.secho(
                                        f"Ex-Work output: {json.dumps(patch_apply_summary, indent=2)}",
                                        fg="yellow",
                                    )
                                    break  # Exit loop on patch failure
                            elif fix_type in [
                                "COMMAND",
                                "MANUAL_STEPS",
                                "CONFIG_ADJUSTMENT",
                                "INFO_REQUEST",
                                "RAW_LLM_OUTPUT",
                                "PARSE_ERROR",
                            ]:
                                click.secho(
                                    f"Suggested fix type '{fix_type}' requires manual action or is informational. Content: {fix_content}",
                                    fg="yellow",
                                )
                                if not questionary.confirm(
                                    "Manually address and re-validate?"
                                ).ask():
                                    break
                                else:
                                    current_file_content = target_file.read_text(
                                        encoding="utf-8"
                                    )  # Re-read in case of manual change
                                    continue
                            else:
                                click.secho(
                                    f"Unknown or unhandled fix_type: {fix_type}. Cannot apply automatically.",
                                    fg="yellow",
                                )
                                break
                        else:
                            click.echo("Skipping AI fix application.")
                            break  # Exit loop if user doesn't want to apply
                    else:
                        click.secho(
                            "AI provided a diagnosis but no actionable fix content.",
                            fg="yellow",
                        )
                        if not questionary.confirm(
                            "No actionable fix. Continue loop to re-validate current state or abort? (Continue/Abort)"
                        ).ask(default=False):
                            break
                        else:
                            continue  # re-validate current state

                except json.JSONDecodeError:
                    click.secho("Failed to parse AI diagnosis from Ex-Work.", fg="red")
                    click.secho(
                        f"Ex-Work raw output: {exwork_summary.get('action_results', [{}])[0].get('message_or_payload', '')[:500]}",
                        fg="yellow",
                    )
                    break
                except Exception as e_diag:
                    click.secho(f"Error processing AI diagnosis: {e_diag}", fg="red")
                    break
            else:
                click.secho("Ex-Work failed to provide AI diagnosis.", fg="red")
                click.secho(
                    f"Ex-Work output: {json.dumps(exwork_summary, indent=2)}",
                    fg="yellow",
                )
                break
        elif scribe_report and scribe_report.get("overall_status") == "SUCCESS":
            click.secho("Scribe validation PASSED! Code looks good.", fg="green")
            break  # Exit loop, code is polished
        else:  # Scribe report missing or status unknown
            click.secho(
                "Scribe validation did not complete as expected. Aborting polish.",
                fg="red",
            )
            break

    # Final Scribe run if changes were made and loop didn't break early on SUCCESS
    if loop_count > 0 and (
        not scribe_report or scribe_report.get("overall_status") != "SUCCESS"
    ):
        click.secho("\n--- Final Scribe Validation Pass ---", fg="yellow")
        scribe_report = run_scribe(
            target_file, project_dir, scribe_args_extra=["--skip-tests"]
        )
        display_scribe_summary(scribe_report)

    if scribe_report and scribe_report.get("overall_status") == "SUCCESS":
        if questionary.confirm(
            f"\nFinal Scribe validation passed. Commit changes to '{target_file.name}'?"
        ).ask():
            commit_message_default = (
                f"TPC: Polish {target_file.name} with nexcon (Scribe & AI)"
            )
            commit_message = questionary.text(
                "Enter commit message:", default=commit_message_default
            ).ask()
            if commit_message:
                git_payload = {
                    "step_id": f"commit_polished_{target_file.name}",
                    "actions": [
                        {
                            "type": "GIT_ADD",
                            "paths": [str(target_file.relative_to(project_dir))],
                        },
                        {"type": "GIT_COMMIT", "message": commit_message},
                    ],
                }
                click.secho("Attempting to commit changes via Ex-Work...", fg="magenta")
                commit_summary = run_exwork(git_payload, cwd=project_dir)
                if commit_summary and commit_summary.get("overall_success"):
                    click.secho("Changes committed successfully!", fg="green")
                else:
                    click.secho("Failed to commit changes via Ex-Work.", fg="red")
                    click.secho(
                        f"Ex-Work output: {json.dumps(commit_summary, indent=2)}",
                        fg="yellow",
                    )
            else:
                click.echo("Commit aborted.")
        else:
            click.echo("Changes not committed.")
    else:
        click.echo(
            "Code polishing did not result in a fully Scribe-validated state. No commit attempted."
        )

    click.secho(
        "\n--- Interactive Code Polish Workflow Finished ---", fg="cyan", bold=True
    )


# Basic logging functions (can be expanded with Python's logging module)
_verbose_mode = False


def log_info(message):
    click.echo(f"{click.style('[INFO]', fg='blue')} {message}")


def log_warning(message):
    click.echo(f"{click.style('[WARN]', fg='yellow')} {message}")


def log_error(message, exc_info=False):
    click.echo(f"{click.style('[ERROR]', fg='red')} {message}")
    if exc_info and _verbose_mode:  # Only show traceback if verbose
        click.echo(traceback.format_exc())


def log_debug(message, verbose_override=None):
    # Use verbose_override if provided, else global _verbose_mode
    current_verbose = _verbose_mode
    if (
        verbose_override is not None
    ):  # This logic isn't quite right for how click options work.
        pass  # Click options are handled by the @click decorator. Verbosity here is manual.

    # For MVE, let's assume if a script is called with --verbose, we want debug logs.
    # This nexcon.py doesn't have its own --verbose yet, but it's implied for debug logs.
    # For now, let's make log_debug always print if called.
    # A proper solution would use Python's logging module configured by Click.
    # For this MVE, let's simplify:
    if True:  # Or check a global _verbose_flag set by a CLI option later
        click.echo(f"{click.style('[DEBUG]', dim=True)} {message}")


if __name__ == "__main__":
    # This makes log_debug print if a hypothetical global verbose is set
    # For Click, you'd typically get the verbose flag from ctx.params in a command.
    # if "--verbose" in sys.argv or "-v" in sys.argv:
    # _verbose_mode = True
    # ^ This simple check is not robust for Click.
    # For MVE, log_debug will always print for now.
    cli()
