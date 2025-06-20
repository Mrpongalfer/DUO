"""
Git operation handlers for the Quantum Orchestrator.

Provides handlers for git operations such as clone, pull, commit, and push.
"""

import os
import subprocess
from typing import Any, Dict

from quantum_orchestrator.handlers import handler
from quantum_orchestrator.utils.logging_utils import get_logger
from quantum_orchestrator.utils.path_resolver import resolve_path
from quantum_orchestrator.utils.security import sanitize_path
from quantum_orchestrator.games.nexus_omniengine_v3.core.config import Config

logger = get_logger(__name__)
config = Config()


@handler(
    name="git_clone",
    description="Clones a git repository",
    parameters={
        "repository": {
            "type": "string",
            "description": "URL of the repository to clone",
        },
        "directory": {
            "type": "string",
            "description": "Local directory to clone into",
            "default": "",
        },
        "branch": {"type": "string", "description": "Branch to clone", "default": ""},
        "depth": {
            "type": "number",
            "description": "Depth of commit history to clone",
            "default": 0,
        },
    },
    returns={
        "success": {
            "type": "boolean",
            "description": "Whether the operation was successful",
        },
        "directory": {"type": "string", "description": "Path to the cloned repository"},
        "stdout": {"type": "string", "description": "Standard output from git"},
        "stderr": {"type": "string", "description": "Standard error from git"},
        "error": {"type": "string", "description": "Error message if operation failed"},
    },
)
def git_clone(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Clone a git repository.

    Args:
        params: Dictionary containing repository, directory, branch, and depth

    Returns:
        Dict containing success flag, directory, stdout, stderr, and error message if any
    """
    try:
        repository = params.get("repository", "")
        directory = params.get("directory", "")
        branch = params.get("branch", "")
        depth = params.get("depth", 0)

        # Validate repository URL
        if not repository:
            return {"success": False, "error": "No repository URL provided"}

        # Sanitize and resolve directory
        if directory:
            safe_dir = sanitize_path(directory)
            if not safe_dir:
                return {
                    "success": False,
                    "error": f"Invalid or unsafe path: {directory}",
                }
            directory = resolve_path(safe_dir)
        else:
            # Extract directory name from repository URL
            repo_name = repository.split("/")[-1]
            if repo_name.endswith(".git"):
                repo_name = repo_name[:-4]
            directory = resolve_path(repo_name)

        # Build git command
        cmd = ["git", "clone", repository]

        # Add branch if specified
        if branch:
            cmd.extend(["-b", branch])

        # Add depth if specified
        if depth > 0:
            cmd.extend(["--depth", str(depth)])

        # Add directory
        cmd.append(directory)

        # Execute git command
        logger.info(f"Cloning repository {repository} to {directory}")
        process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )

        stdout, stderr = process.communicate()
        success = process.returncode == 0

        if success:
            logger.info(f"Successfully cloned repository to {directory}")
            return {
                "success": True,
                "directory": directory,
                "stdout": stdout,
                "stderr": stderr,
            }
        else:
            logger.error(f"Failed to clone repository: {stderr}")
            return {
                "success": False,
                "directory": directory,
                "stdout": stdout,
                "stderr": stderr,
                "error": f"Git clone failed: {stderr}",
            }

    except Exception as e:
        logger.error(f"Error during git clone: {str(e)}")
        return {"success": False, "error": f"Error during git clone: {str(e)}"}


@handler(
    name="git_pull",
    description="Pulls changes from a remote repository",
    parameters={
        "directory": {
            "type": "string",
            "description": "Local repository directory",
            "default": "./",
        },
        "remote": {
            "type": "string",
            "description": "Remote repository name",
            "default": "origin",
        },
        "branch": {"type": "string", "description": "Branch to pull", "default": ""},
    },
    returns={
        "success": {
            "type": "boolean",
            "description": "Whether the operation was successful",
        },
        "directory": {"type": "string", "description": "Path to the repository"},
        "stdout": {"type": "string", "description": "Standard output from git"},
        "stderr": {"type": "string", "description": "Standard error from git"},
        "error": {"type": "string", "description": "Error message if operation failed"},
    },
)
def git_pull(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Pull changes from a remote repository.

    Args:
        params: Dictionary containing directory, remote, and branch

    Returns:
        Dict containing success flag, directory, stdout, stderr, and error message if any
    """
    try:
        directory = params.get("directory", "./")
        remote = params.get("remote", "origin")
        branch = params.get("branch", "")

        # Sanitize and resolve directory
        safe_dir = sanitize_path(directory)
        if not safe_dir:
            return {"success": False, "error": f"Invalid or unsafe path: {directory}"}
        directory = resolve_path(safe_dir)

        # Check if directory exists and is a git repository
        if not os.path.exists(os.path.join(directory, ".git")):
            return {
                "success": False,
                "directory": directory,
                "error": f"Not a git repository: {directory}",
            }

        # Build git command
        cmd = ["git", "pull", remote]

        # Add branch if specified
        if branch:
            cmd.append(branch)

        # Execute git command
        logger.info(f"Pulling changes in {directory}")
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=directory,
        )

        stdout, stderr = process.communicate()
        success = process.returncode == 0

        if success:
            logger.info(f"Successfully pulled changes in {directory}")
            return {
                "success": True,
                "directory": directory,
                "stdout": stdout,
                "stderr": stderr,
            }
        else:
            logger.error(f"Failed to pull changes: {stderr}")
            return {
                "success": False,
                "directory": directory,
                "stdout": stdout,
                "stderr": stderr,
                "error": f"Git pull failed: {stderr}",
            }

    except Exception as e:
        logger.error(f"Error during git pull: {str(e)}")
        return {"success": False, "error": f"Error during git pull: {str(e)}"}


