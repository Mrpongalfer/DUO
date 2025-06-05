from typing import Dict, Optional, Any
from aci_v2.common_exceptions import ACIError

class LEMSError(ACIError):
    """Base exception for LEMS MVP module related errors."""
    pass

class LLMConfigNotFoundError(LEMSError):
    """Raised when the primary LLM configuration is not found in ACLS."""
    pass

class LLMClientInstantiationError(LEMSError):
    """Raised if the LLM API client (e.g., Ollama client) fails to initialize."""
    pass

class OllamaServiceError(LEMSError):
    """Raised for errors returned by the Ollama service itself during interaction."""
    pass
