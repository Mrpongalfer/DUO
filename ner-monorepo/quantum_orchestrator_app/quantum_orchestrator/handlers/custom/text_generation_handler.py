"""
Generated handler: text_generation_handler

Description: Generates text using the configured LLM provider
"""

from typing import Dict, Any

from quantum_orchestrator.handlers import handler
from quantum_orchestrator.utils.logging_utils import get_logger
from quantum_orchestrator.services.llm_service import (
    generate_completion,
    generate_completion_async,
)

logger = get_logger(__name__)


@handler(
    name="text_generation_handler",
    description="Generate text using the configured LLM provider",
    parameters={
        "prompt": {"type": "string", "description": "The prompt to generate text from"},
        "model": {
            "type": "string",
            "description": "The model to use (optional)",
            "default": None,
        },
        "temperature": {
            "type": "number",
            "description": "The temperature for generation (0.0-1.0)",
            "default": 0.7,
        },
        "max_tokens": {
            "type": "integer",
            "description": "Maximum tokens to generate",
            "default": 1000,
        },
        "provider": {
            "type": "string",
            "description": "LLM provider to use (optional)",
            "default": None,
        },
    },
    returns={
        "success": {
            "type": "boolean",
            "description": "Whether the operation was successful",
        },
        "text": {"type": "string", "description": "Generated text"},
        "error": {"type": "string", "description": "Error message if operation failed"},
    },
)
def text_generation_handler(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate text using the configured LLM provider.

    This handler wraps the LLM service to generate text responses based on the given prompt.
    It supports specifying the model, temperature, token limit, and provider preference.

    Args:
        params: Dictionary containing prompt and optional parameters

    Returns:
        Dict containing success flag, generated text, and error message if any
    """
    try:
        # Extract parameters
        prompt = params.get("prompt", "")
        model = params.get("model")
        temperature = params.get("temperature", 0.7)
        max_tokens = params.get("max_tokens", 1000)
        provider = params.get("provider")

        # Validate parameters
        if not prompt:
            return {"success": False, "error": "Prompt is required"}

        if temperature < 0 or temperature > 1:
            logger.warning(
                f"Temperature out of range (0-1): {temperature}, clamping to valid range"
            )
            temperature = max(0, min(1, temperature))

        # Call the LLM service
        response = generate_completion(
            prompt=prompt,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            provider=provider,
        )

        # Return the generated text
        return {"success": True, "text": response}

    except Exception as e:
        logger.error(f"Error in text_generation_handler: {str(e)}")
        return {"success": False, "error": f"Error generating text: {str(e)}"}


@handler(
    name="text_generation_async_handler",
    description="Generate text asynchronously using the configured LLM provider",
    parameters={
        "prompt": {"type": "string", "description": "The prompt to generate text from"},
        "model": {
            "type": "string",
            "description": "The model to use (optional)",
            "default": None,
        },
        "temperature": {
            "type": "number",
            "description": "The temperature for generation (0.0-1.0)",
            "default": 0.7,
        },
        "max_tokens": {
            "type": "integer",
            "description": "Maximum tokens to generate",
            "default": 1000,
        },
        "provider": {
            "type": "string",
            "description": "LLM provider to use (optional)",
            "default": None,
        },
    },
    returns={
        "success": {
            "type": "boolean",
            "description": "Whether the operation was successful",
        },
        "text": {"type": "string", "description": "Generated text"},
        "error": {"type": "string", "description": "Error message if operation failed"},
    },
)
async def text_generation_async_handler(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate text asynchronously using the configured LLM provider.

    This is the asynchronous version of the text_generation_handler.

    Args:
        params: Dictionary containing prompt and optional parameters

    Returns:
        Dict containing success flag, generated text, and error message if any
    """
    try:
        # Extract parameters
        prompt = params.get("prompt", "")
        model = params.get("model")
        temperature = params.get("temperature", 0.7)
        max_tokens = params.get("max_tokens", 1000)
        provider = params.get("provider")

        # Validate parameters
        if not prompt:
            return {"success": False, "error": "Prompt is required"}

        if temperature < 0 or temperature > 1:
            logger.warning(
                f"Temperature out of range (0-1): {temperature}, clamping to valid range"
            )
            temperature = max(0, min(1, temperature))

        # Call the LLM service asynchronously
        response = await generate_completion_async(
            prompt=prompt,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            provider=provider,
        )

        # Return the generated text
        return {"success": True, "text": response}

    except Exception as e:
        logger.error(f"Error in text_generation_async_handler: {str(e)}")
        return {"success": False, "error": f"Error generating text: {str(e)}"}
