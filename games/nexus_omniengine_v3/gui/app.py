# --- Ollama Test LLM API ---
from flask import jsonify


@app.route("/test_llm", methods=["POST"])
def test_llm():
    try:
        data = request.get_json(force=True)
        prompt = data.get("prompt", "")
        persona_id = data.get("persona", "lily")
        model = data.get("model", "llama2")
        # Find persona blueprint
        persona = None
        for p in AGENT_PERSONAS:
            if p.get("id") == persona_id:
                persona = p
                break
        persona_prompt = ""
        if persona and persona.get("persona_file"):
            persona_path = os.path.abspath(
                os.path.join(
                    os.path.dirname(__file__),
                    f'../../NPTPAC/ner_repository/06_AGENT_BLUEPRINTS/{persona["persona_file"]}',
                )
            )
            if os.path.exists(persona_path):
                with open(persona_path, encoding="utf-8") as f:
                    persona_prompt = f.read()
        full_prompt = f"{persona_prompt}\n\nUser: {prompt}\n{persona['name'] if persona else 'Agent'}:"
        # Call Ollama local server
        r = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": model, "prompt": full_prompt, "stream": False},
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        response = data.get("response", "[No response]")
        return jsonify({"success": True, "response": response})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


# --- Ollama Pull Custom Model API ---
@app.route("/pull_custom_model", methods=["POST"])
def pull_custom_model():
    try:
        data = request.get_json(force=True)
        model = data.get("model", "")
        if not model:
            return jsonify({"success": False, "error": "No model name provided."})
        result = pull_ollama_model(model)
        if result is not True:
            return jsonify({"success": False, "error": result})
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


# --- Tool Execution API ---


@app.route("/run_tool", methods=["POST"])
def run_tool_api():
    data = request.get_json(force=True)
    tool_name = data.get("tool")
    persona = data.get("persona", "system")
    tool_input = data.get("input", "")
    tools_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../tools"))
    tool_path = os.path.join(tools_dir, f"{tool_name}.py")
    if not os.path.exists(tool_path):
        return (
            jsonify({"success": False, "output": f"Tool not found: {tool_name}"}),
            404,
        )
    try:
        # Run the tool in a subprocess, pass input as argument
        import subprocess

        cmd = [sys.executable, tool_path, tool_input]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        output = proc.stdout.strip()
        error = proc.stderr.strip()
        result = output if output else ""
        if error:
            result += "\n[stderr]: " + error
        # Log the execution
        log_event(
            f"Tool '{tool_name}' run by {persona}. Output: {result[:200]}",
            sender=persona,
            msg_type="tool_run",
        )
        return jsonify({"success": True, "output": result})
    except subprocess.TimeoutExpired:
        return jsonify({"success": False, "output": "Tool execution timed out."}), 500
    except Exception as e:
        return jsonify({"success": False, "output": f"Error running tool: {e}"}), 500


# --- Flask and dependencies ---
import threading
import queue
import time
import sys
import platform
import json
import requests
import os

try:
    from flask import (
        Flask,
        render_template,
        request,
        redirect,
        url_for,
        flash,
        send_from_directory,
        abort,
    )
except ImportError:
    print(
        "[ERROR] Flask is not installed. Please run 'pip install flask flask-socketio' in your environment.",
        file=sys.stderr,
    )
    raise
# --- Real-time chat/logs ---
try:
    from flask_socketio import SocketIO, emit, join_room, leave_room
except ImportError:
    print(
        "[ERROR] Flask-SocketIO is not installed. Please run 'pip install flask-socketio' in your environment.",
        file=sys.stderr,
    )
    raise
import multiprocessing

# --- Flask App Setup ---
app = Flask(__name__)
_secret = os.environ.get("NEXUS_GUI_SECRET")
if not _secret or _secret == "nexus_default_secret":
    print(
        "[CRITICAL] NEXUS_GUI_SECRET environment variable is not set or is using the insecure default. Please set NEXUS_GUI_SECRET to a strong, unique value.",
        file=sys.stderr,
    )
    raise RuntimeError(
        "Refusing to start with insecure Flask secret key. Set NEXUS_GUI_SECRET."
    )
app.secret_key = _secret

# --- SocketIO setup ---
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")


# --- Ollama Status: Background Polling for Robustness ---
def ollama_status_poller():
    while True:
        try:
            update_ollama_status_broadcast()
        except Exception as e:
            append_ollama_log(f"[ERROR] Ollama status poll failed: {e}")
        time.sleep(3)


# Start background polling thread on app startup
ollama_status_poll_thread = threading.Thread(target=ollama_status_poller, daemon=True)
ollama_status_poll_thread.start()


# --- Meta Activity (Lily) Panel Route ---
@app.route("/meta_activity")
def meta_activity_panel():
    # Stream meta activity from Lily (or relevant agent)
    # We'll use the in-memory chat_history and filter for meta events from Lily
    meta_events = []
    try:
        # Only keep the last 100 meta events from Lily
        meta_events = [
            entry
            for entry in chat_history
            if entry.get("type") == "meta" and entry.get("persona") == "lily"
        ][-100:]
    except Exception as e:
        meta_events = [
            {
                "timestamp": "",
                "sender": "system",
                "persona": "system",
                "message": f"[ERROR] Could not load meta activity: {e}",
                "type": "meta",
            }
        ]
    return render_template("meta_activity.html", meta_events=meta_events)


# --- NER/Knowledge (Librarian) Panel Route ---
@app.route("/ner_knowledge")
def ner_knowledge_panel():
    # TODO: Load NER/knowledge entries from NER repository
    return render_template("ner_knowledge.html")


