(Begin SDSS for ACLS v2.0 MVP: ACI Configuration & Local State Service - Apex Approved & Architect Signed-Off)
Markdown

# Self-Deconstructing Specification Script (SDSS)
## Module: ACLS v2.0 MVP (ACI Configuration & Local State Service)
## ACI Version: 2.0
## Author: Lily AI (DOSAB v2.2 - Full Workflow Active)
## Date: June 2, 2025
## Apex AI Review Confidence: 9.95/10
## Architect Sign-Off: Expedited Protocol (This SDSS is for VS Code Agent Implementation)

### **ACI_VSCODE_AGENT_GENESIS_PROTOCOL_REMINDER:**
// AGENT_ACTION: Ensure you are primed with and strictly adhering to the `ACI_VSCODE_AGENT_GENESIS_PROTOCOL.md` v1.1 for all code generation.
// AGENT_ACTION: All Python code must be fully type-hinted (Python 3.9+), follow PEP 8, include comprehensive Google Style docstrings.
// AGENT_ACTION: Implement ALL specified logic, functions, classes, and error handling. ABSOLUTELY NO placeholders, stubs, or mocked-up logic where implementation is specified.
// AGENT_ACTION: Create all specified files and directory structures precisely.
// AGENT_ACTION: List all new non-standard Python library dependencies at the end of `aci_v2/acls_mvp/service.py` for this module.

---

## 1. Module Overview & Purpose (ACLS MVP)

ACLS v2.0 MVP is a foundational backend service within the Architect's Command Interface (ACI) v2.0. Its **sole responsibilities for this MVP** are:
1.  **Secure Management of Sensitive Secrets:** Specifically, an extensible system for storing and retrieving secrets like API tokens (e.g., the GitHub Personal Access Token (PAT) required by EESRS v2.0), prioritizing OS keychain integration with a robust encrypted-INI file fallback.
2.  **General Application Configuration Management:** Handling ACI's non-sensitive operational settings (e.g., file paths, UI preferences, logging levels) via a local INI file.
3.  **Centralized Logging Facility:** Providing a robust and configurable logging service for all ACI modules, with output to both console and a persistent, rotating log file.

ACLS must be one of the first services initialized by the ACI Core Orchestrator.

## 2. File Structure for ACLS MVP

// AGENT_ACTION: You are operating within an `aci_v2/` Python package root, which is inside the `aci_v2_command_center/` project root (as scaffolded by the "Overall Project Structure" SDSS).
// AGENT_ACTION: Ensure the sub-package directory `aci_v2/acls_mvp/` exists (it should have been created by the scaffolding SDSS).
// AGENT_ACTION: Create an empty `aci_v2/acls_mvp/__init__.py` file if it wasn't fully populated by scaffolding.
// AGENT_ACTION: Create/overwrite the file `aci_v2/acls_mvp/exceptions.py`.
// AGENT_ACTION: Create/overwrite the file `aci_v2/acls_mvp/config_manager.py`.
// AGENT_ACTION: Create/overwrite the file `aci_v2/acls_mvp/secure_store.py`.
// AGENT_ACTION: Create/overwrite the file `aci_v2/acls_mvp/logging_manager.py`.
// AGENT_ACTION: Create/overwrite the file `aci_v2/acls_mvp/service.py`.
// AGENT_ACTION: After creating these files (if they didn't exist) or preparing to populate them, state: "ACLS MVP file structure prepared. Ready to populate exceptions.py." Then proceed to the next `AGENT_ACTION` block without waiting for Architect input.

---
## 3. Custom Exceptions (`aci_v2/acls_mvp/exceptions.py`)

// AGENT_ACTION: Populate `aci_v2/acls_mvp/exceptions.py` with the following content. Ensure correct inheritance and comprehensive docstrings as specified.

# In aci_v2/acls_mvp/exceptions.py
# Date: June 2, 2025
# Author: Lily AI for The Architect (ACI v2.0 Project)

from typing import Dict, Optional, Any
from aci_v2.common_exceptions import ACIError # Assumes ACIError is in aci_v2/common_exceptions.py

class ACLSError(ACIError):
    """Base exception for all ACLS module related errors."""
    # __init__ and __str__ are inherited from ACIError, which should be defined as:
    # class ACIError(Exception):
    #     def __init__(self, message: str, details: Optional[Dict[str, Any]] = None, original_exception: Optional[Exception] = None):
    #         super().__init__(message)
    #         self.message = message
    #         self.details = details or {}
    #         self.original_exception = original_exception
    #     def __str__(self) -> str:
    #         if self.details: return f"{self.message} (Details: {self.details})"
    #         if self.original_exception: return f"{self.message} (Original: {type(self.original_exception).__name__}: {str(self.original_exception)})"
    #         return self.message
    pass # Assuming ACIError provides the rich init and str.

class ConfigPersistenceError(ACLSError):
    """Raised for errors specifically related to saving or loading INI configuration files."""
    pass

class SecureStoreError(ACLSError):
    """Base exception for errors related to the SecureTokenManagerMVP."""
    pass

class KeychainError(SecureStoreError):
    """Raised for specific errors interacting with the OS keychain via the 'keyring' library."""
    pass

class EncryptionError(SecureStoreError):
    """Raised for errors during fallback encryption/decryption of secrets."""
    pass

class PassphraseRequiredError(SecureStoreError):
    """Raised when a master passphrase is required for a fallback secure store operation but not provided by the caller."""
    pass

class LogSetupError(ACLSError):
    """Raised when ACLS fails to set up logging handlers."""
    pass

class ConfigItemNotFoundError(ACLSError):
    """Raised when a specific configuration item is not found by ConfigManagerMVP and no fallback is suitable."""
    pass

// AGENT_ACTION: Confirm aci_v2/acls_mvp/exceptions.py implementation complete. State this, then proceed to the next AGENT_ACTION block for config_manager.py without waiting for Architect input.
4. ConfigManagerMVP (aci_v2/acls_mvp/config_manager.py)

// AGENT_ACTION: Populate aci_v2/acls_mvp/config_manager.py with the ConfigManagerMVP class.
// AGENT_ACTION: Implement all methods fully, with type hints, Google Style docstrings, and specified error handling. Import configparser, Path from pathlib, logging, typing.Any, Optional, Dict, Union. Import ConfigPersistenceError, ConfigItemNotFoundError from .exceptions.
Python

# In aci_v2/acls_mvp/config_manager.py
# Date: June 2, 2025
# Author: Lily AI for The Architect (ACI v2.0 Project)

import configparser
from pathlib import Path
import logging
from typing import Any, Optional, Dict, Union
import datetime # For backup file naming

from .exceptions import ConfigPersistenceError, ConfigItemNotFoundError

