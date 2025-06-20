"""
Path Resolver: Utility for secure and consistent path resolution.

Provides functions for resolving relative paths and preventing directory traversal.
"""

import os
from typing import List

from quantum_orchestrator.utils.logging_utils import get_logger
from quantum_orchestrator.utils.security import sanitize_path

logger = get_logger(__name__)


def resolve_path(path: str, base_dir: str = None) -> str:
    """
    Resolve a path safely, preventing directory traversal.

    Args:
        path: Path to resolve (absolute or relative)
        base_dir: Base directory for relative paths (default: current directory)

    Returns:
        str: Resolved absolute path
    """
    if not path:
        return os.getcwd()

    # Set base directory
    if base_dir is None:
        base_dir = os.getcwd()

    # Make base_dir absolute
    base_dir = os.path.abspath(base_dir)

    # Normalize path separators
    path = path.replace("\\", "/")

    # Handle absolute paths
    if os.path.isabs(path):
        # If the path is already absolute, just normalize it
        result = os.path.normpath(path)
    else:
        # For relative paths, join with base directory
        if path.startswith("./"):
            path = path[2:]
        result = os.path.normpath(os.path.join(base_dir, path))

    # Verify path is not outside base directory (if it's a subdirectory)
    if os.path.commonpath([base_dir, result]) != base_dir and not path.startswith("/"):
        logger.warning(
            f"Path traversal attempt: {path} resolves outside base directory"
        )
        # Fall back to base directory
        return base_dir

    return result


def ensure_directory(path: str) -> bool:
    """
    Ensure a directory exists, creating it if necessary.

    Args:
        path: Path to the directory

    Returns:
        bool: True if directory exists or was created
    """
    try:
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)
            logger.debug(f"Created directory: {path}")
        return True
    except Exception as e:
        logger.error(f"Failed to create directory {path}: {str(e)}")
        return False


def list_directory(path: str, pattern: str = "*", recursive: bool = False) -> List[str]:
    """
    List files in a directory with pattern matching.

    Args:
        path: Directory path
        pattern: Glob pattern for file matching
        recursive: Whether to search recursively

    Returns:
        List of file paths
    """
    import glob

    # Resolve path
    abs_path = resolve_path(path)

    # Build glob pattern
    if recursive:
        glob_pattern = os.path.join(abs_path, "**", pattern)
    else:
        glob_pattern = os.path.join(abs_path, pattern)

    # Get file list
    return glob.glob(glob_pattern, recursive=recursive)


def is_safe_path(path: str, base_dir: str = None) -> bool:
    """
    Check if a path is safe (within base directory).

    Args:
        path: Path to check
        base_dir: Base directory (default: current directory)

    Returns:
        bool: True if path is safe
    """
    # Sanitize the path
    safe_path = sanitize_path(path)
    if not safe_path:
        return False

    # Set base directory
    if base_dir is None:
        base_dir = os.getcwd()

    # Make paths absolute
    abs_path = os.path.abspath(os.path.join(base_dir, safe_path))
    abs_base = os.path.abspath(base_dir)

    # Check if path is within base directory
    return os.path.commonpath([abs_base, abs_path]) == abs_base


def get_relative_path(path: str, base_dir: str = None) -> str:
    """
    Get path relative to base directory.

    Args:
        path: Path to convert
        base_dir: Base directory (default: current directory)

    Returns:
        str: Relative path
    """
    # Set base directory
    if base_dir is None:
        base_dir = os.getcwd()

    # Make paths absolute
    abs_path = os.path.abspath(path)
    abs_base = os.path.abspath(base_dir)

    # Get relative path
    try:
        return os.path.relpath(abs_path, abs_base)
    except ValueError:
        # Path is on different drive (Windows)
        return abs_path
