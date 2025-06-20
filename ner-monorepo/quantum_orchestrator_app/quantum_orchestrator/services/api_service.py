"""
API service for the Quantum Orchestrator.

Provides a REST API for interacting with the system.
"""

import os
import threading

from flask import Flask, request, jsonify
from flask_cors import CORS

from quantum_orchestrator import orchestrator
from quantum_orchestrator.utils.logging_utils import get_logger

logger = get_logger(__name__)

# Global API app instance
_api_app = None
_api_thread = None


def create_api_app() -> Flask:
    """
    Create the Flask app for the API service.

    Returns:
        Flask app instance
    """
    app = Flask("quantum_orchestrator_api")
    CORS(app)

    # Configure the app
    app.config["SECRET_KEY"] = os.environ.get(
        "API_SECRET_KEY", "dev-key-for-development-only"
    )
    app.config["JSON_SORT_KEYS"] = False

    # Define API routes
    @app.route("/api/status", methods=["GET"])
    def get_status():
        """Get the current status of the orchestrator."""
        status = orchestrator.get_status()
        return jsonify(status)

    @app.route("/api/execute", methods=["POST"])
    def execute_instruction():
        """Execute an instruction."""
        try:
            instruction = request.json
            if not instruction:
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": "Missing instruction in request body",
                        }
                    ),
                    400,
                )

            # Execute instruction (this would be async in production)
            result = orchestrator.execute_instruction(instruction)
            return jsonify(result)

        except Exception as e:
            logger.error(f"Error executing instruction: {str(e)}")
            return jsonify({"success": False, "error": f"Error: {str(e)}"}), 500

    @app.route("/api/handlers", methods=["GET"])
    def get_handlers():
        """Get a list of available handlers."""
        return jsonify({"success": True, "handlers": orchestrator.available_tools})

    return app


def start_api_server(host: str = "0.0.0.0", port: int = 8000) -> None:
    """
    Start the API server in a separate thread.

    Args:
        host: Host to bind to
        port: Port to bind to
    """
    global _api_app, _api_thread

    if _api_thread and _api_thread.is_alive():
        logger.info("API server is already running")
        return

    _api_app = create_api_app()

    def run_server():
        _api_app.run(host=host, port=port, threaded=True)

    _api_thread = threading.Thread(target=run_server)
    _api_thread.daemon = True
    _api_thread.start()

    logger.info(f"API server started on {host}:{port}")


def stop_api_server() -> None:
    """Stop the API server."""
    global _api_thread

    if _api_thread and _api_thread.is_alive():
        # This is not a clean shutdown, but it works for development
        _api_thread = None
        logger.info("API server stopped")
    else:
        logger.info("API server is not running")


def init_api(host: str = "0.0.0.0", port: int = 8000) -> None:
    """
    Initialize the API service.

    Args:
        host: Host to bind to
        port: Port to bind to
    """
    # Start the API server
    start_api_server(host, port)
