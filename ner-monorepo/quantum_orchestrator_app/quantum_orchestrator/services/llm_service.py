"""
LLM Service: Interface to various LLM providers.

This module provides a unified interface to multiple large language model providers,
allowing the system to use different LLMs based on configuration and requirements.
"""

import os
import asyncio
import re
import requests
from typing import List, Optional

from quantum_orchestrator.utils.logging_utils import get_logger
from quantum_orchestrator.games.nexus_omniengine_v3.core.config import Config

logger = get_logger(__name__)

# Global constants
DEFAULT_MODEL = "gpt-4"
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 1000
API_REQUEST_TIMEOUT = 30  # seconds

# Try to load config, but don't fail if not available
try:
    config = Config()
    model_from_config = config.get("llm", {}).get("model")
    if model_from_config:
        DEFAULT_MODEL = model_from_config
except Exception as e:
    logger.warning(f"Error loading config in LLM service: {str(e)}")
    logger.warning("Using default LLM settings")

# LLM provider configurations
PROVIDER_CONFIGS = {
    "openai": {
        "api_key_env": "OPENAI_API_KEY",
        "api_base": "https://api.openai.com/v1",
        "models": ["gpt-4", "gpt-3.5-turbo"],
    },
    "azure": {
        "api_key_env": "AZURE_OPENAI_API_KEY",
        "api_base_env": "AZURE_OPENAI_ENDPOINT",
        "models": ["gpt-4", "gpt-3.5-turbo"],
    },
    "anthropic": {
        "api_key_env": "ANTHROPIC_API_KEY",
        "api_base": "https://api.anthropic.com/v1",
        "models": ["claude-2", "claude-instant-1"],
    },
}


class LLMProvider:
    """Base class for LLM providers."""

    def __init__(self, provider_name: str, api_key: Optional[str] = None):
        """
        Initialize the LLM provider.

        Args:
            provider_name: Name of the provider
            api_key: API key for the provider
        """
        self.provider_name = provider_name
        self.api_key = api_key or self._get_api_key()
        self.config = PROVIDER_CONFIGS.get(provider_name, {})

    def _get_api_key(self) -> Optional[str]:
        """Get API key from environment variables."""
        env_var = PROVIDER_CONFIGS.get(self.provider_name, {}).get("api_key_env", "")
        return os.environ.get(env_var)

    def get_api_base(self) -> str:
        """Get API base URL."""
        if self.provider_name == "azure":
            return os.environ.get(self.config.get("api_base_env", ""), "")
        return self.config.get("api_base", "")

    def is_available(self) -> bool:
        """Check if the provider is available."""
        return bool(self.api_key and self.get_api_base())

    async def generate_completion_async(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = DEFAULT_TEMPERATURE,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        **kwargs,
    ) -> str:
        """
        Generate a completion asynchronously.

        Args:
            prompt: The prompt to complete
            model: The model to use
            temperature: Temperature for generation
            max_tokens: Maximum tokens to generate
            **kwargs: Additional provider-specific parameters

        Returns:
            Generated completion
        """
        raise NotImplementedError("Subclasses must implement this method")

    def generate_completion(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = DEFAULT_TEMPERATURE,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        **kwargs,
    ) -> str:
        """
        Generate a completion synchronously.

        Args:
            prompt: The prompt to complete
            model: The model to use
            temperature: Temperature for generation
            max_tokens: Maximum tokens to generate
            **kwargs: Additional provider-specific parameters

        Returns:
            Generated completion
        """
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(
                self.generate_completion_async(
                    prompt=prompt,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs,
                )
            )
        finally:
            loop.close()


class OpenAIProvider(LLMProvider):
    """Provider for OpenAI API."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the OpenAI provider.

        Args:
            api_key: OpenAI API key
        """
        super().__init__("openai", api_key)

    async def generate_completion_async(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = DEFAULT_TEMPERATURE,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        **kwargs,
    ) -> str:
        """
        Generate a completion using OpenAI API.

        Args:
            prompt: The prompt to complete
            model: The model to use
            temperature: Temperature for generation
            max_tokens: Maximum tokens to generate
            **kwargs: Additional OpenAI-specific parameters

        Returns:
            Generated completion
        """
        if not self.api_key:
            logger.error("OpenAI API key not available")
            raise ValueError(
                "OpenAI API key not available. Set the OPENAI_API_KEY environment variable."
            )

        api_base = self.get_api_base()
        model = model or "gpt-4"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        data = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
            **kwargs,
        }

        try:
            url = f"{api_base}/chat/completions"
            response = requests.post(
                url, headers=headers, json=data, timeout=API_REQUEST_TIMEOUT
            )
            response.raise_for_status()

            response_data = response.json()
            return response_data["choices"][0]["message"]["content"]

        except Exception as e:
            logger.error(f"Error calling OpenAI API: {str(e)}")
            raise


