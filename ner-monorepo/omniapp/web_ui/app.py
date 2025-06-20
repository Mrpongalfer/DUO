#!/usr/bin/env python3
# Omni Web UI - Flask Backend (v1.2 Bootstrap)
import sys
import os
from flask import Flask, render_template, request, flash
import subprocess
import json
from pathlib import Path

# Add parent directory (omnitide_cli package dir) to sys.path to import config_manager
# This assumes omni_web_ui and omnitide_cli are siblings under omniapp root
OMNIAPP_ROOT_DIR_FROM_WEBUI = Path(__file__).resolve().parent.parent
sys.path.insert(
    0, str(OMNIAPP_ROOT_DIR_FROM_WEBUI / "omnitide_cli")
)  # Add omnitide_cli package path

try:
    from omnitide_cli import config_manager as cli_config_mgr  # Import from package
except ImportError:
    print("ERROR: Could not import omnitide_cli.config_manager for Web UI.")
    print(
        f"Ensure omnitide_cli module is in PYTHONPATH or structured correctly relative to {OMNIAPP_ROOT_DIR_FROM_WEBUI}"
    )

    # Fallback definition for basic operation if import fails
    class cli_config_mgr:
        @staticmethod
        def load_config():
            return {
                "omnitide_app_root": str(OMNIAPP_ROOT_DIR_FROM_WEBUI),
                "exwork_agent_script": "../agents/exworkagent.py",
                "agents_dir": "../agents",
            }

        @staticmethod
        def get_config_value(key, cfg=None):
            config = cfg or cli_config_mgr.load_config()
            return config.get(key)


app = Flask(__name__)
app.secret_key = os.urandom(24)


def get_python_executable() -> str:
    return sys.executable or "python3"


@app.route("/")
def index():
    return render_template("index.html", title="Omnitide Web UI")


@app.route("/exwork", methods=["GET", "POST"])
def run_exwork_ui_route():
    config = cli_config_mgr.load_config()
    omniapp_root = Path(
        config.get("omnitide_app_root", str(OMNIAPP_ROOT_DIR_FROM_WEBUI))
    )
    agents_dir = omniapp_root / config.get("agents_dir", "agents")
    exwork_script_name = config.get("exwork_agent_script", "exworkagent.py")
    exwork_agent_script = (agents_dir / exwork_script_name).resolve()

    default_project_cwd_str = config.get("default_project_cwd", ".")
    project_cwd = Path(default_project_cwd_str)
    if not project_cwd.is_absolute():
        project_cwd = (omniapp_root / default_project_cwd_str).resolve()

    if request.method == "POST":
        exwork_json_payload_str = request.form.get("exwork_json_payload")
        if not exwork_json_payload_str:
            flash("ExWork JSON payload cannot be empty.", "error")
            return render_template(
                "run_exwork_ui.html",
                title="Run ExWork",
                submitted_payload=exwork_json_payload_str,
            )
        try:
            json.loads(exwork_json_payload_str)
        except json.JSONDecodeError as e:
            flash(f"Invalid JSON: {e}", "error")
            return render_template(
                "run_exwork_ui.html",
                title="Run ExWork",
                submitted_payload=exwork_json_payload_str,
            )

        if not exwork_agent_script.is_file():
            flash(
                f"ExWork Agent script not found at '{exwork_agent_script}'. Configure via 'omnitide-cli config wizard'.",
                "error",
            )
            return render_template(
                "run_exwork_ui.html",
                title="Run ExWork",
                submitted_payload=exwork_json_payload_str,
            )
        if not project_cwd.is_dir():
            flash(
                f"Project CWD not found at '{project_cwd}'. Configure via 'omnitide-cli config wizard'.",
                "error",
            )
            return render_template(
                "run_exwork_ui.html",
                title="Run ExWork",
                submitted_payload=exwork_json_payload_str,
            )

        python_exe = get_python_executable()
        command = [python_exe, str(exwork_agent_script)]

        results = {}
        try:
            process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=str(project_cwd),
                encoding="utf-8",
                errors="replace",
            )
            stdout, stderr = process.communicate(
                input=exwork_json_payload_str, timeout=300
            )

            results = {
                "stdout": stdout,
                "stderr": stderr,
                "return_code": process.returncode,
                "ran_successfully": process.returncode == 0,
            }
            if process.returncode == 0 and stdout:
                try:
                    results["exwork_summary"] = json.loads(stdout)
                except json.JSONDecodeError:
                    results["exwork_summary"] = "Could not parse ExWork stdout as JSON."

            if results["ran_successfully"]:
                flash("ExWork task completed successfully!", "success")
            else:
                flash(
                    f"ExWork task failed (RC: {process.returncode}). Check output.",
                    "error",
                )

        except subprocess.TimeoutExpired:
            flash("ExWork agent timed out.", "error")
            results = {"error": "ExWork agent timed out."}
        except Exception as e:
            flash(f"Error running ExWork agent: {e}", "error")
            results = {"error": f"Error running ExWork agent: {e}"}

        return render_template(
            "run_exwork_ui.html",
            title="Run ExWork",
            results=results,
            submitted_payload=exwork_json_payload_str,
        )

    default_echo_payload = {
        "step_id": "web_echo_01",
        "actions": [
            {"type": "ECHO", "message": "Hello from Omnitide Web UI via ExWork!"}
        ],
    }
    return render_template(
        "run_exwork_ui.html",
        title="Run ExWork",
        submitted_payload=json.dumps(default_echo_payload, indent=2),
    )


# Placeholder for Scribe UI route
@app.route("/scribe", methods=["GET", "POST"])
def run_scribe_ui_route():
    # Logic for Scribe will be similar: get params from form, run scribe.py, display report.
    flash("Scribe UI functionality is not yet implemented.", "info")
    return render_template("run_scribe_ui.html", title="Run Scribe")


if __name__ == "__main__":
    cfg = cli_config_mgr.load_config()
    omniapp_r = cfg.get("omnitide_app_root", "UNKNOWN (Run CLI config wizard)")
    print("INFO: Omnitide Web UI - Flask Application v1.2")
    print(f"INFO: Omniapp Root (from CLI config): {omniapp_r}")
    print("INFO: Flask dev server running on http://127.0.0.1:5678/")
    app.run(host="0.0.0.0", port=5678, debug=True)
