# pac_cli/app/core/config_manager.py
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

import toml

logger = logging.getLogger(__name__)  # Assuming PAC's main.py sets up a root logger

# NPT_BASE_DIR should be set by the npac launcher or defaulted in main.py
# This path is relative to NPT_BASE_DIR
DEFAULT_PAC_CONFIG_DIR_NAME = "config"  # This is NPTPAC's config, not Lily's
DEFAULT_SETTINGS_FILENAME = "settings.toml"


class ConfigManager:
    """Manages PAC's configuration settings, loaded from a TOML file."""

    def __init__(self, npt_base_dir: Path, config_filename: Optional[str] = None):
        self.npt_base_dir = npt_base_dir
        # This is the config directory for NPTPAC itself
        self.pac_config_dir = self.npt_base_dir / DEFAULT_PAC_CONFIG_DIR_NAME
        self.settings_file_path = self.pac_config_dir / (
            config_filename or DEFAULT_SETTINGS_FILENAME
        )
        self.settings: Dict[str, Any] = {}
        self._load_settings()

    def _ensure_pac_config_dir_exists(self):
        """Ensures the NPTPAC config directory exists."""
        try:
            self.pac_config_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logger.error(
                f"Could not create PAC config directory at {self.pac_config_dir}: {e}"
            )
            # For now, log and proceed, load_settings will use defaults.

    def _load_settings(self):
        self._ensure_pac_config_dir_exists()
        defaults = self._get_default_settings()

        if self.settings_file_path.exists() and self.settings_file_path.is_file():
            try:
                with open(self.settings_file_path, "r", encoding="utf-8") as f:
                    user_settings = toml.load(f)
                # Deep merge user settings onto defaults
                self.settings = self._merge_dicts(defaults, user_settings)
                logger.info(f"Loaded PAC settings from: {self.settings_file_path}")
            except toml.TomlDecodeError as e:
                logger.error(
                    f"Error decoding TOML from {self.settings_file_path}: {e}. Using default settings."
                )
                self.settings = defaults
            except OSError as e:
                logger.error(
                    f"Error reading settings file {self.settings_file_path}: {e}. Using default settings."
                )
                self.settings = defaults
        else:
            logger.info(
                f"PAC settings file not found at {self.settings_file_path}. Using default settings and creating a new one with defaults."
            )
            self.settings = defaults
            self.save_settings()  # Save defaults to create the file

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
        # NPT_BASE_DIR is the root of the NPTPAC project structure,
        # often equivalent to the root of my_devsuite_project or a similar top-level dir.
        # It's NOT the ner-monorepo root unless NPTPAC is at the monorepo root.
        # The user should ensure NPT_BASE_DIR is set correctly when pac_cli starts.

        # Default path for LilyCoreMemory assumes it's a sibling to NPTPAC's parent dir,
        # or user provides an absolute path. This default is very speculative.
        # Best if user sets an absolute path in their settings.toml
        default_lily_core_memory_base = (
            Path.home() / "Projects" / "ner-monorepo" / "Lily" / "LilyCoreMemory"
        )

        return {
            "general": {
                "default_ner_path": str(self.npt_base_dir / "ner_repository"),
                "default_user_name": "Architect",
                "preferred_editor": os.environ.get("EDITOR", "nano"),
            },
            "agents": {
                # It's better if these paths are relative to npt_base_dir or absolute
                "ex_work_agent_path": str(
                    self.npt_base_dir / "core_agents" / "ex_work_agentv2.py"
                ),
                "scribe_agent_path": str(
                    self.npt_base_dir / "core_agents" / "scribe_agent.py"
                ),
                "default_ex_work_project_path": ".",  # Relative to where pac_cli is run or a configured root
                "default_scribe_project_path": ".",
            },
            "llm_interface": {
                "provider": "generic",
                "api_base_url": "http://localhost:11434",
                "default_model": "mistral-nemo:latest",
                "api_key_env_var": "OLLAMA_API_KEY",  # Example, adjust per provider
                "timeout_seconds": 180,
                "max_retries": 2,
            },
            "ui": {
                "use_fzf_fallback_if_fzf_missing": True,  # Assuming fzf might be used for selection
                "truncate_output_length": 1000,
                "datetime_format": "%Y-%m-%d %H:%M:%S %Z",
            },
            "lily_core_memory": {
                "base_path": str(
                    default_lily_core_memory_base
                ),  # User MUST override this in settings.toml
                "db_name": "lily_intelligent_memory.db",
                "db_dir_name": "IntelligentMemoryDB_Placeholder",
                "persona_foundation_md": "00_Persona_Foundation.md",
                "interaction_principles_md": "01_InteractionPrinciples_Baseline.md",
                "key_directives_dir": "KeyDirectives",
                "snapshots_dir": "InteractionLog_ContextualSnapshots",
                "proposed_updates_dir": "ProposedPersonaUpdates",
                "raw_logs_dir": "InteractionArchives_Raw",
                "scripts_dir": "Scripts",
            },
            # TODO, Architect: Add sections for workflow engine defaults, plugin paths, etc.
        }

    def save_settings(self) -> bool:
        """Saves the current settings back to the TOML file."""
        self._ensure_pac_config_dir_exists()  # Ensures NPTPAC config dir exists
        try:
            with open(self.settings_file_path, "w", encoding="utf-8") as f:
                toml.dump(self.settings, f)
            logger.info(f"PAC settings saved to: {self.settings_file_path}")
            return True
        except OSError as e:
            logger.error(
                f"Failed to save PAC settings to {self.settings_file_path}: {e}"
            )
            return False

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Access a setting using a dot-separated path (e.g., 'general.user_name').
        Returns the default value if the key_path is not found.
        """
        keys = key_path.split(".")
        value = self.settings
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            # logger.debug(f"Setting '{key_path}' not found, returning default: {default}")
            return default

    def set_value(self, key_path: str, value: Any, auto_save: bool = True):
        """
        Set a configuration value using a dot-separated path.
        Saves settings automatically by default.
        """
        keys = key_path.split(".")
        current_level = self.settings
        for i, key in enumerate(keys[:-1]):
            # If a key in the path doesn't exist or isn't a dict, create it.
            if key not in current_level or not isinstance(current_level[key], dict):
                current_level[key] = {}
            current_level = current_level[key]

            # Safety check if a non-dict is encountered mid-path
            if not isinstance(current_level, dict):
                logger.error(
                    f"Cannot set config value for '{key_path}': Intermediate key '{key}' points to a non-dictionary value '{current_level}'. Path cannot be created."
                )
                return False  # Indicate failure

        current_level[keys[-1]] = value
        logger.info(f"Setting '{key_path}' updated to: {value}")
        if auto_save:
            return self.save_settings()
        return True  # Indicate success without saving (if auto_save is False)

    # --- Properties for LilyCoreMemory Paths ---
    @property
    def lily_core_memory_base_path_str(self) -> Optional[str]:
        return self.get("lily_core_memory.base_path")

    @property
    def lily_core_memory_base_path(self) -> Optional[Path]:
        path_str = self.lily_core_memory_base_path_str
        if path_str:
            return Path(path_str).expanduser().resolve()
        logger.warning("LilyCoreMemory base_path is not configured in settings.toml.")
        return None

    def _get_lcm_subpath(self, config_key: str, default_dirname: str) -> Optional[Path]:
        """Helper to get a subdirectory path within LilyCoreMemory base."""
        base = self.lily_core_memory_base_path
        if not base:
            return None
        dirname = self.get(f"lily_core_memory.{config_key}", default_dirname)
        return base / dirname

    @property
    def lcm_db_path(self) -> Optional[Path]:
        base = self.lily_core_memory_base_path
        if not base:
            return None
        db_dir = base / self.get(
            "lily_core_memory.db_dir_name", "IntelligentMemoryDB_Placeholder"
        )
        db_name = self.get("lily_core_memory.db_name", "lily_intelligent_memory.db")
        return db_dir / db_name

    @property
    def lcm_persona_foundation_file(self) -> Optional[Path]:
        base = self.lily_core_memory_base_path
        if not base:
            return None
        return base / self.get(
            "lily_core_memory.persona_foundation_md", "00_Persona_Foundation.md"
        )

    @property
    def lcm_interaction_principles_file(self) -> Optional[Path]:
        base = self.lily_core_memory_base_path
        if not base:
            return None
        return base / self.get(
            "lily_core_memory.interaction_principles_md",
            "01_InteractionPrinciples_Baseline.md",
        )

    @property
    def lcm_key_directives_dir(self) -> Optional[Path]:
        return self._get_lcm_subpath("key_directives_dir", "KeyDirectives")

    @property
    def lcm_snapshots_dir(self) -> Optional[Path]:
        return self._get_lcm_subpath(
            "snapshots_dir", "InteractionLog_ContextualSnapshots"
        )

    @property
    def lcm_proposed_updates_dir(self) -> Optional[Path]:
        return self._get_lcm_subpath("proposed_updates_dir", "ProposedPersonaUpdates")

    @property
    def lcm_raw_logs_dir(self) -> Optional[Path]:
        return self._get_lcm_subpath("raw_logs_dir", "InteractionArchives_Raw")

    @property
    def lcm_scripts_dir(self) -> Optional[Path]:
        return self._get_lcm_subpath("scripts_dir", "Scripts")


# Example of how to use it in main.py or command files:
# from .core.config_manager import ConfigManager
#
# # Assuming NPT_BASE_DIR is determined appropriately (e.g., from env var or project root discovery)
# # This might be defined once in your main.py and passed around or accessed via a global/contextvar
# NPT_BASE_DIR_FROM_ENV = Path(os.environ.get("NPT_BASE_DIR", Path.cwd()))
# config = ConfigManager(npt_base_dir=NPT_BASE_DIR_FROM_ENV)
#
# # Accessing a general setting
# user_name = config.get("general.user_name", "Valued User")
#
# # Accessing a LilyCoreMemory path
# lily_mem_path = config.lily_core_memory_base_path
# if lily_mem_path and lily_mem_path.exists():
#     logger.info(f"Lily's Core Memory is configured at: {lily_mem_path}")
# else:
#     logger.error("Lily's Core Memory path is not configured or does not exist. Please check settings.toml.")