class AzureOpenAIProvider(LLMProvider):
    """Provider for Azure OpenAI API."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Azure OpenAI provider.

        Args:
            api_key: Azure OpenAI API key
        """
        super().__init__("azure", api_key)

    async def generate_completion_async(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = DEFAULT_TEMPERATURE,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        **kwargs,
    ) -> str:
        """
        Generate a completion using Azure OpenAI API.

        Args:
            prompt: The prompt to complete
            model: The model to use
            temperature: Temperature for generation
            max_tokens: Maximum tokens to generate
            **kwargs: Additional Azure-specific parameters

        Returns:
            Generated completion
        """
        if not self.api_key:
            logger.error("Azure OpenAI API key not available")
            raise ValueError(
                "Azure OpenAI API key not available. Set the AZURE_OPENAI_API_KEY environment variable."
            )

        api_base = self.get_api_base()
        if not api_base:
            logger.error("Azure OpenAI endpoint not available")
            raise ValueError(
                "Azure OpenAI endpoint not available. Set the AZURE_OPENAI_ENDPOINT environment variable."
            )

        model = model or "gpt-4"
        deployment_id = kwargs.pop("deployment_id", model)

        headers = {"Content-Type": "application/json", "api-key": self.api_key}

        data = {
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
            **kwargs,
        }

        try:
            url = f"{api_base}/openai/deployments/{deployment_id}/chat/completions?api-version=2023-05-15"
            response = requests.post(
                url, headers=headers, json=data, timeout=API_REQUEST_TIMEOUT
            )
            response.raise_for_status()

            response_data = response.json()
            return response_data["choices"][0]["message"]["content"]

        except Exception as e:
            logger.error(f"Error calling Azure OpenAI API: {str(e)}")
            raise


class AnthropicProvider(LLMProvider):
    """Provider for Anthropic API."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Anthropic provider.

        Args:
            api_key: Anthropic API key
        """
        super().__init__("anthropic", api_key)

    async def generate_completion_async(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = DEFAULT_TEMPERATURE,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        **kwargs,
    ) -> str:
        """
        Generate a completion using Anthropic API.

        Args:
            prompt: The prompt to complete
            model: The model to use
            temperature: Temperature for generation
            max_tokens: Maximum tokens to generate
            **kwargs: Additional Anthropic-specific parameters

        Returns:
            Generated completion
        """
        if not self.api_key:
            logger.error("Anthropic API key not available")
            raise ValueError(
                "Anthropic API key not available. Set the ANTHROPIC_API_KEY environment variable."
            )

        api_base = self.get_api_base()
        model = model or "claude-2"

        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
        }

        data = {
            "model": model,
            "prompt": f"Human: {prompt}\n\nAssistant:",
            "temperature": temperature,
            "max_tokens_to_sample": max_tokens,
            **kwargs,
        }

        try:
            url = f"{api_base}/complete"
            response = requests.post(
                url, headers=headers, json=data, timeout=API_REQUEST_TIMEOUT
            )
            response.raise_for_status()

            response_data = response.json()
            return response_data["completion"]

        except Exception as e:
            logger.error(f"Error calling Anthropic API: {str(e)}")
            raise


class LocalLLMProvider(LLMProvider):
    """Provider for local LLMs."""

    def __init__(self):
        """Initialize the local LLM provider."""
        super().__init__("local")
        self.available_models = self._discover_models()

    def _discover_models(self) -> List[str]:
        """Discover available local models."""
        # In a real implementation, this would discover models available locally
        # For now, return a list of models we could support
        return ["llama-2-7b", "llama-2-13b", "llama-2-70b", "mistral-7b"]

    def is_available(self) -> bool:
        """Check if local models are available."""
        # In a real implementation, this would check if local models are installed
        return len(self.available_models) > 0

    async def generate_completion_async(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = DEFAULT_TEMPERATURE,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        **kwargs,
    ) -> str:
        """
        Generate a completion using a local LLM.

        Args:
            prompt: The prompt to complete
            model: The model to use
            temperature: Temperature for generation
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters

        Returns:
            Generated completion
        """
        logger.info(f"Using local LLM provider with model: {model}")

        # In a production implementation, this would call a local LLM server
        # For development, return a simple response based on the prompt
        return self._generate_development_response(prompt)

    def _generate_development_response(self, prompt: str) -> str:
        """
        Generate a development response for testing.

        Args:
            prompt: The prompt

        Returns:
            Generated response
        """
        # Extract code generation requests
        if "Generate a complete Python" in prompt and "handler function" in prompt:
            match = re.search(r"Description: (.*?)(?:\n|$)", prompt)
            description = match.group(1) if match else "custom functionality"

            # Generate a simple handler
            function_name = self._generate_function_name(description)

            return f"""
```python
from typing import Any, Dict, List, Optional
from quantum_orchestrator.handlers import handler
from quantum_orchestrator.utils.logging_utils import get_logger

logger = get_logger(__name__)

@handler(
    name="{function_name}",
    description="Handler for {description}",
    parameters={{
        "input": {{"type": "string", "description": "Input data for the operation"}},
        "options": {{"type": "object", "description": "Additional options", "default": {{}}}}
    }},
    returns={{
        "success": {{"type": "boolean", "description": "Whether the operation was successful"}},
        "result": {{"type": "any", "description": "Operation result"}},
        "error": {{"type": "string", "description": "Error message if operation failed"}}
    }}
)
def {function_name}(params: Dict[str, Any]) -> Dict[str, Any]:
    \"\"\"
    Handler for {description}.

    This handler processes the input according to the specified requirements
    and returns the result of the operation.

    Args:
        params: Dictionary containing input parameters

    Returns:
        Dict containing success flag, result, and error message if any
    \"\"\"
    try:
        # Extract parameters
        input_data = params.get("input", "")
        options = params.get("options", {{}})

        # Validate parameters
        if not input_data:
            return {{"success": False, "error": "Input data is required"}}

        # Process the operation based on description
        # This is a placeholder for actual implementation
        result = f"Processed '{{input_data}}' for {description}"

        # Return success response
        return {{
            "success": True,
            "result": result
        }}

    except Exception as e:
        logger.error(f"Error in {function_name}: {{str(e)}}")
        return {{"success": False, "error": f"Error processing request: {{str(e)}}"}}
```
"""

        # Default response
        return "I've processed your request and generated a response."

    def _generate_function_name(self, description: str) -> str:
        """
        Generate a function name from a description.

        Args:
            description: Function description

        Returns:
            Generated function name
        """
        # Extract keywords
        keywords = re.findall(r"\b[a-zA-Z]{3,}\b", description.lower())
        keywords = [
            kw
            for kw in keywords
            if kw not in ["the", "and", "for", "that", "this", "with", "from"]
        ]

        if not keywords:
            return "custom_handler"

        # Use the first 2 keywords
        function_name = "_".join(keywords[:2]) + "_handler"
        return function_name