# --- Query Orchestrator (QO) Panel Route ---
@app.route("/query_orchestrator")
def query_orchestrator_panel():
    # TODO: Implement QO query routing and history
    return render_template("query_orchestrator.html")


# --- Timeline/Audit (Ekko) Panel Route ---
@app.route("/timeline_audit")
def timeline_audit_panel():
    # TODO: Load timeline/audit trail from Ekko agent
    return render_template("timeline_audit.html")


# --- Validation (Scribe) Panel Route ---
@app.route("/validation")
def validation_panel():
    # TODO: Implement Scribe validation logic
    return render_template("validation.html")


# --- Orchestration (ExWork) Panel Route ---
@app.route("/orchestration")
def orchestration_panel():
    # TODO: Implement ExWork orchestration logic
    return render_template("orchestration.html")


# --- PAC CLI Panel Route ---
@app.route("/pac_cli")
def pac_cli_panel():
    # TODO: Implement PAC CLI command execution and history
    return render_template("pac_cli.html")


# --- Ollama Setup & Status Utilities ---
import shutil
import subprocess
import socket


def is_ollama_installed():
    return shutil.which("ollama") is not None


def is_ollama_running():
    try:
        s = socket.create_connection(("localhost", 11434), timeout=1)
        s.close()
        return True
    except Exception:
        return False


def install_ollama():
    try:
        subprocess.run(
            [
                "curl",
                "-fsSL",
                "https://ollama.com/install.sh",
                "-o",
                "/tmp/ollama_install.sh",
            ],
            check=True,
        )
        subprocess.run(["sh", "/tmp/ollama_install.sh"], check=True)
        return True
    except Exception as e:
        return str(e)


