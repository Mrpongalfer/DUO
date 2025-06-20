# pac_cli/app/core/config_manager.py
import os
import toml
from pathlib import Path
from typing import Any, Dict, Optional, List
import logging

logger = logging.getLogger(__name__) # Assuming PAC's main.py sets up a root logger

# NPT_BASE_DIR should be set by the npac launcher or defaulted in main.py
# This path is relative to NPT_BASE_DIR
DEFAULT_PAC_CONFIG_DIR_NAME = "config"
DEFAULT_SETTINGS_FILENAME = "settings.toml"

class ConfigManager:
    """Manages PAC's configuration settings, loaded from a TOML file.".""
    def __init__(self, npt_base_dir: Path, config_filename: Optional[str] = None):
        self.npt_base_dir = npt_base_dir
        self.config_dir = self.npt_base_dir / DEFAULT_PAC_CONFIG_DIR_NAME
        self.settings_file_path = self.config_dir / (config_filename or DEFAULT_SETTINGS_FILENAME)
        self.settings: Dict[str, Any] = {}
        self._load_settings()

    def _ensure_config_dir_exists(self):
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logger.error(f"Could not create PAC config directory at {self.config_dir}: {e}")
            # Depending on severity, could raise an exception or allow running with defaults.
            # For now, log and proceed, load_settings will use defaults.

    def _load_settings(self):
        self._ensure_config_dir_exists()
        defaults = self._get_default_settings()

        if self.settings_file_path.exists() and self.settings_file_path.is_file():
            try:
                with open(self.settings_file_path, "r", encoding="utf-8") as f:
                    user_settings = toml.load(f)

                # Deep merge user settings onto defaults
                self.settings = self._merge_dicts(defaults, user_settings)
                logger.info(f"Loaded PAC settings from: {self.settings_file_path}")
            except toml.TomlDecodeError as e:
                logger.error(f"Error decoding TOML from {self.settings_file_path}: {e}. Using default settings.")
                self.settings = defaults
            except OSError as e:
                logger.error(f"Error reading settings file {self.settings_file_path}: {e}. Using default settings.")
                self.settings = defaults
        else:
            logger.info(f"PAC settings file not found at {self.settings_file_path}. Using default settings and creating a new one.")
            self.settings = defaults
            self.save_settings() # Save defaults to create the file

    def _merge_dicts(self, base: Dict, updates: Dict) -> Dict:
        """Recursively merges 'updates' dict into 'base' dict."""
        merged = base.copy()
        for key, value in updates.items():
            if isinstance(value, dict) and isinstance(merged.get(key), dict):
                merged[key] = self._merge_dicts(merged[key], value)
            else:
                merged[key] = value
        return merged

    def _get_default_settings(self) -> Dict[str, Any]:
        # TODO, Architect: Define comprehensive default settings for PAC
        return {
            "general": {
                "default_ner_path": str(self.npt_base_dir / "ner_repository"),
                "default_user_name": "Architect",
                "preferred_editor": os.environ.get("EDITOR", "nano"), # Or "vi", "code", etc.
            },
            "agents": {
                "ex_work_agent_path": "", # To be filled by user or bootstrap
                "scribe_agent_path": "",  # To be filled by user or bootstrap
                "default_ex_work_project_path": ".",
                "default_scribe_project_path": ".",
            },
            "llm_interface": { # Conceptual, based on args.llm_preference
                "provider": "generic", # e.g., "ollama", "openai", "anthropic"
                "api_base_url": "http://localhost:11434", # Example for Ollama
                "default_model": "mistral-nemo:latest",   # Example
                "api_key_env_var": "OLLAMA_API_KEY", # Placeholder
                "timeout_seconds": 180,
                "max_retries": 2,
            },
            "ui": {
                "use_fzf_fallback_if_fzf_missing": True,
                "truncate_output_length": 1000,
                "datetime_format": "%Y-%m-%d %H:%M:%S %Z",
            },
            # TODO, Architect: Add sections for workflow engine defaults, plugin paths, etc.
        }

    def save_settings(self) -> bool:
        self._ensure_config_dir_exists()
        try:
            with open(self.settings_file_path, "w", encoding="utf-8") as f:
                toml.dump(self.settings, f)
            logger.info(f"PAC settings saved to: {self.settings_file_path}")
            return True
        except OSError as e:
            logger.error(f"Failed to save PAC settings to {self.settings_file_path}: {e}")
            return False

    def get(self, key_path: str, default: Any = None) -> Any:
        """Access a setting using a dot-separated path (e.g., 'general.user_name')."""
        keys = key_path.split('.')
        value = self.settings
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            # logger.debug(f"Setting '{key_path}' not found, returning default: {default}")
            return default

    def set_value(self, key_path: str, value: Any):
        """Set a configuration value using a dot-separated path and save.".""
        keys = key_path.split('.')
        current_level = self.settings
        for i, key in enumerate(keys[:-1]):
            current_level = current_level.setdefault(key, {})
            if not isinstance(current_level, dict):
                logger.error(f"Cannot set config value for '{key_path}': '{key}' is not a dictionary.")
                return
        current_level[keys[-1]] = value
        self.save_settings() # Auto-save on set

# Example of how to use it in main.py:
# from .core.config_manager import ConfigManager
# NPT_BASE_DIR_FROM_ENV = Path(os.environ.get("NPT_BASE_DIR", Path.cwd())) # Fallback to CWD if not set
# config_manager = ConfigManager(npt_base_dir=NPT_BASE_DIR_FROM_ENV)
# user_name = config_manager.get("general.user_name", "Valued User")