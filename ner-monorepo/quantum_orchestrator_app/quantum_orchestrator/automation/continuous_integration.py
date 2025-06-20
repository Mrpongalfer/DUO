"""
Continuous Integration: Integration points for CI/CD pipelines.

Provides functions and classes for integrating with CI/CD workflows,
such as handling webhooks and triggering builds.
"""

import os
import json
import hmac
import hashlib
import requests
from typing import Any, Dict

from quantum_orchestrator.utils.logging_utils import get_logger
from quantum_orchestrator.games.nexus_omniengine_v3.core.config import Config

logger = get_logger(__name__)
config = Config()


class WebhookHandler:
    """Handler for CI/CD webhooks."""

    def __init__(self, orchestrator=None):
        """
        Initialize the webhook handler.

        Args:
            orchestrator: The orchestrator instance to use
        """
        self.orchestrator = orchestrator
        self.webhook_secret = config.get(
            "ci", "webhook_secret", os.environ.get("WEBHOOK_SECRET", "")
        )
        self.handlers = {
            "github": self._handle_github_webhook,
            "gitlab": self._handle_gitlab_webhook,
            "bitbucket": self._handle_bitbucket_webhook,
            "generic": self._handle_generic_webhook,
        }

    def handle_webhook(
        self, source: str, payload: Dict[str, Any], headers: Dict[str, str] = None
    ) -> Dict[str, Any]:
        """
        Handle a webhook from a CI/CD system.

        Args:
            source: Source of the webhook (github, gitlab, etc.)
            payload: Webhook payload
            headers: HTTP headers (for signature verification)

        Returns:
            Dict containing handling result
        """
        if source not in self.handlers:
            logger.error(f"Unknown webhook source: {source}")
            return {"success": False, "error": f"Unknown webhook source: {source}"}

        # Verify webhook signature if applicable
        if headers and source in ["github", "gitlab"]:
            if not self._verify_webhook_signature(source, payload, headers):
                logger.error(f"Invalid webhook signature from {source}")
                return {"success": False, "error": "Invalid webhook signature"}

        # Handle the webhook
        handler = self.handlers[source]
        return handler(payload)

    def _verify_webhook_signature(
        self, source: str, payload: Dict[str, Any], headers: Dict[str, str]
    ) -> bool:
        """
        Verify the signature of a webhook payload.

        Args:
            source: Source of the webhook
            payload: Webhook payload
            headers: HTTP headers

        Returns:
            bool: True if signature is valid
        """
        if not self.webhook_secret:
            logger.warning(
                "No webhook secret configured, skipping signature verification"
            )
            return True

        try:
            # Create JSON string from payload
            payload_str = json.dumps(payload, separators=(",", ":"))

            if source == "github":
                # GitHub uses SHA-256 HMAC
                header_sig = headers.get("X-Hub-Signature-256", "")
                if not header_sig.startswith("sha256="):
                    return False

                header_sig = header_sig[7:]  # Remove "sha256=" prefix

                # Calculate expected signature
                mac = hmac.new(
                    self.webhook_secret.encode("utf-8"),
                    payload_str.encode("utf-8"),
                    hashlib.sha256,
                )
                expected_sig = mac.hexdigest()

                return hmac.compare_digest(header_sig, expected_sig)

            elif source == "gitlab":
                # GitLab uses a token in a header
                token = headers.get("X-Gitlab-Token", "")
                return token == self.webhook_secret

            return True

        except Exception as e:
            logger.error(f"Error verifying webhook signature: {str(e)}")
            return False

    def _handle_github_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle a webhook from GitHub.

        Args:
            payload: GitHub webhook payload

        Returns:
            Dict containing handling result
        """
        if not self.orchestrator:
            return {"success": False, "error": "Orchestrator not available"}

        try:
            # Get event type from payload
            event_type = payload.get("action", "")

            # Get repository information
            repo = payload.get("repository", {})
            repo_name = repo.get("full_name", "")
            repo_url = repo.get("clone_url", "")

            # Create workflow based on event type
            if event_type == "push":
                # For push events, clone repo and run tests
                workflow = [
                    {
                        "id": "clone_repo",
                        "type": "direct",
                        "handler": "git_clone",
                        "params": {
                            "repository": repo_url,
                            "directory": repo_name.split("/")[-1],
                        },
                    },
                    {
                        "id": "run_tests",
                        "type": "direct",
                        "handler": "run_tests",
                        "params": {
                            "path": repo_name.split("/")[-1],
                            "framework": "pytest",
                        },
                        "dependencies": ["clone_repo"],
                    },
                ]

            elif event_type in ["opened", "synchronize"]:
                # For PR events, clone repo, run linter and tests
                workflow = [
                    {
                        "id": "clone_repo",
                        "type": "direct",
                        "handler": "git_clone",
                        "params": {
                            "repository": repo_url,
                            "directory": repo_name.split("/")[-1],
                        },
                    },
                    {
                        "id": "run_linter",
                        "type": "direct",
                        "handler": "run_linter",
                        "params": {
                            "path": repo_name.split("/")[-1],
                            "linter": "flake8",
                        },
                        "dependencies": ["clone_repo"],
                    },
                    {
                        "id": "run_tests",
                        "type": "direct",
                        "handler": "run_tests",
                        "params": {
                            "path": repo_name.split("/")[-1],
                            "framework": "pytest",
                        },
                        "dependencies": ["clone_repo"],
                    },
                ]

            else:
                # Unknown event type
                return {
                    "success": False,
                    "error": f"Unsupported GitHub event type: {event_type}",
                }

            # Create workflow instruction
            instruction = {"type": "workflow", "steps": workflow}

            # Execute workflow asynchronously
            import asyncio

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(
                self.orchestrator.execute_instruction(instruction)
            )
            loop.close()

            return {"success": result.get("success", False), "result": result}

        except Exception as e:
            logger.error(f"Error handling GitHub webhook: {str(e)}")
            return {
                "success": False,
                "error": f"Error handling GitHub webhook: {str(e)}",
            }

    def _handle_gitlab_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle a webhook from GitLab.

        Args:
            payload: GitLab webhook payload

        Returns:
            Dict containing handling result
        """
        if not self.orchestrator:
            return {"success": False, "error": "Orchestrator not available"}

        try:
            # Get event type from payload
            event_type = payload.get("object_kind", "")

            # Get repository information
            project = payload.get("project", {})
            repo_name = project.get("path_with_namespace", "")
            repo_url = project.get("git_http_url", "")

            # Create workflow based on event type
            if event_type == "push":
                # For push events, clone repo and run tests
                workflow = [
                    {
                        "id": "clone_repo",
                        "type": "direct",
                        "handler": "git_clone",
                        "params": {
                            "repository": repo_url,
                            "directory": repo_name.split("/")[-1],
                        },
                    },
                    {
                        "id": "run_tests",
                        "type": "direct",
                        "handler": "run_tests",
                        "params": {
                            "path": repo_name.split("/")[-1],
                            "framework": "pytest",
                        },
                        "dependencies": ["clone_repo"],
                    },
                ]

            elif event_type == "merge_request":
                # For MR events, clone repo, run linter and tests
                workflow = [
                    {
                        "id": "clone_repo",
                        "type": "direct",
                        "handler": "git_clone",
                        "params": {
                            "repository": repo_url,
                            "directory": repo_name.split("/")[-1],
                        },
                    },
                    {
                        "id": "run_linter",
                        "type": "direct",
                        "handler": "run_linter",
                        "params": {
                            "path": repo_name.split("/")[-1],
                            "linter": "flake8",
                        },
                        "dependencies": ["clone_repo"],
                    },
                    {
                        "id": "run_tests",
                        "type": "direct",
                        "handler": "run_tests",
                        "params": {
                            "path": repo_name.split("/")[-1],
                            "framework": "pytest",
                        },
                        "dependencies": ["clone_repo"],
                    },
                ]

            else:
                # Unknown event type
                return {
                    "success": False,
                    "error": f"Unsupported GitLab event type: {event_type}",
                }

            # Create workflow instruction
            instruction = {"type": "workflow", "steps": workflow}

            # Execute workflow asynchronously
            import asyncio

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(
                self.orchestrator.execute_instruction(instruction)
            )
            loop.close()

            return {"success": result.get("success", False), "result": result}

        except Exception as e:
            logger.error(f"Error handling GitLab webhook: {str(e)}")
            return {
                "success": False,
                "error": f"Error handling GitLab webhook: {str(e)}",
            }

    def _handle_bitbucket_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle a webhook from Bitbucket.

        Args:
            payload: Bitbucket webhook payload

        Returns:
            Dict containing handling result
        """
        if not self.orchestrator:
            return {"success": False, "error": "Orchestrator not available"}

        try:
            # Get event type from payload
            event_key = payload.get("eventKey", "")

            # Get repository information
            repo = payload.get("repository", {})
            repo_name = repo.get("full_name", "")
            links = repo.get("links", {})
            clone_links = links.get("clone", [])

            # Find HTTPS clone URL
            repo_url = ""
            for link in clone_links:
                if link.get("name") == "https":
                    repo_url = link.get("href", "")
                    break

            if not repo_url:
                return {
                    "success": False,
                    "error": "Could not find HTTPS clone URL in payload",
                }

            # Create workflow based on event type
            if event_key == "repo:push":
                # For push events, clone repo and run tests
                workflow = [
                    {
                        "id": "clone_repo",
                        "type": "direct",
                        "handler": "git_clone",
                        "params": {
                            "repository": repo_url,
                            "directory": repo_name.split("/")[-1],
                        },
                    },
                    {
                        "id": "run_tests",
                        "type": "direct",
                        "handler": "run_tests",
                        "params": {
                            "path": repo_name.split("/")[-1],
                            "framework": "pytest",
                        },
                        "dependencies": ["clone_repo"],
                    },
                ]

            elif event_key in ["pullrequest:created", "pullrequest:updated"]:
                # For PR events, clone repo, run linter and tests
                workflow = [
                    {
                        "id": "clone_repo",
                        "type": "direct",
                        "handler": "git_clone",
                        "params": {
                            "repository": repo_url,
                            "directory": repo_name.split("/")[-1],
                        },
                    },
                    {
                        "id": "run_linter",
                        "type": "direct",
                        "handler": "run_linter",
                        "params": {
                            "path": repo_name.split("/")[-1],
                            "linter": "flake8",
                        },
                        "dependencies": ["clone_repo"],
                    },
                    {
                        "id": "run_tests",
                        "type": "direct",
                        "handler": "run_tests",
                        "params": {
                            "path": repo_name.split("/")[-1],
                            "framework": "pytest",
                        },
                        "dependencies": ["clone_repo"],
                    },
                ]

            else:
                # Unknown event type
                return {
                    "success": False,
                    "error": f"Unsupported Bitbucket event type: {event_key}",
                }

            # Create workflow instruction
            instruction = {"type": "workflow", "steps": workflow}

            # Execute workflow asynchronously
            import asyncio

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(
                self.orchestrator.execute_instruction(instruction)
            )
            loop.close()

            return {"success": result.get("success", False), "result": result}

        except Exception as e:
            logger.error(f"Error handling Bitbucket webhook: {str(e)}")
            return {
                "success": False,
                "error": f"Error handling Bitbucket webhook: {str(e)}",
            }

    def _handle_generic_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle a generic webhook.

        Args:
            payload: Webhook payload

        Returns:
            Dict containing handling result
        """
        if not self.orchestrator:
            return {"success": False, "error": "Orchestrator not available"}

        try:
            # Check if payload contains instructions
            if "instruction" in payload:
                # Execute the instruction directly
                instruction = payload["instruction"]

                # Execute instruction asynchronously
                import asyncio

                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(
                    self.orchestrator.execute_instruction(instruction)
                )
                loop.close()

                return {"success": result.get("success", False), "result": result}

            else:
                return {
                    "success": False,
                    "error": "Generic webhook payload does not contain an instruction",
                }

        except Exception as e:
            logger.error(f"Error handling generic webhook: {str(e)}")
            return {
                "success": False,
                "error": f"Error handling generic webhook: {str(e)}",
            }


