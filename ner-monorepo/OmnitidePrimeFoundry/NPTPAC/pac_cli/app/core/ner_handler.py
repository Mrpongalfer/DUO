# pac_cli/app/core/ner_handler.py
from pathlib import Path
from typing import List, Optional, Dict, Any
import os
import logging
import json # For manifest.json or other structured NER files
import yaml # If using YAML for some NER content

logger = logging.getLogger(__name__)

class NERHandler:
    """Handles Browse, reading, and managing content within the NER.".""
    def __init__(self, ner_root_path: Path, config_manager: Optional[Any] = None): # config_manager for future use (e.g. NER validation schemas)
        self.ner_root = ner_root_path.resolve()
        self.config_manager = config_manager # Placeholder for using config
        if not self.ner_root.is_dir():
            # This should ideally be caught by PAC's main startup check.
            logger.critical(f"NER root path does not exist or is not a directory: {self.ner_root}")
            raise FileNotFoundError(f"NER root path not found: {self.ner_root}")

    def list_categories(self) -> List[str]:
        """Lists top-level directories (categories) in NER, ignoring dotfiles/dirs.".""
        try:
            return sorted([d.name for d in self.ner_root.iterdir() if d.is_dir() and not d.name.startswith('.')])
        except OSError as e:
            logger.error(f"Error listing NER categories in {self.ner_root}: {e}")
            return []

    def list_items_in_category(self, category_path_relative: str, recursive: bool = False) -> List[Dict[str, str]]:
        """
        Lists items (files and subdirectories) in a given NER category.
        Returns a list of dicts, each with 'name', 'type' ('file'/'directory'), 'relative_path'.
        """
        category_abs_path = (self.ner_root / category_path_relative).resolve()
        if not str(category_abs_path).startswith(str(self.ner_root)):
            logger.warning(f"Attempt to list items outside NER root rejected: {category_path_relative}")
            return []
        if not category_abs_path.is_dir():
            logger.warning(f"Category path is not a directory: {category_abs_path}")
            return []

        items = []
        glob_pattern = "**/*" if recursive else "*"

        try:
            for item_path in sorted(category_abs_path.glob(glob_pattern)):
                if item_path.name.startswith('.'): # Skip hidden files/dirs
                    continue

                # For recursive, we want paths relative to the initial category_abs_path
                # For non-recursive, paths relative to category_abs_path will just be item.name
                # This formulation makes it relative to NER root for consistency in representation.
                path_relative_to_ner_root = item_path.relative_to(self.ner_root)

                item_type = "directory" if item_path.is_dir() else "file"

                # If not recursive and item is in a sub-sub-directory, skip it for non-recursive listing
                if not recursive and item_path.parent != category_abs_path:
                    continue

                items.append({
                    "name": item_path.name,
                    "type": item_type,
                    "relative_path_to_ner": str(path_relative_to_ner_root),
                    "absolute_path": str(item_path)
                })
        except OSError as e:
            logger.error(f"Error listing items in NER category {category_abs_path}: {e}")
        return items

    def get_item_content(self, item_relative_path_to_ner: str) -> Optional[str]:
        """Reads and returns the content of a file in NER.".""
        item_abs_path = (self.ner_root / item_relative_path_to_ner).resolve()
        if not str(item_abs_path).startswith(str(self.ner_root)):
            logger.warning(f"Attempt to read item outside NER root rejected: {item_relative_path_to_ner}")
            return None

        if item_abs_path.is_file():
            try:
                return item_abs_path.read_text(encoding="utf-8")
            except OSError as e:
                logger.error(f"Error reading NER item {item_abs_path}: {e}")
                return f"# ERROR: Could not read file: {e.strerror}"
            except UnicodeDecodeError as e:
                logger.error(f"Unicode decode error reading NER item {item_abs_path}: {e}")
                return f"# ERROR: Could not decode file content (not valid UTF-8)."
        else:
            logger.warning(f"Requested NER item is not a file or does not exist: {item_abs_path}")
            return None # Or raise error

    def search_ner(self, query: str, search_in_category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Searches NER content for a query string.
        Returns a list of matches, potentially with context snippets.
        TODO, Architect: Implement robust search (e.g., ripgrep integration, Whoosh index).
                         For now, a basic filename and content grep placeholder.
        """
        logger.info(f"Searching NER for '{query}'{f' in category {search_in_category}' if search_in_category else ''}...")
        results = []
        search_root = (self.ner_root / search_in_category).resolve() if search_in_category else self.ner_root

        if not str(search_root).startswith(str(self.ner_root)) or not search_root.is_dir():
            logger.error(f"Invalid search root for NER search: {search_root}")
            return []

        try:
            for item_path in search_root.rglob("*"): # Recursive glob
                if item_path.is_file() and not item_path.name.startswith('.'):
                    match_found_in_filename = query.lower() in item_path.name.lower()
                    match_found_in_content = False
                    content_snippet = ""

                    try:
                        content = item_path.read_text(encoding="utf-8")
                        if query.lower() in content.lower():
                            match_found_in_content = True
                            # Basic snippet logic
                            idx = content.lower().find(query.lower())
                            start = max(0, idx - 50)
                            end = min(len(content), idx + len(query) + 50)
                            content_snippet = f"...{content[start:end]}..."
                    except Exception:
                        pass # Ignore read/decode errors for content search, focus on filename

                    if match_found_in_filename or match_found_in_content:
                        results.append({
                            "name": item_path.name,
                            "relative_path_to_ner": str(item_path.relative_to(self.ner_root)),
                            "type": "file",
                            "match_type": "filename_and_content" if match_found_in_filename and match_found_in_content                                                   else "filename" if match_found_in_filename else "content",
                            "snippet": content_snippet if match_found_in_content else ""
                        })
        except OSError as e:
            logger.error(f"Error during NER search in {search_root}: {e}")

        logger.info(f"NER search found {len(results)} item(s) for query '{query}'.")
        return results

    # TODO, Architect: Implement NER content creation, update, deletion methods
    # These would need careful validation, user confirmation, and git integration.
    # Example Signatures:
    # def create_ner_item(self, relative_path_to_ner: str, content: str, is_directory: bool = False) -> bool:
    #     pass
    # def update_ner_item(self, relative_path_to_ner: str, new_content: str) -> bool:
    #     pass
    # def delete_ner_item(self, relative_path_to_ner: str) -> bool:
    #     pass
    # def validate_ner_template(self, template_path_relative: str, template_type: str) -> bool:
    #     # e.g., validate Ex-Work JSON against a schema, Scribe TOML structure
    #     pass

    def git_commit_ner_changes(self, commit_message: str, add_all: bool = True) -> Tuple[bool, str]:
        """Commits changes in the NER directory if it's a Git repository.".""
        if not (self.ner_root / ".git").is_dir():
            return False, "NER is not a Git repository. Cannot commit."

        try:
            if add_all:
                add_cmd = ["git", "add", "."]
                subprocess.run(add_cmd, cwd=self.ner_root, check=True, capture_output=True, text=True)

            commit_cmd = ["git", "commit", "-m", commit_message]
            result = subprocess.run(commit_cmd, cwd=self.ner_root, check=False, capture_output=True, text=True) # check=False to parse output

            if result.returncode == 0:
                return True, f"NER changes committed successfully. Output:\n{result.stdout}"
            elif "nothing to commit" in result.stdout.lower() or "no changes added to commit" in result.stdout.lower():
                return True, "No changes to commit in NER."
            else:
                return False, f"Git commit failed (RC {result.returncode}):\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}"
        except FileNotFoundError:
            return False, "'git' command not found. Ensure Git is installed and in PATH."
        except subprocess.CalledProcessError as e:
            return False, f"Git 'add' command failed: {e.stderr}"
        except Exception as e:
            logger.error(f"Unexpected error during NER git commit: {e}", exc_info=True)
            return False, f"Unexpected error during Git commit: {e}"

    def git_pull_ner(self) -> Tuple[bool, str]:
         """Pulls latest changes for the NER repository.".""
         # ... (Implementation similar to one in PAC main.py's _run_agent_command, but specific to NER path)
         # TODO, Architect: Implement robust git pull for NER, handling remotes, branches, conflicts.
         return False, "Git pull for NER not fully implemented yet."

    def git_push_ner(self) -> Tuple[bool, str]:
         """Pushes NER changes to its remote.".""
         # TODO, Architect: Implement robust git push for NER.
         return False, "Git push for NER not fully implemented yet."