class ConfigManagerMVP:
    """
    Manages ACI's general configuration settings via a local INI file for the MVP.
    Handles loading, creating default configurations, getting, and setting values.
    """
    DEFAULT_CONFIG_FILENAME: str = "aci_mvp_config.ini"
    DEFAULT_CONFIG_SUBDIR_IN_OS_CONFIG_DIR: str = "aci_v2_mvp"

    def __init__(self, config_file_path_override: Optional[Union[str, Path]] = None, bootstrap_logger: Optional[logging.Logger] = None) -> None:
        """
        Initializes ConfigManagerMVP with the specified config file path.
        If no path is provided, it constructs a default path in the user's config directory.
        Loads the configuration or creates a default one if the file doesn't exist.

        Args:
            config_file_path_override (Optional[Union[str, Path]]): Absolute path to override the default configuration INI file.
            bootstrap_logger (Optional[logging.Logger]): A logger instance for initialization messages.
                                                        If None, a default logger for this class will be used.
        """
        self.logger = bootstrap_logger if bootstrap_logger else logging.getLogger(f"ACI.ACLS.{self.__class__.__name__}")

        if config_file_path_override:
            self.config_file_path: Path = Path(config_file_path_override).expanduser().resolve()
        else:
            # Default path: ~/.config/aci_v2_mvp/aci_mvp_config.ini
            self.config_file_path: Path = Path.home() / ".config" / self.DEFAULT_CONFIG_SUBDIR_IN_OS_CONFIG_DIR / self.DEFAULT_CONFIG_FILENAME

        self.config: configparser.ConfigParser = configparser.ConfigParser(interpolation=None) # Disable % interpolation
        self.logger.info(f"ConfigManagerMVP targeting INI file: '{self.config_file_path}'")
        self._ensure_config_dir_exists()
        self._load_or_create_config()

    def _ensure_config_dir_exists(self) -> None:
        """Ensures the directory for the configuration file exists."""
        try:
            self.config_file_path.parent.mkdir(parents=True, exist_ok=True)
            self.logger.debug(f"Ensured config directory exists: '{self.config_file_path.parent}'")
        except OSError as e:
            self.logger.error(f"Failed to create config directory '{self.config_file_path.parent}': {e}", exc_info=True)
            raise ConfigPersistenceError(f"Failed to create config directory '{self.config_file_path.parent}'", original_exception=e)

    def _get_default_config_structure(self) -> configparser.ConfigParser:
        """
        Returns a ConfigParser object populated with default sections and keys for ACI MVP.
        This defines the initial structure if no config file exists.
        """
        config = configparser.ConfigParser(interpolation=None)

        # Default paths should resolve ~ correctly and be strings for configparser
        default_user_cache_dir = Path.home() / ".cache" / self.DEFAULT_CONFIG_SUBDIR_IN_OS_CONFIG_DIR
        default_user_data_share_dir = Path.home() / ".local" / "share" / self.DEFAULT_CONFIG_SUBDIR_IN_OS_CONFIG_DIR

        config["General"] = {
            "aci_version": "2.0-MVP",
            "default_lily_persona_id": "proto_lily"
            # This key might be used by ICGS/LISMS to know which persona to load by default.
        }
        config["ACLS_MVP_Logging"] = {
            "console_log_level": "INFO",
            "file_log_level": "DEBUG",
            "log_file_path": str(default_user_data_share_dir / "logs" / "aci_mvp.log"),
            "log_file_max_bytes": str(10 * 1024 * 1024), # 10MB
            "log_file_backup_count": str(5)
        }
        config["ACLS_MVP_SecureStore"] = { # For SecureTokenManagerMVP fallback
            "fallback_pat_salt_for_ACI_MVP_GITHUB_PAT": "", # Salt will be auto-generated if fallback is used
            # Actual encrypted secrets are written by SecureTokenManagerMVP
        }
        config["EESRS_MVP_GitHub"] = { # For EESRS to know where the Architect's Master Repo is
             "repository_url": "", # CRITICAL: Architect MUST set this via ACI TUI settings.
             "default_branch": "main",
             "local_clone_path": str(default_user_cache_dir / "architect_master_repository_clone") # Path for EESRS to manage local clone for RAG (post-MVP) or direct file reads
        }
        config["LEMS_MVP_Primary"] = { # Default for the single Ollama endpoint in MVP
            "config_id": "primary_ollama_mvp", # Fixed ID
            "display_name": "Ollama Local (Default)",
            "provider_type": "ollama",
            "base_url": "http://localhost:11434",
            "model_name": "mistral:latest", # Architect can change this via ACI TUI
            "supports_system_prompt_directly": "True",
            "timeout_seconds": "120"
            # api_key_id is not applicable for this default Ollama config
        }
        self.logger.debug("Generated default configuration structure.")
        return config

    def _load_or_create_config(self) -> None:
        """
        Loads config from `self.config_file_path`.
        If the file doesn't exist or is invalid, it creates/overwrites with default structure.
        Raises ConfigPersistenceError on unrecoverable IOErrors during backup or initial save.
        """
        self._ensure_config_dir_exists() # Ensure directory is there
        if self.config_file_path.exists() and self.config_file_path.is_file():
            try:
                self.config.read(self.config_file_path, encoding='utf-8')
                self.logger.info(f"Configuration loaded successfully from '{self.config_file_path}'.")
                # Optional: Add validation here to ensure essential sections/keys exist from default,
                # and merge defaults for missing ones if a partial config is found.
                # For MVP, a full overwrite on corruption is simpler.
            except configparser.Error as e:
                self.logger.warning(f"Existing config file '{self.config_file_path}' is corrupt or malformed. Error: {e}. Attempting to back it up and create a new default config.", exc_info=True)
                try:
                    timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
                    backup_path = self.config_file_path.with_suffix(f".corrupt.{timestamp}")
                    self.config_file_path.rename(backup_path)
                    self.logger.info(f"Corrupt config file backed up to '{backup_path}'.")
                except OSError as backup_e:
                    self.logger.error(f"Could not back up corrupt config file '{self.config_file_path}': {backup_e}", exc_info=True)
                    # Proceed to create new default, but this is a more severe warning.

                self.config = self._get_default_config_structure()
                self._save_config() # This will raise ConfigPersistenceError if it fails
                self.logger.info(f"New default configuration file created at '{self.config_file_path}'.")
        else:
            self.logger.info(f"Config file not found at '{self.config_file_path}'. Creating with default values.")
            self.config = self._get_default_config_structure()
            self._save_config() # This will raise ConfigPersistenceError if it fails

    def _save_config(self) -> None:
        """Saves the current `self.config` object to `self.config_file_path` with UTF-8 encoding."""
        self._ensure_config_dir_exists()
        try:
            with self.config_file_path.open("w", encoding="utf-8") as config_file:
                self.config.write(config_file)
            self.logger.debug(f"Configuration saved successfully to '{self.config_file_path}'.")
        except IOError as e:
            self.logger.error(f"Failed to save configuration to '{self.config_file_path}': {e}", exc_info=True)
            raise ConfigPersistenceError(f"Failed to save configuration to '{self.config_file_path}'", original_exception=e)

    def get_config_value(self, section: str, key: str, fallback: Any = None, value_type: type = str) -> Any:
        """
        Retrieves a configuration value, converting to `value_type`.
        Returns `fallback` if section/key not found or if conversion fails.
        Logs warnings on missing keys/sections or conversion errors.
        """
        if not self.config.has_section(section):
            self.logger.debug(f"Section '{section}' not found in config. Returning fallback for key '{key}'.")
            return fallback
        if not self.config.has_option(section, key):
            self.logger.debug(f"Key '{key}' not found in section '{section}'. Returning fallback.")
            return fallback

        try:
            if value_type == bool: return self.config.getboolean(section, key) # Fallback not used by getboolean by default
            if value_type == int: return self.config.getint(section, key)
            if value_type == float: return self.config.getfloat(section, key)
            # For str or Any other type, get as string
            return self.config.get(section, key)
        except ValueError as e: # Handles conversion errors for getint/float/boolean
            self.logger.warning(f"ValueError converting config: [{section}]{key} to {value_type.__name__}. Using fallback. Error: {e}", exc_info=True)
            return fallback
        except Exception as e_unexpected: # Should not happen if has_option is true
            self.logger.error(f"Unexpected error getting config: [{section}]{key}. Using fallback. Error: {e_unexpected}", exc_info=True)
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
        current_value = self.config.get(section, key, fallback=object()) # Use a unique object as fallback to detect if key exists

        if current_value is object() or current_value != str_value: # Only save if key new or value changed
            self.config[section][key] = str_value
            self.logger.info(f"Set config: [{section}]{key} = '{str_value}' (actual value type: {type(value).__name__})")
            self._save_config() # Raises ConfigPersistenceError on failure
        else:
            self.logger.debug(f"Config: [{section}]{key} already set to '{str_value}'. No change made.")


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
                self._save_config() # Raises ConfigPersistenceError on failure
                self.logger.info(f"Config key '{key}' removed successfully from section '{section}'.")
                return True
            else:
                # This state (has_option true, but remove_option false) should be rare for configparser
                self.logger.warning(f"Config key '{key}' in section '{section}' reported as present but remove_option failed internally.")
                return False
        self.logger.info(f"Config key '{key}' not found in section '{section}' for deletion.")
        return False

    def get_app_data_path(self, relative_path: str = "") -> Path:
        """Constructs and ensures existence of paths relative to the ACI data directory."""
        base_data_dir = Path.home() / ".local" / "share" / self.DEFAULT_CONFIG_SUBDIR_IN_OS_CONFIG_DIR
        full_path = (base_data_dir / relative_path).resolve()

        # If relative_path is a filename, create its parent. If relative_path is a dir, create it.
        dir_to_create = full_path.parent if not relative_path.endswith(('/', '\\')) and '.' in full_path.name else full_path

        try:
            dir_to_create.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            self.logger.error(f"Failed to create data directory {dir_to_create}: {e}", exc_info=True)
            raise ConfigPersistenceError(f"Failed to create data directory {dir_to_create}", original_exception=e)
        return full_path

    def get_app_config_path(self, relative_path: str = "") -> Path:
        """Constructs and ensures existence of paths relative to the ACI config directory."""
        base_config_dir = Path.home() / ".config" / self.DEFAULT_CONFIG_SUBDIR_IN_OS_CONFIG_DIR
        full_path = (base_config_dir / relative_path).resolve()

        dir_to_create = full_path.parent if not relative_path.endswith(('/', '\\')) and '.' in full_path.name else full_path

        try:
            dir_to_create.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            self.logger.error(f"Failed to create config directory {dir_to_create}: {e}", exc_info=True)
            raise ConfigPersistenceError(f"Failed to create config directory {dir_to_create}", original_exception=e)
        return full_path

