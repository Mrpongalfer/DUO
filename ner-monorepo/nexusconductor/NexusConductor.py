#!/usr/bin/env python3
# NexusConductor.py - MVE v0.1
# Orchestrates Project Scribe and Agent Ex-Work using YAML Pipe Definitions.

import argparse
import json
import subprocess
import sys
import yaml  # Requires PyYAML: pip install PyYAML
import re
import shlex

# --- Configuration (for MVE, paths can be made more configurable later) ---
# Assume scribe.py and exworkagent.py are in PATH or full paths are given in pipe.
# For simplicity, if not in PATH, a pipe step would need to use full paths for them.
SCRIBE_EXECUTABLE = "scribe"  # Or full path
EXWORK_EXECUTABLE = "exworkagent"  # Or full path
PYTHON_EXECUTABLE = sys.executable  # Use the same python that runs NexusConductor


# --- Logging Setup (Basic for MVE) ---
def log_info(message):
    print(f"[INFO] {message}")


def log_warning(message):
    print(f"[WARN] {message}")


def log_error(message):
    print(f"[ERROR] {message}")


def log_debug(message, verbose=False):
    if verbose:
        print(f"[DEBUG] {message}")


# --- Templating Engine (Basic) ---
def render_template(template_string: str, context: dict) -> str:
    """
    Renders a string with {{ vars.key }} and {{ context.steps_output.step_name.field }}
    Handles basic dot notation for context.
    """
    if not isinstance(template_string, str):
        return template_string  # Not a string, return as-is

    def replace_match(match):
        full_match = match.group(0)
        prefix = match.group(1)  # 'vars' or 'context'
        path = match.group(2)  # 'key' or 'steps_output.step_name.field'

        current_data = context
        if prefix == "vars":
            current_data = context.get("vars", {})
        elif prefix == "context":
            # For context, we expect paths like steps_output.step_name.field
            # We'll only allow access to context.steps_output for simplicity and security
            if not path.startswith("steps_output."):
                log_warning(
                    f"Templating: Access to context path '{path}' is not allowed. Only 'steps_output.sub_path'."
                )
                return full_match  # Return original if path is not allowed
            current_data = (
                context  # Start from root context for 'context.steps_output...'
            )

        try:
            keys = path.split(".")
            val = current_data
            for key in keys:
                if isinstance(val, dict):
                    val = val.get(key)
                elif isinstance(val, list) and key.isdigit():  # Basic list index access
                    val = val[int(key)]
                else:
                    val = None  # Key not found or not indexable
                    break

            if val is not None:
                return str(val)
            else:
                log_warning(
                    f"Templating: Variable '{prefix}.{path}' not found in context. Original: {full_match}"
                )
                return full_match  # Or raise an error, or return empty string
        except Exception as e:
            log_warning(
                f"Templating: Error accessing '{prefix}.{path}': {e}. Original: {full_match}"
            )
            return full_match

    # Regex to find {{ vars.path }} or {{ context.path }}
    # Allows alphanumeric, underscore, dot, and basic list indexing like [0]
    # This is a simplified regex; for production robust dot notation and list access, a proper parser or Jinja2 is better.
    # For MVE, this will handle basic cases like context.steps_output.step_name.status or context.steps_output.step_name.report.overall_status
    pattern = r"\{\{\s*(vars|context)\.([a-zA-Z0-9_.\-\[\]]+)\s*\}\}"
    return re.sub(pattern, replace_match, template_string)


def render_structured_data(data, context):
    """Recursively renders templates in strings within lists and dicts."""
    if isinstance(data, str):
        return render_template(data, context)
    elif isinstance(data, list):
        return [render_structured_data(item, context) for item in data]
    elif isinstance(data, dict):
        return {k: render_structured_data(v, context) for k, v in data.items()}
    return data


