# AGENT_ACTION: Implement the `if __name__ == "__main__":` test block for `service.py`.
if __name__ == "__main__":
    import sys

    print("--- Testing ACIServiceMVP ---")
    print("WARNING: This test will use/create config files in your user directory.")
    print("         (~/.config/aci_v2_mvp/ and ~/.local/share/aci_v2_mvp/)")
    print(
        "         Consider manual cleanup after test if these are not desired production paths yet."
    )
    try:
        service = ACIServiceMVP()
        print("\n[OK] ACIServiceMVP initialized successfully.")

        # Test general config
        print("\n--- Testing General Config ---")
        service.set_config("TestSection", "TestKey", "TestValue123")
        val = service.get_config("TestSection", "TestKey")
        print(f"Get TestSection/TestKey: {val} (Expected: TestValue123)")
        assert val == "TestValue123"
        service.delete_config("TestSection", "TestKey")
        val_after_delete = service.get_config(
            "TestSection", "TestKey", fallback="NOT_FOUND"
        )
        print(
            f"Get TestSection/TestKey after delete: {val_after_delete} (Expected: NOT_FOUND)"
        )
        assert val_after_delete == "NOT_FOUND"
        print("[OK] General Config R/W/D test passed.")

        # Test Secure Store
        print("\n--- Testing Secure Store (GitHub PAT / Generic Secret) ---")
        test_key_id = "ACI_MVP_TEST_SECRET"
        test_secret_value = "my_super_secret_test_value_12345"
        print(
            f"Attempting to set secret for '{test_key_id}'. If keychain unavailable, this may fail or require a passphrase you can't provide here."
        )
        print(
            "For full fallback test, SecureTokenManagerMVP.set_secure_secret needs interactive passphrase input if keychain fails."
        )
        passphrase_for_test = (
            None  # Set to a string to test fallback path if keyring is known to fail
        )
        if service.set_secure_secret(
            test_key_id,
            test_secret_value,
            master_passphrase_for_fallback=passphrase_for_test,
        ):
            print(
                f"Successfully called set_secure_secret for '{test_key_id}'. Check keychain or config if fallback used."
            )
            retrieved_secret = service.get_secure_secret(
                test_key_id, master_passphrase_for_test=passphrase_for_test
            )
            if retrieved_secret == test_secret_value:
                print(
                    f"[OK] Secure secret for '{test_key_id}' SET and GET successfully."
                )
            elif (
                retrieved_secret is None
                and passphrase_for_test is None
                and service.secure_store.config_manager.get_config_value(
                    "ACLS_MVP_SecureStore", f"encrypted_secret_{test_key_id}"
                )
            ):
                print(
                    f"[INFO] Secure secret for '{test_key_id}' likely stored in fallback, but passphrase needed to retrieve."
                )
            else:
                print(
                    f"[FAIL] Secure secret for '{test_key_id}' GET mismatch or failed. Retrieved: {retrieved_secret}"
                )
            if service.delete_secure_secret(test_key_id):
                print(
                    f"[OK] Secure secret for '{test_key_id}' delete called successfully."
                )
                retrieved_after_delete = service.get_secure_secret(
                    test_key_id, master_passphrase_for_fallback=passphrase_for_test
                )
                if retrieved_after_delete is None:
                    print(
                        f"[OK] Secure secret for '{test_key_id}' confirmed deleted or irretrievable."
                    )
                else:
                    print(
                        f"[FAIL] Secure secret for '{test_key_id}' still retrievable after delete."
                    )
            else:
                print(
                    f"[FAIL] Call to delete_secure_secret for '{test_key_id}' reported failure."
                )
        else:
            print(
                f"[FAIL] Failed to set_secure_secret for '{test_key_id}'. This might be due to keychain failure and no passphrase for fallback."
            )

        # Test Logging
        print("\n--- Testing Logging ---")
        test_logger = service.get_logger("ACI.TestMainBlock")
        test_logger.debug("This is a DEBUG message from ACLS test block.")
        test_logger.info("This is an INFO message from ACLS test block.")
        test_logger.warning("This is a WARNING message from ACLS test block.")
        test_logger.error("This is an ERROR message from ACLS test block.")
        test_logger.critical(
            "This is a CRITICAL message from ACLS test block.",
            extra={"details": {"test_detail": 123}},
        )
        print("[OK] Logging test messages sent. Check console and configured log file.")
        print(
            f"      Log file path (from config via service): {service.config_manager.get_config_value('ACLS_MVP_Logging', 'log_file_path')}"
        )

    except ACLSError as e:
        print(f"\n[ACI_ERROR] An ACLS Error occurred: {e.message}")
        if hasattr(e, "details") and e.details:
            print(f"    Details: {e.details}")
        if hasattr(e, "original_exception") and e.original_exception:
            print(
                f"    Original Exception: {type(e.original_exception).__name__}: {e.original_exception}"
            )
    except Exception as e_global_test:
        print(
            f"\n[UNHANDLED_ERROR] An unexpected error occurred in test block: {e_global_test}",
            file=sys.stderr,
        )
    print("--- ACIServiceMVP Test Block Finished ---")