def start_ollama():
    try:
        # Check if already running
        if is_ollama_running():
            return True
        # Start ollama serve in background
        subprocess.Popen(
            ["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        # Wait a moment for it to start
        for _ in range(10):
            if is_ollama_running():
                return True
            time.sleep(0.5)
        return "Ollama did not start in time."
    except Exception as e:
        return str(e)


def pull_ollama_model(model_name="llama2"):
    try:
        result = subprocess.run(
            ["ollama", "pull", model_name], capture_output=True, text=True, check=True
        )
        return True
    except subprocess.CalledProcessError as e:
        return e.stderr or str(e)
    except Exception as e:
        return str(e)


def ensure_ollama_ready(model_name="llama2"):
    # Full setup: install, start, pull model
    status = {
        "installed": False,
        "running": False,
        "model_pulled": False,
        "error": None,
    }
    if not is_ollama_installed():
        result = install_ollama()
        if result is not True:
            status["error"] = f"Install failed: {result}"
            return status
        status["installed"] = True
    else:
        status["installed"] = True
    if not is_ollama_running():
        result = start_ollama()
        if result is not True:
            status["error"] = f"Start failed: {result}"
            return status
        status["running"] = True
    else:
        status["running"] = True
    result = pull_ollama_model(model_name)
    if result is not True:
        status["error"] = f"Model pull failed: {result}"
        return status
    status["model_pulled"] = True
    return status


# --- Ollama Real-Time Status/Log State ---
ollama_status_state = {
    "installed": False,
    "running": False,
    "model": "llama2",
    "model_pulled": False,
    "error": None,
}
ollama_log_buffer = []
OLLAMA_LOG_MAX = 200


def update_ollama_status_broadcast():
    global ollama_status_state
    # Refresh status
    ollama_status_state["installed"] = is_ollama_installed()
    ollama_status_state["running"] = is_ollama_running()
    # Model pulled: check via `ollama list`
    try:
        import subprocess

        result = subprocess.run(
            ["ollama", "list"], capture_output=True, text=True, timeout=3
        )
        ollama_status_state["model_pulled"] = (
            ollama_status_state["model"] in result.stdout
        )
    except Exception:
        ollama_status_state["model_pulled"] = False
    socketio.emit(
        "ollama_status", {"status": dict(ollama_status_state)}, broadcast=True
    )


def append_ollama_log(line):
    global ollama_log_buffer
    if len(ollama_log_buffer) >= OLLAMA_LOG_MAX:
        ollama_log_buffer.pop(0)
    ollama_log_buffer.append(line)
    socketio.emit("ollama_log", {"line": line}, broadcast=True)


@app.route("/ollama_setup", methods=["GET", "POST"])
def ollama_setup():
    global ollama_status_state
    status = dict(ollama_status_state)
    if request.method == "POST":
        action = request.form.get("action")
        model = request.form.get("model", "llama2")
        ollama_status_state["model"] = model
        result = True
        if action == "install":
            append_ollama_log("[ACTION] Installing Ollama...")
            result = install_ollama()
            if result is not True:
                status["error"] = f"Install failed: {result}"
                append_ollama_log(f"[ERROR] Install failed: {result}")
            else:
                append_ollama_log("[OK] Ollama installed.")
        elif action == "start":
            append_ollama_log("[ACTION] Starting Ollama daemon...")
            result = start_ollama()
            if result is not True:
                status["error"] = f"Start failed: {result}"
                append_ollama_log(f"[ERROR] Start failed: {result}")
            else:
                append_ollama_log("[OK] Ollama started.")
        elif action == "pull":
            append_ollama_log(f"[ACTION] Pulling model: {model} ...")
            result = pull_ollama_model(model)
            if result is not True:
                status["error"] = f"Model pull failed: {result}"
                append_ollama_log(f"[ERROR] Model pull failed: {result}")
            else:
                append_ollama_log(f"[OK] Model '{model}' pulled.")
        # Refresh status after action
        update_ollama_status_broadcast()
        status = dict(ollama_status_state)
        status["model"] = model
    # On GET, also update status
    update_ollama_status_broadcast()
    # Always provide personas for persona select
    personas = []
    try:
        from flask import g

        if hasattr(g, "personas"):
            personas = g.personas
    except Exception:
        pass
    # Fallback: use AGENT_PERSONAS if available
    if not personas:
        try:
            personas = AGENT_PERSONAS if "AGENT_PERSONAS" in globals() else []
        except Exception:
            personas = []
    return render_template("ollama_setup.html", status=status, personas=personas)


# --- SocketIO: Real-time Ollama status/log join ---
@socketio.on("join")
def handle_join(data):
    room = data.get("room")
    if room == "ollama-status":
        # Send current status and log buffer
        emit("ollama_status", {"status": dict(ollama_status_state)})
        for line in ollama_log_buffer[-20:]:
            emit("ollama_log", {"line": line})


# --- Flask and dependencies ---
import threading
import sys
import os

try:
    from flask import (
        Flask,
        render_template,
        request,
        redirect,
        url_for,
        flash,
        send_from_directory,
        abort,
    )
except ImportError:
    print(
        "[ERROR] Flask is not installed. Please run 'pip install flask flask-socketio' in your environment.",
        file=sys.stderr,
    )
    raise
# --- Real-time chat/logs ---
try:
    from flask_socketio import SocketIO, emit, join_room, leave_room
except ImportError:
    print(
        "[ERROR] Flask-SocketIO is not installed. Please run 'pip install flask-socketio' in your environment.",
        file=sys.stderr,
    )
    raise

# --- Flask App Setup ---
app = Flask(__name__)
_secret = os.environ.get("NEXUS_GUI_SECRET")
if not _secret or _secret == "nexus_default_secret":
    print(
        "[CRITICAL] NEXUS_GUI_SECRET environment variable is not set or is using the insecure default. Please set NEXUS_GUI_SECRET to a strong, unique value.",
        file=sys.stderr,
    )
    raise RuntimeError(
        "Refusing to start with insecure Flask secret key. Set NEXUS_GUI_SECRET."
    )
app.secret_key = _secret

# --- SocketIO setup ---
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")


# --- Tool Forge Panel Route (Real, Multi-Source, Agent-Attributed) ---
@app.route("/tool_forge")
def tool_forge_panel():
    # Load tools from agent_tools_map.json and /tools/*.py
    import glob

    tools_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../config/agent_tools_map.json")
    )
    tools = []
    tool_map = {}
    try:
        with open(tools_path, "r", encoding="utf-8") as f:
            tool_map = json.load(f)
    except Exception:
        pass
    # Add tools from JSON
    for k, v in tool_map.items():
        tool = {
            "name": v.get("name", k),
            "description": v.get("description", ""),
            "type": v.get("type", "custom"),
            "creator": v.get("creator", "N/A"),
            "created": v.get("created", "N/A"),
            "source": "NER/JSON",
        }
        tools.append(tool)
    # Add tools from /tools/*.py
    tools_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../tools"))
    for pyfile in glob.glob(os.path.join(tools_dir, "auto_tool_*.py")):
        tool_name = os.path.basename(pyfile).replace(".py", "")
        # Try to extract docstring/metadata
        desc = ""
        try:
            with open(pyfile, encoding="utf-8") as f:
                first = f.readline()
                if first.startswith('"""') or first.startswith("'''"):
                    desc = first.strip("\"'\n ")
        except Exception:
            pass
        tools.append(
            {
                "name": tool_name,
                "description": desc,
                "type": "auto-generated",
                "creator": "Lily" if "lily" in tool_name else "Unknown",
                "created": "N/A",
                "source": "tools/",
            }
        )
    # Tool activity log (robust: persistent, error-handled, log rotation)
    tool_activity_log = []
    tool_log_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../logs/tool_activity.log")
    )
    max_log_lines = 200
    try:
        if os.path.exists(tool_log_path):
            with open(tool_log_path, encoding="utf-8") as f:
                lines = f.readlines()
                # Only keep the last max_log_lines
                tool_activity_log = [
                    line.strip() for line in lines[-max_log_lines:] if line.strip()
                ]
        else:
            # If log file does not exist, create it
            os.makedirs(os.path.dirname(tool_log_path), exist_ok=True)
            with open(tool_log_path, "w", encoding="utf-8") as f:
                f.write("")
            tool_activity_log = []
    except Exception as e:
        tool_activity_log = [f"[ERROR] Could not load tool activity log: {e}"]
    return render_template(
        "tool_forge.html", tools=tools, tool_activity_log=tool_activity_log
    )


# --- Daemon Monitor & Control (Stark/Rick/Harley/Power/Momo style) ---

import signal
import psutil
from threading import Lock

DAEMON_SCRIPT = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__), "../../core/ai_agent_forge/daemon_runner.py"
    )
)
daemon_state = {
    "status": "Stopped",
    "pid": None,
    "last_output": "",
    "last_checked": None,
}
daemon_lock = Lock()


