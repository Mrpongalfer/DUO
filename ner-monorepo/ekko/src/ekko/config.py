# File: src/ekko/config.py
"""
Project Ekko - Configuration Loading using Pydantic Settings.
Loads from .env files and environment variables. Corrected lint issues.
"""

import logging
from pathlib import Path

from pydantic import Field  # Keep HttpUrl if used
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class EkkoConfigurationError(ValueError):
    """Custom exception for Ekko configuration errors."""

    pass


class AIServiceConfig(BaseSettings):
    """Configuration for a single AI provider."""

    api_key: str | None = Field(None, validation_alias="API_KEY")
    base_url: str | None = None  # Allow plain string for base_url
    default_model: str | None = None

    model_config = SettingsConfigDict(extra="ignore")


class EkkoSettings(BaseSettings):
    """Main configuration model for Ekko."""

    log_level: str = Field("INFO", validation_alias="EKKO_LOG_LEVEL")
    project_base_dir: Path = Field(
        default_factory=lambda: Path.home() / "ekko_projects",
        validation_alias="EKKO_PROJECT_BASE",
    )

    gemini_config: AIServiceConfig | None = Field(
        default=None, validation_alias="EKKO_GEMINI"
    )
    claude_config: AIServiceConfig | None = Field(
        default=None, validation_alias="EKKO_CLAUDE"
    )
    openai_config: AIServiceConfig | None = Field(
        default=None, validation_alias="EKKO_OPENAI"
    )
    ollama_config: AIServiceConfig = Field(
        default_factory=lambda: AIServiceConfig(
            base_url="http://localhost:11434", default_model="mistral"
        ),
        validation_alias="EKKO_OLLAMA",
    )

    primary_generator: str = Field("gemini", validation_alias="EKKO_PRIMARY_GENERATOR")
    security_validator: str = Field(
        "claude", validation_alias="EKKO_SECURITY_VALIDATOR"
    )
    docs_generator: str = Field("openai", validation_alias="EKKO_DOCS_GENERATOR")

    ansible_playbook_dir: Path | None = Field(None, validation_alias="EKKO_ANSIBLE_DIR")
    terraform_dir: Path | None = Field(None, validation_alias="EKKO_TERRAFORM_DIR")

    scribe_agent_path: Path | None = Field(None, validation_alias="EKKO_SCRIBE_PATH")

    model_config = SettingsConfigDict(
        env_file=(
            Path() / "config" / ".env",
            Path.home() / ".config" / "ekko" / ".env",
        ),
        env_prefix="EKKO_",
        case_sensitive=False,
        extra="ignore",
        env_nested_delimiter="__",
    )


_cached_settings: EkkoSettings | None = None


def get_ekko_settings() -> EkkoSettings:
    """Loads and returns the Ekko settings, caching the instance."""
    global _cached_settings
    if _cached_settings is None:
        logger.debug("Loading Ekko settings...")
        try:
            _cached_settings = EkkoSettings()
            logger.info("Ekko settings loaded successfully.")
            logger.debug(f"  Log Level: {_cached_settings.log_level}")
            logger.debug(f"  Project Base: {_cached_settings.project_base_dir}")
        except FileNotFoundError as e:
            logger.error(f"Configuration file not found: {e}")
            # Handle specific FileNotFoundError exceptions
        except ValueError as e:
            logger.error(f"Value error occurred: {e}")
            # Handle specific ValueError exceptions
        except PermissionError as e:
            logger.error(f"Permission error occurred: {e}")
            # Handle specific PermissionError exceptions
        except RuntimeError as e:
            logger.error(f"Runtime error occurred: {e}")
            # Handle specific RuntimeError exceptions
        except Exception as e:
            logger.error(
                f"FATAL: Failed to load/validate Ekko settings: {e}", exc_info=True
            )
            raise EkkoConfigurationError(f"Ekko settings load failed: {e}") from e
    return _cached_settings


if __name__ == "__main__":
    try:
        settings = get_ekko_settings()
        print("Ekko Settings Loaded:")
        print(
            settings.model_dump_json(
                indent=2, exclude={"gemini_config", "claude_config", "openai_config"}
            )
        )
    except EkkoConfigurationError as e:
        print(f"Error loading settings: {e}")
    except Exception as e:
        print(f"Unexpected error loading settings: {type(e).__name__}: {e}")