# Global provider instances
_providers = {"openai": None, "azure": None, "anthropic": None, "local": None}


def get_provider(provider_name: str) -> LLMProvider:
    """
    Get a provider instance.

    Args:
        provider_name: Name of the provider

    Returns:
        Provider instance
    """
    global _providers

    if provider_name not in _providers or _providers[provider_name] is None:
        if provider_name == "openai":
            _providers[provider_name] = OpenAIProvider()
        elif provider_name == "azure":
            _providers[provider_name] = AzureOpenAIProvider()
        elif provider_name == "anthropic":
            _providers[provider_name] = AnthropicProvider()
        elif provider_name == "local":
            _providers[provider_name] = LocalLLMProvider()
        else:
            raise ValueError(f"Unknown provider: {provider_name}")

    return _providers[provider_name]


def get_best_available_provider() -> LLMProvider:
    """
    Get the best available provider based on configuration and availability.

    Returns:
        The best available provider
    """
    # Default provider order
    provider_preference = ["openai", "azure", "anthropic", "local"]

    # Try to get preference from config
    try:
        if "config" in globals() and config is not None:
            config_preference = config.get("llm", {}).get("providers")
            if config_preference:
                provider_preference = config_preference
    except Exception:
        pass

    # Try providers in order of preference
    for provider_name in provider_preference:
        try:
            provider = get_provider(provider_name)
            if provider.is_available():
                logger.info(f"Using {provider_name} as LLM provider")
                return provider
        except Exception as e:
            logger.warning(f"Error checking provider {provider_name}: {str(e)}")

    # Fallback to local provider
    logger.warning("No external LLM providers available, using local provider")
    return get_provider("local")


async def generate_completion_async(
    prompt: str,
    model: Optional[str] = None,
    temperature: float = DEFAULT_TEMPERATURE,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    provider: Optional[str] = None,
    **kwargs,
) -> str:
    """
    Generate a completion asynchronously using the best available provider.

    Args:
        prompt: The prompt to complete
        model: The model to use
        temperature: Temperature for generation
        max_tokens: Maximum tokens to generate
        provider: Specific provider to use
        **kwargs: Additional provider-specific parameters

    Returns:
        Generated completion
    """
    if provider:
        # Use specified provider
        provider_instance = get_provider(provider)
    else:
        # Use best available provider
        provider_instance = get_best_available_provider()

    return await provider_instance.generate_completion_async(
        prompt=prompt,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        **kwargs,
    )


def generate_completion(
    prompt: str,
    model: Optional[str] = None,
    temperature: float = DEFAULT_TEMPERATURE,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    provider: Optional[str] = None,
    **kwargs,
) -> str:
    """
    Generate a completion synchronously using the best available provider.

    Args:
        prompt: The prompt to complete
        model: The model to use
        temperature: Temperature for generation
        max_tokens: Maximum tokens to generate
        provider: Specific provider to use
        **kwargs: Additional provider-specific parameters

    Returns:
        Generated completion
    """
    if provider:
        # Use specified provider
        provider_instance = get_provider(provider)
    else:
        # Use best available provider
        provider_instance = get_best_available_provider()

    return provider_instance.generate_completion(
        prompt=prompt,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        **kwargs,
    )