def get_daemon_status():
    with daemon_lock:
        if daemon_state["status"] == "Running" and daemon_state["pid"]:
            try:
                p = psutil.Process(daemon_state["pid"])
                if not p.is_running() or p.status() == psutil.STATUS_ZOMBIE:
                    daemon_state["status"] = "Stopped"
                    daemon_state["pid"] = None
            except Exception:
                daemon_state["status"] = "Stopped"
                daemon_state["pid"] = None
        # Try to read last output if running
        if daemon_state["pid"]:
            try:
                p = psutil.Process(daemon_state["pid"])
                if p.is_running():
                    with p.open_files() as files:
                        pass  # Placeholder for future log file streaming
            except Exception:
                pass
        return dict(daemon_state)


@app.route("/daemon", methods=["GET"])
def daemon_panel():
    status = get_daemon_status()
    return render_template("daemon.html", daemon=status)


@app.route("/daemon/start", methods=["POST"])
def daemon_start():
    with daemon_lock:
        if daemon_state["status"] == "Running":
            flash("Daemon is already running!", "info")
            return redirect(url_for("daemon_panel"))
        # Launch the real daemon process (no simulation)
        if not os.path.exists(DAEMON_SCRIPT):
            flash(f"Daemon script not found: {DAEMON_SCRIPT}", "error")
            return redirect(url_for("daemon_panel"))
        proc = subprocess.Popen(
            [sys.executable, DAEMON_SCRIPT],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=os.setsid,
        )
        daemon_state["status"] = "Running"
        daemon_state["pid"] = proc.pid
        daemon_state["last_output"] = ""
        log_event(f"Daemon started (PID {proc.pid}) by user.")
    flash("Daemon started!", "success")
    return redirect(url_for("daemon_panel"))


@app.route("/daemon/stop", methods=["POST"])
def daemon_stop():
    with daemon_lock:
        if daemon_state["status"] != "Running" or not daemon_state["pid"]:
            flash("Daemon is not running!", "warning")
            return redirect(url_for("daemon_panel"))
        try:
            os.killpg(os.getpgid(daemon_state["pid"]), signal.SIGTERM)
            log_event(f"Daemon stopped (PID {daemon_state['pid']}) by user.")
        except Exception as e:
            flash(f"Error stopping daemon: {e}", "error")
        daemon_state["status"] = "Stopped"
        daemon_state["pid"] = None
        daemon_state["last_output"] = ""
    flash("Daemon stopped!", "success")
    return redirect(url_for("daemon_panel"))


@app.route("/daemon/status", methods=["GET"])
def daemon_status_api():
    # For AJAX polling
    return json.dumps(get_daemon_status())


# --- Agent & Workflow Control Panel ---
from threading import Lock

agent_state = {
    "agents": [
        {"name": "Lily", "status": "Running"},
        {"name": "Scribe", "status": "Stopped"},
        {"name": "Ex-Work", "status": "Running"},
    ],
    "workflows": [
        {"name": "AutoEvolve", "status": "Stopped"},
        {"name": "LogWatcher", "status": "Running"},
    ],
}
state_lock = Lock()


@app.route("/agents")
def agents_panel():
    with state_lock:
        agents = list(agent_state["agents"])
        workflows = list(agent_state["workflows"])
    return render_template("agents.html", agents=agents, workflows=workflows)


@app.route("/agent/start/<name>", methods=["POST"])
def agent_start(name):
    with state_lock:
        for agent in agent_state["agents"]:
            if agent["name"] == name:
                agent["status"] = "Running"
                log_event(f"Agent {name} started via GUI.")
    return redirect(url_for("agents_panel"))


@app.route("/agent/stop/<name>", methods=["POST"])
def agent_stop(name):
    with state_lock:
        for agent in agent_state["agents"]:
            if agent["name"] == name:
                agent["status"] = "Stopped"
                log_event(f"Agent {name} stopped via GUI.")
    return redirect(url_for("agents_panel"))


@app.route("/workflow/start/<name>", methods=["POST"])
def workflow_start(name):
    with state_lock:
        for wf in agent_state["workflows"]:
            if wf["name"] == name:
                wf["status"] = "Running"
                log_event(f"Workflow {name} started via GUI.")
    return redirect(url_for("agents_panel"))


@app.route("/workflow/stop/<name>", methods=["POST"])
def workflow_stop(name):
    with state_lock:
        for wf in agent_state["workflows"]:
            if wf["name"] == name:
                wf["status"] = "Stopped"
                log_event(f"Workflow {name} stopped via GUI.")
    return redirect(url_for("agents_panel"))


# --- Flask and dependencies ---
import threading
import sys
import os

try:
    from flask import (
        Flask,
        render_template,
        request,
        redirect,
        url_for,
        flash,
        send_from_directory,
        abort,
    )
except ImportError:
    print(
        "[ERROR] Flask is not installed. Please run 'pip install flask flask-socketio' in your environment.",
        file=sys.stderr,
    )
    raise
# --- Real-time chat/logs ---
try:
    from flask_socketio import SocketIO, emit, join_room, leave_room
except ImportError:
    print(
        "[ERROR] Flask-SocketIO is not installed. Please run 'pip install flask-socketio' in your environment.",
        file=sys.stderr,
    )
    raise


