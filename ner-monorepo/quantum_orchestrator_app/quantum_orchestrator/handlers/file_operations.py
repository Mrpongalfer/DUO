"""
File operation handlers for the Quantum Orchestrator.

Provides handlers for creating, modifying, reading, deleting, and listing files.
"""

import os
import stat
import shutil
from typing import Any, Dict

from quantum_orchestrator.handlers import handler
from quantum_orchestrator.utils.path_resolver import resolve_path
from quantum_orchestrator.utils.security import sanitize_path
from quantum_orchestrator.utils.logging_utils import get_logger

logger = get_logger(__name__)


@handler(
    name="create_file",
    description="Creates a new file with the given content",
    parameters={
        "path": {"type": "string", "description": "Path to the file to create"},
        "content": {"type": "string", "description": "Content to write to the file"},
        "overwrite": {
            "type": "boolean",
            "description": "Whether to overwrite if file exists",
            "default": False,
        },
        "make_executable": {
            "type": "boolean",
            "description": "Add executable permissions",
            "default": False,
        },
    },
    returns={
        "success": {
            "type": "boolean",
            "description": "Whether the operation was successful",
        },
        "path": {"type": "string", "description": "Absolute path to the created file"},
        "error": {"type": "string", "description": "Error message if operation failed"},
    },
)
def create_file(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a new file with the given content.

    Args:
        params: Dictionary containing path, content, overwrite, and make_executable

    Returns:
        Dict containing success flag, path, and error message if any
    """
    try:
        file_path = params.get("path", "")
        content = params.get("content", "")
        overwrite = params.get("overwrite", False)
        make_executable = params.get("make_executable", False)

        # Validate and resolve path
        if not file_path:
            return {"success": False, "error": "No file path provided"}

        # Check if path is safe
        safe_path = sanitize_path(file_path)
        if not safe_path:
            return {"success": False, "error": f"Invalid or unsafe path: {file_path}"}

        # Resolve path
        abs_path = resolve_path(safe_path)

        # Ensure directory exists
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)

        # Check if file exists and handle overwrite
        if os.path.exists(abs_path) and not overwrite:
            return {
                "success": False,
                "error": f"File already exists: {abs_path}",
                "path": abs_path,
            }

        # Write content to file
        with open(abs_path, "w") as f:
            f.write(content)

        # Make executable if requested
        if make_executable:
            current_mode = os.stat(abs_path).st_mode
            os.chmod(
                abs_path, current_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
            )

        logger.info(f"Created file: {abs_path}")
        return {"success": True, "path": abs_path}

    except Exception as e:
        logger.error(f"Error creating file: {str(e)}")
        return {"success": False, "error": f"Error creating file: {str(e)}"}


@handler(
    name="modify_file",
    description="Modifies an existing file",
    parameters={
        "path": {"type": "string", "description": "Path to the file to modify"},
        "content": {"type": "string", "description": "New content for the file"},
        "append": {
            "type": "boolean",
            "description": "Whether to append to existing content",
            "default": False,
        },
        "create_if_missing": {
            "type": "boolean",
            "description": "Whether to create the file if it doesn't exist",
            "default": False,
        },
        "make_executable": {
            "type": "boolean",
            "description": "Add executable permissions",
            "default": False,
        },
    },
    returns={
        "success": {
            "type": "boolean",
            "description": "Whether the operation was successful",
        },
        "path": {"type": "string", "description": "Absolute path to the modified file"},
        "created": {"type": "boolean", "description": "Whether a new file was created"},
        "error": {"type": "string", "description": "Error message if operation failed"},
    },
)
def modify_file(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Modify an existing file.

    Args:
        params: Dictionary containing path, content, append, create_if_missing, and make_executable

    Returns:
        Dict containing success flag, path, created flag, and error message if any
    """
    try:
        file_path = params.get("path", "")
        content = params.get("content", "")
        append = params.get("append", False)
        create_if_missing = params.get("create_if_missing", False)
        make_executable = params.get("make_executable", False)

        # Validate and resolve path
        if not file_path:
            return {"success": False, "error": "No file path provided"}

        # Check if path is safe
        safe_path = sanitize_path(file_path)
        if not safe_path:
            return {"success": False, "error": f"Invalid or unsafe path: {file_path}"}

        # Resolve path
        abs_path = resolve_path(safe_path)

        # Check if file exists
        file_exists = os.path.exists(abs_path)
        created = False

        if not file_exists:
            if create_if_missing:
                # Create parent directories if needed
                os.makedirs(os.path.dirname(abs_path), exist_ok=True)
                created = True
            else:
                return {
                    "success": False,
                    "error": f"File not found: {abs_path}",
                    "path": abs_path,
                }

        # Write or append content
        mode = "a" if append else "w"
        with open(abs_path, mode) as f:
            f.write(content)

        # Make executable if requested
        if make_executable:
            current_mode = os.stat(abs_path).st_mode
            os.chmod(
                abs_path, current_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
            )

        logger.info(f"Modified file: {abs_path}")
        return {"success": True, "path": abs_path, "created": created}

    except Exception as e:
        logger.error(f"Error modifying file: {str(e)}")
        return {"success": False, "error": f"Error modifying file: {str(e)}"}


@handler(
    name="read_file",
    description="Reads the content of a file",
    parameters={
        "path": {"type": "string", "description": "Path to the file to read"},
        "binary": {
            "type": "boolean",
            "description": "Whether to read in binary mode",
            "default": False,
        },
        "encoding": {
            "type": "string",
            "description": "Encoding to use for text files",
            "default": "utf-8",
        },
    },
    returns={
        "success": {
            "type": "boolean",
            "description": "Whether the operation was successful",
        },
        "content": {
            "type": "string",
            "description": "Content of the file (base64 encoded if binary)",
        },
        "path": {"type": "string", "description": "Absolute path to the file"},
        "error": {"type": "string", "description": "Error message if operation failed"},
    },
)
def read_file(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Read the content of a file.

    Args:
        params: Dictionary containing path, binary, and encoding

    Returns:
        Dict containing success flag, content, path, and error message if any
    """
    try:
        file_path = params.get("path", "")
        binary = params.get("binary", False)
        encoding = params.get("encoding", "utf-8")

        # Validate and resolve path
        if not file_path:
            return {"success": False, "error": "No file path provided"}

        # Check if path is safe
        safe_path = sanitize_path(file_path)
        if not safe_path:
            return {"success": False, "error": f"Invalid or unsafe path: {file_path}"}

        # Resolve path
        abs_path = resolve_path(safe_path)

        # Check if file exists
        if not os.path.exists(abs_path):
            return {
                "success": False,
                "error": f"File not found: {abs_path}",
                "path": abs_path,
            }

        # Read file content
        if binary:
            import base64

            with open(abs_path, "rb") as f:
                content = base64.b64encode(f.read()).decode("ascii")
        else:
            with open(abs_path, "r", encoding=encoding) as f:
                content = f.read()

        logger.info(f"Read file: {abs_path}")
        return {"success": True, "content": content, "path": abs_path}

    except UnicodeDecodeError:
        # Handle encoding errors
        logger.error(f"Encoding error reading file {file_path}. Try binary mode.")
        return {
            "success": False,
            "error": "File encoding error. The file may be binary, try with binary=true",
            "path": abs_path,
        }
    except Exception as e:
        logger.error(f"Error reading file: {str(e)}")
        return {"success": False, "error": f"Error reading file: {str(e)}"}


@handler(
    name="delete_file",
    description="Deletes a file or directory",
    parameters={
        "path": {
            "type": "string",
            "description": "Path to the file or directory to delete",
        },
        "recursive": {
            "type": "boolean",
            "description": "Whether to delete directories recursively",
            "default": False,
        },
    },
    returns={
        "success": {
            "type": "boolean",
            "description": "Whether the operation was successful",
        },
        "path": {
            "type": "string",
            "description": "Absolute path to the deleted file or directory",
        },
        "error": {"type": "string", "description": "Error message if operation failed"},
    },
)
def delete_file(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Delete a file or directory.

    Args:
        params: Dictionary containing path and recursive

    Returns:
        Dict containing success flag, path, and error message if any
    """
    try:
        file_path = params.get("path", "")
        recursive = params.get("recursive", False)

        # Validate and resolve path
        if not file_path:
            return {"success": False, "error": "No file path provided"}

        # Check if path is safe
        safe_path = sanitize_path(file_path)
        if not safe_path:
            return {"success": False, "error": f"Invalid or unsafe path: {file_path}"}

        # Resolve path
        abs_path = resolve_path(safe_path)

        # Check if file exists
        if not os.path.exists(abs_path):
            return {
                "success": False,
                "error": f"File or directory not found: {abs_path}",
                "path": abs_path,
            }

        # Delete file or directory
        if os.path.isdir(abs_path):
            if recursive:
                shutil.rmtree(abs_path)
            else:
                os.rmdir(abs_path)
        else:
            os.remove(abs_path)

        logger.info(f"Deleted: {abs_path}")
        return {"success": True, "path": abs_path}

    except Exception as e:
        logger.error(f"Error deleting file: {str(e)}")
        return {"success": False, "error": f"Error deleting file: {str(e)}"}


@handler(
    name="list_files",
    description="Lists files and directories in a specified path",
    parameters={
        "path": {
            "type": "string",
            "description": "Path to list files from",
            "default": "./",
        },
        "recursive": {
            "type": "boolean",
            "description": "Whether to list recursively",
            "default": False,
        },
        "include_hidden": {
            "type": "boolean",
            "description": "Whether to include hidden files",
            "default": False,
        },
        "pattern": {
            "type": "string",
            "description": "Glob pattern to filter files",
            "default": "*",
        },
    },
    returns={
        "success": {
            "type": "boolean",
            "description": "Whether the operation was successful",
        },
        "files": {"type": "array", "description": "List of file information objects"},
        "path": {"type": "string", "description": "Absolute path that was listed"},
        "error": {"type": "string", "description": "Error message if operation failed"},
    },
)
def list_files(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    List files and directories in a specified path.

    Args:
        params: Dictionary containing path, recursive, include_hidden, and pattern

    Returns:
        Dict containing success flag, files list, path, and error message if any
    """
    try:
        import glob

        dir_path = params.get("path", "./")
        recursive = params.get("recursive", False)
        include_hidden = params.get("include_hidden", False)
        pattern = params.get("pattern", "*")

        # Validate and resolve path
        if not dir_path:
            dir_path = "./"

        # Check if path is safe
        safe_path = sanitize_path(dir_path)
        if not safe_path:
            return {"success": False, "error": f"Invalid or unsafe path: {dir_path}"}

        # Resolve path
        abs_path = resolve_path(safe_path)

        # Check if directory exists
        if not os.path.exists(abs_path) or not os.path.isdir(abs_path):
            return {
                "success": False,
                "error": f"Directory not found: {abs_path}",
                "path": abs_path,
            }

        # Build glob pattern
        if recursive:
            glob_pattern = os.path.join(abs_path, "**", pattern)
        else:
            glob_pattern = os.path.join(abs_path, pattern)

        # List files
        files = []
        for file_path in glob.glob(glob_pattern, recursive=recursive):
            # Skip hidden files if not included
            if not include_hidden and os.path.basename(file_path).startswith("."):
                continue

            # Get file stats
            stats = os.stat(file_path)

            # Create file info object
            file_info = {
                "path": file_path,
                "name": os.path.basename(file_path),
                "size": stats.st_size,
                "modified": stats.st_mtime,
                "is_dir": os.path.isdir(file_path),
            }

            files.append(file_info)

        logger.info(f"Listed {len(files)} files in {abs_path}")
        return {"success": True, "files": files, "path": abs_path}

    except Exception as e:
        logger.error(f"Error listing files: {str(e)}")
        return {"success": False, "error": f"Error listing files: {str(e)}"}
