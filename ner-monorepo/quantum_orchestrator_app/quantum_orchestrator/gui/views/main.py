"""
Main views blueprint.

This module provides the main views for the Quantum Orchestrator web interface.
"""

import time
import uuid
import asyncio

from flask import (
    Blueprint,
    render_template,
    request,
    jsonify,
    session,
)

from quantum_orchestrator import orchestrator
from quantum_orchestrator.utils.logging_utils import get_logger

logger = get_logger(__name__)

# Create blueprint
bp = Blueprint("main", __name__)

# Store conversation history for each session
conversation_history = {}


@bp.route("/")
def index():
    """
    Render the main dashboard page.

    Returns:
        Rendered dashboard template
    """
    # Get system status
    status = orchestrator.get_status()

    # Get recent workflows
    recent_workflows = orchestrator.state_manager.get_recent_workflows(10)

    # Get agent status information
    agents_status = orchestrator.get_agents_status()

    return render_template(
        "dashboard.html",
        status=status,
        recent_workflows=recent_workflows,
        agents_status=agents_status,
    )


@bp.route("/status")
def status():
    """
    Return system status as JSON.

    Returns:
        JSON with system status
    """
    status = orchestrator.get_status()
    return jsonify(status)


@bp.route("/about")
def about():
    """
    Render the about page.

    Returns:
        Rendered about template
    """
    return render_template("about.html")


@bp.route("/docs")
def docs():
    """
    Render the documentation page.

    Returns:
        Rendered documentation template
    """
    prime_function = {
        "code": "def is_prime(n):\n    if n <= 1:\n        return False\n    if n <= 3:\n        return True\n    if n % 2 == 0 or n % 3 == 0:\n        return False\n    i = 5\n    while i * i <= n:\n        if n % i == 0 or n % (i + 2) == 0:\n            return False\n        i += 6\n    return True\n\ndef get_primes(limit):\n    return [n for n in range(2, limit + 1) if is_prime(n)]"
    }
    return render_template("docs.html", prime_function=prime_function)


@bp.route("/chat")
def chat():
    """
    Render the interactive chat interface.

    Returns:
        Rendered chat template
    """
    # Generate session ID if not exists
    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())

    # Initialize conversation history for this session if needed
    session_id = session["session_id"]
    if session_id not in conversation_history:
        conversation_history[session_id] = [
            {
                "role": "system",
                "content": "Welcome to the Quantum Orchestrator interactive console. How can I assist you today?",
            }
        ]

    # Get system status and agents status
    status = orchestrator.get_status()
    agents_status = orchestrator.get_agents_status()

    return render_template(
        "chat.html",
        status=status,
        agents_status=agents_status,
        conversation=conversation_history[session_id],
    )


@bp.route("/api/chat", methods=["POST"])
def api_chat():
    """
    API endpoint for chat interactions.

    Returns:
        JSON response with chat result
    """
    try:
        # Get session ID
        if "session_id" not in session:
            session["session_id"] = str(uuid.uuid4())

        session_id = session["session_id"]

        # Initialize conversation history if needed
        if session_id not in conversation_history:
            conversation_history[session_id] = [
                {
                    "role": "system",
                    "content": "Welcome to the Quantum Orchestrator interactive console. How can I assist you today?",
                }
            ]

        # Get user message from request
        data = request.json
        user_message = data.get("message", "")

        if not user_message:
            return jsonify({"success": False, "error": "No message provided"})

        # Add user message to conversation history
        conversation_history[session_id].append(
            {"role": "user", "content": user_message, "timestamp": time.time()}
        )

        # Process the message as an intent-based instruction
        instruction = {"type": "intent", "intent": user_message}

        # Execute the instruction
        result = asyncio.run(orchestrator.execute_instruction(instruction))

        # Generate response based on result
        if result.get("success", False):
            response_content = result.get("result", {}).get(
                "output", "I've processed your request successfully."
            )
        else:
            response_content = (
                f"I encountered an error: {result.get('error', 'Unknown error')}"
            )

        # Add assistant response to conversation history
        conversation_history[session_id].append(
            {
                "role": "assistant",
                "content": response_content,
                "timestamp": time.time(),
                "execution_data": result,
            }
        )

        # Limit conversation history length
        if len(conversation_history[session_id]) > 50:
            conversation_history[session_id] = conversation_history[session_id][-50:]

        # Return the updated conversation
        return jsonify(
            {"success": True, "conversation": conversation_history[session_id]}
        )

    except Exception as e:
        logger.error(f"Error in chat API: {str(e)}")
        return jsonify({"success": False, "error": f"Error: {str(e)}"})


@bp.route("/console")
def console():
    """
    Render the interactive console interface.

    Returns:
        Rendered console template
    """
    # Get available tools/handlers for display
    available_tools = orchestrator.available_tools

    # Get system status
    status = orchestrator.get_status()

    return render_template(
        "console.html", status=status, available_tools=available_tools
    )


@bp.route("/api/execute", methods=["POST"])
def api_execute():
    """
    API endpoint for executing instructions directly.

    Returns:
        JSON response with execution result
    """
    try:
        # Get instruction from request
        data = request.json
        instruction = data.get("instruction", {})

        if not instruction:
            return jsonify({"success": False, "error": "No instruction provided"})

        # Execute the instruction
        result = asyncio.run(orchestrator.execute_instruction(instruction))

        # Return the result
        return jsonify(result)

    except Exception as e:
        logger.error(f"Error in execute API: {str(e)}")
        return jsonify({"success": False, "error": f"Error: {str(e)}"})