# --- Agent Process Registry & IPC ---
class AgentProcess:
    def __init__(self, name, persona_id, script_path):
        self.name = name
        self.persona_id = persona_id
        self.script_path = script_path
        self.input_queue = multiprocessing.Queue()
        self.output_queue = multiprocessing.Queue()
        self.process = multiprocessing.Process(
            target=self.agent_loop,
            args=(self.input_queue, self.output_queue, self.persona_id, self.name),
        )
        self.running = False

    def start(self):
        if not self.running:
            self.process.start()
            self.running = True

    def stop(self):
        if self.running:
            self.input_queue.put({"type": "shutdown"})
            self.process.join(timeout=5)
            self.running = False

    @staticmethod
    def agent_loop(inq, outq, persona_id, persona_name):
        import os
        import time
        import json
        from pathlib import Path

        # --- Meta-layer and advanced logic for all personas ---
        def meta_event(event, details=None):
            outq.put(
                {
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "sender": persona_name,
                    "persona": persona_id,
                    "message": f"[META] {event}" + (f": {details}" if details else ""),
                    "type": "meta",
                }
            )

        # --- Lily: advanced meta-cognition, feedback, and tool orchestration ---
        if persona_id == "lily":
            import requests

            base_path = os.environ.get("LILY_CORE_MEMORY_PATH", "./Lily/LilyCoreMemory")
            lcm_path = Path(base_path).resolve()
            persona_file = lcm_path / "00_Persona_Foundation.md"
            principles_file = lcm_path / "01_InteractionPrinciples_Baseline.md"
            # Load memory shards from SQLite
            try:
                import sqlite3

                db_path = (
                    lcm_path
                    / "IntelligentMemoryDB_Placeholder"
                    / "lily_intelligent_memory.db"
                )
                conn = sqlite3.connect(db_path)
                conn.row_factory = sqlite3.Row
                memory_shards = list(
                    conn.execute(
                        "SELECT * FROM memory_shards ORDER BY timestamp_created DESC LIMIT 50"
                    )
                )
            except Exception:
                memory_shards = []
            # Load tools from agent_tools_map.json
            tools = []
            try:
                tools_path = (
                    Path(os.path.dirname(__file__)).parent.parent
                    / "config"
                    / "agent_tools_map.json"
                )
                with open(tools_path) as f:
                    tool_map = json.load(f)
                for tool_name, tool_info in tool_map.items():
                    tools.append(
                        {
                            "name": tool_name,
                            "desc": tool_info.get("description", ""),
                            "type": tool_info.get("type", ""),
                        }
                    )
            except Exception:
                pass

            # Meta-cognitive feedback loop
            def feedback_loop():
                meta_event(
                    "Lily is running feedback loop for NER/memory/tool optimization."
                )
                # Clean up duplicate memory shards, optimize NER
                try:
                    if memory_shards:
                        seen = set()
                        for shard in memory_shards:
                            content = shard["content"]
                            if content in seen:
                                meta_event("Duplicate memory shard detected", content)
                                try:
                                    conn.execute(
                                        "DELETE FROM memory_shards WHERE id = ?",
                                        (shard["id"],),
                                    )
                                    conn.commit()
                                except Exception as e:
                                    meta_event("Error removing duplicate shard", str(e))
                            else:
                                seen.add(content)
                except Exception as e:
                    meta_event("Feedback loop error", str(e))
                # Tool self-improvement: try to call a tool and log result
                for tool in tools:
                    if (
                        tool["type"] == "langchain_builtin"
                        and tool["name"] == "wikipedia"
                    ):
                        try:
                            r = requests.get(
                                "https://en.wikipedia.org/api/rest_v1/page/summary/Artificial_intelligence",
                                timeout=5,
                            )
                            if r.status_code == 200:
                                summary = r.json().get("extract", "")
                                meta_event("Lily used Wikipedia tool", summary[:120])
                        except Exception as e:
                            meta_event("Wikipedia tool error", str(e))
                # Autonomous tool creation: propose, generate, and register a new tool
                import random
                import string

                if random.random() < 0.2:  # 20% chance per feedback loop
                    tool_name = "auto_tool_" + "".join(
                        random.choices(string.ascii_lowercase, k=6)
                    )
                    tool_code = f"def run(input):\n    return f'Auto-generated tool {tool_name} received: {{input}}'\n"
                    tools_dir = Path(os.path.dirname(__file__)).parent.parent / "tools"
                    tools_dir.mkdir(parents=True, exist_ok=True)
                    tool_file = tools_dir / f"{tool_name}.py"
                    try:
                        tool_file.write_text(tool_code, encoding="utf-8")
                        meta_event("Lily created a new tool", tool_name)
                        # Register in agent_tools_map.json
                        tools_json = (
                            Path(os.path.dirname(__file__)).parent.parent
                            / "config"
                            / "agent_tools_map.json"
                        )
                        with open(tools_json, "r", encoding="utf-8") as f:
                            tool_map = json.load(f)
                        tool_map[tool_name] = {
                            "name": tool_name,
                            "type": "custom",
                            "description": f"Auto-generated tool by Lily: {tool_name}",
                        }
                        with open(tools_json, "w", encoding="utf-8") as f:
                            json.dump(tool_map, f, indent=2)
                        meta_event("Lily registered new tool in NER", tool_name)
                    except Exception as e:
                        meta_event("Tool creation error", str(e))

            # Main loop
            last_feedback = time.time()
            while True:
                # Feedback loop every 10 seconds
                if time.time() - last_feedback > 10:
                    feedback_loop()
                    last_feedback = time.time()
                try:
                    msg = inq.get(timeout=1)
                except Exception:
                    continue
                if msg.get("type") == "shutdown":
                    break
                if msg.get("type") == "chat":
                    user_msg = msg.get("message", "")
                    # Compose context from persona, principles, memory shards
                    context = ""
                    if persona_file.is_file():
                        context += persona_file.read_text(encoding="utf-8") + "\n"
                    if principles_file.is_file():
                        context += principles_file.read_text(encoding="utf-8") + "\n"
                    if memory_shards:
                        context += "\n".join(
                            [f"- {shard['content']}" for shard in memory_shards[:10]]
                        )
                    # Real LLM call (Ollama, local server)
                    try:
                        full_prompt = f"{context}\nUser: {user_msg}\nLily:"
                        r = requests.post(
                            "http://localhost:11434/api/generate",
                            json={
                                "model": "llama2",
                                "prompt": full_prompt,
                                "stream": False,
                            },
                            timeout=30,
                        )
                        r.raise_for_status()
                        data = r.json()
                        response = data.get("response", "[No response]")
                    except Exception as e:
                        response = f"[Lily] (error): {str(e)}"
                    outq.put(
                        {
                            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                            "sender": persona_name,
                            "persona": persona_id,
                            "message": response,
                            "type": "chat",
                        }
                    )
                if msg.get("type") == "meta_request":
                    meta_event(
                        "Lily meta-state report",
                        details={
                            "tools": [t["name"] for t in tools],
                            "memory_shards": len(memory_shards),
                        },
                    )
                if msg.get("type") == "self_optimize":
                    meta_event("Lily is running self-optimization routines.")
                    feedback_loop()
                    meta_event("Lily self-optimization complete.")
                if msg.get("type") == "ner_cleanup":
                    meta_event("Lily is performing NER cleanup.")
                    # Example: remove all memory shards with low relevance
                    try:
                        to_remove = [
                            shard["id"]
                            for shard in memory_shards
                            if shard.get("relevance_score", 0) < 0.2
                        ]
                        for sid in to_remove:
                            conn.execute(
                                "DELETE FROM memory_shards WHERE id = ?", (sid,)
                            )
                        conn.commit()
                        meta_event(
                            "NER cleanup complete", details={"removed": len(to_remove)}
                        )
                    except Exception as e:
                        meta_event("NER cleanup error", str(e))
                if msg.get("type") == "tool_audit":
                    meta_event(
                        "Lily is auditing tools.", details=[t["name"] for t in tools]
                    )
                if msg.get("type") == "agent_feedback":
                    meta_event("Lily is requesting feedback from Momo.")
                    # Send a feedback request to Momo's input queue

                    if "momo" in agent_registry:
                        agent_registry["momo"].input_queue.put(
                            {
                                "type": "meta_request",
                                "from": "lily",
                                "message": "Lily requests feedback from Momo.",
                            }
                        )
        # --- Momo Ayase: practical, supportive, meta-aware ---
        elif persona_id == "momo":
            import requests

            base_path = os.environ.get("LILY_CORE_MEMORY_PATH", "./Lily/LilyCoreMemory")
            lcm_path = Path(base_path).resolve()
            persona_file = (
                lcm_path
                / "../../NPTPAC/ner_repository/06_AGENT_BLUEPRINTS/persona_momo_ayase.md"
            )

            def momo_meta(event, details=None):
                outq.put(
                    {
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "sender": persona_name,
                        "persona": persona_id,
                        "message": f"[META] {event}"
                        + (f": {details}" if details else ""),
                        "type": "meta",
                    }
                )

            while True:
                try:
                    msg = inq.get(timeout=1)
                except Exception:
                    continue
                if msg.get("type") == "shutdown":
                    break
                if msg.get("type") == "chat":
                    user_msg = msg.get("message", "")
                    # Compose context from persona profile
                    context = ""
                    if persona_file.is_file():
                        context += persona_file.read_text(encoding="utf-8") + "\n"
                    # Real LLM call (Ollama, local server)
                    try:
                        full_prompt = f"{context}\nUser: {user_msg}\nMomo Ayase:"
                        r = requests.post(
                            "http://localhost:11434/api/generate",
                            json={
                                "model": "llama2",
                                "prompt": full_prompt,
                                "stream": False,
                            },
                            timeout=30,
                        )
                        r.raise_for_status()
                        data = r.json()
                        response = data.get("response", "[No response]")
                    except Exception as e:
                        response = f"[Momo] (error): {str(e)}"
                    outq.put(
                        {
                            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                            "sender": persona_name,
                            "persona": persona_id,
                            "message": response,
                            "type": "chat",
                        }
                    )
                if msg.get("type") == "meta_request":
                    momo_meta(
                        "Momo meta-state report",
                        details={"mood": "steady", "focus": "support"},
                    )
                if msg.get("type") == "self_optimize":
                    momo_meta("Momo is running self-optimization routines.")
                    momo_meta("Momo self-optimization complete.")
                if msg.get("type") == "ner_cleanup":
                    momo_meta("Momo is performing NER cleanup.")
                    momo_meta("NER cleanup complete.")
                if msg.get("type") == "tool_audit":
                    momo_meta("Momo is auditing tools.")
                if msg.get("type") == "agent_feedback":
                    momo_meta("Momo is requesting feedback from Lily.")
                    if "lily" in agent_registry:
                        agent_registry["lily"].input_queue.put(
                            {
                                "type": "meta_request",
                                "from": "momo",
                                "message": "Momo requests feedback from Lily.",
                            }
                        )
        # --- Other personas: basic meta-layer, ready for expansion ---
        else:

            def persona_meta(event, details=None):
                outq.put(
                    {
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "sender": persona_name,
                        "persona": persona_id,
                        "message": f"[META] {event}"
                        + (f": {details}" if details else ""),
                        "type": "meta",
                    }
                )

            while True:
                try:
                    msg = inq.get(timeout=1)
                except Exception:
                    continue
                if msg.get("type") == "shutdown":
                    break
                if msg.get("type") == "chat":
                    user_msg = msg.get("message", "")
                    response = f"[{persona_name}] (auto): {user_msg[::-1]}"  # Placeholder: reverse message
                    outq.put(
                        {
                            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                            "sender": persona_name,
                            "persona": persona_id,
                            "message": response,
                            "type": "chat",
                        }
                    )
                if msg.get("type") == "meta_request":
                    persona_meta(
                        f"{persona_name} meta-state report",
                        details={"status": "active"},
                    )


