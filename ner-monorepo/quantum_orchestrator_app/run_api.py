# File: ~/Projects/quantum_orchestrator_app/run_api.py
"""
Production WSGI Server runner using Gunicorn.

Reads configuration from the core config module and environment variables
to launch the Flask application defined in the api_server module.
"""

import os
import sys
import logging
from pathlib import Path

# Ensure the project root is in the Python path
project_root = Path(__file__).parent.resolve()
sys.path.insert(0, str(project_root))

try:
    # Import the settings loader from the core config module
    from quantum_orchestrator.games.nexus_omniengine_v3.core.config import get_settings

    settings = get_settings()
    # Apply logging level from config to root logger *before* Gunicorn forks
    log_level_int = getattr(logging, settings.logging_level.upper(), logging.INFO)
    logging.basicConfig(
        level=log_level_int, format=settings.logging.get("format", None)
    )  # Use format from config if defined
    logger = logging.getLogger(__name__)
    logger.info(f"Attempting to start Gunicorn for {settings.app_name}...")

except ImportError:
    print(
        "ERROR: Cannot import core configuration. Ensure quantum_orchestrator package is installed or in PYTHONPATH."
    )
    sys.exit(1)
except Exception as e:
    print(f"ERROR: Failed to load settings: {e}")
    sys.exit(1)

# --- Gunicorn Configuration ---
# Get host and port from validated settings
HOST = settings.api_host
PORT = settings.api_port

# Application Module and Callable
# ASSUMPTION: Your Flask app is created by create_app() in api_server.py
# Adjust if your app object is named differently or located elsewhere.
APP_MODULE = "quantum_orchestrator.api.api_server:create_app()"

# Determine number of workers (sensible default based on CPU)
DEFAULT_WORKERS = (os.cpu_count() or 1) * 2 + 1
WORKERS = os.environ.get("GUNICORN_WORKERS", DEFAULT_WORKERS)

# Gunicorn command arguments
gunicorn_args = [
    "gunicorn",
    "--bind",
    f"{HOST}:{PORT}",
    "--workers",
    str(WORKERS),
    "--log-level",
    settings.logging_level.lower(),  # Use log level from config
    # '--access-logfile', '-', # Log access logs to stdout (can be verbose)
    "--error-logfile",
    "-",  # Log error logs to stdout
    APP_MODULE,
]

logger.info(f"Launching Gunicorn with command: {' '.join(gunicorn_args)}")

# Execute Gunicorn using execvp to replace the current process
# This is common practice for running web servers in containers
try:
    os.execvp("gunicorn", gunicorn_args)
except FileNotFoundError:
    logger.error(
        "ERROR: 'gunicorn' command not found. Is it installed in the environment?"
    )
    sys.exit(1)
except Exception as e:
    logger.error(f"ERROR: Failed to execute Gunicorn: {e}")
    sys.exit(1)
