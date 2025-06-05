from typing import TypedDict, Optional, Literal

class LEMSConfigMVP(TypedDict):
    # For MVP, we manage a single, primary configuration.
    # This structure defines what LEMS expects to be stored in ACLS for that primary config.
    config_id: Literal["primary_ollama_mvp"] # Fixed ID for the single MVP config
    display_name: str # e.g., "Primary Local Ollama (Mistral)"
    provider_type: Literal["ollama"] # MVP only supports Ollama
    base_url: str # e.g., "http://localhost:11434"
    model_name: str # e.g., "mistral:latest" (specific model to use with the client)
    # api_key_id is not needed for Ollama in MVP, so omit from this TypedDict
    # is_active is implicitly True as it's the only config for MVP
    supports_system_prompt_directly: bool # Typically True for Ollama API
    timeout_seconds: int # e.g., 120
    last_tested_timestamp: Optional[str] # ISO format timestamp
    last_test_status: Optional[str] # "OK", "ERROR: <message>", "UNTESTED"
