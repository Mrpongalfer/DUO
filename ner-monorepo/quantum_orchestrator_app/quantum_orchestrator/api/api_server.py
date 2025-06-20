"""
API Server for the Quantum Orchestrator.

This module implements a simple API server for the Quantum Orchestrator.
"""

import json
import logging
from typing import Any
from http.server import HTTPServer, BaseHTTPRequestHandler
import socketserver
import urllib.parse

logger = logging.getLogger(__name__)

# Global orchestrator instance
_orchestrator_instance = None


class OrchestrationHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the orchestration API."""

    def do_GET(self):
        """Handle GET requests."""
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path

        # Handle different API endpoints
        if path == "/api/status":
            self._handle_status()
        elif path == "/api/tools":
            self._handle_get_tools()
        elif path == "/api/services":
            self._handle_get_services()
        else:
            self._send_response(404, {"error": "Not found"})

    def do_POST(self):
        """Handle POST requests."""
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path

        # Get request body
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8")

        try:
            # Parse JSON body if present
            data = json.loads(body) if body else {}

            # Handle different API endpoints
            if path == "/api/execute":
                self._handle_execute(data)
            elif path == "/api/services/discover":
                self._handle_discover_services()
            elif path == "/api/services/invoke":
                self._handle_invoke_service(data)
            else:
                self._send_response(404, {"error": "Not found"})

        except json.JSONDecodeError:
            self._send_response(400, {"error": "Invalid JSON"})
        except Exception as e:
            logger.error(f"Error handling request: {str(e)}")
            self._send_response(500, {"error": f"Internal server error: {str(e)}"})

    def _handle_status(self):
        """Handle status endpoint."""
        global _orchestrator_instance

        if _orchestrator_instance:
            # Get status from orchestrator
            status = _orchestrator_instance.get_status()
            self._send_response(200, status)
        else:
            self._send_response(500, {"error": "Orchestrator not available"})

    def _handle_get_tools(self):
        """Handle get tools endpoint."""
        global _orchestrator_instance

        if _orchestrator_instance:
            # Get available tools from orchestrator
            tools = _orchestrator_instance.get_available_tools()
            self._send_response(200, {"tools": tools})
        else:
            self._send_response(500, {"error": "Orchestrator not available"})

    def _handle_get_services(self):
        """Handle get services endpoint."""
        global _orchestrator_instance

        if _orchestrator_instance:
            # Get available services from orchestrator
            try:
                from quantum_orchestrator.services.integration_service import (
                    get_service_registry,
                )

                services = get_service_registry()

                # Convert ServiceInfo objects to dictionaries
                services_dict = {
                    service_id: service.to_dict()
                    for service_id, service in services.items()
                }

                self._send_response(200, {"services": services_dict})
            except Exception as e:
                logger.error(f"Error getting services: {str(e)}")
                self._send_response(500, {"error": f"Error getting services: {str(e)}"})
        else:
            self._send_response(500, {"error": "Orchestrator not available"})

    def _handle_execute(self, data):
        """Handle execute endpoint."""
        global _orchestrator_instance

        if _orchestrator_instance:
            # Execute instruction through orchestrator
            try:
                # Get instruction from request
                instruction = data.get("instruction")
                if not instruction:
                    self._send_response(400, {"error": "Missing instruction"})
                    return

                # Execute the instruction asynchronously
                import asyncio

                result = asyncio.run(
                    _orchestrator_instance.execute_instruction(instruction)
                )

                self._send_response(200, result)
            except Exception as e:
                logger.error(f"Error executing instruction: {str(e)}")
                self._send_response(
                    500, {"error": f"Error executing instruction: {str(e)}"}
                )
        else:
            self._send_response(500, {"error": "Orchestrator not available"})

    def _handle_discover_services(self):
        """Handle discover services endpoint."""
        global _orchestrator_instance

        if _orchestrator_instance:
            try:
                from quantum_orchestrator.services.integration_service import (
                    discover_services,
                )

                # Force discovery of services
                services = discover_services(force=True)

                # Convert ServiceInfo objects to dictionaries
                services_dict = [service.to_dict() for service in services]

                self._send_response(200, {"services": services_dict})
            except Exception as e:
                logger.error(f"Error discovering services: {str(e)}")
                self._send_response(
                    500, {"error": f"Error discovering services: {str(e)}"}
                )
        else:
            self._send_response(500, {"error": "Orchestrator not available"})

    def _handle_invoke_service(self, data):
        """Handle invoke service endpoint."""
        global _orchestrator_instance

        if _orchestrator_instance:
            try:
                # Extract parameters
                service_url = data.get("service_url")
                api_endpoint = data.get("api_endpoint")
                parameters = data.get("parameters", {})
                auth_credentials = data.get("auth_credentials")
                method = data.get("method", "GET")

                # Validate parameters
                if not service_url or not api_endpoint:
                    self._send_response(
                        400, {"error": "Missing service_url or api_endpoint"}
                    )
                    return

                # Invoke the service
                result = _orchestrator_instance.invoke_service(
                    service_url=service_url,
                    api_endpoint=api_endpoint,
                    parameters=parameters,
                    auth_credentials=auth_credentials,
                    method=method,
                )

                self._send_response(200, result)
            except Exception as e:
                logger.error(f"Error invoking service: {str(e)}")
                self._send_response(500, {"error": f"Error invoking service: {str(e)}"})
        else:
            self._send_response(500, {"error": "Orchestrator not available"})

    def _send_response(self, status_code, data):
        """Send a JSON response."""
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()

        response = json.dumps(data, default=str).encode("utf-8")
        self.wfile.write(response)


class ThreadedHTTPServer(socketserver.ThreadingMixIn, HTTPServer):
    """Threaded HTTP server for handling concurrent requests."""

    pass


def start_api_server(orchestrator_instance: Any, port: int = 8000) -> None:
    """
    Start the API server.

    Args:
        orchestrator_instance: The orchestrator instance to use
        port: Port to listen on
    """
    global _orchestrator_instance
    _orchestrator_instance = orchestrator_instance

    # Create and start the server
    server = ThreadedHTTPServer(("0.0.0.0", port), OrchestrationHandler)

    logger.info(f"Starting API server on port {port}")
    try:
        server.serve_forever()
    except Exception as e:
        logger.error(f"Error starting API server: {str(e)}")
    finally:
        server.server_close()
        logger.info("API server stopped")
