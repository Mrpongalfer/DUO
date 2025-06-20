"""
Input Sources: Handles different input formats for instructions.

Provides classes and functions for processing instructions from various sources
such as JSON files, YAML files, and command-line input.
"""

import os
import json
from typing import Any, Dict, List

from quantum_orchestrator.utils.logging_utils import get_logger
from quantum_orchestrator.games.nexus_omniengine_v3.core.instruction_parser import InstructionParser

logger = get_logger(__name__)
parser = InstructionParser()


class InputSource:
    """Base class for instruction input sources."""

    def __init__(self):
        """Initialize the input source."""
        pass

    def get_instructions(self) -> List[Dict[str, Any]]:
        """
        Get instructions from this source.

        Returns:
            List of instruction dictionaries
        """
        raise NotImplementedError("Subclasses must implement get_instructions()")


class JsonFileInput(InputSource):
    """Input source for JSON files."""

    def __init__(self, file_path: str):
        """
        Initialize the JSON file input.

        Args:
            file_path: Path to the JSON file
        """
        super().__init__()
        self.file_path = file_path

    def get_instructions(self) -> List[Dict[str, Any]]:
        """
        Get instructions from a JSON file.

        Returns:
            List of instruction dictionaries
        """
        try:
            if not os.path.exists(self.file_path):
                logger.error(f"File not found: {self.file_path}")
                return []

            with open(self.file_path, "r") as f:
                data = json.load(f)

            # Handle both single instructions and arrays
            if isinstance(data, dict):
                return [parser.normalize(data)]
            elif isinstance(data, list):
                return [
                    parser.normalize(item) for item in data if isinstance(item, dict)
                ]
            else:
                logger.error(f"Invalid JSON data in {self.file_path}")
                return []

        except Exception as e:
            logger.error(f"Error reading JSON file {self.file_path}: {str(e)}")
            return []


class YamlFileInput(InputSource):
    """Input source for YAML files."""

    def __init__(self, file_path: str):
        """
        Initialize the YAML file input.

        Args:
            file_path: Path to the YAML file
        """
        super().__init__()
        self.file_path = file_path

    def get_instructions(self) -> List[Dict[str, Any]]:
        """
        Get instructions from a YAML file.

        Returns:
            List of instruction dictionaries
        """
        try:
            # Import yaml here to avoid adding a global dependency
            import yaml

            if not os.path.exists(self.file_path):
                logger.error(f"File not found: {self.file_path}")
                return []

            with open(self.file_path, "r") as f:
                data = yaml.safe_load(f)

            # Handle both single instructions and arrays
            if isinstance(data, dict):
                return [parser.normalize(data)]
            elif isinstance(data, list):
                return [
                    parser.normalize(item) for item in data if isinstance(item, dict)
                ]
            else:
                logger.error(f"Invalid YAML data in {self.file_path}")
                return []

        except ImportError:
            logger.error(
                "PyYAML is not installed. Install it with 'pip install pyyaml'"
            )
            return []
        except Exception as e:
            logger.error(f"Error reading YAML file {self.file_path}: {str(e)}")
            return []


class CommandLineInput(InputSource):
    """Input source for command-line JSON input."""

    def __init__(self, json_string: str):
        """
        Initialize the command-line input.

        Args:
            json_string: JSON string containing instructions
        """
        super().__init__()
        self.json_string = json_string

    def get_instructions(self) -> List[Dict[str, Any]]:
        """
        Get instructions from a JSON string.

        Returns:
            List of instruction dictionaries
        """
        try:
            data = json.loads(self.json_string)

            # Handle both single instructions and arrays
            if isinstance(data, dict):
                return [parser.normalize(data)]
            elif isinstance(data, list):
                return [
                    parser.normalize(item) for item in data if isinstance(item, dict)
                ]
            else:
                logger.error("Invalid JSON data in command-line input")
                return []

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Error processing command-line input: {str(e)}")
            return []


class ApiInput(InputSource):
    """Input source for API requests."""

    def __init__(self, request_data: Any):
        """
        Initialize the API input.

        Args:
            request_data: Data from API request
        """
        super().__init__()
        self.request_data = request_data

    def get_instructions(self) -> List[Dict[str, Any]]:
        """
        Get instructions from API request data.

        Returns:
            List of instruction dictionaries
        """
        try:
            if isinstance(self.request_data, dict):
                return [parser.normalize(self.request_data)]
            elif isinstance(self.request_data, list):
                return [
                    parser.normalize(item)
                    for item in self.request_data
                    if isinstance(item, dict)
                ]
            elif isinstance(self.request_data, str):
                # Try to parse as JSON
                data = json.loads(self.request_data)
                if isinstance(data, dict):
                    return [parser.normalize(data)]
                elif isinstance(data, list):
                    return [
                        parser.normalize(item)
                        for item in data
                        if isinstance(item, dict)
                    ]

            logger.error("Invalid API request data")
            return []

        except Exception as e:
            logger.error(f"Error processing API input: {str(e)}")
            return []


def get_input_source(source_type: str, **kwargs) -> InputSource:
    """
    Get an input source based on type.

    Args:
        source_type: Type of input source
        **kwargs: Arguments for the input source

    Returns:
        InputSource instance
    """
    source_type = source_type.lower()

    if source_type == "json":
        return JsonFileInput(kwargs.get("file_path", ""))
    elif source_type == "yaml":
        return YamlFileInput(kwargs.get("file_path", ""))
    elif source_type == "command_line":
        return CommandLineInput(kwargs.get("json_string", ""))
    elif source_type == "api":
        return ApiInput(kwargs.get("request_data", {}))
    else:
        logger.error(f"Unknown input source type: {source_type}")
        raise ValueError(f"Unknown input source type: {source_type}")


def process_input_file(file_path: str) -> List[Dict[str, Any]]:
    """
    Process an input file and return instructions.

    Args:
        file_path: Path to the input file

    Returns:
        List of instruction dictionaries
    """
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return []

    # Determine file type from extension
    file_ext = os.path.splitext(file_path)[1].lower()

    if file_ext == ".json":
        source = JsonFileInput(file_path)
        return source.get_instructions()
    elif file_ext in [".yaml", ".yml"]:
        source = YamlFileInput(file_path)
        return source.get_instructions()
    else:
        logger.error(f"Unsupported file type: {file_ext}")
        return []
