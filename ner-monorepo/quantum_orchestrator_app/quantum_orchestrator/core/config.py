# File: ~/Projects/quantum_orchestrator_app/quantum_orchestrator/core/config.py
"""
Configuration management for the Quantum Orchestrator application using pydantic-settings.

Handles loading settings from JSON and environment variables with ENV taking precedence.
Provides a cached, validated settings object for application-wide use.
Adheres to TPC standards.
"""

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional  # Added List for broader compatibility

# Ensure pydantic v2+ features are used if available
from pydantic import AnyHttpUrl, Field, SecretStr, ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# --- Initial Logging Setup ---
# Configure basic logging; main.py or logging_utils might refine this later
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# --- Configuration File Path ---
# Assumes config.json lives at the project root relative to this file's location
# Project Root = quantum_orchestrator_app/
# Config File = quantum_orchestrator_app/config.json
try:
    # This assumes config.py is in quantum_orchestrator/core/
    PROJECT_ROOT_DIR = Path(__file__).parent.parent.parent
    DEFAULT_CONFIG_FILENAME = "config.json"
    DEFAULT_CONFIG_PATH = PROJECT_ROOT_DIR / DEFAULT_CONFIG_FILENAME
except NameError:
    # Fallback if __file__ is not defined (e.g., in interactive sessions)
    logger.warning(
        "Could not determine project root automatically, defaulting config path."
    )
    PROJECT_ROOT_DIR = Path(".").resolve()  # Use current dir as root
    DEFAULT_CONFIG_FILENAME = "config.json"
    DEFAULT_CONFIG_PATH = PROJECT_ROOT_DIR / DEFAULT_CONFIG_FILENAME
    logger.info(f"Using fallback config path: {DEFAULT_CONFIG_PATH}")


# --- Helper: Load Base Config from JSON ---
def load_json_config(config_path: Path) -> Dict[str, Any]:
    """Loads base configuration from the specified JSON file."""
    if not config_path.is_file():
        logger.warning(
            f"JSON config file not found: {config_path}. Using defaults/ENV only."
        )
        return {}
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            logger.error(
                f"Invalid JSON format in {config_path}: Expected a dictionary. Using defaults/ENV only."
            )
            return {}
        logger.info(f"Loaded base configuration from {config_path}")
        return data
    except json.JSONDecodeError:
        logger.exception(
            f"Error decoding JSON from {config_path}. Using defaults/ENV only."
        )
        return {}
    except OSError as e:
        logger.exception(
            f"Error reading config file {config_path}: {e}. Using defaults/ENV only."
        )
        return {}


# --- Settings Model Definition ---
class LLMSettings(BaseSettings):
    """Specific settings for the LLM Service."""

    # Allow None initially, handle default logic later if needed
    default_provider: Optional[str] = Field(
        "ollama", description="Default LLM provider ('ollama', 'openai', etc.)"
    )
    api_base: Optional[AnyHttpUrl] = Field(
        None,
        alias="LLM_API_BASE",
        description="Base URL for the LLM API (e.g., Ollama server).",
    )
    model_name: Optional[str] = Field(
        "mistral-nemo:12b-instruct-2407-q4_k_m",
        alias="LLM_MODEL_NAME",
        description="Default LLM model to use.",
    )
    api_key: Optional[SecretStr] = Field(
        None,
        alias="LLM_API_KEY",
        description="API key for the LLM provider, if required.",
    )
    temperature: float = Field(0.7, description="Default sampling temperature for LLM.")
    max_tokens: int = Field(4096, description="Default max tokens for LLM generation.")

    # Pydantic config specific to this sub-model if needed
    # model_config = SettingsConfigDict(env_prefix='LLM_')