class BuildTrigger:
    """Trigger builds in CI/CD systems."""

    def __init__(self):
        """Initialize the build trigger."""
        pass

    def trigger_github_workflow(
        self,
        repo: str,
        workflow_id: str,
        ref: str = "main",
        inputs: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        Trigger a GitHub Actions workflow.

        Args:
            repo: Repository name (owner/repo)
            workflow_id: Workflow ID or file name
            ref: Git reference (branch, tag, SHA)
            inputs: Workflow inputs

        Returns:
            Dict containing trigger result
        """
        # Get GitHub token
        token = os.environ.get("GITHUB_TOKEN")
        if not token:
            return {"success": False, "error": "GitHub token not available"}

        try:
            # Prepare request
            url = f"https://api.github.com/repos/{repo}/actions/workflows/{workflow_id}/dispatches"
            headers = {
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3+json",
            }
            data = {"ref": ref}

            if inputs:
                data["inputs"] = inputs

            # Trigger workflow
            response = requests.post(url, headers=headers, json=data)

            if response.status_code in [204, 200]:
                return {"success": True, "message": "GitHub workflow triggered"}
            else:
                return {
                    "success": False,
                    "error": f"Failed to trigger GitHub workflow: {response.text}",
                    "status_code": response.status_code,
                }

        except Exception as e:
            logger.error(f"Error triggering GitHub workflow: {str(e)}")
            return {
                "success": False,
                "error": f"Error triggering GitHub workflow: {str(e)}",
            }

    def trigger_gitlab_pipeline(
        self, project_id: str, ref: str = "main", variables: Dict[str, str] = None
    ) -> Dict[str, Any]:
        """
        Trigger a GitLab CI pipeline.

        Args:
            project_id: Project ID
            ref: Git reference (branch, tag, SHA)
            variables: Pipeline variables

        Returns:
            Dict containing trigger result
        """
        # Get GitLab token
        token = os.environ.get("GITLAB_TOKEN")
        if not token:
            return {"success": False, "error": "GitLab token not available"}

        try:
            # Prepare request
            url = f"https://gitlab.com/api/v4/projects/{project_id}/pipeline"
            headers = {"Private-Token": token}
            data = {"ref": ref}

            if variables:
                data["variables"] = [
                    {"key": k, "value": v} for k, v in variables.items()
                ]

            # Trigger pipeline
            response = requests.post(url, headers=headers, data=data)

            if response.status_code in [201, 200]:
                return {
                    "success": True,
                    "message": "GitLab pipeline triggered",
                    "pipeline_id": response.json().get("id"),
                }
            else:
                return {
                    "success": False,
                    "error": f"Failed to trigger GitLab pipeline: {response.text}",
                    "status_code": response.status_code,
                }

        except Exception as e:
            logger.error(f"Error triggering GitLab pipeline: {str(e)}")
            return {
                "success": False,
                "error": f"Error triggering GitLab pipeline: {str(e)}",
            }


# Global webhook handler instance
_webhook_handler = None


def get_webhook_handler(orchestrator=None) -> WebhookHandler:
    """
    Get the global webhook handler instance.

    Args:
        orchestrator: The orchestrator instance to use

    Returns:
        WebhookHandler: The webhook handler
    """
    global _webhook_handler
    if _webhook_handler is None:
        _webhook_handler = WebhookHandler(orchestrator)
    elif orchestrator is not None and _webhook_handler.orchestrator is None:
        _webhook_handler.orchestrator = orchestrator

    return _webhook_handler