// AGENT_ACTION: Confirm aci_v2/acls_mvp/acls_config.py implementation complete. State this, then proceed to the next AGENT_ACTION block for secure_store.py without waiting for Architect input.
5. SecureTokenManagerMVP (aci_v2/acls_mvp/secure_store.py)

// AGENT_ACTION: Populate aci_v2/acls_mvp/secure_store.py with the SecureTokenManagerMVP class.
// AGENT_ACTION: Implement all methods fully, with type hints, Google Style docstrings, and specified error handling.
// AGENT_ACTION: Import keyring, base64, os (for os.urandom), logging, Fernet from cryptography.fernet, PBKDF2HMAC from cryptography.hazmat.primitives.kdf.pbkdf2, hashes from cryptography.hazmat.primitives, default_backend from cryptography.hazmat.backends, Optional, Any from typing.
// AGENT_ACTION: Import ConfigManagerMVP from .config_manager. Import custom exceptions from .exceptions.
Python

# In aci_v2/acls_mvp/secure_store.py
# Date: June 2, 2025
# Author: Lily AI for The Architect (ACI v2.0 Project)

import keyring
import base64
import os
import logging
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from typing import Optional, Any

from .config_manager import ConfigManagerMVP # Assuming ConfigManagerMVP is the class name
from .exceptions import SecureStoreError, KeychainError, EncryptionError, PassphraseRequiredError