class Settings(BaseSettings):
    """
    Main application settings model.

    Loads values with priority: ENV > JSON > Defaults.
    """

    # Core App
    app_name: str = Field("Quantum Orchestrator", description="Application name.")
    environment: str = Field(
        "development",
        description="Deployment environment (development, staging, production).",
    )
    debug: bool = Field(False, description="Enable debug mode.")
    logging_level: str = Field(
        "INFO", description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)."
    )

    # Database (Example using DATABASE_URL)
    # Ensure your app reads this specific env var name
    database_url: SecretStr = Field(
        ..., alias="DATABASE_URL", description="Primary database connection string."
    )

    # LLM Service Config (Nested Model)
    # Pydantic-settings uses env var like LLM_SERVICE__API_BASE = "http://..."
    llm_service: LLMSettings = Field(default_factory=LLMSettings)

    # API Service Config
    api_enabled: bool = Field(True, description="Enable the API server.")
    api_host: str = Field("0.0.0.0", description="Host for the API server.")
    api_port: int = Field(8000, description="Port for the API server.")
    api_allow_cors: bool = Field(
        True, description="Allow Cross-Origin Resource Sharing for API."
    )

    # Web Interface / Flask Specific (if needed)
    flask_secret_key: SecretStr = Field(
        ...,
        alias="FLASK_SECRET_KEY",
        description="Secret key for Flask security/sessions.",
    )
    # Add other Flask/Web related settings from config.json if necessary

    # Agent Settings (add more as needed from config.json)
    agent_default_prompt: str = Field("You are a helpful AI assistant.")
    agent_max_tokens: int = Field(4096)  # Inherited from llm_service defaults now
    handler_timeout: int = Field(
        30, description="Default timeout for handlers in seconds."
    )

    # Pydantic-Settings Configuration
    model_config = SettingsConfigDict(
        env_file=None,  # Explicitly disable .env loading, we handle sources
        env_nested_delimiter="__",  # Allows ENV var like LLM_SERVICE__API_BASE
        case_sensitive=False,  # Env vars are case-insensitive
        extra="ignore",  # Ignore extra fields from JSON/ENV
    )

    # Validator to ensure logging level is valid
    @field_validator("logging_level")
    @classmethod
    def validate_logging_level(cls, v: str) -> str:
        level = v.upper()
        if level not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            raise ValueError(
                f"Invalid logging_level: {v}. Must be one of DEBUG, INFO, WARNING, ERROR, CRITICAL"
            )
        return level

    @classmethod
    def load_settings(cls, json_config_path: Path = DEFAULT_CONFIG_PATH) -> "Settings":
        """Loads settings from JSON and environment variables."""
        json_values = load_json_config(json_config_path)

        # Prepare init kwargs by deep merging nested dicts if they exist in JSON
        # Example: merge llm_service settings from JSON if present
        # This requires careful handling if JSON structure differs from Pydantic model
        # For simplicity now, assume top-level keys match or ENV vars override fully.
        # A more robust loader could recursively update defaults with JSON data.
        init_kwargs = json_values  # Start with JSON values

        try:
            # Initialize BaseSettings. ENV vars automatically loaded and override init_kwargs.
            instance = cls(**init_kwargs)
            logger.info("Configuration loaded successfully (ENV vars override JSON).")

            # Configure root logger based on final loaded settings
            try:
                log_level_int = getattr(logging, instance.logging_level.upper())
                # Check if basicConfig was already called, update level if so
                if logging.getLogger().hasHandlers():
                    logging.getLogger().setLevel(log_level_int)
                else:
                    # Set basicConfig here if not set elsewhere (e.g., main.py)
                    logging.basicConfig(
                        level=log_level_int,
                        format=(
                            logging.getLogger().handlers[0].formatter._fmt
                            if logging.getLogger().hasHandlers()
                            else None
                        ),
                    )
                logger.info(
                    f"Effective logging level set to: {instance.logging_level.upper()}"
                )
            except Exception as log_e:
                logger.error(
                    f"Could not apply logging level from config: {log_e}. Using previous/default level."
                )

            return instance
        except ValidationError as e:
            logger.critical(f"Configuration validation failed! Errors:\n{e}")
            # Provide detailed error context
            # for error in e.errors():
            #     field = ".".join(map(str, error["loc"]))
            #     logger.critical(f"  - Field '{field}': {error['msg']}")
            raise ValueError(
                "CRITICAL CONFIGURATION ERROR - Review environment variables and config.json"
            ) from e


# --- Cached Accessor ---
@lru_cache()
def get_settings() -> Settings:
    """Returns a cached singleton instance of the application settings."""
    logger.debug("Accessing settings instance (will load if not cached)...")
    return Settings.load_settings()


# --- Example Usage ---
if __name__ == "__main__":
    print("Attempting to load settings for Quantum Orchestrator...")
    # Example: Set environment variables BEFORE loading settings for testing override
    # os.environ["DATABASE_URL"] = "postgresql://env_user:env_pass@env_host:5432/env_db"
    # os.environ["LLM_SERVICE__MODEL_NAME"] = "env_model"
    # os.environ["FLASK_SECRET_KEY"] = "env_secret_key_shhh"

    try:
        settings = get_settings()
        print("\n--- Settings Loaded Successfully ---")
        # Use model_dump for clean output, automatically handling SecretStr
        print(settings.model_dump_json(indent=2))

        print("\n--- Accessing Specific Settings ---")
        print(f"Database URL Type: {type(settings.database_url)}")
        print(f"LLM Provider: {settings.llm_service.default_provider}")
        print(f"LLM Model: {settings.llm_service.model_name}")
        print(f"LLM API Base: {settings.llm_service.api_base}")
        print(f"Logging Level: {settings.logging_level}")
        print(f"Flask Secret Type: {type(settings.flask_secret_key)}")
        # To access secret value (use very carefully):
        # print(f"DB URL Actual: {settings.database_url.get_secret_value()}")

        # Verify caching
        print("\n--- Verifying Settings Caching ---")
        settings_2 = get_settings()
        print(f"get_settings() called again. Same instance? {settings is settings_2}")

    except ValueError as e:
        print("\n--- FAILED TO LOAD SETTINGS ---")
        print(f"Error: {e}")