# --- Condition Evaluator (Basic & Safe) ---
def evaluate_condition(condition_string: str, context: dict, verbose: bool) -> bool:
    rendered_condition = render_template(condition_string, context)
    log_debug(
        f"Evaluating condition: Original='{condition_string}', Rendered='{rendered_condition}'",
        verbose,
    )

    # Basic safe evaluations for MVE
    # Examples: "{{ context.steps_output.step1.status == 'SUCCESS' }}"
    #           "{{ vars.proceed_flag is true }}"
    #           "{{ context.steps_output.step1.report.overall_status != 'FAILURE' }}"
    try:
        # Restricted evaluation environment
        # This is a very simplified and somewhat risky way to do it.
        # A more robust solution would use a proper expression parsing library or safer eval.
        # For MVE, we allow simple comparisons.
        if "==" in rendered_condition:
            left, right = rendered_condition.split("==", 1)
            left_val = eval(
                left.strip(),
                {"__builtins__": {}},
                {"true": True, "false": False, "none": None},
            )
            right_val = eval(
                right.strip(),
                {"__builtins__": {}},
                {"true": True, "false": False, "none": None},
            )
            return left_val == right_val
        elif "!=" in rendered_condition:
            left, right = rendered_condition.split("!=", 1)
            left_val = eval(
                left.strip(),
                {"__builtins__": {}},
                {"true": True, "false": False, "none": None},
            )
            right_val = eval(
                right.strip(),
                {"__builtins__": {}},
                {"true": True, "false": False, "none": None},
            )
            return left_val != right_val
        elif "is true" in rendered_condition.lower():
            var_part = rendered_condition.lower().split("is true")[0].strip()
            val = eval(
                var_part,
                {"__builtins__": {}},
                {"true": True, "false": False, "none": None},
            )
            return val is True
        elif "is false" in rendered_condition.lower():
            var_part = rendered_condition.lower().split("is false")[0].strip()
            val = eval(
                var_part,
                {"__builtins__": {}},
                {"true": True, "false": False, "none": None},
            )
            return val is False
        elif (
            "is none" in rendered_condition.lower()
            or "is null" in rendered_condition.lower()
        ):
            var_part = re.split(
                r"is (none|null)", rendered_condition.lower(), flags=re.IGNORECASE
            )[0].strip()
            val = eval(
                var_part,
                {"__builtins__": {}},
                {"true": True, "false": False, "none": None},
            )
            return val is None
        elif (
            "is not none" in rendered_condition.lower()
            or "is not null" in rendered_condition.lower()
        ):
            var_part = re.split(
                r"is not (none|null)", rendered_condition.lower(), flags=re.IGNORECASE
            )[0].strip()
            val = eval(
                var_part,
                {"__builtins__": {}},
                {"true": True, "false": False, "none": None},
            )
            return val is not None
        else:
            log_warning(
                f"Condition format not recognized or too complex for MVE: '{rendered_condition}'. Assuming false."
            )
            return False
    except Exception as e:
        log_error(
            f"Error evaluating condition '{rendered_condition}': {e}. Assuming false."
        )
        return False


# --- Interactive Prompt Handler ---
def handle_interactive_prompt(
    prompt_config: dict, context: dict, verbose: bool
) -> bool:
    prompt_type = prompt_config.get("type", "confirm")
    message_template = prompt_config.get("message", "Proceed?")
    variable_to_set = prompt_config.get("variable")

    message = render_template(message_template, context)

    if prompt_type == "confirm":
        log_debug(f"Prompting user (confirm): {message} (y/n)", verbose)
        while True:
            response = input(f"{message} [y/n]: ").strip().lower()
            if response in ["y", "yes"]:
                if variable_to_set:
                    context["vars"][variable_to_set] = True
                return True
            elif response in ["n", "no"]:
                if variable_to_set:
                    context["vars"][variable_to_set] = False
                return False
            else:
                print("Invalid input. Please enter 'y' or 'n'.")
    elif prompt_type == "input":
        log_debug(f"Prompting user (input): {message}", verbose)
        response = input(f"{message}: ").strip()
        if variable_to_set:
            context["vars"][variable_to_set] = response
        return True  # Input prompt itself always "succeeds" in getting some input
    # Add 'confirm_with_view' or other types later
    else:
        log_warning(f"Unknown prompt type: '{prompt_type}'. Skipping prompt.")
        return True  # Default to continue if prompt is misconfigured


# --- File Reader Utility ---
def read_file_content(
    file_path_template: str, context: dict, verbose: bool
) -> Optional[str]:
    file_path_str = render_template(file_path_template, context)
    try:
        file_path = Path(file_path_str).resolve()
        if file_path.is_file():
            log_debug(f"Reading file content from: {file_path}", verbose)
            return file_path.read_text(encoding="utf-8")
        else:
            log_warning(f"File not found for reading: {file_path}")
            return None
    except Exception as e:
        log_error(f"Error reading file {file_path_str}: {e}")
        return None