class SecureTokenManagerMVP:
    """
    Manages secure storage and retrieval of sensitive tokens (e.g., API keys, PATs) for ACI MVP.
    Prioritizes OS keychain and uses an encrypted INI file section as a fallback.
    """
    KEYRING_SERVICE_NAME: str = "ACI_V2_MVP_SECRETS" # Service name for keyring
    # Config section and key prefixes for fallback storage, managed by ConfigManagerMVP
    CONFIG_SECTION_FALLBACK: str = "ACLS_MVP_SecureStore"
    CONFIG_KEY_SALT_PREFIX: str = "fallback_salt_for_"
    CONFIG_KEY_ENCRYPTED_PREFIX: str = "encrypted_secret_"
    KEY_DERIVATION_ITERATIONS: int = 480000 # OWASP recommended minimum (as of recent knowledge)

    def __init__(self, config_manager: ConfigManagerMVP, bootstrap_logger: Optional[logging.Logger] = None):
        """
        Initializes SecureTokenManagerMVP with a ConfigManagerMVP instance.

        Args:
            config_manager (ConfigManagerMVP): Instance of ConfigManagerMVP to manage fallback storage.
            bootstrap_logger (Optional[logging.Logger]): Logger instance.
        """
        if config_manager is None:
            # This should be caught by ACIServiceMVP during instantiation.
            temp_logger = bootstrap_logger if bootstrap_logger else logging.getLogger(f"ACI.ACLS.Bootstrap.{self.__class__.__name__}")
            temp_logger.critical("ConfigManagerMVP instance cannot be None for SecureTokenManagerMVP.")
            raise ValueError("ConfigManagerMVP instance cannot be None.")
        self.config_manager: ConfigManagerMVP = config_manager
        self.logger = bootstrap_logger if bootstrap_logger else logging.getLogger(f"ACI.ACLS.{self.__class__.__name__}")
        self.logger.debug("SecureTokenManagerMVP initialized.")


    def _derive_key_from_passphrase(self, passphrase: str, salt: bytes) -> bytes:
        """Derives a Fernet encryption key from a passphrase and salt using PBKDF2HMAC-SHA256."""
        if not passphrase: # Should be caught by UI before calling set_secure_secret
            raise ValueError("Passphrase cannot be empty for key derivation.")
        if not salt: # Should be generated if not existing
             raise ValueError("Salt cannot be empty for key derivation.")

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32, # Fernet key size is 32 bytes (urlsafe_b64encoded)
            salt=salt,
            iterations=self.KEY_DERIVATION_ITERATIONS,
            backend=default_backend()
        )
        derived_key = kdf.derive(passphrase.encode('utf-8'))
        return base64.urlsafe_b64encode(derived_key)

    def set_secure_secret(self, key_identifier: str, secret_value: str, master_passphrase_for_fallback: Optional[str] = None) -> bool:
        """
        Stores a secret securely, prioritizing OS keychain, then encrypted INI fallback.

        Args:
            key_identifier (str): Unique identifier for the secret (e.g., "ACI_MVP_GITHUB_PAT", "OPENAI_API_KEY"). Used as 'username' in keyring.
            secret_value (str): The actual secret to store.
            master_passphrase_for_fallback (Optional[str]): Master passphrase for fallback encryption if keychain fails.
                                                            If keychain fails and this is None/empty, storage fails.
        Returns:
            bool: True if successfully stored in either keychain or fallback, False otherwise.
        Raises:
            SecureStoreError: For underlying storage issues not gracefully handled by returning False.
            EncryptionError: If fallback encryption specifically fails.
        """
        if not isinstance(key_identifier, str) or not key_identifier.strip():
            raise ValueError("key_identifier must be a non-empty string.")
        if not isinstance(secret_value, str): # Secrets are typically strings
            raise ValueError("secret_value must be a string.")

        self.logger.info(f"Attempting to store secure secret for key_identifier: '{key_identifier}' (Value NOT logged).")
        try:
            keyring.set_password(self.KEYRING_SERVICE_NAME, key_identifier, secret_value)
            self.logger.info(f"Secret for '{key_identifier}' stored successfully in OS keychain.")
            # If keychain works, ensure any old fallback data for this key is cleared
            self._clear_fallback_data(key_identifier)
            return True
        except keyring.errors.NoKeyringError:
            self.logger.warning(f"No OS keychain backend found for '{key_identifier}'. Attempting encrypted INI fallback.")
        except keyring.errors.KeyringError as e_keyring: # Other keychain errors
            self.logger.warning(f"OS Keychain failed for '{key_identifier}'. Error: {e_keyring}. Attempting encrypted INI fallback.", exc_info=True)

        # Fallback to encrypted INI if keychain failed
        if master_passphrase_for_fallback and master_passphrase_for_fallback.strip():
            try:
                salt_config_key = f"{self.CONFIG_KEY_SALT_PREFIX}{key_identifier}"
                encrypted_config_key = f"{self.CONFIG_KEY_ENCRYPTED_PREFIX}{key_identifier}"

                salt_str = self.config_manager.get_config_value(self.CONFIG_SECTION_FALLBACK, salt_config_key, fallback=None, value_type=str)
                salt_bytes: bytes
                if not salt_str:
                    salt_bytes = os.urandom(16) # Generate cryptographically secure salt
                    salt_str_to_save = base64.urlsafe_b64encode(salt_bytes).decode('utf-8')
                    self.config_manager.set_config_value(self.CONFIG_SECTION_FALLBACK, salt_config_key, salt_str_to_save)
                    self.logger.info(f"Generated and stored new salt for fallback key '{key_identifier}'.")
                else:
                    salt_bytes = base64.urlsafe_b64decode(salt_str.encode('utf-8'))

                fernet_encryption_key = self._derive_key_from_passphrase(master_passphrase_for_fallback, salt_bytes)
                f = Fernet(fernet_encryption_key)
                encrypted_secret = f.encrypt(secret_value.encode('utf-8')).decode('utf-8')

                self.config_manager.set_config_value(self.CONFIG_SECTION_FALLBACK, encrypted_config_key, encrypted_secret)
                self.logger.info(f"Secret for '{key_identifier}' stored successfully using encrypted INI fallback.")
                return True
            except Exception as e_fallback: # Catch broad errors during complex fallback
                self.logger.error(f"Fallback encryption failed for '{key_identifier}': {e_fallback}", exc_info=True)
                raise EncryptionError(f"Fallback encryption failed for '{key_identifier}'", original_exception=e_fallback)
        else: # Keychain failed AND no/empty master_passphrase provided
            self.logger.error(f"Keychain failed for '{key_identifier}' and fallback requires a valid master passphrase. Secret NOT stored.")
            # This specific scenario should raise PassphraseRequiredError as per SDSS
            raise PassphraseRequiredError(f"Keychain unavailable/failed for '{key_identifier}', and master passphrase for fallback was not provided or was empty.")

        # Fallthrough case if something unexpected happens (should be caught by exceptions)
        return False # Should not be reached if exceptions are raised correctly

    def get_secure_secret(self, key_identifier: str, master_passphrase_for_fallback: Optional[str] = None) -> Optional[str]:
        # // AGENT_ACTION: Implement get_secure_secret as per SDSS for ACLS v2.0 (SecureTokenManager section, generic version).
        # // Prioritize keychain, then fallback. Handle errors, log appropriately.
        # // Raise PassphraseRequiredError if fallback data exists but passphrase missing/empty.
        # // Raise EncryptionError if decryption fails.
        pass # AGENT_ACTION_PLACEHOLDER

    def delete_secure_secret(self, key_identifier: str) -> bool:
        # // AGENT_ACTION: Implement delete_secure_secret as per SDSS for ACLS v2.0 (SecureTokenManager section, generic version).
        # // Delete from keychain (ignore if not found error).
        # // Delete fallback salt and encrypted secret from ConfigManager using `delete_config_key`.
        # // Return True if deletion was successful from at least one store or if secret wasn't found.
        pass # AGENT_ACTION_PLACEHOLDER

    def _clear_fallback_data(self, key_identifier: str) -> None:
        """Helper to remove fallback data if keychain operation is successful."""
        # // AGENT_ACTION: Implement _clear_fallback_data.
        # // Logic:
        # // 1. salt_config_key = f"{self.CONFIG_KEY_SALT_PREFIX}{key_identifier}"
        # // 2. encrypted_config_key = f"{self.CONFIG_KEY_ENCRYPTED_PREFIX}{key_identifier}"
        # // 3. self.config_manager.delete_config_key(self.CONFIG_SECTION_FALLBACK, encrypted_config_key)
        # // 4. self.config_manager.delete_config_key(self.CONFIG_SECTION_FALLBACK, salt_config_key)
        # // 5. Log: "Cleared any existing fallback data for key_identifier '{key_identifier}' due to successful keychain operation."
        pass # AGENT_ACTION_PLACEHOLDER

// AGENT_ACTION: Confirm aci_v2/acls_mvp/acls_secure_store.py implementation complete. State this, then proceed to the next AGENT_ACTION block for logging_manager.py without waiting for Architect input.
6. LoggingManagerMVP (aci_v2/acls_mvp/acls_logging.py)

// AGENT_ACTION: Populate aci_v2/acls_mvp/acls_logging.py with the LoggingManagerMVP class.
// AGENT_ACTION: Implement all methods fully, type hints, Google Style docstrings.
// AGENT_ACTION: Import logging, sys, RotatingFileHandler from logging.handlers, Path from pathlib, Optional, Any.
// AGENT_ACTION: Import ConfigManagerMVP from .config_manager. Import LogSetupError from .exceptions.
Python

