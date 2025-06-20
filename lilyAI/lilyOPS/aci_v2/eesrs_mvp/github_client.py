"""
GitHubClientMVP: Robust, generic GitHub API client for EESRS v2.0 MVP.
"""

from typing import Any

from aci_v2.eesrs_mvp.exceptions import (
    FileNotFoundErrorInRepoError,
    GitHubAPIError,
    RepositoryConfigurationError,
)

try:
    from github import ContentFile, Github, GithubException, Repository
except ImportError:
    Github = None
    GithubException = Exception
    Repository = None
    ContentFile = None


class GitHubClientMVP:
    MODULE_NAME: str = "EESRS_GitHubClientMVP"
    CONFIG_KEY_REPO_URL: str = "repository_url"
    CONFIG_KEY_DEFAULT_BRANCH: str = "default_branch"
    GITHUB_PAT_KEY_IDENTIFIER: str = "ACI_MVP_GITHUB_PAT"

    def __init__(self, acl_service: Any):
        """
        Initializes the GitHub client using ACLS for credentials and repo info.
        Args:
            acl_service: The ACLS MVP service instance.
        Raises:
            RepositoryConfigurationError: If required config is missing or invalid.
            GitHubAPIError: If GitHub client initialization fails.
        """
        if Github is None:
            raise ImportError(
                "PyGithub is required. Please install with 'pip install PyGithub'."
            )
        self.acls = acl_service
        self.logger = self.acls.get_logger(f"ACI.{self.MODULE_NAME}")
        self.github_pat: str | None = self.acls.get_secure_secret(
            self.GITHUB_PAT_KEY_IDENTIFIER
        )
        if not self.github_pat:
            self.logger.critical(
                "GitHub PAT not configured in ACLS. EESRS GitHub client cannot be initialized."
            )
            raise RepositoryConfigurationError(
                "GitHub PAT not configured in ACLS. EESRS GitHub client cannot be initialized."
            )
        repo_url_str: str | None = self.acls.get_config(
            "EESRS_MVP_GitHub", self.CONFIG_KEY_REPO_URL, value_type=str
        )
        if not repo_url_str or not repo_url_str.strip():
            self.logger.critical(
                "GitHub repository URL not configured in ACLS (section [EESRS_MVP_GitHub], key 'repository_url')."
            )
            raise RepositoryConfigurationError(
                "GitHub repository URL not configured in ACLS (section [EESRS_MVP_GitHub], key 'repository_url')."
            )
        from pathlib import Path

        clean_url = repo_url_str.removesuffix(".git")
        path_parts = Path(clean_url).parts
        if len(path_parts) >= 2:
            self.repo_name = path_parts[-1]
            self.repo_owner = path_parts[-2]
        else:
            raise RepositoryConfigurationError(
                f"Invalid GitHub repository URL format: {repo_url_str}"
            )
        self.default_branch: str = self.acls.get_config(
            "EESRS_MVP_GitHub",
            self.CONFIG_KEY_DEFAULT_BRANCH,
            fallback="main",
            value_type=str,
        )
        try:
            self.gh_api = Github(self.github_pat, timeout=30)
            self.repo = self.gh_api.get_repo(f"{self.repo_owner}/{self.repo_name}")
        except GithubException as e:
            self.logger.error(
                f"Failed to initialize GitHub client or access repository '{self.repo_owner}/{self.repo_name}'. Status: {getattr(e, 'status', None)}. Message: {getattr(e, 'data', {}).get('message', str(e))}"
            )
            raise GitHubAPIError(
                f"Failed to initialize GitHub client or access repository '{self.repo_owner}/{self.repo_name}'. Status: {getattr(e, 'status', None)}. Message: {getattr(e, 'data', {}).get('message', str(e))}",
                original_exception=e,
            )
        except Exception as e_unexp:
            self.logger.error(
                f"Unexpected error initializing GitHub client for '{self.repo_owner}/{self.repo_name}': {str(e_unexp)}"
            )
            raise GitHubAPIError(
                f"Unexpected error initializing GitHub client for '{self.repo_owner}/{self.repo_name}': {str(e_unexp)}",
                original_exception=e_unexp,
            )
        self.logger.info(
            f"GitHubClientMVP initialized for repo: {self.repo_owner}/{self.repo_name} on branch {self.default_branch}"
        )

    def get_file_content(
        self, file_path_in_repo: str, branch: str | None = None
    ) -> str:
        """
        Fetches the content of a file from the repository.
        Args:
            file_path_in_repo (str): Path to the file in the repo.
            branch (Optional[str]): Branch name.
        Returns:
            str: File content as a string.
        Raises:
            FileNotFoundErrorInRepoError: If the file is not found.
            GitHubAPIError: For other API errors.
        """
        target_branch = branch if branch and branch.strip() else self.default_branch
        self.logger.debug(
            f"Attempting to fetch file: '{file_path_in_repo}' from repo '{self.repo.full_name}' branch '{target_branch}'"
        )
        try:
            content_file_obj = self.repo.get_contents(
                file_path_in_repo, ref=target_branch
            )
            if isinstance(content_file_obj, list) or (
                hasattr(content_file_obj, "type") and content_file_obj.type == "dir"
            ):
                self.logger.error(
                    f"Path '{file_path_in_repo}' in branch '{target_branch}' is a directory, not a file."
                )
                raise FileNotFoundErrorInRepoError(
                    f"Path '{file_path_in_repo}' in branch '{target_branch}' is a directory, not a file."
                )
            if (
                not hasattr(content_file_obj, "content")
                or content_file_obj.content is None
            ):
                self.logger.error(
                    f"File content for '{file_path_in_repo}' in branch '{target_branch}' is empty or not directly downloadable."
                )
                raise FileNotFoundErrorInRepoError(
                    f"File content for '{file_path_in_repo}' in branch '{target_branch}' is empty or not directly downloadable."
                )
            import base64

            decoded_content = base64.b64decode(content_file_obj.content).decode("utf-8")
            self.logger.info(
                f"File content retrieved successfully for: '{file_path_in_repo}' from branch '{target_branch}'."
            )
            return decoded_content
        except GithubException as e_gh:
            if getattr(e_gh, "status", None) == 404:
                self.logger.warning(
                    f"File '{file_path_in_repo}' not found in branch '{target_branch}'."
                )
                raise FileNotFoundErrorInRepoError(
                    f"File '{file_path_in_repo}' not found in branch '{target_branch}'.",
                    original_exception=e_gh,
                )
            self.logger.error(
                f"GitHub API error fetching file '{file_path_in_repo}': Status {getattr(e_gh, 'status', None)}, Message: {getattr(e_gh, 'data', {}).get('message', str(e_gh))}"
            )
            raise GitHubAPIError(
                f"GitHub API error fetching file '{file_path_in_repo}': Status {getattr(e_gh, 'status', None)}, Message: {getattr(e_gh, 'data', {}).get('message', str(e_gh))}",
                original_exception=e_gh,
            )
        except Exception as e_unexp:
            self.logger.error(
                f"Unexpected error processing file '{file_path_in_repo}': {str(e_unexp)}"
            )
            raise FileNotFoundErrorInRepoError(
                f"Unexpected error processing file '{file_path_in_repo}': {str(e_unexp)}",
                original_exception=e_unexp,
            )

    def get_latest_file_from_directory_by_timestamp_in_name(
        self,
        directory_path_in_repo: str,
        file_suffix: str,
        timestamp_format_in_name: str = "%Y%m%d-%H%M%S",
        branch: str | None = None,
    ) -> tuple[str, str] | None:
        """
        Finds the latest file in a directory by extracting a timestamp from the filename, sorting, and returning its name and content.
        Args:
            directory_path_in_repo (str): Directory path in the repo.
            file_suffix (str): Suffix to match files.
            timestamp_format_in_name (str): Datetime format string for parsing timestamps in filenames.
            branch (Optional[str]): Branch name.
        Returns:
            Optional[tuple[str, str]]: (filename, content) of the latest file, or None if no files found.
        Raises:
            FileNotFoundErrorInRepoError: If no files are found in the directory.
            GitHubAPIError: For API errors.
        """
        import datetime
        import re

        target_branch = branch if branch and branch.strip() else self.default_branch
        self.logger.debug(
            f"Searching for latest file with suffix '{file_suffix}' in dir '{directory_path_in_repo}' of branch '{target_branch}'"
        )
        try:
            contents = self.repo.get_contents(directory_path_in_repo, ref=target_branch)
            if not isinstance(contents, list):
                raise FileNotFoundErrorInRepoError(
                    f"Path '{directory_path_in_repo}' is not a directory or not found in branch '{target_branch}'."
                )
            candidate_files = [
                item
                for item in contents
                if hasattr(item, "name") and item.name.endswith(file_suffix)
            ]
            if not candidate_files:
                self.logger.info(
                    f"No files found with suffix '{file_suffix}' in '{directory_path_in_repo}'."
                )
                return None
            parsed_files = []
            for item in candidate_files:
                match = re.match(r"(\d{8,14})", item.name)
                if match:
                    try:
                        dt_obj = datetime.datetime.strptime(
                            match.group(1), timestamp_format_in_name
                        )
                        parsed_files.append((dt_obj, item))
                    except Exception:
                        self.logger.warning(
                            f"Could not parse timestamp from filename {item.name}"
                        )
                        continue
            if not parsed_files:
                self.logger.warning(
                    f"No files with valid timestamps found in '{directory_path_in_repo}'."
                )
                return None
            parsed_files.sort(key=lambda x: x[0], reverse=True)
            latest_file_info = parsed_files[0][1]
            latest_file_path_in_repo = latest_file_info.path
            content_str = self.get_file_content(
                latest_file_path_in_repo, branch=target_branch
            )
            self.logger.info(
                f"Latest file '{latest_file_info.name}' content retrieved from '{directory_path_in_repo}'."
            )
            return (latest_file_info.name, content_str)
        except GithubException as e_gh:
            if getattr(e_gh, "status", None) == 404:
                self.logger.info(
                    f"Directory '{directory_path_in_repo}' not found in branch '{target_branch}'."
                )
                raise FileNotFoundErrorInRepoError(
                    f"Directory '{directory_path_in_repo}' not found in branch '{target_branch}'.",
                    original_exception=e_gh,
                )
            self.logger.error(
                f"GitHub API error searching directory '{directory_path_in_repo}': {e_gh}"
            )
            raise GitHubAPIError(
                f"GitHub API error searching directory '{directory_path_in_repo}': {e_gh}",
                original_exception=e_gh,
            )
        except Exception as e_unexp:
            self.logger.error(
                f"Unexpected error searching directory '{directory_path_in_repo}': {e_unexp}"
            )
            raise FileNotFoundErrorInRepoError(
                f"Unexpected error searching directory '{directory_path_in_repo}': {e_unexp}",
                original_exception=e_unexp,
            )


# MODULE_DEPENDENCIES_FOR_PYPROJECT_TOML:
#   PyGithub>=1.55


# Non-standard dependencies:
#   PyGithub (https://pypi.org/project/PyGithub/)
#   PyGithub (https://pypi.org/project/PyGithub/)