# --- Tool Executors ---
def execute_scribe_step(
    step_name: str, step_config: dict, context: dict, verbose: bool
) -> dict:
    log_info(f"Executing Scribe step: {step_name}")
    args_dict = render_structured_data(step_config.get("args", {}), context)

    command = [PYTHON_EXECUTABLE, SCRIBE_EXECUTABLE]
    for key, value in args_dict.items():
        if isinstance(value, bool):
            if value:
                command.append(f"--{key}")
        elif value is not None:  # Handle cases where value could be empty string
            command.append(f"--{key}")
            command.append(str(value))

    log_debug(f"Scribe command: {' '.join(shlex.quote(c) for c in command)}", verbose)

    result_details = {
        "status": "FAILURE",
        "command_executed": " ".join(shlex.quote(c) for c in command),
        "scribe_report": None,
        "error": None,
    }

    try:
        process = subprocess.run(
            command, capture_output=True, text=True, encoding="utf-8", check=False
        )
        log_debug(f"Scribe STDOUT:\n{process.stdout}", verbose)
        log_debug(f"Scribe STDERR:\n{process.stderr}", verbose)

        if (
            process.stderr
            and "Traceback" in process.stderr
            and "Scribe" in process.stderr
        ):  # Heuristic for Scribe crashing
            result_details["error"] = (
                f"Scribe execution error: {process.stderr.strip()}"
            )
            log_error(
                f"Scribe step '{step_name}' execution error. Stderr: {process.stderr.strip()}"
            )
        else:
            try:
                scribe_report = json.loads(process.stdout)
                result_details["scribe_report"] = scribe_report
                if scribe_report.get("overall_status") == "SUCCESS":
                    result_details["status"] = "SUCCESS"
                else:
                    result_details["status"] = (
                        "FAILURE"  # Or WARNING if Scribe reports that
                    )
                    result_details["error"] = (
                        f"Scribe validation {scribe_report.get('overall_status', 'ended with issues')}."
                    )
                log_info(
                    f"Scribe step '{step_name}' completed with Scribe status: {result_details['status']}"
                )
            except json.JSONDecodeError:
                result_details["error"] = (
                    "Failed to parse Scribe JSON report from stdout."
                )
                result_details["raw_stdout"] = process.stdout
                log_error(
                    f"Scribe step '{step_name}' failed to produce valid JSON report. stdout: {process.stdout[:500]}..."
                )
            except Exception as e:  # Catch other errors during Scribe JSON processing
                result_details["error"] = (
                    f"Unexpected error processing Scribe output for '{step_name}': {e}"
                )
                log_error(result_details["error"])

    except FileNotFoundError:
        result_details["error"] = (
            f"{SCRIBE_EXECUTABLE} not found. Ensure it's in PATH or path is configured."
        )
        log_error(result_details["error"])
    except subprocess.TimeoutExpired:
        result_details["error"] = f"Scribe step '{step_name}' timed out."
        log_error(result_details["error"])
    except Exception as e:
        result_details["error"] = f"Error executing Scribe step '{step_name}': {e}"
        log_error(result_details["error"], exc_info=verbose)

    return result_details