# In aci_v2/acls_mvp/acls_logging.py
# Date: June 2, 2025
# Author: Lily AI for The Architect (ACI v2.0 Project)

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional, Any

from .config_manager import ConfigManagerMVP # Assuming ConfigManagerMVP is the class name
from .exceptions import LogSetupError

class LoggingManagerMVP:
    """
    Manages centralized Python logging setup for ACI MVP modules based on configuration
    from ConfigManagerMVP.
    """
    ROOT_LOGGER_NAME = "ACI_MVP" # All ACI loggers will be children of this

    def __init__(self, bootstrap_logger: Optional[logging.Logger] = None):
        """
        Initializes the LoggingManagerMVP.

        Args:
            bootstrap_logger (Optional[logging.Logger]): An optional logger for its own init messages.
        """
        self.logger = bootstrap_logger if bootstrap_logger else logging.getLogger(f"ACI.ACLS.{self.__class__.__name__}") # Fallback for its own logging
        self.is_setup_called: bool = False
        self.logger.debug("LoggingManagerMVP initialized.")

    def setup_logging(self, config_manager: ConfigManagerMVP) -> None:
        """
        Sets up the ACI root logger with console and rotating file handlers
        based on settings read from the provided ConfigManagerMVP instance.
        This method should ideally be called only once by ACIServiceMVP during ACI startup.

        Args:
            config_manager (ConfigManagerMVP): An initialized instance of ConfigManagerMVP.

        Raises:
            LogSetupError: If logging setup encounters an unrecoverable error.
            ConfigItemNotFoundError: If essential logging configuration keys are missing and have no fallback.
        """
        if self.is_setup_called:
            self.logger.warning("setup_logging called more than once. Logging system already configured. Ignoring subsequent calls.")
            return

        self.logger.info("Attempting to set up ACI logging system...")
        try:
            # Retrieve logging configuration using ConfigManagerMVP
            # Section name in INI file is [ACLS_MVP_Logging] as defined in ConfigManagerMVP defaults
            log_config_section = "ACLS_MVP_Logging"

            console_level_str = config_manager.get_config_value(log_config_section, "console_log_level", fallback="INFO", value_type=str)
            file_level_str = config_manager.get_config_value(log_config_section, "file_log_level", fallback="DEBUG", value_type=str)

            default_log_path = str(Path.home() / ".local" / "share" / ConfigManagerMVP.DEFAULT_CONFIG_SUBDIR / "logs" / "aci_mvp.log")
            log_file_path_str = config_manager.get_config_value(log_config_section, "log_file_path", fallback=default_log_path, value_type=str)

            log_file_max_bytes = config_manager.get_config_value(log_config_section, "log_file_max_bytes", fallback=10485760, value_type=int) # 10MB
            log_file_backup_count = config_manager.get_config_value(log_config_section, "log_file_backup_count", fallback=5, value_type=int)

            log_file_path = Path(log_file_path_str).expanduser().resolve()

            # Get or create the ACI root logger
            aci_root_logger = logging.getLogger(self.ROOT_LOGGER_NAME)
            # Set its level to the most verbose of its handlers to allow all messages through.
            # Handlers will then filter based on their own levels.
            aci_root_logger.setLevel(logging.DEBUG)

            # Clear existing handlers from ACI root logger to prevent duplication if re-setup (though is_setup_called should prevent this)
            if aci_root_logger.hasHandlers():
                self.logger.debug(f"Clearing existing handlers from logger '{self.ROOT_LOGGER_NAME}' before setup.")
                aci_root_logger.handlers.clear()

            # Common Formatter
            detailed_formatter = logging.Formatter(
                '%(asctime)s [%(levelname)-8s] %(name)-35s - %(message)s (%(filename)s:%(lineno)d [%(process)d])'
            )

            # Console Handler
            if console_level_str.upper() != "NONE":
                console_handler = logging.StreamHandler(sys.stdout) # Log to stdout for TUI compatibility
                try:
                    console_handler.setLevel(console_level_str.upper())
                except ValueError:
                    self.logger.warning(f"Invalid console_log_level '{console_level_str}'. Defaulting to INFO.")
                    console_handler.setLevel("INFO")
                console_handler.setFormatter(detailed_formatter)
                aci_root_logger.addHandler(console_handler)
                self.logger.info(f"Console logging for '{self.ROOT_LOGGER_NAME}' configured at level {console_handler.level}.")
            else:
                self.logger.info(f"Console logging for '{self.ROOT_LOGGER_NAME}' is disabled via configuration.")

            # Rotating File Handler
            if file_level_str.upper() != "NONE":
                try:
                    log_file_path.parent.mkdir(parents=True, exist_ok=True)
                    file_handler = RotatingFileHandler(
                        filename=log_file_path,
                        maxBytes=log_file_max_bytes,
                        backupCount=log_file_backup_count,
                        encoding='utf-8'
                    )
                    try:
                        file_handler.setLevel(file_level_str.upper())
                    except ValueError:
                        self.logger.warning(f"Invalid file_log_level '{file_level_str}'. Defaulting to DEBUG for file.")
                        file_handler.setLevel("DEBUG")
                    file_handler.setFormatter(detailed_formatter)
                    aci_root_logger.addHandler(file_handler)
                    self.logger.info(f"File logging for '{self.ROOT_LOGGER_NAME}' configured at level {file_handler.level} to '{log_file_path}'.")
                except OSError as e:
                    self.logger.error(f"Failed to create log directory or file for '{log_file_path}': {e}", exc_info=True)
                    # Continue without file logging if it fails, console might still work.
                except Exception as e_fh: # Catch any other file handler setup error
                    self.logger.error(f"Unexpected error setting up file logging for '{log_file_path}': {e_fh}", exc_info=True)

            else:
                self.logger.info(f"File logging for '{self.ROOT_LOGGER_NAME}' is disabled via configuration.")

            self.is_setup_called = True
            aci_root_logger.info("ACI Logging system setup process complete.") # Logged via ACI root logger itself

        except ConfigItemNotFoundError as e_config: # If ConfigManager raises this for a critical log setting
            self.logger.error(f"Essential logging configuration missing: {e_config}", exc_info=True)
            raise LogSetupError(f"Essential logging configuration missing: {e_config}", original_exception=e_config)
        except Exception as e_setup: # Catch any other unexpected error during setup
            self.logger.error(f"Fatal error during logging setup: {e_setup}", exc_info=True)
            raise LogSetupError(f"Fatal error during ACI logging system setup: {e_setup}", original_exception=e_setup)

    def get_logger(self, name: str) -> logging.Logger:
        """
        Returns a Python logger instance, ensuring it's a child of the ACI root logger.
        Example: name = "LEMS_Service" -> logger name = "ACI_MVP.LEMS_Service"
        Args:
            name (str): The desired specific name for the logger (e.g., module name or class name).
        Returns:
            logging.Logger: The configured logger instance.
        """
        if not name.startswith(self.ROOT_LOGGER_NAME + "."):
            qualified_name = f"{self.ROOT_LOGGER_NAME}.{name}"
        else:
            qualified_name = name # Already qualified

        # Log using own bootstrap logger if setup hasn't been called, otherwise this is post-setup
        # self.logger.debug(f"Providing logger instance for '{qualified_name}'.")
        return logging.getLogger(qualified_name)