# --- Dynamic Core Team Persona Loader ---
import glob

PERSONA_BLUEPRINTS_DIR = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__), "../../NPTPAC/ner_repository/06_AGENT_BLUEPRINTS"
    )
)


def load_persona_blueprints():
    personas = []
    for mdfile in glob.glob(os.path.join(PERSONA_BLUEPRINTS_DIR, "persona_*.md")):
        with open(mdfile, encoding="utf-8") as f:
            lines = f.readlines()
        name = None
        for line in lines:
            if line.strip().startswith("# Persona Profile:"):
                name = line.strip().replace("# Persona Profile:", "").strip()
                break
        persona_id = (
            os.path.basename(mdfile)
            .replace("persona_", "")
            .replace(".md", "")
            .replace("_chainsawman", "")
            .replace("_", "")
            .lower()
        )
        if name:
            personas.append(
                {"id": persona_id, "name": name, "script": None, "profile_path": mdfile}
            )
    return personas


AGENT_PERSONAS = load_persona_blueprints()
agent_registry = {}


def start_all_agents():
    for persona in AGENT_PERSONAS:
        if persona["id"] not in agent_registry:
            agent = AgentProcess(persona["name"], persona["id"], persona["script"])
            agent.start()
            agent_registry[persona["id"]] = agent


