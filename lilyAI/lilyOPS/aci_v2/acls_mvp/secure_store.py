# In aci_v2/acls_mvp/secure_store.py
# Date: June 2, 2025
# Author: Lily AI for The Architect (ACI v2.0 Project)

import base64
import logging
import os

import keyring
from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from .config_manager import ConfigManagerMVP
from .exceptions import EncryptionError, PassphraseRequiredError


class SecureTokenManagerMVP:
    """
    Manages secure storage and retrieval of sensitive tokens (e.g., API keys, PATs) for ACI MVP.
    Prioritizes OS keychain and uses an encrypted INI file section as a fallback.
    This version implements generic secret management.
    """

    KEYRING_SERVICE_NAME: str = "ACI_V2_MVP_SECRETS"  # Generic service name for keyring
    CONFIG_SECTION_FALLBACK: str = "ACLS_MVP_SecureStore"
    CONFIG_KEY_SALT_PREFIX: str = "fallback_salt_for_"
    CONFIG_KEY_ENCRYPTED_PREFIX: str = "encrypted_secret_"
    KEY_DERIVATION_ITERATIONS: int = 480000

    def __init__(
        self,
        config_manager: ConfigManagerMVP,
        bootstrap_logger: logging.Logger | None = None,
    ):
        self.config_manager: ConfigManagerMVP = config_manager
        self.logger = (
            bootstrap_logger
            if bootstrap_logger
            else logging.getLogger(f"ACI.ACLS.{self.__class__.__name__}")
        )
        self.logger.debug(
            "SecureTokenManagerMVP (Generic Secrets Version) initialized."
        )

    def _derive_key_from_passphrase(self, passphrase: str, salt: bytes) -> bytes:
        if not passphrase:
            raise ValueError("Passphrase cannot be empty for key derivation.")
        if not salt:
            raise ValueError("Salt cannot be empty for key derivation.")
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=self.KEY_DERIVATION_ITERATIONS,
            backend=default_backend(),
        )
        derived_key = kdf.derive(passphrase.encode("utf-8"))
        return base64.urlsafe_b64encode(derived_key)

    def _clear_fallback_data(self, key_identifier: str) -> None:
        """Helper to remove fallback data if keychain operation is successful or for explicit deletion."""
        salt_config_key = f"{self.CONFIG_KEY_SALT_PREFIX}{key_identifier}"
        encrypted_config_key = f"{self.CONFIG_KEY_ENCRYPTED_PREFIX}{key_identifier}"
        self.config_manager.delete_config_key(
            self.CONFIG_SECTION_FALLBACK, encrypted_config_key
        )
        self.config_manager.delete_config_key(
            self.CONFIG_SECTION_FALLBACK, salt_config_key
        )
        self.logger.debug(
            f"Cleared fallback data for key_identifier '{key_identifier}'."
        )

    def set_secure_secret(
        self,
        key_identifier: str,
        secret_value: str,
        master_passphrase_for_fallback: str | None = None,
    ) -> bool:
        """
        Stores a secret securely, prioritizing OS keychain, then encrypted INI fallback.

        Args:
            key_identifier (str): Unique identifier for the secret (e.g., "ACI_MVP_GITHUB_PAT"). Used as 'username' in keyring.
            secret_value (str): The actual secret to store.
            master_passphrase_for_fallback (Optional[str]): Master passphrase for fallback encryption.
        Returns:
            bool: True if successfully stored.
        Raises:
            ValueError: If key_identifier or secret_value is invalid.
            PassphraseRequiredError: If keychain fails and fallback passphrase is not provided.
            EncryptionError: If fallback encryption fails.
            SecureStoreError: For other underlying storage issues.
        """
        if not isinstance(key_identifier, str) or not key_identifier.strip():
            raise ValueError("key_identifier must be a non-empty string.")
        if not isinstance(secret_value, str):
            raise ValueError("secret_value must be a string.")

        self.logger.info(
            f"Attempting to store secure secret for key_identifier: '{key_identifier}'."
        )
        try:
            keyring.set_password(
                self.KEYRING_SERVICE_NAME, key_identifier, secret_value
            )
            self.logger.info(
                f"Secret for '{key_identifier}' stored successfully in OS keychain."
            )
            self._clear_fallback_data(
                key_identifier
            )  # Clear any old fallback if keychain now works
            return True
        except keyring.errors.NoKeyringError:
            self.logger.warning(
                f"No OS keychain backend found for '{key_identifier}'. Attempting encrypted INI fallback."
            )
        except keyring.errors.KeyringError as e_keyring:
            self.logger.warning(
                f"OS Keychain failed for '{key_identifier}'. Error: {e_keyring}. Attempting encrypted INI fallback.",
                exc_info=True,
            )

        # Fallback to encrypted INI
        if (
            not master_passphrase_for_fallback
            or not master_passphrase_for_fallback.strip()
        ):
            self.logger.error(
                f"Keychain unavailable/failed for '{key_identifier}', and master passphrase for fallback was not provided or was empty. Secret NOT stored."
            )
            raise PassphraseRequiredError(
                f"Keychain unavailable/failed for '{key_identifier}', master passphrase for fallback required but not provided."
            )

        try:
            salt_config_key = f"{self.CONFIG_KEY_SALT_PREFIX}{key_identifier}"
            encrypted_config_key = f"{self.CONFIG_KEY_ENCRYPTED_PREFIX}{key_identifier}"

            salt_str = self.config_manager.get_config_value(
                self.CONFIG_SECTION_FALLBACK,
                salt_config_key,
                fallback=None,
                value_type=str,
            )
            salt_bytes: bytes
            if not salt_str:
                salt_bytes = os.urandom(16)
                salt_str_to_save = base64.urlsafe_b64encode(salt_bytes).decode("utf-8")
                self.config_manager.set_config_value(
                    self.CONFIG_SECTION_FALLBACK, salt_config_key, salt_str_to_save
                )
                self.logger.info(
                    f"Generated and stored new salt for fallback key '{key_identifier}'."
                )
            else:
                salt_bytes = base64.urlsafe_b64decode(salt_str.encode("utf-8"))

            fernet_key = self._derive_key_from_passphrase(
                master_passphrase_for_fallback, salt_bytes
            )
            f = Fernet(fernet_key)
            encrypted_secret = f.encrypt(secret_value.encode("utf-8")).decode("utf-8")

            self.config_manager.set_config_value(
                self.CONFIG_SECTION_FALLBACK, encrypted_config_key, encrypted_secret
            )
            self.logger.info(
                f"Secret for '{key_identifier}' stored successfully using encrypted INI fallback."
            )
            return True
        except Exception as e_fallback:
            self.logger.error(
                f"Fallback encryption failed for '{key_identifier}': {e_fallback}",
                exc_info=True,
            )
            raise EncryptionError(
                f"Fallback encryption failed for '{key_identifier}'",
                original_exception=e_fallback,
            )

    def get_secure_secret(
        self, key_identifier: str, master_passphrase_for_fallback: str | None = None
    ) -> str | None:
        """
        Retrieves a secret securely, prioritizing OS keychain, then encrypted INI fallback.
        Returns the secret string or None if not found.
        Raises PassphraseRequiredError if fallback needs passphrase, EncryptionError on decryption failure.
        """
        self.logger.debug(
            f"Attempting to retrieve secure secret for key_identifier: '{key_identifier}'."
        )
        try:
            token = keyring.get_password(self.KEYRING_SERVICE_NAME, key_identifier)
            if token is not None:
                self.logger.info(
                    f"Secret for '{key_identifier}' retrieved successfully from OS keychain."
                )
                return token
            # If token is None, keyring had no password or a backend is available but no password for this service/username
            self.logger.info(
                f"Secret for '{key_identifier}' not found in OS keychain or keychain returned None. Attempting fallback."
            )
        except keyring.errors.NoKeyringError:  # No backend available
            self.logger.warning(
                f"No OS keychain backend found for '{key_identifier}'. Attempting encrypted INI fallback."
            )
        except keyring.errors.KeyringError as e_keyring:  # Other keychain errors
            self.logger.warning(
                f"OS Keychain error for '{key_identifier}'. Error: {e_keyring}. Attempting encrypted INI fallback.",
                exc_info=True,
            )

        # Fallback logic
        salt_config_key = f"{self.CONFIG_KEY_SALT_PREFIX}{key_identifier}"
        encrypted_config_key = f"{self.CONFIG_KEY_ENCRYPTED_PREFIX}{key_identifier}"
        encrypted_secret_str = self.config_manager.get_config_value(
            self.CONFIG_SECTION_FALLBACK,
            encrypted_config_key,
            fallback=None,
            value_type=str,
        )
        salt_str = self.config_manager.get_config_value(
            self.CONFIG_SECTION_FALLBACK, salt_config_key, fallback=None, value_type=str
        )

        if encrypted_secret_str and salt_str:
            if (
                not master_passphrase_for_fallback
                or not master_passphrase_for_fallback.strip()
            ):
                self.logger.warning(
                    f"Encrypted secret for '{key_identifier}' exists in fallback, but master passphrase required for retrieval."
                )
                raise PassphraseRequiredError(
                    f"Master passphrase required to decrypt fallback secret for '{key_identifier}'."
                )
            try:
                salt_bytes = base64.urlsafe_b64decode(salt_str.encode("utf-8"))
                fernet_key = self._derive_key_from_passphrase(
                    master_passphrase_for_fallback, salt_bytes
                )
                f = Fernet(fernet_key)
                decrypted_secret = f.decrypt(
                    encrypted_secret_str.encode("utf-8")
                ).decode("utf-8")
                self.logger.info(
                    f"Secret for '{key_identifier}' retrieved successfully using encrypted INI fallback."
                )
                return decrypted_secret
            except (
                EncryptionError,
                ValueError,
                TypeError,
                base64.binascii.Error,
            ) as e_decrypt:  # Catch specific decrypt errors
                self.logger.error(
                    f"Fallback decryption failed for '{key_identifier}'. Likely wrong passphrase or corrupt data. Error: {e_decrypt}",
                    exc_info=True,
                )
                raise EncryptionError(
                    f"Fallback decryption failed for '{key_identifier}'",
                    original_exception=e_decrypt,
                )
            except Exception as e_unexp_decrypt:
                self.logger.error(
                    f"Unexpected error during fallback decryption for '{key_identifier}': {e_unexp_decrypt}",
                    exc_info=True,
                )
                raise EncryptionError(
                    f"Unexpected error during fallback decryption for '{key_identifier}'",
                    original_exception=e_unexp_decrypt,
                )

        self.logger.info(
            f"Secret for '{key_identifier}' not found in fallback storage either."
        )
        return None

    def delete_secure_secret(self, key_identifier: str) -> bool:
        """
        Deletes a secret from both OS keychain and encrypted INI fallback.
        Returns True if deletion was attempted from at least one store (even if secret wasn't present).
        """
        self.logger.info(
            f"Attempting to delete secure secret for key_identifier: '{key_identifier}'."
        )
        keychain_attempted_delete = False
        try:
            # Try to delete from keychain. If it's not there, PasswordNotFoundError might be raised by some backends.
            # Other backends might not error if password not found. We want to ensure an attempt was made.
            keyring.delete_password(self.KEYRING_SERVICE_NAME, key_identifier)
            self.logger.info(
                f"Secret for '{key_identifier}' (if it existed) deleted from OS keychain."
            )
            keychain_attempted_delete = True
        except keyring.errors.PasswordNotFoundError:
            self.logger.info(
                f"Secret for '{key_identifier}' not found in OS keychain to delete."
            )
            keychain_attempted_delete = True  # Attempt was made
        except keyring.errors.NoKeyringError:
            self.logger.warning(
                f"No OS keychain backend found. Cannot delete '{key_identifier}' from keychain."
            )
            # keychain_attempted_delete remains False, but we proceed to clear fallback.
        except keyring.errors.KeyringError as e_keyring:
            self.logger.warning(
                f"Error deleting secret for '{key_identifier}' from keychain: {e_keyring}. Proceeding to clear fallback.",
                exc_info=True,
            )
            keychain_attempted_delete = True  # Attempt was made, though it errored

        # Always attempt to clear fallback data
        self._clear_fallback_data(key_identifier)
        self.logger.info(
            f"Attempted deletion of fallback data for key_identifier '{key_identifier}' completed."
        )
        return True  # Indicates deletion process from all known stores was completed