// AGENT_ACTION: Confirm aci_v2/acls_mvp/acls_logging.py implementation complete. State this, then proceed to the next AGENT_ACTION block for service.py without waiting for Architect input.
7. Main ACIServiceMVP Class (aci_v2/acls_mvp/service.py)

// AGENT_ACTION: Populate aci_v2/acls_mvp/service.py with the ACIServiceMVP class.
// AGENT_ACTION: Implement all methods fully, type hints, Google Style docstrings, error handling.
// AGENT_ACTION: Import logging, Path from pathlib, typing elements (Any, Optional, List, Dict, Literal).
// AGENT_ACTION: Import ConfigManagerMVP from .config_manager, SecureTokenManagerMVP from .secure_store, LoggingManagerMVP from .logging_manager.
// AGENT_ACTION: Import ACLSError and other relevant exceptions from .exceptions.
Python

# In aci_v2/acls_mvp/service.py
# Date: June 2, 2025
# Author: Lily AI for The Architect (ACI v2.0 Project)

import logging
from pathlib import Path
from typing import Any, Optional, List, Dict, Literal

from .config_manager import ConfigManagerMVP
from .secure_store import SecureTokenManagerMVP
from .logging_manager import LoggingManagerMVP
from .exceptions import ACLSError, ConfigPersistenceError, SecureStoreError, PassphraseRequiredError, ConfigItemNotFoundError # Import all used exceptions

class ACIServiceMVP:
    """
    ACI Configuration & Logging Service (ACLS) MVP.
    Aggregates ConfigManagerMVP, SecureTokenManagerMVP, and LoggingManagerMVP
    to provide a unified service interface for other ACI modules.
    """
    MODULE_NAME: str = "ACLS_MVP_Service"

    def __init__(self,
                 base_config_dir_override: Optional[Union[str, Path]] = None,
                 base_data_dir_override: Optional[Union[str, Path]] = None,
                 console_log_level_override: Optional[str] = "INFO") -> None: # Default console log level
        """
        Initializes all ACLS MVP sub-components (ConfigManager, SecureStore, LoggingManager).
        Sets up application-wide logging.

        Args:
            base_config_dir_override (Optional[Union[str, Path]]): Override for ACI config directory
                                                               (e.g., `~/.config/aci_v2_mvp`).
            base_data_dir_override (Optional[Union[str, Path]]): Override for ACI data directory
                                                             (e.g., `~/.local/share/aci_v2_mvp`).
            console_log_level_override (Optional[str]): Override for initial bootstrap console log level.
                                                        Valid: DEBUG, INFO, WARNING, ERROR, CRITICAL, NONE.
        Raises:
            ACLSError: If any critical sub-component fails to initialize.
        """
        # Bootstrap logger for the __init__ phase itself, before full logging is setup
        bootstrap_logger = logging.getLogger(f"ACI.Bootstrap.{self.MODULE_NAME}")
        initial_handler_present = bool(bootstrap_logger.handlers)
        if not initial_handler_present: # Minimal setup if no handlers exist from ACI Core Orchestrator
            _handler = logging.StreamHandler(sys.stdout) # Changed from sys.stderr to stdout
            _formatter = logging.Formatter('%(asctime)s [%(levelname)-8s] %(name)-30s - %(message)s')
            _handler.setFormatter(_formatter)
            bootstrap_logger.addHandler(_handler)
            bootstrap_logger.setLevel(console_log_level_override.upper() if console_log_level_override else "INFO")

        bootstrap_logger.info("ACIServiceMVP initialization started...")
        try:
            # Determine actual config_path for ConfigManagerMVP
            config_path = Path(base_config_dir_override or Path.home() / ".config" / ConfigManagerMVP.DEFAULT_CONFIG_SUBDIR_IN_OS_CONFIG_DIR)

            self.config_manager: ConfigManagerMVP = ConfigManagerMVP(
                config_file_path_override = config_path / ConfigManagerMVP.DEFAULT_CONFIG_FILENAME,
                bootstrap_logger = bootstrap_logger
            )
            bootstrap_logger.info("ConfigManagerMVP initialized.")

            self.secure_store: SecureTokenManagerMVP = SecureTokenManagerMVP(
                config_manager_instance = self.config_manager,
                bootstrap_logger = bootstrap_logger
            )
            bootstrap_logger.info("SecureTokenManagerMVP initialized.")

            self.logging_manager: LoggingManagerMVP = LoggingManagerMVP(bootstrap_logger = bootstrap_logger)
            self.logging_manager.setup_logging(config_manager = self.config_manager) # Setup ACI root logger and handlers
            bootstrap_logger.info("LoggingManagerMVP setup complete.")

            # Now use the fully configured ACI logger for this service
            self.logger = self.logging_manager.get_logger(f"ACI.{self.MODULE_NAME}")
            self.logger.info(f"ACLS Service MVP fully initialized and logging configured.",
                             extra={"details": {"config_file_used": str(self.config_manager.config_file_path)}})

        except Exception as e: # Catch any exception from sub-component initializations
            bootstrap_logger.critical(f"CRITICAL FAILURE during ACIServiceMVP initialization: {e}", exc_info=True)
            raise ACLSError(f"Failed to initialize one or more ACLS_ServiceMVP core components: {e}", original_exception=e)

    # --- Secure Secret Methods (Generic Interface) ---
    def get_secure_secret(self, key_identifier: str, master_passphrase_for_fallback: Optional[str] = None) -> Optional[str]:
        """
        Retrieves a generic named secure secret (e.g., API key, PAT) via SecureTokenManagerMVP.

        Args:
            key_identifier (str): The unique identifier for the secret.
            master_passphrase_for_fallback (Optional[str]): Passphrase for encrypted fallback if keychain fails.

        Returns:
            Optional[str]: The secret value if found, else None.

        Raises:
            SecureStoreError (and its children like PassphraseRequiredError, EncryptionError): If errors occur during retrieval.
        """
        self.logger.debug(f"ACLS_Service attempting to retrieve secure secret for key_identifier: '{key_identifier}' (Passphrase provided: {'Yes' if master_passphrase_for_fallback else 'No'}).")
        try:
            token = self.secure_store.get_secure_secret(key_identifier, master_passphrase_for_fallback)
            if token:
                self.logger.info(f"Secure secret for key_identifier '{key_identifier}' retrieved.")
            else:
                self.logger.info(f"Secure secret for key_identifier '{key_identifier}' not found.")
            return token
        except SecureStoreError as e: # Catch specific errors from secure_store and re-log with service context
            self.logger.error(f"SecureStoreError retrieving secret for '{key_identifier}': {e}", exc_info=True)
            raise # Re-raise the original specific exception
        except Exception as e_unhandled: # Catch any other unexpected error
            self.logger.critical(f"Unexpected error retrieving secret for '{key_identifier}': {e_unhandled}", exc_info=True)
            raise SecureStoreError(f"Unexpected error retrieving secret for '{key_identifier}'", original_exception=e_unhandled)


    def set_secure_secret(self, key_identifier: str, secret_value: str, master_passphrase_for_fallback: Optional[str] = None) -> bool:
        """
        Stores a generic named secure secret via SecureTokenManagerMVP.

        Args:
            key_identifier (str): The unique identifier for the secret.
            secret_value (str): The secret value to store.
            master_passphrase_for_fallback (Optional[str]): Passphrase for encrypted fallback if keychain fails.

        Returns:
            bool: True if storage was successful, False otherwise.

        Raises:
            SecureStoreError (and its children): If errors occur during storage.
        """
        self.logger.info(f"ACLS_Service attempting to store secure secret for key_identifier: '{key_identifier}'.")
        # DO NOT log secret_value
        try:
            success = self.secure_store.set_secure_secret(key_identifier, secret_value, master_passphrase_for_fallback)
            if success:
                self.logger.info(f"Secure secret for key_identifier '{key_identifier}' stored successfully.")
            else:
                # SecureTokenManagerMVP should raise specific errors if keychain fails AND no passphrase,
                # so this 'else' might only be hit for very specific unhandled keyring returns.
                self.logger.warning(f"Storage of secure secret for key_identifier '{key_identifier}' reported as unsuccessful by SecureTokenManagerMVP without raising an exception.")
            return success
        except SecureStoreError as e:
            self.logger.error(f"SecureStoreError storing secret for '{key_identifier}': {e}", exc_info=True)
            raise
        except Exception as e_unhandled:
            self.logger.critical(f"Unexpected error storing secret for '{key_identifier}': {e_unhandled}", exc_info=True)
            raise SecureStoreError(f"Unexpected error storing secret for '{key_identifier}'", original_exception=e_unhandled)

    def delete_secure_secret(self, key_identifier: str) -> bool:
        """Deletes a generic named secure secret via SecureTokenManagerMVP."""
        self.logger.info(f"ACLS_Service attempting to delete secure secret for key_identifier: '{key_identifier}'.")
        try:
            success = self.secure_store.delete_secure_secret(key_identifier)
            if success:
                self.logger.info(f"Secure secret for key_identifier '{key_identifier}' deleted successfully (or was not present in all stores).")
            else:
                # SecureTokenManagerMVP's delete usually returns True if deleted from at least one or not found.
                # This path might indicate an issue if it's expected to always return True on non-error.
                 self.logger.warning(f"Deletion of secure secret for key_identifier '{key_identifier}' reported as unsuccessful by SecureTokenManagerMVP without raising an exception.")
            return success
        except SecureStoreError as e:
            self.logger.error(f"SecureStoreError deleting secret for '{key_identifier}': {e}", exc_info=True)
            raise
        except Exception as e_unhandled:
            self.logger.critical(f"Unexpected error deleting secret for '{key_identifier}': {e_unhandled}", exc_info=True)
            raise SecureStoreError(f"Unexpected error deleting secret for '{key_identifier}'", original_exception=e_unhandled)

    # --- General Config Methods ---
    def get_config(self, section: str, key: str, fallback: Any = None, value_type: type = str) -> Any:
        """Delegates to ConfigManagerMVP to retrieve a general configuration value."""
        self.logger.debug(f"Getting config: [{section}]{key}")
        return self.config_manager.get_config_value(section, key, fallback=fallback, value_type=value_type)

    def set_config(self, section: str, key: str, value: Any) -> None:
        """Delegates to ConfigManagerMVP to set a general configuration value."""
        # Logging is handled by ConfigManagerMVP's set_config_value now
        self.config_manager.set_config_value(section, key, value)
        # self.logger.info(f"General config set via ACLS: [{section}]{key}", {"value_type": str(type(value))}) # Redundant if CM logs

    def delete_config(self, section: str, key: str) -> bool:
        """Delegates to ConfigManagerMVP to delete a general configuration key."""
        # Logging is handled by ConfigManagerMVP's delete_config_key now
        deleted = self.config_manager.delete_config_key(section, key)
        # if deleted:
        #     self.logger.info(f"General config deleted via ACLS: [{section}]{key}")
        # else:
        #     self.logger.info(f"General config not found for deletion via ACLS: [{section}]{key}")
        return deleted

    # --- Logging Method (for other modules to get their dedicated logger) ---
    def get_logger(self, name: str) -> logging.Logger:
        """Delegates to LoggingManagerMVP to provide a configured ACI logger."""
        return self.logging_manager.get_logger(name)