@handler(
    name="git_commit",
    description="Commits changes to the local repository",
    parameters={
        "directory": {
            "type": "string",
            "description": "Local repository directory",
            "default": "./",
        },
        "message": {"type": "string", "description": "Commit message"},
        "add_all": {
            "type": "boolean",
            "description": "Whether to add all changes",
            "default": True,
        },
        "files": {
            "type": "array",
            "description": "Specific files to add",
            "default": [],
        },
    },
    returns={
        "success": {
            "type": "boolean",
            "description": "Whether the operation was successful",
        },
        "directory": {"type": "string", "description": "Path to the repository"},
        "stdout": {"type": "string", "description": "Standard output from git"},
        "stderr": {"type": "string", "description": "Standard error from git"},
        "error": {"type": "string", "description": "Error message if operation failed"},
    },
)
def git_commit(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Commit changes to the local repository.

    Args:
        params: Dictionary containing directory, message, add_all, and files

    Returns:
        Dict containing success flag, directory, stdout, stderr, and error message if any
    """
    try:
        directory = params.get("directory", "./")
        message = params.get("message", "")
        add_all = params.get("add_all", True)
        files = params.get("files", [])

        # Validate commit message
        if not message:
            return {"success": False, "error": "No commit message provided"}

        # Sanitize and resolve directory
        safe_dir = sanitize_path(directory)
        if not safe_dir:
            return {"success": False, "error": f"Invalid or unsafe path: {directory}"}
        directory = resolve_path(safe_dir)

        # Check if directory exists and is a git repository
        if not os.path.exists(os.path.join(directory, ".git")):
            return {
                "success": False,
                "directory": directory,
                "error": f"Not a git repository: {directory}",
            }

        # Add files to staging area
        if add_all:
            add_cmd = ["git", "add", "-A"]
        elif files:
            # Sanitize file paths
            safe_files = [sanitize_path(f) for f in files]
            if not all(safe_files):
                return {"success": False, "error": "Invalid or unsafe file paths"}
            add_cmd = ["git", "add"] + safe_files
        else:
            # Nothing to add
            return {
                "success": False,
                "directory": directory,
                "error": "No files specified to add",
            }

        # Execute git add command
        logger.info(f"Adding files in {directory}")
        add_process = subprocess.Popen(
            add_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=directory,
        )

        add_stdout, add_stderr = add_process.communicate()
        if add_process.returncode != 0:
            logger.error(f"Failed to add files: {add_stderr}")
            return {
                "success": False,
                "directory": directory,
                "stdout": add_stdout,
                "stderr": add_stderr,
                "error": f"Git add failed: {add_stderr}",
            }

        # Execute git commit command
        commit_cmd = ["git", "commit", "-m", message]

        logger.info(f"Committing changes in {directory}")
        commit_process = subprocess.Popen(
            commit_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=directory,
        )

        commit_stdout, commit_stderr = commit_process.communicate()
        success = commit_process.returncode == 0

        if success:
            logger.info(f"Successfully committed changes in {directory}")
            return {
                "success": True,
                "directory": directory,
                "stdout": commit_stdout,
                "stderr": commit_stderr,
            }
        else:
            logger.error(f"Failed to commit changes: {commit_stderr}")
            return {
                "success": False,
                "directory": directory,
                "stdout": commit_stdout,
                "stderr": commit_stderr,
                "error": f"Git commit failed: {commit_stderr}",
            }

    except Exception as e:
        logger.error(f"Error during git commit: {str(e)}")
        return {"success": False, "error": f"Error during git commit: {str(e)}"}


@handler(
    name="git_push",
    description="Pushes commits to a remote repository",
    parameters={
        "directory": {
            "type": "string",
            "description": "Local repository directory",
            "default": "./",
        },
        "remote": {
            "type": "string",
            "description": "Remote repository name",
            "default": "origin",
        },
        "branch": {"type": "string", "description": "Branch to push", "default": ""},
        "force": {
            "type": "boolean",
            "description": "Whether to force push",
            "default": False,
        },
    },
    returns={
        "success": {
            "type": "boolean",
            "description": "Whether the operation was successful",
        },
        "directory": {"type": "string", "description": "Path to the repository"},
        "stdout": {"type": "string", "description": "Standard output from git"},
        "stderr": {"type": "string", "description": "Standard error from git"},
        "error": {"type": "string", "description": "Error message if operation failed"},
    },
)
def git_push(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Push commits to a remote repository.

    Args:
        params: Dictionary containing directory, remote, branch, and force

    Returns:
        Dict containing success flag, directory, stdout, stderr, and error message if any
    """
    try:
        directory = params.get("directory", "./")
        remote = params.get("remote", "origin")
        branch = params.get("branch", "")
        force = params.get("force", False)

        # Sanitize and resolve directory
        safe_dir = sanitize_path(directory)
        if not safe_dir:
            return {"success": False, "error": f"Invalid or unsafe path: {directory}"}
        directory = resolve_path(safe_dir)

        # Check if directory exists and is a git repository
        if not os.path.exists(os.path.join(directory, ".git")):
            return {
                "success": False,
                "directory": directory,
                "error": f"Not a git repository: {directory}",
            }

        # Build git command
        cmd = ["git", "push", remote]

        # Add branch if specified
        if branch:
            cmd.append(branch)

        # Add force flag if specified
        if force:
            cmd.append("--force")

        # Execute git command
        logger.info(f"Pushing changes to {remote} from {directory}")
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=directory,
        )

        stdout, stderr = process.communicate()
        success = process.returncode == 0

        if success:
            logger.info(f"Successfully pushed changes to {remote}")
            return {
                "success": True,
                "directory": directory,
                "stdout": stdout,
                "stderr": stderr,
            }
        else:
            logger.error(f"Failed to push changes: {stderr}")
            return {
                "success": False,
                "directory": directory,
                "stdout": stdout,
                "stderr": stderr,
                "error": f"Git push failed: {stderr}",
            }

    except Exception as e:
        logger.error(f"Error during git push: {str(e)}")
        return {"success": False, "error": f"Error during git push: {str(e)}"}
