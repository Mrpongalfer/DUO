"""
Web Interface for the Quantum Orchestrator.

This module provides a user-friendly web interface for interacting with
the Quantum Orchestrator system.
"""

import logging
import os  # Add this import

from flask import Flask, render_template, request, jsonify

logger = logging.getLogger(__name__)


def create_app():
    """
    Create and configure the Flask application.

    Returns:
        The Flask application
    """
    app = Flask(__name__)

    # Configure the app
    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY", "quantum-orchestrator-dev-key"),
        DEBUG=True,
        SEND_FILE_MAX_AGE_DEFAULT=0,
    )

    # Register routes
    register_routes(app)

    return app


def register_routes(app):
    """
    Register routes for the Flask application.

    Args:
        app: The Flask application
    """

    @app.route("/")
    def index():
        """Main dashboard page."""
        return render_template("index.html")

    @app.route("/api/status")
    def status():
        """API status endpoint."""
        orchestrator = _get_orchestrator(app)

        if orchestrator:
            return jsonify(orchestrator.get_status())
        else:
            return jsonify({"error": "Orchestrator not available"}), 500

    @app.route("/api/execute", methods=["POST"])
    def execute():
        """API execute endpoint."""
        orchestrator = _get_orchestrator(app)

        if not orchestrator:
            return jsonify({"error": "Orchestrator not available"}), 500

        try:
            # Get instruction from request
            data = request.get_json()
            instruction = data.get("instruction")

            if not instruction:
                return jsonify({"error": "Missing instruction"}), 400

            # Execute the instruction asynchronously
            import asyncio

            result = asyncio.run(orchestrator.execute_instruction(instruction))

            return jsonify(result)
        except Exception as e:
            logger.error(f"Error executing instruction: {str(e)}")
            return jsonify({"error": f"Error executing instruction: {str(e)}"}), 500

    @app.route("/tools")
    def tools():
        """Tools page."""
        orchestrator = _get_orchestrator(app)

        if orchestrator:
            tools = orchestrator.get_available_tools()
            return render_template("tools.html", tools=tools)
        else:
            return render_template("error.html", error="Orchestrator not available")

    @app.route("/services")
    def services():
        """Services page."""
        try:
            from quantum_orchestrator.services.integration_service import (
                get_service_registry,
            )

            services = get_service_registry()
            return render_template("services.html", services=services)
        except Exception as e:
            logger.error(f"Error getting services: {str(e)}")
            return render_template(
                "error.html", error=f"Error getting services: {str(e)}"
            )

    @app.route("/console")
    def console():
        """Interactive console page."""
        return render_template("console.html")

    @app.route("/team")
    def team():
        """Core Team page."""
        return render_template("team.html")

    @app.errorhandler(404)
    def page_not_found(e):
        """404 error handler."""
        return render_template("error.html", error="Page not found"), 404

    @app.errorhandler(500)
    def server_error(e):
        """500 error handler."""
        return render_template("error.html", error=str(e)), 500


def _get_orchestrator(app):
    """
    Get the orchestrator instance from the Flask app.

    Args:
        app: The Flask application

    Returns:
        The orchestrator instance, or None if not available
    """
    return app.config.get("ORCHESTRATOR")