# AGENT_ACTION: Implement the `if __name__ == "__main__":` test block for `service_mvp.py`.
# It should:
# 1. `import os`, `import sys` (for path manipulation if needed for test config paths, and for stdout).
# 2. Instantiate `ACIServiceMVP` (potentially with test paths for config/data dirs, e.g., in a temp folder).
#    Wrap this in a try-except block to catch initialization errors.
# 3. Demonstrate setting and getting a general config value using `service.set_config()` and `service.get_config()`.
# 4. Demonstrate setting a secure secret (e.g., "TEST_ACI_API_KEY") using `service.set_secure_secret()`.
#    - For testing, the Architect will need to be prompted to provide a dummy master passphrase for the fallback mechanism if keychain is expected to fail in a non-interactive test environment. The test code should state this clearly.
#    - Print a message about where to check for the secret (keychain: service="ACI_V2_MVP_SECRETS", username="TEST_ACI_API_KEY"; or if fallback, state it used fallback).
# 5. Demonstrate getting that secure secret using `service.get_secure_secret()`. Print if retrieved or not (DO NOT print the secret value itself). This will again need the master passphrase if fallback was used.
# 6. Log a few messages at different levels (INFO, WARNING, ERROR) using `service.get_logger("ACI.TestMain").<level>()`.
# 7. (Optional advanced test) Demonstrate deleting the secure secret and a config value, then trying to get them again.
# Ensure all operations are wrapped in try-except blocks to catch and print ACLS custom exceptions gracefully.
# Example:
# ```python
# if __name__ == "__main__":
#     print("--- Testing ACIServiceMVP ---")
#     # It's often better to use a temporary directory for test config files
#     # For simplicity, this example uses default paths but warns user
#     print("WARNING: This test will use/create config files in your user directory.")
#     print("         (~/.config/aci_v2_mvp/ and ~/.local/share/aci_v2_mvp/)")
#     print("         Consider manual cleanup after test if these are not desired production paths yet.")
#
#     try:
#         # One way to allow Architect to override paths for testing:
#         # test_config_dir = os.environ.get("ACI_TEST_CONFIG_DIR")
#         # test_data_dir = os.environ.get("ACI_TEST_DATA_DIR")
#         # service = ACIServiceMVP(base_config_dir_override=test_config_dir, base_data_dir_override=test_data_dir)
#         service = ACIServiceMVP() # Uses default paths
#         print("\n[OK] ACIServiceMVP initialized successfully.")
#
#         # Test general config
#         print("\n--- Testing General Config ---")
#         service.set_config("TestSection", "TestKey", "TestValue123")
#         val = service.get_config("TestSection", "TestKey")
#         print(f"Get TestSection/TestKey: {val} (Expected: TestValue123)")
#         assert val == "TestValue123"
#         service.delete_config("TestSection", "TestKey")
#         val_after_delete = service.get_config("TestSection", "TestKey", fallback="NOT_FOUND")
#         print(f"Get TestSection/TestKey after delete: {val_after_delete} (Expected: NOT_FOUND)")
#         assert val_after_delete == "NOT_FOUND"
#         print("[OK] General Config R/W/D test passed.")
#
#         # Test Secure Store
#         print("\n--- Testing Secure Store (GitHub PAT / Generic Secret) ---")
#         test_key_id = "ACI_MVP_TEST_SECRET"
#         test_secret_value = "my_super_secret_test_value_12345"
#         # For non-interactive test, we can't easily get passphrase.
#         # This test will likely use keychain or fail gracefully if keychain not available and no passphrase.
#         # The real test for fallback requires interactive passphrase input.
#         print(f"Attempting to set secret for '{test_key_id}'. If keychain unavailable, this may fail or require a passphrase you can't provide here.")
#         print("For full fallback test, SecureTokenManagerMVP.set_secure_secret needs interactive passphrase input if keychain fails.")
#
#         # Simulate needing a passphrase for fallback if keychain is known to be problematic in test env
#         # In a real test script, one might mock keyring to force fallback.
#         # For this self-contained block, we rely on the existing logic.
#         # If Architect has a working `keyring` backend, this will use it.
#         # If not, `set_secure_secret` as defined in SDSS would raise PassphraseRequiredError if no passphrase given.
#         # To make this test runnable without interactive input for now, let's assume keychain works or skip fallback test.
#
#         # Simplified test - this will use keychain if available.
#         # Fallback path is harder to test non-interactively here.
#         passphrase_for_test = None # Set to a string to test fallback path if keyring is known to fail
#                                 # e.g. passphrase_for_test = "test_passphrase"
#                                 # BUT, prompting for this in a non-interactive test is an issue.
#                                 # So, for this __main__ block, we mostly test keychain path.
#
#         if service.set_secure_secret(test_key_id, test_secret_value, master_passphrase_for_fallback=passphrase_for_test):
#             print(f"Successfully called set_secure_secret for '{test_key_id}'. Check keychain or config if fallback used.")
#             retrieved_secret = service.get_secure_secret(test_key_id, master_passphrase_for_fallback=passphrase_for_test)
#             if retrieved_secret == test_secret_value:
#                 print(f"[OK] Secure secret for '{test_key_id}' SET and GET successfully.")
#             elif retrieved_secret is None and passphrase_for_test is None and service.secure_store.config_manager.get_config_value("ACLS_MVP_SecureStore", f"encrypted_secret_{test_key_id}"):
#                 print(f"[INFO] Secure secret for '{test_key_id}' likely stored in fallback, but passphrase needed to retrieve.")
#             else:
#                 print(f"[FAIL] Secure secret for '{test_key_id}' GET mismatch or failed. Retrieved: {retrieved_secret}")
#
#             if service.delete_secure_secret(test_key_id):
#                 print(f"[OK] Secure secret for '{test_key_id}' delete called successfully.")
#                 retrieved_after_delete = service.get_secure_secret(test_key_id, master_passphrase_for_fallback=passphrase_for_test)
#                 if retrieved_after_delete is None:
#                     print(f"[OK] Secure secret for '{test_key_id}' confirmed deleted or irretrievable.")
#                 else:
#                     print(f"[FAIL] Secure secret for '{test_key_id}' still retrievable after delete.")
#             else:
#                 print(f"[FAIL] Call to delete_secure_secret for '{test_key_id}' reported failure.")
#         else:
#             print(f"[FAIL] Failed to set_secure_secret for '{test_key_id}'. This might be due to keychain failure and no passphrase for fallback.")
#
#         # Test Logging
#         print("\n--- Testing Logging ---")
#         test_logger = service.get_logger("ACI.TestMainBlock")
#         test_logger.debug("This is a DEBUG message from ACLS test block.")
#         test_logger.info("This is an INFO message from ACLS test block.")
#         test_logger.warning("This is a WARNING message from ACLS test block.")
#         test_logger.error("This is an ERROR message from ACLS test block.")
#         test_logger.critical("This is a CRITICAL message from ACLS test block.", extra={"details": {"test_detail": 123}})
#         print("[OK] Logging test messages sent. Check console and configured log file.")
#         print(f"      Log file path (from config via service): {service.config_manager.get_config_value('ACLS_MVP_Logging', 'log_file_path')}")
#
#     except ACLSError as e:
#         print(f"\n[ACI_ERROR] An ACLS Error occurred: {e.message}")
#         if e.details: print(f"    Details: {e.details}")
#         if e.original_exception: print(f"    Original Exception: {type(e.original_exception).__name__}: {e.original_exception}")
#     except Exception as e_global_test:
#         print(f"\n[UNHANDLED_ERROR] An unexpected error occurred in test block: {e_global_test}", file=sys.stderr)
#     finally:
#         if 'service' in locals() and service.conn: # Check if service and conn were initialized
#             print("\nClosing ACLS Service DB connection if open...")
#             service.close() # Add a close() method to ACIServiceMVP that calls self.conn.close()
#         print("--- ACIServiceMVP Test Block Finished ---")
# ```

