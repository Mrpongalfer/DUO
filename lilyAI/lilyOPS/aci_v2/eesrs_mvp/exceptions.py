"""
Custom exceptions for EESRS v2.0 MVP.
Date: June 3, 2025
Author: Lily AI for The Architect (ACI v2.0 Project)
"""

from typing import Any

from aci_v2.common_exceptions import ACIError


class EESRSError(ACIError):
    """Base exception for EESRS MVP errors."""

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
        original_exception: Exception | None = None,
    ):
        super().__init__(message)
        self.details = details
        self.original_exception = original_exception

    def __str__(self) -> str:
        base = super().__str__()
        if self.details:
            base += f" | Details: {self.details}"
        if self.original_exception:
            base += f" | Caused by: {repr(self.original_exception)}"
        return base


class GitHubAPIError(EESRSError):
    """Raised for errors interacting with the GitHub API itself (e.g., network, auth, rate limits)."""

    pass


class FileNotFoundErrorInRepoError(EESRSError):
    """Raised when a specified file or directory is not found in the GitHub repository via API."""

    pass


class RepositoryConfigurationError(EESRSError):
    """Raised if essential GitHub repository configuration (owner, repo name, PAT from ACLS) is missing or invalid."""

    pass


class EchoSigilProcessingError(EESRSError):
    """Raised for errors specific to finding or processing Echo Sigil files."""

    pass
