"""
EESRS v2.0 MVP: Externalized Evolution & State Repository Service
Exports EESRServiceMVP and key exceptions.
"""

from .exceptions import (
    EESRSError,
    FileNotFoundErrorInRepoError,
    GitHubAPIError,
    RepositoryConfigurationError,
)
from .service import EESRServiceMVP

__all__ = [
    "EESRServiceMVP",
    "EESRSError",
    "GitHubAPIError",
    "FileNotFoundErrorInRepoError",
    "RepositoryConfigurationError",
]
