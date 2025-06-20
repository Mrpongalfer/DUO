# File: ~/Projects/quantum_orchestrator_app/quantum_orchestrator/core/state_manager.py
# Version: 1.0 - JSON persistence, transaction placeholders

import json
import logging
import os
from pathlib import Path
from threading import RLock # Use RLock for potential re-entrant scenarios
from typing import Any, Dict, Optional, Set, Type

# Use absolute import path
try:
    # Assumes config.py defines PROJECT_ROOT_DIR pointing to quantum_orchestrator_app/
    from quantum_orchestrator.games.nexus_omniengine_v3.core.config import Settings, get_settings, PROJECT_ROOT_DIR
except ImportError as config_e:
    logging.getLogger(__name__).critical(f"CRITICAL: StateManager cannot import core config: {config_e}", exc_info=True)
    # Define dummies if import fails to allow class definition, but app likely won't work
    class Settings: pass # type: ignore
    PROJECT_ROOT_DIR = Path(".").resolve() # Fallback CWD

logger = logging.getLogger(__name__)

DEFAULT_STATE_FILENAME = "orchestrator_state.json"
# Use PROJECT_ROOT_DIR imported from config for consistency
DEFAULT_STATE_PATH = PROJECT_ROOT_DIR / DEFAULT_STATE_FILENAME

class StateManagerError(Exception):
    """Base exception for StateManager errors."""
    pass

class StatePersistenceError(StateManagerError):
    """Error during state file loading or saving."""
    pass

class TransactionError(StateManagerError):
    """Error related to transaction management."""
    pass