def execute_exwork_step(
    step_name: str, step_config: dict, context: dict, verbose: bool
) -> dict:
    log_info(f"Executing Ex-Work step: {step_name}")

    payload_template = step_config.get("payload")
    if step_config.get("payload_template_file"):  # Allow loading payload from a file
        template_file_path = render_template(
            step_config["payload_template_file"], context
        )
        content = read_file_content(template_file_path, context, verbose)
        if content:
            try:
                payload_template = json.loads(content)
            except json.JSONDecodeError as e:
                log_error(
                    f"Failed to parse JSON from payload_template_file '{template_file_path}': {e}"
                )
                return {
                    "status": "FAILURE",
                    "error": f"Invalid JSON in template file {template_file_path}",
                }
        else:
            return {
                "status": "FAILURE",
                "error": f"Could not read payload_template_file {template_file_path}",
            }

    if not payload_template:
        log_error(
            f"No payload or payload_template_file defined for Ex-Work step: {step_name}"
        )
        return {"status": "FAILURE", "error": "Missing payload for Ex-Work step."}

    exwork_payload_rendered = render_structured_data(payload_template, context)
    exwork_payload_json_str = json.dumps(exwork_payload_rendered, indent=2)

    command = [PYTHON_EXECUTABLE, EXWORK_EXECUTABLE]
    log_debug(f"Ex-Work command: {' '.join(shlex.quote(c) for c in command)}", verbose)
    log_debug(f"Ex-Work Payload:\n{exwork_payload_json_str}", verbose)

    result_details = {
        "status": "FAILURE",
        "command_executed": " ".join(shlex.quote(c) for c in command),
        "exwork_summary": None,
        "error": None,
    }

    try:
        process = subprocess.run(
            command,
            input=exwork_payload_json_str,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        log_debug(f"Ex-Work STDOUT:\n{process.stdout}", verbose)
        log_debug(f"Ex-Work STDERR:\n{process.stderr}", verbose)

        if (
            process.stderr
            and "Traceback" in process.stderr
            and "ExWork" in process.stderr
        ):  # Heuristic for ExWork crashing
            result_details["error"] = (
                f"Ex-Work execution error: {process.stderr.strip()}"
            )
            log_error(
                f"Ex-Work step '{step_name}' execution error. Stderr: {process.stderr.strip()}"
            )
        else:
            try:
                exwork_summary = json.loads(process.stdout)
                result_details["exwork_summary"] = exwork_summary
                if exwork_summary.get("overall_success"):
                    result_details["status"] = "SUCCESS"
                else:
                    result_details["status"] = "FAILURE"
                    result_details["error"] = (
                        f"Ex-Work execution reported failure: {exwork_summary.get('status_message', 'Unknown Ex-Work failure')}"
                    )
                log_info(
                    f"Ex-Work step '{step_name}' completed with Ex-Work status: {result_details['status']}"
                )
            except json.JSONDecodeError:
                result_details["error"] = (
                    "Failed to parse Ex-Work JSON summary from stdout."
                )
                result_details["raw_stdout"] = process.stdout
                log_error(
                    f"Ex-Work step '{step_name}' failed to produce valid JSON summary. stdout: {process.stdout[:500]}..."
                )
            except Exception as e:  # Catch other errors during ExWork JSON processing
                result_details["error"] = (
                    f"Unexpected error processing Ex-Work output for '{step_name}': {e}"
                )
                log_error(result_details["error"])

    except FileNotFoundError:
        result_details["error"] = (
            f"{EXWORK_EXECUTABLE} not found. Ensure it's in PATH or path is configured."
        )
        log_error(result_details["error"])
    except (
        subprocess.TimeoutExpired
    ):  # Timeout not implemented in subprocess.run here, but good practice
        result_details["error"] = f"Ex-Work step '{step_name}' timed out."
        log_error(result_details["error"])
    except Exception as e:
        result_details["error"] = f"Error executing Ex-Work step '{step_name}': {e}"
        log_error(result_details["error"], exc_info=verbose)

    return result_details


# --- Pipe Execution Logic ---
def run_pipe(pipe_definition: dict, initial_vars: dict, verbose: bool) -> dict:
    run_context = {
        "vars": {
            **pipe_definition.get("vars", {}),
            **initial_vars,
        },  # CLI vars override pipe vars
        "steps_output": {},
    }
    pipe_name = pipe_definition.get("name", "Unnamed Pipe")
    log_info(f"Starting execution of Pipe: {pipe_name}")
    log_debug(f"Initial Context Vars: {run_context['vars']}", verbose)

    overall_pipe_status = "SUCCESS"

    for i, step_config in enumerate(pipe_definition.get("steps", [])):
        step_name = step_config.get("name", f"step_{i+1}")
        log_info(f"--- Starting Pipe Step: {step_name} ---")

        if "skip_if" in step_config:
            should_skip = evaluate_condition(
                step_config["skip_if"], run_context, verbose
            )
            if should_skip:
                log_info(
                    f"Skipping step '{step_name}' due to 'skip_if' condition: {step_config['skip_if']}"
                )
                run_context["steps_output"][step_name] = {
                    "status": "SKIPPED",
                    "reason": "skip_if condition met",
                }
                log_info(f"--- Finished Pipe Step: {step_name} (SKIPPED) ---")
                continue

        if "condition" in step_config:
            if not evaluate_condition(step_config["condition"], run_context, verbose):
                log_info(
                    f"Skipping step '{step_name}' due to unmet condition: {step_config['condition']}"
                )
                run_context["steps_output"][step_name] = {
                    "status": "SKIPPED",
                    "reason": "condition not met",
                }
                log_info(f"--- Finished Pipe Step: {step_name} (SKIPPED) ---")
                continue

        step_result = {}
        tool_type = step_config.get("tool")

        if tool_type == "scribe":
            step_result = execute_scribe_step(
                step_name, step_config, run_context, verbose
            )
        elif tool_type == "exwork":
            step_result = execute_exwork_step(
                step_name, step_config, run_context, verbose
            )
        elif "prompt_user" in step_config:  # A step can be just a prompt
            handle_interactive_prompt(step_config["prompt_user"], run_context, verbose)
            step_result = {"status": "SUCCESS", "message": "User prompt completed."}
            # Vars set by prompt are directly in run_context['vars']
        else:
            log_error(
                f"Unknown tool type '{tool_type}' or no action in step '{step_name}'. Skipping."
            )
            step_result = {
                "status": "SKIPPED",
                "error": f"Unknown tool '{tool_type}' or no action",
            }

        run_context["steps_output"][step_name] = step_result

        if step_result.get("status") == "FAILURE":
            overall_pipe_status = "FAILURE"
            log_error(
                f"Step '{step_name}' FAILED. Error: {step_result.get('error', 'Unknown error')}"
            )
            on_failure_config = step_config.get("on_failure")
            if on_failure_config:
                if "message" in on_failure_config:
                    log_info(
                        f"On_failure message for '{step_name}': {render_template(on_failure_config['message'], run_context)}"
                    )
                if "set_context_var" in on_failure_config:
                    for var_name, var_value_template in on_failure_config[
                        "set_context_var"
                    ].items():
                        run_context["vars"][var_name] = render_structured_data(
                            var_value_template, run_context
                        )
                        log_debug(
                            f"Set context var on failure: {var_name} = {run_context['vars'][var_name]}",
                            verbose,
                        )
                if "confirm_continue" in on_failure_config:
                    if not handle_interactive_prompt(
                        {
                            "type": "confirm",
                            "message": render_template(
                                on_failure_config["confirm_continue"], run_context
                            ),
                        },
                        run_context,
                        verbose,
                    ):
                        log_warning(
                            f"Pipe execution halted by Architect after failure in step '{step_name}'."
                        )
                        break  # Stop processing further steps in the pipe
            else:  # Default behavior if no on_failure: halt pipe
                log_warning(
                    f"Pipe execution halted due to failure in step '{step_name}'."
                )
                break
        elif step_result.get("status") == "SUCCESS":
            on_success_config = step_config.get("on_success")
            if on_success_config:
                if "message" in on_success_config:
                    log_info(
                        f"On_success message for '{step_name}': {render_template(on_success_config['message'], run_context)}"
                    )
                if "set_context_var" in on_success_config:
                    for var_name, var_value_template in on_success_config[
                        "set_context_var"
                    ].items():
                        run_context["vars"][var_name] = render_structured_data(
                            var_value_template, run_context
                        )
                        log_debug(
                            f"Set context var on success: {var_name} = {run_context['vars'][var_name]}",
                            verbose,
                        )

        # Post-step prompt, regardless of success/failure if not halted
        if (
            "prompt_user_after" in step_config
        ):  # Renamed from prompt_user to avoid conflict with prompt-only step
            handle_interactive_prompt(
                step_config["prompt_user_after"], run_context, verbose
            )

        log_info(
            f"--- Finished Pipe Step: {step_name} (Status: {step_result.get('status')}) ---"
        )

    log_info(
        f"Pipe '{pipe_name}' execution finished with Overall Status: {overall_pipe_status}"
    )
    run_context["overall_pipe_status"] = overall_pipe_status
    return run_context


# --- Main CLI Parsing and Execution ---
def main():
    parser = argparse.ArgumentParser(
        description="NexusConductor: Orchestrates Scribe and Ex-Work using YAML Pipe Definitions.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--pipe", required=True, help="Path to the YAML Pipe Definition file."
    )
    parser.add_argument(
        "--vars",
        default="{}",
        help='A JSON string of initial variables to pass to the pipe (e.g., \'{"key": "value"}\')',
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Enable verbose debug logging."
    )
    args = parser.parse_args()

    try:
        initial_vars = json.loads(args.vars)
        if not isinstance(initial_vars, dict):
            raise ValueError("--vars must be a JSON object (dictionary).")
    except json.JSONDecodeError as e:
        log_error(f"Invalid JSON string for --vars: {e}")
        sys.exit(1)
    except ValueError as e:
        log_error(str(e))
        sys.exit(1)

    pipe_file_path = Path(args.pipe)
    if not pipe_file_path.is_file():
        log_error(f"Pipe definition file not found: {pipe_file_path}")
        sys.exit(1)

    try:
        with open(pipe_file_path, "r", encoding="utf-8") as f:
            pipe_definition = yaml.safe_load(f)
        if not pipe_definition or not isinstance(pipe_definition.get("steps"), list):
            log_error(
                f"Invalid pipe definition in '{pipe_file_path}'. Must be YAML with a 'steps' list."
            )
            sys.exit(1)
    except yaml.YAMLError as e:
        log_error(f"Error parsing YAML pipe definition file '{pipe_file_path}': {e}")
        sys.exit(1)
    except Exception as e:
        log_error(f"Could not load pipe definition '{pipe_file_path}': {e}")
        sys.exit(1)

    final_context = run_pipe(pipe_definition, initial_vars, args.verbose)

    log_info("\n--- Final Pipe Context (vars and step outputs) ---")
    # Pretty print the context for review
    print(json.dumps(final_context, indent=2, default=str))

    if final_context.get("overall_pipe_status") != "SUCCESS":
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
