"""
Security: Utility functions for security.

Provides functions for input sanitization, command validation, and path security.
"""

import os
import re
import shlex
from typing import List, Optional, Any

from quantum_orchestrator.utils.logging_utils import get_logger

logger = get_logger(__name__)


def sanitize_path(path: str) -> Optional[str]:
    """
    Sanitize a file path to prevent path traversal attacks.

    Args:
        path: The path to sanitize

    Returns:
        Sanitized path or None if path is invalid
    """
    if not path:
        return None

    # Normalize path separators
    path = path.replace("\\", "/")

    # Check for path traversal attempts
    if ".." in path.split("/"):
        logger.warning(f"Path traversal attempt detected: {path}")
        return None

    # Remove any leading slashes to make relative to current directory
    path = path.lstrip("/")

    # Check for suspicious patterns
    suspicious_patterns = [
        r"^~/",  # Home directory
        r"^/etc/",  # System configuration
        r"^/var/",  # System logs
        r"^/root/",  # Root user directory
        r"^/bin/",  # System binaries
        r"^/sbin/",  # System admin binaries
        r"^/proc/",  # Process information
        r"^/sys/",  # System information
        r"^/dev/",  # Device files
        r"^/tmp/",  # Temporary files
        r".*\.\..*",  # Path traversal
        r".*[\x00-\x1F].*",  # Control characters
    ]

    for pattern in suspicious_patterns:
        if re.match(pattern, path):
            logger.warning(f"Suspicious path detected: {path}")
            return None

    return path


def sanitize_command(command: str) -> str:
    """
    Sanitize a command to prevent command injection.

    Args:
        command: The command to sanitize

    Returns:
        Sanitized command
    """
    if not command:
        return ""

    # Use shlex to parse command, which handles quotes correctly
    try:
        # This will raise an exception if the command has unclosed quotes
        shlex.split(command)
    except ValueError as e:
        logger.warning(f"Invalid command syntax: {command}, error: {str(e)}")
        # Fix unclosed quotes by adding a closing quote
        if "No closing quotation" in str(e):
            command += '"'

    # Remove shell metacharacters
    unsafe_chars = [
        ";",
        "&",
        "|",
        ">",
        "<",
        "`",
        "$",
        "(",
        ")",
        "{",
        "}",
        "[",
        "]",
        "\\",
        "\n",
        "\r",
    ]
    for char in unsafe_chars:
        command = command.replace(char, "")

    return command


def is_allowed_command(command: str, allowed_commands: List[str]) -> bool:
    """
    Check if a command is in the list of allowed commands.

    Args:
        command: The command to check
        allowed_commands: List of allowed commands

    Returns:
        bool: True if command is allowed
    """
    # Extract the base command (remove any path and arguments)
    base_command = os.path.basename(command.split(" ")[0])

    # Check if base command is in allowed list
    return base_command in allowed_commands


def validate_input(input_data: Any, input_type: str, max_length: int = None) -> bool:
    """
    Validate input based on type and constraints.

    Args:
        input_data: The input to validate
        input_type: Type of input (str, int, float, bool, dict, list)
        max_length: Maximum length for strings and lists

    Returns:
        bool: True if input is valid
    """
    # Check if input is None
    if input_data is None:
        return False

    # Check type
    if input_type == "str":
        if not isinstance(input_data, str):
            return False
        if max_length and len(input_data) > max_length:
            return False
    elif input_type == "int":
        try:
            int(input_data)
        except (ValueError, TypeError):
            return False
    elif input_type == "float":
        try:
            float(input_data)
        except (ValueError, TypeError):
            return False
    elif input_type == "bool":
        if not isinstance(input_data, bool):
            # Check for string representations
            if isinstance(input_data, str):
                if input_data.lower() not in ("true", "false", "1", "0"):
                    return False
            else:
                return False
    elif input_type == "dict":
        if not isinstance(input_data, dict):
            return False
    elif input_type == "list":
        if not isinstance(input_data, list):
            return False
        if max_length and len(input_data) > max_length:
            return False
    else:
        # Unknown type
        return False

    return True


def sanitize_html(html: str) -> str:
    """
    Sanitize HTML to prevent XSS.

    Args:
        html: The HTML to sanitize

    Returns:
        Sanitized HTML
    """
    if not html:
        return ""

    # Replace potentially dangerous characters with entities
    replacements = {
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#x27;",
        "/": "&#x2F;",
        "&": "&amp;",
    }

    for char, entity in replacements.items():
        html = html.replace(char, entity)

    return html


def generate_secure_key() -> str:
    """
    Generate a secure random key.

    Returns:
        str: Secure random key
    """
    try:
        import secrets

        return secrets.token_hex(32)
    except ImportError:
        # Fallback for older Python versions
        import random
        import time
        import hashlib

        seed = f"{time.time()}{random.random()}"
        return hashlib.sha256(seed.encode()).hexdigest()
