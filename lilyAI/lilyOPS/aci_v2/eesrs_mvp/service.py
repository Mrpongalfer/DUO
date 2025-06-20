"""
EESRServiceMVP: SDSS-compliant implementation for EESRS v2.0 MVP.
Date: June 3, 2025
Author: Lily AI for The Architect (ACI v2.0 Project)
"""

import datetime
from typing import Any

from .exceptions import (
    EchoSigilProcessingError,
    EESRSError,
    FileNotFoundErrorInRepoError,
    GitHubAPIError,
    RepositoryConfigurationError,
)

# from aci_v2.acls_mvp.service import ACIServiceMVP  # For type hinting
from .github_client import GitHubClientMVP

ACIServiceMVP = Any  # Placeholder for type hinting


class EESRServiceMVP:
    """
    Externalized Evolution & State Repository Service (EESRS) MVP implementation.

    This service interfaces with the Architect's Master GitHub Repository to fetch
    Proto-Lily's GSRA/EDL and the latest Echo Sigil, and to prepare new Echo Sigil
    commit details for the Architect.
    """

    MODULE_NAME: str = "EESRS_MVP"
    PROTO_LILY_GSRA_EDL_REPO_PATH: str = "lily_foundation/proto_lily_gsra_edl_master.md"
    PROTO_LILY_ECHO_SIGIL_DIR_REPO_PATH: str = "lily_foundation/echo_sigils/"

    def __init__(self, acl_service: ACIServiceMVP) -> None:
        """
        Initializes the EESRServiceMVP using ACLS for GitHub credentials and repo info.

        Args:
            acl_service (ACIServiceMVP): Reference to the ACLS MVP service.

        Raises:
            RepositoryConfigurationError: If required config is missing or invalid.
            GitHubAPIError: If GitHub client initialization fails.
        """
        self.acls = acl_service
        self.logger = self.acls.get_logger(f"ACI.{self.MODULE_NAME}")
        try:
            self.github_client: GitHubClientMVP | None = GitHubClientMVP(
                acl_service=self.acls
            )
            self.logger.info(
                "EESRS Service MVP Initialized successfully with GitHub client."
            )
        except (RepositoryConfigurationError, GitHubAPIError):
            self.logger.critical(
                "EESRS_MVP cannot function: GitHub client initialization failed. "
                "Please configure GitHub PAT and repository URL in ACI settings via ACLS."
            )
            self.github_client = None
        except Exception as e:
            self.logger.error(f"Unexpected error initializing EESRS GitHub client: {e}")
            self.github_client = None
        if self.github_client is None:
            self.logger.error(
                "EESRS Service MVP Initialized with NON-FUNCTIONAL GitHub client due to configuration errors."
            )

    def _ensure_client_ready(self) -> GitHubClientMVP:
        """
        Ensures the GitHub client is initialized and functional.

        Returns:
            GitHubClientMVP: The initialized GitHub client.

        Raises:
            EESRSError: If the GitHub client is not ready.
        """
        if self.github_client is None or not isinstance(
            self.github_client, GitHubClientMVP
        ):
            self.logger.error("EESRS GitHub client is not available or not configured.")
            raise EESRSError(
                "EESRS GitHub client not initialized. Check ACI configuration for PAT and repository URL."
            )
        return self.github_client

    def get_gsra_edl_content(self) -> str:
        """
        Fetches the GSRA/EDL file for Proto-Lily from the repository as Markdown.

        Returns:
            str: The Markdown content of the GSRA/EDL file.

        Raises:
            FileNotFoundErrorInRepoError: If the file is not found in the repository.
            EESRSError: For other errors.
        """
        client = self._ensure_client_ready()
        self.logger.info(
            f"Fetching GSRA/EDL from repo path: {self.PROTO_LILY_GSRA_EDL_REPO_PATH}"
        )
        try:
            content_str = client.get_file_content(self.PROTO_LILY_GSRA_EDL_REPO_PATH)
            return content_str
        except FileNotFoundErrorInRepoError:
            self.logger.critical(
                f"Critical: Proto-Lily GSRA/EDL file not found at '{self.PROTO_LILY_GSRA_EDL_REPO_PATH}' in configured repository."
            )
            raise
        except GitHubAPIError as e:
            self.logger.error(f"GitHub API error while fetching GSRA/EDL: {e}")
            raise
        except Exception as e_unexp:
            self.logger.error(f"Unexpected error fetching GSRA/EDL: {e_unexp}")
            raise EESRSError(
                f"Unexpected error fetching GSRA/EDL: {e_unexp}",
                original_exception=e_unexp,
            )

    def get_latest_proto_lily_echo_sigil_content(self) -> str | None:
        """
        Fetches the latest Echo Sigil for Proto-Lily from the repository.

        Returns:
            Optional[str]: The content of the latest Echo Sigil file, or None if not found.

        Raises:
            EchoSigilProcessingError: For GitHub API errors while fetching Echo Sigil.
            EESRSError: For other errors.
        """
        client = self._ensure_client_ready()
        self.logger.info(
            f"Fetching latest Proto-Lily Echo Sigil from repo dir: {self.PROTO_LILY_ECHO_SIGIL_DIR_REPO_PATH}"
        )
        try:
            result_tuple = client.get_latest_file_from_directory_by_timestamp_in_name(
                self.PROTO_LILY_ECHO_SIGIL_DIR_REPO_PATH, file_suffix="_sigil.json"
            )
            if result_tuple is None:
                self.logger.info("No Echo Sigils found for Proto-Lily.")
                return None
            _filename, content_str = result_tuple
            self.logger.info(
                f"Latest Proto-Lily Echo Sigil '{_filename}' content retrieved."
            )
            return content_str
        except FileNotFoundErrorInRepoError:
            self.logger.warning(
                "Proto-Lily Echo Sigil directory not found or no sigils present."
            )
            return None
        except GitHubAPIError as e:
            self.logger.error(
                "GitHub API error while fetching latest Echo Sigil for Proto-Lily."
            )
            raise EchoSigilProcessingError(
                "GitHub API error while fetching latest Echo Sigil for Proto-Lily.",
                original_exception=e,
            )
        except Exception as e_unexp:
            self.logger.error(
                f"Unexpected error fetching latest Proto-Lily Echo Sigil: {e_unexp}"
            )
            raise EESRSError(
                f"Unexpected error fetching latest Proto-Lily Echo Sigil: {e_unexp}",
                original_exception=e_unexp,
            )

    def prepare_new_echo_sigil_for_architect_commit(
        self, sigil_content_json: str, persona_id: str, lily_creation_timestamp_utc: str
    ) -> dict[str, str]:
        """
        Prepares a new Echo Sigil file for Architect commit (returns path/content/message, does not commit).

        Args:
            sigil_content_json (str): The Echo Sigil content as a JSON string.
            persona_id (str): Persona identifier (e.g., "proto_lily").
            lily_creation_timestamp_utc (str): ISO timestamp when Lily generated the sigil.

        Returns:
            Dict[str, str]: Dict with 'file_path_in_repo', 'content_to_commit', and 'suggested_commit_message'.
        """
        self.logger.info(
            f"Preparing new Echo Sigil details for Architect commit (persona: '{persona_id}')."
        )
        if persona_id == "proto_lily":
            sigil_dir_in_repo = self.PROTO_LILY_ECHO_SIGIL_DIR_REPO_PATH
        else:
            sigil_dir_in_repo = f"lily_personas/{persona_id}/echo_sigils/"
        dt_obj = datetime.datetime.fromisoformat(
            lily_creation_timestamp_utc.replace("Z", "+00:00")
        )
        timestamp_for_filename = dt_obj.strftime("%Y%m%d_%H%M%S")
        suggested_filename = f"{timestamp_for_filename}_{persona_id}_sigil.json"
        full_file_path_in_repo = f"{sigil_dir_in_repo.rstrip('/')}/{suggested_filename}"
        suggested_commit_message = (
            f"feat(lily-{persona_id}): Add Echo Sigil {timestamp_for_filename}"
        )
        return {
            "file_path_in_repo": full_file_path_in_repo,
            "content_to_commit": sigil_content_json,
            "suggested_commit_message": suggested_commit_message,
        }
