# In aci_v2/acls_mvp/exceptions.py
# Date: June 2, 2025
# Author: Lily AI for The Architect (ACI v2.0 Project)

from aci_v2.common_exceptions import (
    ACIError,
)


class ACLSError(ACIError):
    """Base exception for all ACLS module related errors."""

    pass


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


class ConfigItemNotFoundError(ACLSError):
    """Raised when a specific configuration item is not found by ConfigManagerMVP and no fallback is suitable."""

    pass
