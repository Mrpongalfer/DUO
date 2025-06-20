"""
Generated handler: chat_interface_handler

Description: Handles interactions with the chat interface and processes natural language commands
"""

import json
import time
import re
from typing import Dict, Any, List

from quantum_orchestrator.handlers import handler
from quantum_orchestrator.utils.logging_utils import get_logger
from quantum_orchestrator.services.llm_service import (
    generate_completion,
)

logger = get_logger(__name__)


@handler(
    name="chat_message_handler",
    description="Process a chat message and generate an appropriate response",
    parameters={
        "message": {"type": "string", "description": "The user message to process"},
        "conversation_history": {
            "type": "array",
            "description": "Previous messages in the conversation",
            "default": [],
        },
        "user_id": {
            "type": "string",
            "description": "ID of the user sending the message",
            "default": "default_user",
        },
        "context": {
            "type": "object",
            "description": "Additional context for message processing",
            "default": {},
        },
    },
    returns={
        "success": {
            "type": "boolean",
            "description": "Whether the message was processed successfully",
        },
        "response": {"type": "string", "description": "The generated response"},
        "actions": {
            "type": "array",
            "description": "List of actions to perform based on the message",
        },
        "error": {
            "type": "string",
            "description": "Error message if processing failed",
        },
    },
)
def chat_message_handler(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a chat message and generate an appropriate response.

    This handler takes a user message from the chat interface, analyzes it,
    and generates a response. It can also determine actions to take based
    on the message content.

    Args:
        params: Dictionary containing message, conversation history, and context

    Returns:
        Dict containing success flag, response, actions, and error message if any
    """
    try:
        # Extract parameters
        message = params.get("message", "")
        conversation_history = params.get("conversation_history", [])
        user_id = params.get("user_id", "default_user")
        context = params.get("context", {})

        # Validate parameters
        if not message:
            return {"success": False, "error": "Message is required"}

        # Process the message
        logger.info(f"Processing chat message from user {user_id}: {message[:50]}...")

        # Check for specific commands
        if message.startswith("/"):
            return _process_command(message, user_id, context)

        # Convert conversation history to a format suitable for context
        formatted_history = _format_conversation_history(conversation_history)

        # Generate a response using LLM
        system_prompt = """You are the Quantum Orchestrator, an advanced AI system with multiple specialized agents.
        Your capabilities include code generation, data processing, system optimization, and task planning.
        Respond to the user's query in a helpful and informative manner. If the user is asking for a specific action,
        identify the intention and suggest how you can help implement it."""

        full_prompt = f"{system_prompt}\n\nCONVERSATION HISTORY:\n{formatted_history}\n\nUSER: {message}\n\nQUANTUM ORCHESTRATOR:"

        response = generate_completion(
            prompt=full_prompt, temperature=0.7, max_tokens=1000
        )

        # Analyze the response for potential actions
        actions = _extract_actions(message, response)

        return {
            "success": True,
            "response": response,
            "actions": actions,
            "user_id": user_id,
            "timestamp": time.time(),
        }

    except Exception as e:
        logger.error(f"Error in chat_message_handler: {str(e)}")
        return {
            "success": False,
            "error": f"Error processing message: {str(e)}",
            "response": "I encountered an error processing your message. Please try again.",
        }


@handler(
    name="command_handler",
    description="Process a command entered in the chat interface",
    parameters={
        "command": {"type": "string", "description": "The command to process"},
        "args": {"type": "object", "description": "Command arguments", "default": {}},
        "user_id": {
            "type": "string",
            "description": "ID of the user issuing the command",
            "default": "default_user",
        },
    },
    returns={
        "success": {
            "type": "boolean",
            "description": "Whether the command was processed successfully",
        },
        "response": {"type": "string", "description": "The command response"},
        "data": {
            "type": "object",
            "description": "Additional data returned by the command",
        },
        "error": {"type": "string", "description": "Error message if command failed"},
    },
)
def command_handler(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a command entered in the chat interface.

    This handler processes special commands that start with "/" in the chat interface,
    providing direct access to system functionality.

    Args:
        params: Dictionary containing command, arguments, and user ID

    Returns:
        Dict containing success flag, response, data, and error message if any
    """
    try:
        # Extract parameters
        command = params.get("command", "")
        user_id = params.get("user_id", "default_user")

        # Validate parameters
        if not command:
            return {"success": False, "error": "Command is required"}

        # Remove leading slash if present
        if command.startswith("/"):
            command = command[1:]

        # Process commands
        logger.info(f"Processing command '{command}' from user {user_id}")

        if command == "help":
            return {
                "success": True,
                "response": """
Available commands:
/help - Show this help message
/status - Show system status
/agents - List available AI agents
/handlers - List available handlers
/execute [handler] [params] - Execute a handler directly
/generate [description] - Generate a new tool
                """.strip(),
                "data": {"command_type": "help"},
            }

        elif command == "status":
            # In a real implementation, we would query the Orchestrator for status
            return {
                "success": True,
                "response": "Quantum Orchestrator is running normally. All systems operational.",
                "data": {
                    "command_type": "status",
                    "status": "operational",
                    "uptime": "12h 34m",
                    "active_agents": 5,
                    "available_handlers": 16,
                },
            }

        elif command == "agents":
            # List of available agents
            agents = [
                "PlanningAgent - Formulates plans to accomplish complex tasks",
                "CodeAgent - Generates and modifies code",
                "TestAgent - Creates tests and verifies code quality",
                "OptimizationAgent - Improves performance and efficiency",
                "MetaAgent - Generates new tools and components",
            ]

            return {
                "success": True,
                "response": "Available AI agents:\n" + "\n".join(agents),
                "data": {"command_type": "agents", "agents": agents},
            }

        elif command == "handlers":
            # In a real implementation, we would query the Orchestrator for handlers
            handlers = [
                "text_generation_handler - Generate text using the configured LLM provider",
                "data_processing_handler - Process data with various transformations and analytics functions",
                "data_filtering_handler - Filter data based on various conditions",
                "chat_message_handler - Process a chat message and generate an appropriate response",
                "command_handler - Process a command entered in the chat interface",
            ]

            return {
                "success": True,
                "response": "Available handlers:\n" + "\n".join(handlers),
                "data": {"command_type": "handlers", "handlers": handlers},
            }

        elif command.startswith("execute "):
            # Parse handler and parameters
            parts = command.split(" ", 2)
            if len(parts) < 2:
                return {"success": False, "error": "Handler name required"}

            handler_name = parts[1]
            params_json = parts[2] if len(parts) > 2 else "{}"

            try:
                execute_params = json.loads(params_json)
            except json.JSONDecodeError:
                return {"success": False, "error": "Invalid JSON parameters"}

            return {
                "success": True,
                "response": f"Would execute handler '{handler_name}' with parameters: {params_json}",
                "data": {
                    "command_type": "execute",
                    "handler": handler_name,
                    "params": execute_params,
                },
            }

        elif command.startswith("generate "):
            # Extract description
            description = command[9:].strip()
            if not description:
                return {"success": False, "error": "Tool description required"}

            return {
                "success": True,
                "response": f"Generating tool for: {description}",
                "data": {
                    "command_type": "generate",
                    "description": description,
                    "status": "in_progress",
                },
            }

        else:
            return {
                "success": False,
                "error": f"Unknown command: {command}",
                "response": f"Unknown command: {command}. Type /help for available commands.",
            }

    except Exception as e:
        logger.error(f"Error in command_handler: {str(e)}")
        return {"success": False, "error": f"Error processing command: {str(e)}"}


# Helper functions
def _process_command(
    message: str, user_id: str, context: Dict[str, Any]
) -> Dict[str, Any]:
    """Process a command message."""
    # Strip the leading slash
    command_text = message[1:].strip()

    # Split into command and arguments
    parts = command_text.split(" ", 1)
    command = parts[0]
    args_text = parts[1] if len(parts) > 1 else ""

    # Parse arguments
    args = {}
    if args_text:
        # Try to parse as JSON
        try:
            args = json.loads(args_text)
        except json.JSONDecodeError:
            # If not valid JSON, treat as plain text argument
            args = {"text": args_text}

    # Call the command handler
    return command_handler({"command": command, "args": args, "user_id": user_id})


def _format_conversation_history(history: List[Dict[str, Any]]) -> str:
    """Format conversation history for inclusion in prompts."""
    if not history:
        return ""

    formatted = []
    for entry in history:
        role = entry.get("role", "").upper()
        content = entry.get("content", "")
        formatted.append(f"{role}: {content}")

    return "\n".join(formatted)


def _extract_actions(message: str, response: str) -> List[Dict[str, Any]]:
    """Extract potential actions from the message and response."""
    actions = []

    # Check for data processing requests
    if re.search(
        r"\b(process|analyze|calculate|compute)\b.*\bdata\b", message, re.IGNORECASE
    ):
        actions.append(
            {
                "type": "suggest_handler",
                "handler": "data_processing_handler",
                "confidence": 0.8,
                "description": "Process data with statistical functions",
            }
        )

    # Check for filtering requests
    if re.search(r"\b(filter|find|search|where)\b", message, re.IGNORECASE):
        actions.append(
            {
                "type": "suggest_handler",
                "handler": "data_filtering_handler",
                "confidence": 0.7,
                "description": "Filter data based on conditions",
            }
        )

    # Check for text generation requests
    if re.search(
        r"\b(generate|create|write)\b.*\b(text|content|story|description)\b",
        message,
        re.IGNORECASE,
    ):
        actions.append(
            {
                "type": "suggest_handler",
                "handler": "text_generation_handler",
                "confidence": 0.9,
                "description": "Generate text using LLM",
            }
        )

    # Check for tool generation requests
    if re.search(
        r"\b(create|build|make)\b.*\b(tool|handler|function)\b", message, re.IGNORECASE
    ):
        tool_description = re.search(
            r"create.*?tool.+?for\s+(.+?)(?:\.|$)", message, re.IGNORECASE
        )
        description = (
            tool_description.group(1) if tool_description else "custom functionality"
        )

        actions.append(
            {
                "type": "suggest_handler",
                "handler": "meta_agent.generate_tool",
                "confidence": 0.9,
                "params": {"description": description},
                "description": f"Generate a new tool for {description}",
            }
        )

    return actions
