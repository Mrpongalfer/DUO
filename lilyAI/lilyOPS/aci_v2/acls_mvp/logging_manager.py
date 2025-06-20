# In aci_v2/acls_mvp/logging_manager.py
# Date: June 2, 2025
# Author: Lily AI for The Architect (ACI v2.0 Project)

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from .config_manager import ConfigManagerMVP
from .exceptions import LogSetupError


class LoggingManagerMVP:
    """
    Provides a centralized, robust logging facility for ACI modules.
    Configures both console and rotating file handlers based on config.
    """

    def __init__(
        self,
        config_manager: ConfigManagerMVP,
        bootstrap_logger: logging.Logger | None = None,
    ) -> None:
        """
        Initializes the LoggingManagerMVP with the provided ConfigManagerMVP.
        Sets up logging handlers as per configuration.

        Args:
            config_manager (ConfigManagerMVP): The configuration manager instance.
            bootstrap_logger (Optional[logging.Logger]): Logger for initialization messages.
        Raises:
            LogSetupError: If logging handlers cannot be set up.
        """
        self.config_manager = config_manager
        self.logger = (
            bootstrap_logger
            if bootstrap_logger
            else logging.getLogger("ACI.ACLS.LoggingManagerMVP")
        )
        self._root_logger = logging.getLogger()
        self._handlers_set = False
        self._setup_logging_handlers()

    def _setup_logging_handlers(self) -> None:
        """
        Sets up console and rotating file handlers as per config.
        Raises LogSetupError if setup fails.
        """
        try:
            # Remove all handlers if already set (idempotent)
            if self._handlers_set:
                for handler in self._root_logger.handlers[:]:
                    self._root_logger.removeHandler(handler)
            # Console handler
            console_level = self._get_log_level_from_config(
                "console_log_level", default="INFO"
            )
            ch = logging.StreamHandler(sys.stdout)
            ch.setLevel(console_level)
            ch.setFormatter(
                logging.Formatter("[%(asctime)s] %(levelname)s %(name)s: %(message)s")
            )
            self._root_logger.addHandler(ch)
            # Rotating file handler
            file_level = self._get_log_level_from_config(
                "file_log_level", default="DEBUG"
            )
            log_file_path = self.config_manager.get_config_value(
                "ACLS_MVP_Logging",
                "log_file_path",
                fallback=str(
                    Path.home()
                    / ".local"
                    / "share"
                    / "aci_v2_mvp"
                    / "logs"
                    / "aci_mvp.log"
                ),
                value_type=str,
            )
            log_file_path = Path(log_file_path).expanduser().resolve()
            log_file_path.parent.mkdir(parents=True, exist_ok=True)
            max_bytes = self.config_manager.get_config_value(
                "ACLS_MVP_Logging",
                "log_file_max_bytes",
                fallback=10 * 1024 * 1024,
                value_type=int,
            )
            backup_count = self.config_manager.get_config_value(
                "ACLS_MVP_Logging", "log_file_backup_count", fallback=5, value_type=int
            )
            fh = RotatingFileHandler(
                log_file_path,
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding="utf-8",
            )
            fh.setLevel(file_level)
            fh.setFormatter(
                logging.Formatter("[%(asctime)s] %(levelname)s %(name)s: %(message)s")
            )
            self._root_logger.addHandler(fh)
            self._root_logger.setLevel(min(console_level, file_level))
            self._handlers_set = True
            self.logger.info(
                f"LoggingManagerMVP initialized. Console level: {console_level}, File level: {file_level}, Log file: {log_file_path}"
            )
        except Exception as e:
            self.logger.error(f"Failed to set up logging handlers: {e}", exc_info=True)
            raise LogSetupError(
                f"Failed to set up logging handlers: {e}", original_exception=e
            )

    def _get_log_level_from_config(self, key: str, default: str = "INFO") -> int:
        """
        Helper to get log level from config, defaulting to INFO if not found or invalid.
        """
        level_str = self.config_manager.get_config_value(
            "ACLS_MVP_Logging", key, fallback=default, value_type=str
        )
        return getattr(logging, level_str.upper(), logging.INFO)

    def get_logger(self, name: str) -> logging.Logger:
        """
        Returns a logger with the specified name, inheriting handlers from root.

        Args:
            name (str): The logger name.

        Returns:
            logging.Logger: The logger instance.
        """
        return logging.getLogger(name)
        return logging.getLogger(name)
