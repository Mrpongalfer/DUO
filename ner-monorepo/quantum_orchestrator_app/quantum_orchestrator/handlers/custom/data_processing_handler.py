"""
Generated handler: data_processing_handler

Description: Processes data with various transformations and analytics functions
"""

import re
import statistics
from typing import Dict, Any

from quantum_orchestrator.handlers import handler
from quantum_orchestrator.utils.logging_utils import get_logger

logger = get_logger(__name__)


@handler(
    name="data_processing_handler",
    description="Process data with various transformations and analytics functions",
    parameters={
        "data": {"type": "array", "description": "The data array to process"},
        "operation": {
            "type": "string",
            "description": "The operation to perform on the data",
            "enum": [
                "sum",
                "average",
                "median",
                "min",
                "max",
                "std_dev",
                "normalize",
                "sort",
            ],
        },
        "options": {
            "type": "object",
            "description": "Additional options for the operation",
            "default": {},
        },
    },
    returns={
        "success": {
            "type": "boolean",
            "description": "Whether the operation was successful",
        },
        "result": {
            "type": "any",
            "description": "The result of the data processing operation",
        },
        "error": {"type": "string", "description": "Error message if operation failed"},
    },
)
def data_processing_handler(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process data with various transformations and analytics functions.

    This handler supports several common data processing operations including:
    - Basic statistics (sum, average, median, min, max, standard deviation)
    - Data transformations (normalization, sorting)

    Args:
        params: Dictionary containing data, operation, and options

    Returns:
        Dict containing success flag, operation result, and error message if any
    """
    try:
        # Extract parameters
        data = params.get("data", [])
        operation = params.get("operation", "")
        options = params.get("options", {})

        # Validate parameters
        if not data:
            return {
                "success": False,
                "error": "Data array is required and cannot be empty",
            }

        if not operation:
            return {"success": False, "error": "Operation is required"}

        # Process numeric data for statistical operations
        numeric_data = []
        if operation in [
            "sum",
            "average",
            "median",
            "min",
            "max",
            "std_dev",
            "normalize",
        ]:
            for item in data:
                try:
                    numeric_data.append(float(item))
                except (ValueError, TypeError):
                    return {
                        "success": False,
                        "error": f"Non-numeric value found in data: {item}",
                    }

        # Perform the requested operation
        if operation == "sum":
            result = sum(numeric_data)

        elif operation == "average":
            result = sum(numeric_data) / len(numeric_data)

        elif operation == "median":
            result = statistics.median(numeric_data)

        elif operation == "min":
            result = min(numeric_data)

        elif operation == "max":
            result = max(numeric_data)

        elif operation == "std_dev":
            result = statistics.stdev(numeric_data) if len(numeric_data) > 1 else 0

        elif operation == "normalize":
            min_val = min(numeric_data)
            max_val = max(numeric_data)
            if min_val == max_val:
                result = [0.5 for _ in numeric_data]  # All values are the same
            else:
                result = [(x - min_val) / (max_val - min_val) for x in numeric_data]

        elif operation == "sort":
            reverse = options.get("reverse", False)
            if all(isinstance(x, (int, float)) for x in data):
                # Sort numeric data
                result = sorted(data, reverse=reverse)
            elif all(isinstance(x, str) for x in data):
                # Sort string data
                result = sorted(data, reverse=reverse)
            else:
                # Mixed data, convert to strings for consistent sorting
                result = sorted(data, key=str, reverse=reverse)

        else:
            return {"success": False, "error": f"Unsupported operation: {operation}"}

        return {"success": True, "result": result, "operation": operation}

    except Exception as e:
        logger.error(f"Error in data_processing_handler: {str(e)}")
        return {"success": False, "error": f"Error processing data: {str(e)}"}


@handler(
    name="data_filtering_handler",
    description="Filter data based on various conditions",
    parameters={
        "data": {"type": "array", "description": "The data array to filter"},
        "condition": {
            "type": "string",
            "description": "The condition to apply (e.g., 'greater_than', 'contains')",
        },
        "value": {"type": "any", "description": "The value to compare against"},
        "field": {
            "type": "string",
            "description": "For object arrays, the field to check",
            "default": None,
        },
    },
    returns={
        "success": {
            "type": "boolean",
            "description": "Whether the operation was successful",
        },
        "result": {"type": "array", "description": "The filtered data"},
        "count": {
            "type": "integer",
            "description": "The number of items that passed the filter",
        },
        "error": {"type": "string", "description": "Error message if operation failed"},
    },
)
def data_filtering_handler(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Filter data based on various conditions.

    This handler filters arrays based on specified conditions such as greater than,
    less than, equals, contains, etc.

    Args:
        params: Dictionary containing data, condition, value, and optional field

    Returns:
        Dict containing success flag, filtered data, and error message if any
    """
    try:
        # Extract parameters
        data = params.get("data", [])
        condition = params.get("condition", "")
        value = params.get("value")
        field = params.get("field")

        # Validate parameters
        if not data:
            return {
                "success": False,
                "error": "Data array is required and cannot be empty",
            }

        if not condition:
            return {"success": False, "error": "Condition is required"}

        if value is None:
            return {"success": False, "error": "Value is required"}

        # Initialize result
        filtered_data = []

        # Apply filtering
        for item in data:
            # Extract the value to compare
            compare_value = item
            if field:
                if isinstance(item, dict):
                    compare_value = item.get(field)
                else:
                    return {
                        "success": False,
                        "error": f"Field specified but item is not an object: {item}",
                    }

            # Apply the condition
            if condition == "equals":
                if compare_value == value:
                    filtered_data.append(item)

            elif condition == "not_equals":
                if compare_value != value:
                    filtered_data.append(item)

            elif condition == "greater_than":
                if isinstance(compare_value, (int, float)) and isinstance(
                    value, (int, float)
                ):
                    if compare_value > value:
                        filtered_data.append(item)
                else:
                    return {
                        "success": False,
                        "error": "Numeric comparison requires numeric values",
                    }

            elif condition == "less_than":
                if isinstance(compare_value, (int, float)) and isinstance(
                    value, (int, float)
                ):
                    if compare_value < value:
                        filtered_data.append(item)
                else:
                    return {
                        "success": False,
                        "error": "Numeric comparison requires numeric values",
                    }

            elif condition == "contains":
                if isinstance(compare_value, str) and isinstance(value, str):
                    if value in compare_value:
                        filtered_data.append(item)
                elif isinstance(compare_value, list):
                    if value in compare_value:
                        filtered_data.append(item)
                else:
                    return {
                        "success": False,
                        "error": "Contains comparison requires string or list values",
                    }

            elif condition == "starts_with":
                if isinstance(compare_value, str) and isinstance(value, str):
                    if compare_value.startswith(value):
                        filtered_data.append(item)
                else:
                    return {
                        "success": False,
                        "error": "Starts with comparison requires string values",
                    }

            elif condition == "ends_with":
                if isinstance(compare_value, str) and isinstance(value, str):
                    if compare_value.endswith(value):
                        filtered_data.append(item)
                else:
                    return {
                        "success": False,
                        "error": "Ends with comparison requires string values",
                    }

            elif condition == "matches_regex":
                if isinstance(compare_value, str) and isinstance(value, str):
                    try:
                        if re.search(value, compare_value):
                            filtered_data.append(item)
                    except re.error as e:
                        return {
                            "success": False,
                            "error": f"Invalid regex pattern: {str(e)}",
                        }
                else:
                    return {
                        "success": False,
                        "error": "Regex comparison requires string values",
                    }

            else:
                return {
                    "success": False,
                    "error": f"Unsupported condition: {condition}",
                }

        return {
            "success": True,
            "result": filtered_data,
            "count": len(filtered_data),
            "condition": condition,
        }

    except Exception as e:
        logger.error(f"Error in data_filtering_handler: {str(e)}")
        return {"success": False, "error": f"Error filtering data: {str(e)}"}