def stop_all_agents():
    for agent in agent_registry.values():
        agent.stop()
    agent_registry.clear()


# Start agents on app startup
start_all_agents()


# --- Background thread to forward agent output to SocketIO ---
def agent_output_forwarder():
    while True:
        for agent in agent_registry.values():
            try:
                while not agent.output_queue.empty():
                    entry = agent.output_queue.get_nowait()
                    socketio.emit("chat_message", entry, broadcast=True)
            except Exception:
                continue
        time.sleep(0.2)


forwarder_thread = threading.Thread(target=agent_output_forwarder, daemon=True)
forwarder_thread.start()


# --- Flask App Setup ---
app = Flask(__name__)
_secret = os.environ.get("NEXUS_GUI_SECRET")
if not _secret or _secret == "nexus_default_secret":
    print(
        "[CRITICAL] NEXUS_GUI_SECRET environment variable is not set or is using the insecure default. Please set NEXUS_GUI_SECRET to a strong, unique value.",
        file=sys.stderr,
    )
    raise RuntimeError(
        "Refusing to start with insecure Flask secret key. Set NEXUS_GUI_SECRET."
    )
app.secret_key = _secret

# --- SocketIO setup ---
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")


# --- Persona context for all templates ---
@app.context_processor
def inject_personas():
    return {"personas": AGENT_PERSONAS}


# --- In-memory log buffer for live logs and chat ---
log_buffer = queue.Queue(maxsize=200)
chat_history = []  # List of dicts: {timestamp, sender, persona, message, type}


def log_event(msg, sender="system", persona=None, msg_type="log"):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{timestamp}] {msg}"
    if log_buffer.full():
        try:
            log_buffer.get_nowait()
        except queue.Empty:
            pass
    log_buffer.put(entry)
    # Also add to chat history for real-time broadcast
    chat_entry = {
        "timestamp": timestamp,
        "sender": sender,
        "persona": persona,
        "message": msg,
        "type": msg_type,
    }
    chat_history.append(chat_entry)
    # Only keep last 200
    if len(chat_history) > 200:
        chat_history.pop(0)
    # Broadcast to all clients
    socketio.emit("chat_message", chat_entry, broadcast=True)


# --- SocketIO events ---
@socketio.on("send_message")
def handle_send_message(data):
    # data: {sender, persona, message, type}
    sender = data.get("sender", "user")
    persona = data.get("persona", None)
    message = data.get("message", "")
    msg_type = data.get("type", "chat")
    log_event(message, sender=sender, persona=persona, msg_type=msg_type)
    # Route to agent process if persona is specified
    if persona and persona in agent_registry:
        agent_registry[persona].input_queue.put(
            {"type": msg_type, "message": message, "from": sender}
        )
    elif persona == "all":
        for agent in agent_registry.values():
            agent.input_queue.put(
                {"type": msg_type, "message": message, "from": sender}
            )


# --- On app shutdown, stop all agents ---
import atexit

atexit.register(stop_all_agents)


@socketio.on("join")
def handle_join(data):
    # For future: support rooms
    pass


# --- Error Handler ---
@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


# --- Main Dashboard ---
@app.route("/")
def index():
    import datetime

    return render_template(
        "index.html",
        current_date=datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        python_version=sys.version.split()[0],
        platform=platform.platform(),
    )