class StateManager:
    """
    Manages the persistent state of the Orchestrator using a JSON file.
    Provides basic transactional context methods (placeholder rollback).
    Implements basic thread safety for state access and file I/O.
    Adheres to TPC standards. Version 1.0.
    """

    def __init__(self, settings: Optional[Settings] = None, state_file_path: Optional[Path] = None):
        """
        Initializes the StateManager.

        Args:
            settings: The application settings object (optional, uses get_settings()).
            state_file_path: Optional path to the state file. Defaults to
                             'orchestrator_state.json' in the project root.

        Raises:
            StatePersistenceError: If the state file cannot be initialized or loaded correctly.
        """
        self.settings = settings or get_settings()
        # Ensure state_file_path resolves relative to PROJECT_ROOT_DIR if not absolute
        path_arg = state_file_path or DEFAULT_STATE_PATH
        if not Path(path_arg).is_absolute():
             self.state_file_path = (PROJECT_ROOT_DIR / path_arg).resolve()
        else:
             self.state_file_path = Path(path_arg).resolve()

        self._state: Dict[str, Any] = {}
        self._lock = RLock() # Use re-entrant lock for safety
        self._active_transactions: Set[str] = set()

        try:
            self._ensure_file_exists()
            # Use lock for initial load as well
            with self._lock:
                self._load_state_internal() # Load initial state
            logger.info(f"StateManager initialized. State file: {self.state_file_path}")
        except Exception as e:
            logger.critical(f"Failed to initialize StateManager state from {self.state_file_path}: {e}", exc_info=True)
            logger.warning("Proceeding with empty in-memory state.")
            self._state = {}

    def _ensure_file_exists(self):
        """Ensures the state file and its directory exist. Raises error on failure."""
        try:
            self.state_file_path.parent.mkdir(parents=True, exist_ok=True)
            if not self.state_file_path.exists():
                # Initialize with empty JSON object if creating
                with open(self.state_file_path, 'w', encoding='utf-8') as f:
                    json.dump({}, f)
                logger.info(f"Created empty state file at: {self.state_file_path}")
            # Basic permission check (might be insufficient on some OS/filesystems)
            if not os.access(self.state_file_path, os.R_OK): logger.warning(f"State file may not be readable: {self.state_file_path}")
            if not os.access(self.state_file_path, os.W_OK): logger.warning(f"State file may not be writable: {self.state_file_path}")
        except OSError as e:
            raise StatePersistenceError(f"Error ensuring state file exists at {self.state_file_path}: {e}") from e

    def _load_state_internal(self) -> None:
        """Internal: Loads state from file (caller must hold lock)."""
        if not self.state_file_path.is_file():
            logger.warning(f"State file not found during load attempt: {self.state_file_path}. Using empty state.")
            self._state = {}; return
        try:
            content = self.state_file_path.read_text(encoding='utf-8').strip()
            if not content:
                logger.info(f"State file is empty: {self.state_file_path}. Initializing empty state.")
                self._state = {}; return

            loaded_state = json.loads(content)
            if isinstance(loaded_state, dict):
                self._state = loaded_state
                logger.info(f"Successfully loaded state ({len(self._state)} keys).")
            else:
                logger.error(f"Invalid state file format (not JSON object): {self.state_file_path}. Resetting state.")
                self._state = {}
                self._save_state_internal() # Attempt overwrite with {}

        except (json.JSONDecodeError, OSError) as e:
            logger.exception(f"Error loading state from {self.state_file_path}. State may be stale/lost.")
            # Do not reset state here if already loaded, keep potentially stale memory state
            if not self._state: self._state = {} # Reset only if state was never loaded
            raise StatePersistenceError(f"Failed to load/parse state file: {e}") from e

    def load_state(self) -> None:
        """Loads state from file (thread-safe)."""
        with self._lock:
            self._load_state_internal()

    def _save_state_internal(self) -> None:
        """Internal: Saves state to file (caller must hold lock). Raises error on failure."""
        # Use unique temp file in same directory for atomic replace
        temp_path = self.state_file_path.with_suffix(f".{os.getpid()}_{time.time_ns()}.tmp")
        try:
            # Ensure directory exists before writing temp file
            self.state_file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(temp_path, "w", encoding="utf-8") as f:
                # Use default=str for common non-serializable types (e.g., Path, datetime)
                json.dump(self._state, f, indent=2, default=str)
            os.replace(temp_path, self.state_file_path) # Atomic rename on POSIX
            logger.debug(f"State successfully saved ({len(self._state)} keys) to {self.state_file_path}")
        except (OSError, TypeError) as e:
            logger.exception(f"Failed to save state to {self.state_file_path}: {e}")
            if temp_path.exists(): try: os.remove(temp_path) except OSError: pass
            raise StatePersistenceError(f"Failed to save state: {e}") from e
        finally: # Ensure temp file is removed even if os.replace fails somehow
            if temp_path.exists(): try: os.remove(temp_path) except OSError: pass

    def save_state(self) -> None:
        """Saves the current in-memory state to the JSON file (thread-safe)."""
        with self._lock:
            self._save_state_internal()

    def get_state(self, key: str, default: Any = None) -> Any:
        """Retrieves a value from the state (thread-safe)."""
        with self._lock: return self._state.get(key, default)

    def set_state(self, key: str, value: Any) -> None:
        """Sets a value in the state (thread-safe, does not auto-save)."""
        with self._lock: self._state[key] = value; logger.debug(f"State key '{key}' set (in memory).")

    def update(self, key: str, value: Any) -> None: self.set_state(key, value)

    def delete_state(self, key: str) -> None:
        """Deletes a key from the state (thread-safe, does not auto-save)."""
        with self._lock:
            if key in self._state:
                del self._state[key]; logger.debug(f"State key '{key}' deleted (in memory).")
            else: logger.warning(f"Delete called on non-existent key: '{key}'")

    # --- Transactional Methods ---
    def begin_transaction(self, transaction_id: str) -> None:
        """Marks the beginning of a transaction context."""
        with self._lock:
            if transaction_id in self._active_transactions: raise TransactionError(f"TX ID '{transaction_id}' already active.")
            self._active_transactions.add(transaction_id); logger.info(f"Transaction '{transaction_id}' started.")
            # TODO: Implement state snapshotting ('snapshot_{transaction_id}.json')

    def commit_transaction(self, transaction_id: str) -> None:
        """Commits changes by saving the current state."""
        with self._lock:
            if transaction_id not in self._active_transactions: raise TransactionError(f"Cannot commit inactive TX ID: '{transaction_id}'")
            logger.info(f"Committing transaction '{transaction_id}'...")
            try:
                self._save_state_internal() # Commit = Save current state
                logger.info(f"State saved for commit TX '{transaction_id}'.")
                # TODO: Clean up snapshot file for transaction_id
                self._active_transactions.discard(transaction_id) # Remove AFTER successful save
            except StatePersistenceError as e: logger.error(f"Commit failed for TX '{transaction_id}' (save error). TX remains active."); raise

    def rollback_transaction(self, transaction_id: str) -> None:
        """Rolls back changes (Basic: Reloads state from last successful save)."""
        with self._lock:
            if transaction_id not in self._active_transactions: logger.warning(f"Rollback called on inactive TX ID: '{transaction_id}'"); return
            logger.warning(f"Rolling back transaction '{transaction_id}' (Basic: Reloading state)...")
            try:
                # Basic rollback: discard in-memory changes and reload from disk
                self._load_state_internal()
                logger.info("State reverted to last saved version.")
            except StatePersistenceError as e: logger.error(f"Failed reload during rollback for TX '{transaction_id}': {e}. State maybe inconsistent!")
            finally: self._active_transactions.discard(transaction_id); logger.info(f"TX '{transaction_id}' rollback processed.")
            # raise NotImplementedError("Full transactional rollback not implemented.")
