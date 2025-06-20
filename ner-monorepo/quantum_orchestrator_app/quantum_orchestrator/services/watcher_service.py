"""
Watcher Service: File system monitoring and event handling.

Monitors specified directories for changes and triggers configured actions.
"""

import os
import time
import threading
import logging
from typing import Any, Dict, List, Callable, Set
from pathlib import Path
import queue

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileSystemEvent
except ImportError:
    logging.error(
        "watchdog package not found. File watching functionality will be disabled."
    )
    Observer = None
    FileSystemEventHandler = object

from quantum_orchestrator.utils.logging_utils import get_logger
from quantum_orchestrator.games.nexus_omniengine_v3.core.config import Config

# Initialize logger and config
logger = get_logger(__name__)
config = Config()


class WatcherEventHandler(FileSystemEventHandler):
    """Custom event handler for file system events."""

    def __init__(self, callback: Callable[[Dict[str, Any]], None]):
        """
        Initialize the event handler.

        Args:
            callback: Function to call when events occur
        """
        self.callback = callback
        self.ignore_patterns = config.get(
            "watcher", "ignore_patterns", ["__pycache__", "*.pyc", ".git/"]
        )

    def should_ignore(self, path: str) -> bool:
        """
        Check if a path should be ignored.

        Args:
            path: Path to check

        Returns:
            bool: True if path should be ignored, False otherwise
        """
        for pattern in self.ignore_patterns:
            if pattern.endswith("/"):
                # Directory pattern
                pattern = pattern[:-1]
                if pattern in path.split(os.sep):
                    return True
            elif pattern.startswith("*."):
                # Extension pattern
                if path.endswith(pattern[1:]):
                    return True
            elif pattern in path:
                # Simple pattern
                return True
        return False

    def on_any_event(self, event: FileSystemEvent):
        """
        Handle any file system event.

        Args:
            event: The file system event
        """
        # Skip events for ignored patterns
        if self.should_ignore(event.src_path):
            return

        # Call the callback with event data
        self.callback(
            {
                "event_type": event.event_type,
                "path": event.src_path,
                "is_directory": event.is_directory,
                "timestamp": time.time(),
            }
        )


class WatcherService:
    """Service for monitoring file system changes."""

    def __init__(self):
        """Initialize the watcher service."""
        self.observer = None
        self.paths: Set[str] = set()
        self.callbacks: List[Callable[[Dict[str, Any]], None]] = []
        self.event_queue = queue.Queue()
        self.running = False
        self.thread = None

    def add_path(self, path: str):
        """
        Add a path to watch.

        Args:
            path: Directory path to watch
        """
        abs_path = str(Path(path).resolve())
        self.paths.add(abs_path)

        # If observer is running, schedule this path
        if self.observer and self.observer.is_alive():
            handler = WatcherEventHandler(self._on_event)
            self.observer.schedule(handler, abs_path, recursive=True)
            logger.info(f"Added path to watch: {abs_path}")

    def remove_path(self, path: str):
        """
        Remove a path from watching.

        Args:
            path: Directory path to stop watching
        """
        abs_path = str(Path(path).resolve())
        if abs_path in self.paths:
            self.paths.remove(abs_path)
            logger.info(f"Removed path from watch: {abs_path}")

            # Currently, watchdog doesn't provide a clean way to unschedule a specific path
            # So we'll need to restart the observer if we're running
            if self.running:
                self.stop()
                self.start()

    def add_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """
        Add a callback for file system events.

        Args:
            callback: Function to call when events occur
        """
        self.callbacks.append(callback)

    def _on_event(self, event_data: Dict[str, Any]):
        """
        Internal method to handle file system events.

        Args:
            event_data: Data about the event
        """
        # Add event to queue
        self.event_queue.put(event_data)

    def _process_events(self):
        """Process events from the queue."""
        while self.running:
            try:
                # Get event with timeout to allow checking self.running periodically
                event_data = self.event_queue.get(timeout=1.0)

                # Call all callbacks with this event
                for callback in self.callbacks:
                    try:
                        callback(event_data)
                    except Exception as e:
                        logger.error(f"Error in watcher callback: {str(e)}")

                # Mark task as done
                self.event_queue.task_done()

            except queue.Empty:
                # Timeout, just continue the loop
                pass
            except Exception as e:
                logger.error(f"Error processing watcher events: {str(e)}")

    def start(self):
        """Start the file watcher."""
        if Observer is None:
            logger.error("Cannot start watcher: watchdog package not installed")
            return False

        if self.running:
            return True

        try:
            self.running = True
            self.observer = Observer()

            # Schedule all paths
            for path in self.paths:
                handler = WatcherEventHandler(self._on_event)
                self.observer.schedule(handler, path, recursive=True)

            # Start the observer
            self.observer.start()

            # Start the event processing thread
            self.thread = threading.Thread(target=self._process_events)
            self.thread.daemon = True
            self.thread.start()

            logger.info(f"Watcher service started, monitoring {len(self.paths)} paths")
            return True

        except Exception as e:
            self.running = False
            logger.error(f"Failed to start watcher service: {str(e)}")
            return False

    def stop(self):
        """Stop the file watcher."""
        if not self.running:
            return

        self.running = False

        # Stop the observer
        if self.observer:
            self.observer.stop()
            self.observer.join()
            self.observer = None

        # Wait for the thread to finish
        if self.thread:
            self.thread.join(timeout=5.0)
            self.thread = None

        logger.info("Watcher service stopped")


# Global watcher service instance
_watcher = None


def get_watcher() -> WatcherService:
    """
    Get the global watcher service instance.

    Returns:
        WatcherService: The global watcher service
    """
    global _watcher
    if _watcher is None:
        _watcher = WatcherService()
    return _watcher


def init_watcher() -> WatcherService:
    """
    Initialize and start the watcher service with configured paths.

    Returns:
        WatcherService: The initialized watcher service
    """
    watcher = get_watcher()

    # Add configured paths
    paths = config.get("watcher", "paths", ["./"])
    for path in paths:
        watcher.add_path(path)

    # Start the watcher if enabled
    if config.get("watcher", "enabled", True):
        watcher.start()

    return watcher


def add_watcher_callback(callback: Callable[[Dict[str, Any]], None]):
    """
    Add a callback to the watcher service.

    Args:
        callback: Function to call when events occur
    """
    watcher = get_watcher()
    watcher.add_callback(callback)