# In aci_v2/acls_mvp/service.py
# Date: June 2, 2025
# Author: Lily AI for The Architect (ACI v2.0 Project)

import logging
from typing import Any

from .config_manager import ConfigManagerMVP
from .exceptions import ACLSError
from .logging_manager import LoggingManagerMVP
from .secure_store import SecureTokenManagerMVP


class ACIServiceMVP:
    """
    Main service class for ACLS MVP, providing configuration, secure secret management, and logging.
    """

    def __init__(
        self,
        config_file_path_override: str | None = None,
        bootstrap_logger: logging.Logger | None = None,
    ) -> None:
        """
        Initializes the ACIServiceMVP, setting up config, secure store, and logging managers.

        Args:
            config_file_path_override (Optional[str]): Optional override for config file path.
            bootstrap_logger (Optional[logging.Logger]): Logger for initialization messages.
        Raises:
            ACLSError: If any component fails to initialize.
        """
        try:
            self.config_manager = ConfigManagerMVP(
                config_file_path_override=config_file_path_override,
                bootstrap_logger=bootstrap_logger,
            )
            self.secure_store = SecureTokenManagerMVP(
                config_manager=self.config_manager,
                bootstrap_logger=bootstrap_logger,
            )
            self.logging_manager = LoggingManagerMVP(
                config_manager=self.config_manager,
                bootstrap_logger=bootstrap_logger,
            )
            self.logger = self.logging_manager.get_logger("ACI.ACLS.ACIServiceMVP")
            self.logger.info("ACIServiceMVP initialized successfully.")
        except Exception as e:
            raise ACLSError("Failed to initialize ACIServiceMVP.", original_exception=e)

    def get_config(
        self, section: str, key: str, fallback: Any = None, value_type: type = str
    ) -> Any:
        """
        Retrieves a configuration value from the config manager.

        Args:
            section (str): The config section.
            key (str): The config key.
            fallback (Any): Value to return if not found.
            value_type (type): Type to cast the value to.
        Returns:
            Any: The config value or fallback.
        """
        return self.config_manager.get_config_value(section, key, fallback, value_type)

    def set_config(self, section: str, key: str, value: Any) -> None:
        """
        Sets a configuration value in the config manager.

        Args:
            section (str): The config section.
            key (str): The config key.
            value (Any): The value to set.
        """
        self.config_manager.set_config_value(section, key, value)

    def delete_config(self, section: str, key: str) -> bool:
        """
        Deletes a configuration key from the config manager.

        Args:
            section (str): The config section.
            key (str): The config key.
        Returns:
            bool: True if deleted, False otherwise.
        """
        return self.config_manager.delete_config_key(section, key)

    def set_secure_secret(
        self,
        key_identifier: str,
        secret_value: str,
        master_passphrase_for_fallback: str | None = None,
    ) -> bool:
        """
        Stores a secure secret using the secure store manager.

        Args:
            key_identifier (str): The secret's identifier.
            secret_value (str): The secret value.
            master_passphrase_for_fallback (Optional[str]): Passphrase for fallback if keychain fails.
        Returns:
            bool: True if stored successfully.
        Raises:
            PassphraseRequiredError: If fallback is needed but no passphrase provided.
            EncryptionError: If encryption fails.
        """
        return self.secure_store.set_secure_secret(
            key_identifier, secret_value, master_passphrase_for_fallback
        )

    def get_secure_secret(
        self, key_identifier: str, master_passphrase_for_fallback: str | None = None
    ) -> str | None:
        """
        Retrieves a secure secret using the secure store manager.

        Args:
            key_identifier (str): The secret's identifier.
            master_passphrase_for_fallback (Optional[str]): Passphrase for fallback if keychain fails.
        Returns:
            Optional[str]: The secret value or None.
        Raises:
            PassphraseRequiredError: If fallback is needed but no passphrase provided.
            EncryptionError: If decryption fails.
        """
        return self.secure_store.get_secure_secret(
            key_identifier, master_passphrase_for_fallback
        )

    def delete_secure_secret(self, key_identifier: str) -> bool:
        """
        Deletes a secure secret from both keychain and fallback store.

        Args:
            key_identifier (str): The secret's identifier.
        Returns:
            bool: True if deleted from at least one store.
        """
        return self.secure_store.delete_secure_secret(key_identifier)

    def get_logger(self, name: str) -> logging.Logger:
        """
        Returns a logger with the specified name.

        Args:
            name (str): The logger name.
        Returns:
            logging.Logger: The logger instance.
        """
        return self.logging_manager.get_logger(name)


#
# ACLS MVP Module Dependencies (for ACI's pyproject.toml or requirements.txt):
# keyring >= 23.0.0
# cryptography >= 3.4.0
# keyring >= 23.0.0