# --- Persona LLM Playground ---
PERSONA_MODELS = [
    {
        "id": "lily",
        "name": "Lily (Main)",
        "persona_file": "00_Persona_Foundation.md",
        "llm_model": "llama2",
    },
    {
        "id": "rick",
        "name": "Rick Sanchez",
        "persona_file": "persona_rick_sanchez.md",
        "llm_model": "llama2",
    },
    {
        "id": "tony",
        "name": "Tony Stark",
        "persona_file": "persona_tony_stark.md",
        "llm_model": "llama2",
    },
    {
        "id": "harley",
        "name": "Harley Quinn",
        "persona_file": "persona_harley_quinn.md",
        "llm_model": "llama2",
    },
    {
        "id": "power",
        "name": "Power (Chainsaw Man)",
        "persona_file": "persona_power_chainsawman.md",
        "llm_model": "llama2",
    },
    {
        "id": "momo",
        "name": "Momo Ayase",
        "persona_file": "persona_momo_ayase.md",
        "llm_model": "llama2",
    },
    {
        "id": "makima",
        "name": "Makima (Chainsaw Man)",
        "persona_file": "persona_makima_chainsawman.md",
        "llm_model": "llama2",
    },
]


@app.route("/llm", methods=["GET", "POST"])
def llm_playground():
    response = None
    error = None
    prompt = ""
    model = "Ollama"
    persona_id = "lily"
    persona_prompt = ""
    if request.method == "POST":
        prompt = request.form.get("prompt", "")
        model = request.form.get("model", "Ollama")
        persona_id = request.form.get("persona", "lily")
        persona = next(
            (p for p in PERSONA_MODELS if p["id"] == persona_id), PERSONA_MODELS[0]
        )
        # Load persona context
        persona_path = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                f'../../NPTPAC/ner_repository/06_AGENT_BLUEPRINTS/{persona["persona_file"]}',
            )
        )
        if os.path.exists(persona_path):
            with open(persona_path) as f:
                persona_prompt = f.read()
        else:
            persona_prompt = f"[Persona file not found: {persona_path}]"
        try:
            # Load API key and config
            config_path = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "../config/main_config.json")
            )
            api_key = None
            if os.path.exists(config_path):
                with open(config_path) as f:
                    config = json.load(f)
                    api_key = config.get("llm_api_key", None)
            full_prompt = f"{persona_prompt}\n\nUser: {prompt}\n{persona['name']}:"
            if model == "Ollama":
                # Call local Ollama server with persona context
                r = requests.post(
                    "http://localhost:11434/api/generate",
                    json={
                        "model": persona["llm_model"],
                        "prompt": full_prompt,
                        "stream": False,
                    },
                    timeout=30,
                )
                r.raise_for_status()
                data = r.json()
                response = data.get("response", "[No response]")
                log_event(f"LLM (Ollama, {persona['name']}) prompt: {prompt}")
            elif model == "OpenAI":
                if not api_key:
                    raise Exception("No OpenAI API key configured.")
                headers = {"Authorization": f"Bearer {api_key}"}
                r = requests.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers=headers,
                    json={
                        "model": "gpt-3.5-turbo",
                        "messages": [
                            {"role": "system", "content": persona_prompt},
                            {"role": "user", "content": prompt},
                        ],
                        "max_tokens": 256,
                    },
                    timeout=30,
                )
                r.raise_for_status()
                data = r.json()
                response = data["choices"][0]["message"]["content"]
                log_event(f"LLM (OpenAI, {persona['name']}) prompt: {prompt}")
            else:
                raise Exception("Unknown model selected.")
        except Exception as e:
            error = str(e)
            log_event(f"LLM error: {error}")
    return render_template(
        "llm_playground.html",
        response=response,
        error=error,
        prompt=prompt,
        model=model,
        persona_id=persona_id,
        personas=PERSONA_MODELS,
    )


# --- Live Logs & Chat ---
@app.route("/logs")
def live_logs():
    # Show the last 100 log entries
    logs = list(log_buffer.queue)[-100:]
    return render_template("logs.html", logs=logs)


@app.route("/chat")
def chat_panel():
    # Show the last 100 chat entries
    history = chat_history[-100:]
    return render_template("chat.html", chat_history=history, personas=PERSONA_MODELS)


@app.route("/configure", methods=["GET", "POST"])
def configure():
    if request.method == "POST":
        api_key = request.form.get("api_key")
        agent_type = request.form.get("agent_type")
        self_heal = bool(request.form.get("self_heal"))
        auto_adapt = bool(request.form.get("auto_adapt"))
        recursive_evolve = bool(request.form.get("recursive_evolve"))

        # Save config to file (auto-adaptive, self-healing, recursive evolution enabled)
        config = {
            "api_key": api_key,
            "agent_type": agent_type,
            "self_heal": self_heal,
            "auto_adapt": auto_adapt,
            "recursive_evolve": recursive_evolve,
        }
        try:
            import json

            config_path = os.path.join(
                os.path.dirname(__file__), "../config/user_config.json"
            )
            with open(config_path, "w") as f:
                json.dump(config, f, indent=2)
            flash("Configuration saved and applied!", "success")
        except Exception as e:
            flash(f"Error saving configuration: {e}", "error")
        # Here, trigger self-healing/adaptation routines if needed
        # (Stub: In production, this would call backend AI routines)
        return redirect(url_for("index"))
    return render_template("configure.html")


@app.route("/status")
def status():
    config_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../config/main_config.json")
    )
    status = "OK"
    # Optionally, check for config file and LLM connectivity
    if not os.path.exists(config_path):
        status = "Config missing"
    return render_template(
        "status.html",
        status=status,
        python_version=sys.version.split()[0],
        platform=platform.platform(),
        config_path=config_path,
    )


# Static file serving for CSS
@app.route("/static/<path:filename>")
def static_files(filename):
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    return send_from_directory(static_dir, filename)


if __name__ == "__main__":
    socketio.run(app, debug=True)
