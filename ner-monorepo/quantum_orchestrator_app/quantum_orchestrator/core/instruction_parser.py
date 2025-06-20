"""
InstructionParser: Validates and processes instructions for the Quantum Orchestrator.

Provides schema validation and parsing of instruction JSON.
"""

import json
import os
import jsonschema
from typing import Any, Dict, List
from quantum_orchestrator.utils.logging_utils import get_logger


class InstructionParser:
    """
    InstructionParser: Validates and processes instructions based on schema.

    Provides methods to validate instruction JSON against schema and normalize
    instruction format.
    """

    def __init__(self, schema_file: str = None):
        """
        Initialize the InstructionParser.

        Args:
            schema_file: Path to the schema file
        """
        self.logger = get_logger(__name__)

        # Set default schema file path if not provided
        if schema_file is None:
            # Look for schema file in the same directory as this module
            current_dir = os.path.dirname(os.path.abspath(__file__))
            parent_dir = os.path.dirname(current_dir)
            self.schema_file = os.path.join(parent_dir, "instruction_schema.json")
        else:
            self.schema_file = schema_file

        # Load the schema
        try:
            self.schema = self._load_schema()
            self.logger.info(f"Instruction schema loaded from {self.schema_file}")
        except Exception as e:
            self.logger.error(f"Failed to load schema, using fallback: {str(e)}")
            self.schema = self._get_fallback_schema()

    def _load_schema(self) -> Dict[str, Any]:
        """
        Load the JSON schema from file.

        Returns:
            Dict: The loaded schema
        """
        if os.path.exists(self.schema_file):
            with open(self.schema_file, "r") as f:
                return json.load(f)
        else:
            self.logger.warning(
                f"Schema file not found at {self.schema_file}, using fallback"
            )
            schema = self._get_fallback_schema()

            # Write fallback schema to file for future use
            try:
                os.makedirs(os.path.dirname(self.schema_file), exist_ok=True)
                with open(self.schema_file, "w") as f:
                    json.dump(schema, f, indent=2)
                self.logger.info(f"Created fallback schema at {self.schema_file}")
            except Exception as e:
                self.logger.error(f"Failed to write fallback schema: {str(e)}")

            return schema

    def _get_fallback_schema(self) -> Dict[str, Any]:
        """
        Get a fallback schema for validation.

        Returns:
            Dict: The fallback schema
        """
        return {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "title": "Quantum Orchestrator Instruction",
            "description": "Schema for Quantum Orchestrator instructions",
            "type": "object",
            "required": ["type"],
            "properties": {
                "type": {
                    "type": "string",
                    "enum": ["direct", "workflow", "intent", "tool_request"],
                    "description": "The type of instruction",
                },
                "id": {
                    "type": "string",
                    "description": "Optional identifier for the instruction",
                },
            },
            "allOf": [
                {
                    "if": {"properties": {"type": {"const": "direct"}}},
                    "then": {
                        "required": ["handler", "params"],
                        "properties": {
                            "handler": {
                                "type": "string",
                                "description": "The handler to execute",
                            },
                            "params": {
                                "type": "object",
                                "description": "Parameters for the handler",
                            },
                            "store_result": {
                                "type": "boolean",
                                "description": "Whether to store the result in state",
                            },
                            "result_key": {
                                "type": "string",
                                "description": "Key for storing the result",
                            },
                            "optimize": {
                                "type": "boolean",
                                "description": "Whether to optimize any generated code",
                            },
                            "context": {
                                "type": "object",
                                "description": "Additional context for optimization",
                            },
                        },
                    },
                },
                {
                    "if": {"properties": {"type": {"const": "workflow"}}},
                    "then": {
                        "required": ["steps"],
                        "properties": {
                            "steps": {
                                "type": "array",
                                "description": "Steps to execute in the workflow",
                                "items": {"type": "object"},
                            },
                            "parallel": {
                                "type": "boolean",
                                "description": "Whether to execute steps in parallel",
                            },
                            "fail_fast": {
                                "type": "boolean",
                                "description": "Whether to stop on first failure",
                            },
                            "optimize_workflow": {
                                "type": "boolean",
                                "description": "Whether to optimize workflow execution",
                            },
                        },
                    },
                },
                {
                    "if": {"properties": {"type": {"const": "intent"}}},
                    "then": {
                        "required": ["intent"],
                        "properties": {
                            "intent": {
                                "type": "string",
                                "description": "The intent to execute",
                            },
                            "context": {
                                "type": "object",
                                "description": "Additional context for intent resolution",
                            },
                        },
                    },
                },
                {
                    "if": {"properties": {"type": {"const": "tool_request"}}},
                    "then": {
                        "required": ["description"],
                        "properties": {
                            "description": {
                                "type": "string",
                                "description": "Description of the tool to generate",
                            },
                            "name": {
                                "type": "string",
                                "description": "Name for the generated tool",
                            },
                            "integrate": {
                                "type": "boolean",
                                "description": "Whether to integrate the generated tool",
                            },
                        },
                    },
                },
            ],
        }

    def validate(self, instruction: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate an instruction against the schema.

        Args:
            instruction: The instruction to validate

        Returns:
            Dict with validation results
        """
        try:
            jsonschema.validate(instance=instruction, schema=self.schema)
            return {"valid": True}
        except jsonschema.exceptions.ValidationError as e:
            self.logger.error(f"Instruction validation failed: {str(e)}")
            return {"valid": False, "errors": str(e)}

    def normalize(self, instruction: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize an instruction by filling in defaults and standardizing format.

        Args:
            instruction: The instruction to normalize

        Returns:
            Normalized instruction
        """
        normalized = instruction.copy()

        # Add timestamp if not present
        if "timestamp" not in normalized:
            import time

            normalized["timestamp"] = time.time()

        # Add ID if not present
        if "id" not in normalized:
            import uuid

            normalized["id"] = str(uuid.uuid4())

        # Handle type-specific normalization
        if normalized.get("type") == "direct":
            # Ensure params is an object
            if "params" not in normalized:
                normalized["params"] = {}
            elif not isinstance(normalized["params"], dict):
                normalized["params"] = {"value": normalized["params"]}

            # Default store_result to False
            normalized.setdefault("store_result", False)

        elif normalized.get("type") == "workflow":
            # Ensure steps is a list
            if "steps" not in normalized:
                normalized["steps"] = []

            # Default parallel to False
            normalized.setdefault("parallel", False)

            # Default fail_fast to True
            normalized.setdefault("fail_fast", True)

            # Normalize each step
            for i, step in enumerate(normalized["steps"]):
                if "id" not in step:
                    step["id"] = f"step_{i}"
                if isinstance(step, dict):
                    normalized["steps"][i] = self.normalize(step)

        elif normalized.get("type") == "intent":
            # Ensure context is an object
            if "context" not in normalized:
                normalized["context"] = {}

        elif normalized.get("type") == "tool_request":
            # Default integrate to False
            normalized.setdefault("integrate", False)

            # Generate a name if not present
            if "name" not in normalized and "description" in normalized:
                # Simple heuristic to generate a name from description
                import re

                desc = normalized["description"]
                words = re.findall(r"\b\w+\b", desc.lower())
                if words:
                    normalized["name"] = f"{words[0]}_tool"

        return normalized

    def parse_yaml(self, yaml_content: str) -> List[Dict[str, Any]]:
        """
        Parse YAML format instructions into dictionary format.

        Args:
            yaml_content: The YAML content to parse

        Returns:
            List of instruction dictionaries
        """
        try:
            import yaml

            instructions = yaml.safe_load(yaml_content)

            # Ensure result is a list
            if not isinstance(instructions, list):
                instructions = [instructions]

            # Normalize each instruction
            normalized = [
                self.normalize(instr)
                for instr in instructions
                if isinstance(instr, dict)
            ]

            return normalized
        except Exception as e:
            self.logger.error(f"Failed to parse YAML: {str(e)}")
            return []
