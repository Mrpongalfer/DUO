"""
LLM operation handlers for the Quantum Orchestrator.

Provides handlers for generating code, documentation, and analyzing text using LLMs.
"""

from typing import Any, Dict

from quantum_orchestrator.handlers import handler
from quantum_orchestrator.utils.logging_utils import get_logger
from quantum_orchestrator.services.llm_service import (
    generate_completion,
)

logger = get_logger(__name__)


@handler(
    name="generate_code",
    description="Generates code based on the provided description",
    parameters={
        "description": {
            "type": "string",
            "description": "Description of the code to generate",
        },
        "language": {
            "type": "string",
            "description": "Programming language",
            "default": "python",
        },
        "context": {
            "type": "string",
            "description": "Additional context or requirements",
            "default": "",
        },
        "model": {"type": "string", "description": "LLM model to use", "default": ""},
    },
    returns={
        "success": {
            "type": "boolean",
            "description": "Whether the operation was successful",
        },
        "code": {"type": "string", "description": "Generated code"},
        "language": {
            "type": "string",
            "description": "Programming language of the generated code",
        },
        "explanation": {
            "type": "string",
            "description": "Explanation of the generated code",
        },
        "error": {"type": "string", "description": "Error message if operation failed"},
    },
)
def generate_code(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate code based on the provided description.

    Args:
        params: Dictionary containing description, language, context, and model

    Returns:
        Dict containing success flag, code, language, explanation, and error message if any
    """
    try:
        description = params.get("description", "")
        language = params.get("language", "python")
        context = params.get("context", "")
        model = params.get("model", "")

        # Validate description
        if not description:
            return {"success": False, "error": "No description provided"}

        # Prepare prompt
        prompt = f"""Generate {language} code based on the following description:

Description: {description}

{f"Additional context: {context}" if context else ""}

Please provide only the code without explanations, comments, or surrounding backticks.
"""

        # Generate code using LLM
        logger.info(f"Generating {language} code from description")
        completion = generate_completion(prompt, model=model)

        if not completion:
            return {"success": False, "error": "Failed to generate code"}

        # Prepare explanation prompt
        explanation_prompt = f"""Please explain the following {language} code in a concise manner:

```{language}
{completion}
```"""

        # Generate explanation using LLM
        logger.info(f"Generating explanation for {language} code")
        explanation = generate_completion(explanation_prompt, model=model)

        # Return successful result
        return {
            "success": True,
            "code": completion,
            "language": language,
            "explanation": explanation or "No explanation available",
        }
    except Exception as e:
        logger.error(f"Error in generate_code: {str(e)}")
        return {"success": False, "error": f"Error: {str(e)}"}
