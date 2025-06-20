# In aci_v2/acls_mvp/config_manager.py
# Date: June 2, 2025
# Author: Lily AI for The Architect (ACI v2.0 Project)

import configparser
import datetime
import logging
from pathlib import Path
from typing import Any

from .exceptions import ConfigPersistenceError


class ConfigManagerMVP:
    """
    Manages ACI's general configuration settings via a local INI file for the MVP.
    Handles loading, creating default configurations, getting, and setting values.
    """

    DEFAULT_CONFIG_FILENAME: str = "aci_mvp_config.ini"
    DEFAULT_CONFIG_SUBDIR_IN_OS_CONFIG_DIR: str = "aci_v2_mvp"

    def __init__(
        self,
        config_file_path_override: str | Path | None = None,
        bootstrap_logger: logging.Logger | None = None,
    ) -> None:
        """
        Initializes ConfigManagerMVP with the specified config file path.
        If no path is provided, it constructs a default path in the user's config directory.
        Loads the configuration or creates a default one if the file doesn't exist.

        Args:
            config_file_path_override (Optional[Union[str, Path]]): Absolute path to override the default configuration INI file.
            bootstrap_logger (Optional[logging.Logger]): A logger instance for initialization messages.
                                                        If None, a default logger for this class will be used.
        """
        self.logger = (
            bootstrap_logger
            if bootstrap_logger
            else logging.getLogger(f"ACI.ACLS.{self.__class__.__name__}")
        )

        if config_file_path_override:
            self.config_file_path: Path = (
                Path(config_file_path_override).expanduser().resolve()
            )
        else:
            self.config_file_path: Path = (
                Path.home()
                / ".config"
                / self.DEFAULT_CONFIG_SUBDIR_IN_OS_CONFIG_DIR
                / self.DEFAULT_CONFIG_FILENAME
            )

        self.config: configparser.ConfigParser = configparser.ConfigParser(
            interpolation=None
        )
        self.logger.info(
            f"ConfigManagerMVP targeting INI file: '{self.config_file_path}'"
        )
        self._ensure_config_dir_exists()
        self._load_or_create_config()

    def _ensure_config_dir_exists(self) -> None:
        """Ensures the directory for the configuration file exists."""
        try:
            self.config_file_path.parent.mkdir(parents=True, exist_ok=True)
            self.logger.debug(
                f"Ensured config directory exists: '{self.config_file_path.parent}'"
            )
        except OSError as e:
            self.logger.error(
                f"Failed to create config directory '{self.config_file_path.parent}': {e}",
                exc_info=True,
            )
            raise ConfigPersistenceError(
                f"Failed to create config directory '{self.config_file_path.parent}'",
                original_exception=e,
            )

    def _get_default_config_structure(self) -> configparser.ConfigParser:
        """
        Returns a ConfigParser object populated with default sections and keys for ACI MVP.
        This defines the initial structure if no config file exists.
        """
        config = configparser.ConfigParser(interpolation=None)

        default_user_cache_dir = (
            Path.home() / ".cache" / self.DEFAULT_CONFIG_SUBDIR_IN_OS_CONFIG_DIR
        )
        default_user_data_share_dir = (
            Path.home()
            / ".local"
            / "share"
            / self.DEFAULT_CONFIG_SUBDIR_IN_OS_CONFIG_DIR
        )

        config["General"] = {
            "aci_version": "2.0-MVP",
            "default_lily_persona_id": "proto_lily",
        }
        config["ACLS_MVP_Logging"] = {
            "console_log_level": "INFO",
            "file_log_level": "DEBUG",
            "log_file_path": str(default_user_data_share_dir / "logs" / "aci_mvp.log"),
            "log_file_max_bytes": str(10 * 1024 * 1024),
            "log_file_backup_count": str(5),
        }
        config["ACLS_MVP_SecureStore"] = {
            "fallback_pat_salt_for_ACI_MVP_GITHUB_PAT": ""
        }
        config["EESRS_MVP_GitHub"] = {
            "repository_url": "",
            "default_branch": "main",
            "local_clone_path": str(
                default_user_cache_dir / "architect_master_repository_clone"
            ),
        }
        config["LEMS_MVP_Primary"] = {
            "config_id": "primary_ollama_mvp",
            "display_name": "Ollama Local (Default)",
            "provider_type": "ollama",
            "base_url": "http://localhost:11434",
            "model_name": "mistral:latest",
            "supports_system_prompt_directly": "True",
            "timeout_seconds": "120",
        }
        self.logger.debug("Generated default configuration structure.")
        return config

    def _load_or_create_config(self) -> None:
        """
        Loads config from `self.config_file_path`.
        If the file doesn't exist or is invalid, it creates/overwrites with default structure.
        Raises ConfigPersistenceError on unrecoverable IOErrors during backup or initial save.
        """
        self._ensure_config_dir_exists()
        if self.config_file_path.exists() and self.config_file_path.is_file():
            try:
                self.config.read(self.config_file_path, encoding="utf-8")
                self.logger.info(
                    f"Configuration loaded successfully from '{self.config_file_path}'."
                )
            except configparser.Error as e:
                self.logger.warning(
                    f"Existing config file '{self.config_file_path}' is corrupt or malformed. Error: {e}. Attempting to back it up and create a new default config.",
                    exc_info=True,
                )
                try:
                    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
                    backup_path = self.config_file_path.with_suffix(
                        f".corrupt.{timestamp}"
                    )
                    self.config_file_path.rename(backup_path)
                    self.logger.info(
                        f"Corrupt config file backed up to '{backup_path}'."
                    )
                except OSError as backup_e:
                    self.logger.error(
                        f"Could not back up corrupt config file '{self.config_file_path}': {backup_e}",
                        exc_info=True,
                    )
                self.config = self._get_default_config_structure()
                self._save_config()
                self.logger.info(
                    f"New default configuration file created at '{self.config_file_path}'."
                )
        else:
            self.logger.info(
                f"Config file not found at '{self.config_file_path}'. Creating with default values."
            )
            self.config = self._get_default_config_structure()
            self._save_config()

    def _save_config(self) -> None:
        """Saves the current `self.config` object to `self.config_file_path` with UTF-8 encoding."""
        self._ensure_config_dir_exists()
        try:
            with self.config_file_path.open("w", encoding="utf-8") as config_file:
                self.config.write(config_file)
            self.logger.debug(
                f"Configuration saved successfully to '{self.config_file_path}'."
            )
        except OSError as e:
            self.logger.error(
                f"Failed to save configuration to '{self.config_file_path}': {e}",
                exc_info=True,
            )
            raise ConfigPersistenceError(
                f"Failed to save configuration to '{self.config_file_path}'",
                original_exception=e,
            )

    def get_config_value(
        self, section: str, key: str, fallback: Any = None, value_type: type = str
    ) -> Any:
        """
        Retrieves a configuration value, converting to `value_type`.
        Returns `fallback` if section/key not found or if conversion fails.
        Logs warnings on missing keys/sections or conversion errors.
        """
        if not self.config.has_section(section):
            self.logger.debug(
                f"Section '{section}' not found in config. Returning fallback for key '{key}'."
            )
            return fallback
        if not self.config.has_option(section, key):
            self.logger.debug(
                f"Key '{key}' not found in section '{section}'. Returning fallback."
            )
            return fallback

        try:
            if value_type == bool:
                return self.config.getboolean(section, key)
            if value_type == int:
                return self.config.getint(section, key)
            if value_type == float:
                return self.config.getfloat(section, key)
            return self.config.get(section, key)
        except ValueError as e:
            self.logger.warning(
                f"ValueError converting config: [{section}]{key} to {value_type.__name__}. Using fallback. Error: {e}",
                exc_info=True,
            )
            return fallback
        except Exception as e_unexpected:
            self.logger.error(
                f"Unexpected error getting config: [{section}]{key}. Using fallback. Error: {e_unexpected}",
                exc_info=True,
            )
            return fallback

    def set_config_value(self, section: str, key: str, value: Any) -> None:
        """
        Sets a configuration value (converts to string for storage) and saves the config file.
        If the section does not exist, it will be created.
        Raises:
            ConfigPersistenceError: If there's an issue saving the config file.
        """
        if not self.config.has_section(section):
            self.config.add_section(section)
            self.logger.info(f"Added new section '{section}' to configuration.")

        str_value = str(value)
        current_value = self.config.get(section, key, fallback=object())

        if current_value is object() or current_value != str_value:
            self.config[section][key] = str_value
            self.logger.info(
                f"Set config: [{section}]{key} = '{str_value}' (actual value type: {type(value).__name__})"
            )
            self._save_config()
        else:
            self.logger.debug(
                f"Config: [{section}]{key} already set to '{str_value}'. No change made."
            )

    def delete_config_key(self, section: str, key: str) -> bool:
        """
        Removes a specific key from a given section in the configuration.
        Returns True if the key was successfully removed and saved, False if the section or key did not exist.
        Raises:
            ConfigPersistenceError: If there's an issue saving the config file after removal.
        """
        self.logger.debug(f"Attempting to delete key '{key}' from section '{section}'.")
        if self.config.has_section(section) and self.config.has_option(section, key):
            removed = self.config.remove_option(section, key)
            if removed:
                self._save_config()
                self.logger.info(
                    f"Config key '{key}' removed successfully from section '{section}'."
                )
                return True
            else:
                self.logger.warning(
                    f"Config key '{key}' in section '{section}' reported as present but remove_option failed internally."
                )
                return False
        self.logger.info(
            f"Config key '{key}' not found in section '{section}' for deletion."
        )
        return False

    def get_app_data_path(self, relative_path: str = "") -> Path:
        """Constructs and ensures existence of paths relative to the ACI data directory."""
        base_data_dir = (
            Path.home()
            / ".local"
            / "share"
            / self.DEFAULT_CONFIG_SUBDIR_IN_OS_CONFIG_DIR
        )
        full_path = (base_data_dir / relative_path).resolve()

        dir_to_create = (
            full_path.parent
            if not relative_path.endswith(("/", "\\")) and "." in full_path.name
            else full_path
        )

        try:
            dir_to_create.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            self.logger.error(
                f"Failed to create data directory {dir_to_create}: {e}", exc_info=True
            )
            raise ConfigPersistenceError(
                f"Failed to create data directory {dir_to_create}", original_exception=e
            )
        return full_path

    def get_app_config_path(self, relative_path: str = "") -> Path:
        """Constructs and ensures existence of paths relative to the ACI config directory."""
        base_config_dir = (
            Path.home() / ".config" / self.DEFAULT_CONFIG_SUBDIR_IN_OS_CONFIG_DIR
        )
        full_path = (base_config_dir / relative_path).resolve()

        dir_to_create = (
            full_path.parent
            if not relative_path.endswith(("/", "\\")) and "." in full_path.name
            else full_path
        )

        try:
            dir_to_create.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            self.logger.error(
                f"Failed to create config directory {dir_to_create}: {e}", exc_info=True
            )
            raise ConfigPersistenceError(
                f"Failed to create config directory {dir_to_create}",
                original_exception=e,
            )
        return full_path
        return full_path