// AGENT_ACTION: Confirm aci_v2/acls_mvp/service_mvp.py implementation complete. State this, then proceed to the next AGENT_ACTION block for __init__.py without waiting for Architect input.
8. Package Initializer (aci_v2/acls_mvp/__init__.py)

// AGENT_ACTION: Populate aci_v2/acls_mvp/__init__.py.
// AGENT_ACTION: Ensure it exports ACIServiceMVP and all custom exceptions defined in aci_v2/acls_mvp/exceptions.py.
Python

# In aci_v2/acls_mvp/__init__.py
# Date: June 2, 2025
# Author: Lily AI for The Architect (ACI v2.0 Project)

from .service_mvp import ACIServiceMVP
from .exceptions import (
    ACLSError,
    ConfigPersistenceError,
    SecureStoreError,
    PassphraseRequiredError,
    ConfigItemNotFoundError,
    LogSetupError, # Added as per exceptions.py
    KeychainError, # Added as per exceptions.py
    EncryptionError # Added as per exceptions.py
    # DatabaseConnectionError was in exceptions.py but might be too low-level to export here unless specifically needed by other modules
)

__all__ = [
    "ACIServiceMVP",
    "ACLSError",
    "ConfigPersistenceError",
    "SecureStoreError",
    "PassphraseRequiredError",
    "ConfigItemNotFoundError",
    "LogSetupError",
    "KeychainError",
    "EncryptionError",
]

// AGENT_ACTION: Confirm aci_v2/acls_mvp/__init__.py implementation complete.
9. Dependencies for ACLS MVP Module

// AGENT_ACTION: At the end of aci_v2/acls_mvp/service_mvp.py (or as a final output for this module), provide the following dependency list as a comment:
Python

## ACLS MVP Module Dependencies (for ACI's pyproject.toml or requirements.txt):
# keyring >= 23.0.0
