# ner-monorepo/my_devsuite_project/NPTPAC/pac_cli/app/core/lily_persona_handler.py
# Version 1.0
# Core logic for managing Lily's Persona (LilyCoreMemory) data,
# including file interactions and SQLite database operations.
# To be used by lily_cmds.py (Typer commands).

import datetime
import logging
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Assuming ConfigManager will be passed or accessible
# from .config_manager import ConfigManager # This line will be used by lily_cmds.py

logger = logging.getLogger("PAC.LilyHandler")  # Child logger of PAC


class LilyPersonaHandler:
    """
    Handles all data operations for LilyCoreMemory, including persona documents,
    interaction logs, memory shards, and evolution proposals.
    """

    def __init__(
        self, config_manager: Any
    ):  # Expects an instance of your ConfigManager
        self.config = config_manager
        self.lcm_base_path: Optional[Path] = self.config.lily_core_memory_base_path

        if not self.lcm_base_path or not self.lcm_base_path.is_dir():
            err_msg = f"LilyCoreMemory base path ('{self.lcm_base_path}') is not configured or not a valid directory. Please check PAC settings."
            logger.critical(err_msg)
            # In a CLI, this might raise an exception caught by the command layer.
            # For now, methods will check self.lcm_base_path and return failure if None.
            # This makes the class instantiable but methods will fail gracefully.
            # Consider raising a custom exception here if preferred.
            # raise ValueError(err_msg) # Or a custom ConfigError
        else:
            logger.info(
                f"LilyPersonaHandler initialized. Managing LilyCoreMemory at: {self.lcm_base_path}"
            )
            self._initialize_database_if_not_exists()

    def _get_db_connection(self) -> Optional[sqlite3.Connection]:
        """Establishes and returns a connection to the LilyCoreMemory SQLite database."""
        if not self.lcm_base_path:
            return None
        db_path = self.config.lcm_db_path  # Uses property from ConfigManager
        if not db_path:
            logger.error("Database path for LilyCoreMemory is not configured.")
            return None

        db_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            return conn
        except sqlite3.Error as e:
            logger.error(f"Database connection error to '{db_path}': {e}")
            return None

    def _initialize_database_if_not_exists(self):
        """Creates database tables if they don't exist. Called on handler init."""
        if not self.lcm_base_path:
            return False
        conn = self._get_db_connection()
        if not conn:
            return False

        try:
            with conn:  # Context manager handles commit/rollback
                cursor = conn.cursor()
                # Interaction Logs Table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS interaction_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        log_filename TEXT UNIQUE NOT NULL,
                        timestamp_added DATETIME DEFAULT CURRENT_TIMESTAMP,
                        interaction_datetime DATETIME,
                        processed_status TEXT DEFAULT 'pending' CHECK(processed_status IN ('pending', 'processing', 'processed_manual', 'processed_agent', 'failed_processing')),
                        agent_processing_id TEXT,
                        notes TEXT
                    )
                """
                )
                # Memory Shards Table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS memory_shards (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        interaction_log_id INTEGER,
                        shard_type TEXT NOT NULL CHECK(shard_type IN (
                            'architect_preference', 'architect_directive', 'architect_feedback_positive', 
                            'architect_feedback_corrective', 'key_topic_summary', 'lily_nuance_observed', 
                            'world_knowledge_update', 'other_insight'
                        )),
                        content TEXT NOT NULL,
                        context_snippet TEXT,
                        architect_sentiment TEXT CHECK(architect_sentiment IN ('positive', 'neutral', 'negative', NULL)),
                        keywords TEXT,
                        source_agent_type TEXT, -- 'manual_input', 'ScribeAgent_vX.Y', 'ExWorkAgent_vX.Y'
                        timestamp_created DATETIME DEFAULT CURRENT_TIMESTAMP,
                        relevance_score REAL DEFAULT 0.5,
                        is_core_memory BOOLEAN DEFAULT FALSE,
                        FOREIGN KEY (interaction_log_id) REFERENCES interaction_logs (id) ON DELETE SET NULL
                    )
                """
                )
                # Persona Evolution Proposals Table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS persona_evolution_proposals (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        proposal_filename TEXT UNIQUE NOT NULL,
                        summary TEXT NOT NULL,
                        detailed_changes TEXT,
                        status TEXT DEFAULT 'pending_review' CHECK(status IN (
                            'pending_review', 'approved_pending_merge', 'merged_to_core', 'rejected', 'archived'
                        )),
                        proposing_agent_type TEXT, -- 'manual_architect', 'PersonaStrategistAgent_vX.Y'
                        timestamp_proposed DATETIME DEFAULT CURRENT_TIMESTAMP,
                        timestamp_reviewed DATETIME,
                        architect_review_notes TEXT,
                        linked_memory_shard_ids TEXT
                    )
                """
                )
            logger.info(
                f"Database schema at '{self.config.lcm_db_path}' initialized/verified."
            )
            return True
        except sqlite3.Error as e:
            logger.error(f"Database initialization error: {e}")
            return False
        finally:
            if conn:
                conn.close()

    def add_interaction_log(
        self,
        log_filename: str,
        interaction_datetime_str: Optional[str],
        notes: Optional[str],
    ) -> Tuple[bool, Optional[int], str]:
        """Adds a reference to a raw interaction log file into the database."""
        if not self.lcm_base_path or not self.config.lcm_raw_logs_dir:
            return False, None, "LilyCoreMemory path or raw_logs_dir not configured."

        raw_logs_dir = self.config.lcm_raw_logs_dir
        raw_logs_dir.mkdir(parents=True, exist_ok=True)  # Ensure it exists

        full_log_path = raw_logs_dir / log_filename
        if not full_log_path.is_file():
            # Log a warning but still add to DB; file might be placed by another process.
            # Commands layer can decide if this is a hard error.
            logger.warning(
                f"Log file '{full_log_path}' not found. Adding DB reference anyway."
            )

        interaction_datetime_iso = None
        if interaction_datetime_str:
            try:
                interaction_datetime_iso = datetime.datetime.strptime(
                    interaction_datetime_str, "%Y-%m-%d %H:%M"
                ).isoformat()
            except ValueError:
                return (
                    False,
                    None,
                    "Invalid datetime format for interaction. Please use YYYY-MM-DD HH:MM.",
                )

        conn = self._get_db_connection()
        if not conn:
            return False, None, "Database connection failed."

        try:
            with conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO interaction_logs (log_filename, interaction_datetime, notes) VALUES (?, ?, ?)",
                    (log_filename, interaction_datetime_iso, notes),
                )
                log_id = cursor.lastrowid
            msg = f"Log file '{log_filename}' (DB ID: {log_id}) reference added for processing."
            logger.info(msg)
            return True, log_id, msg
        except sqlite3.IntegrityError:
            msg = f"Log file '{log_filename}' already exists in the database."
            logger.error(msg)
            return False, None, msg
        except sqlite3.Error as e:
            msg = f"Database error adding log: {e}"
            logger.error(msg)
            return False, None, msg
        finally:
            if conn:
                conn.close()

    def get_pending_logs(self) -> List[Dict[str, Any]]:
        """Retrieves logs marked as 'pending' for processing."""
        if not self.lcm_base_path:
            return []
        conn = self._get_db_connection()
        if not conn:
            return []

        try:
            with conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id, log_filename, interaction_datetime FROM interaction_logs WHERE processed_status = 'pending' ORDER BY timestamp_added ASC"
                )
                logs = [dict(row) for row in cursor.fetchall()]
            return logs
        except sqlite3.Error as e:
            logger.error(f"Database error fetching pending logs: {e}")
            return []
        finally:
            if conn:
                conn.close()

    def add_memory_shards(
        self, log_id: int, shards: List[Dict[str, Any]]
    ) -> Tuple[bool, str]:
        """Adds a list of Memory Shard dictionaries to the database for a given log_id."""
        if not self.lcm_base_path:
            return False, "LilyCoreMemory path not configured."
        if not shards:
            return True, "No shards provided to add."

        conn = self._get_db_connection()
        if not conn:
            return False, "Database connection failed."

        try:
            with conn:
                cursor = conn.cursor()
                for shard in shards:
                    cursor.execute(
                        """
                        INSERT INTO memory_shards 
                        (interaction_log_id, shard_type, content, context_snippet, architect_sentiment, keywords, source_agent_type, relevance_score, is_core_memory)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            log_id,
                            shard.get("shard_type"),
                            shard.get("content"),
                            shard.get("context_snippet"),
                            shard.get("architect_sentiment"),
                            shard.get("keywords"),
                            shard.get(
                                "source_agent_type", "manual_pac_cli"
                            ),  # Default if not specified by agent
                            float(shard.get("relevance_score", 0.5)),
                            bool(shard.get("is_core_memory", False)),
                        ),
                    )
            msg = f"Added {len(shards)} memory shards for log ID {log_id}."
            logger.info(msg)
            return True, msg
        except sqlite3.Error as e:
            msg = f"Database error adding memory shards: {e}"
            logger.error(msg)
            return False, msg
        finally:
            if conn:
                conn.close()

    def update_log_processed_status(
        self, log_id: int, status: str, agent_processing_id: Optional[str] = None
    ) -> Tuple[bool, str]:
        """Updates the processed_status of an interaction log."""
        if not self.lcm_base_path:
            return False, "LilyCoreMemory path not configured."
        conn = self._get_db_connection()
        if not conn:
            return False, "Database connection failed."

        allowed_statuses = [
            "pending",
            "processing",
            "processed_manual",
            "processed_agent",
            "failed_processing",
        ]
        if status not in allowed_statuses:
            return (
                False,
                f"Invalid status '{status}'. Allowed: {', '.join(allowed_statuses)}",
            )

        try:
            with conn:
                conn.execute(
                    "UPDATE interaction_logs SET processed_status = ?, agent_processing_id = ? WHERE id = ?",
                    (status, agent_processing_id, log_id),
                )
            msg = f"Log ID {log_id} status updated to '{status}'."
            logger.info(msg)
            return True, msg
        except sqlite3.Error as e:
            msg = f"Database error updating log status: {e}"
            logger.error(msg)
            return False, msg
        finally:
            if conn:
                conn.close()

    def draft_evolution_proposal(
        self,
        summary: str,
        detailed_changes_md: str,
        proposing_agent_type: str,
        linked_shard_ids: Optional[List[int]] = None,
    ) -> Tuple[bool, Optional[str], str]:
        """Saves a persona evolution proposal as a Markdown file and logs it in the DB."""
        if not self.lcm_base_path or not self.config.lcm_proposed_updates_dir:
            return (
                False,
                None,
                "LilyCoreMemory path or proposed_updates_dir not configured.",
            )

        proposals_dir = self.config.lcm_proposed_updates_dir
        proposals_dir.mkdir(parents=True, exist_ok=True)

        now = datetime.datetime.now()
        timestamp_str = now.strftime("%Y%m%d_%H%M%S")
        clean_summary = (
            "".join(c if c.isalnum() or c in [" ", "_"] else "" for c in summary)
            .replace(" ", "_")
            .lower()[:40]
        )
        proposal_filename = f"proposal_{timestamp_str}_{clean_summary}.md"
        proposal_file_path = proposals_dir / proposal_filename

        # Construct Markdown content for the proposal file
        proposal_md_content = f"# Persona Evolution Proposal: {summary}\n\n"
        proposal_md_content += f"**Date Proposed:** {now.isoformat()}\n"
        proposal_md_content += f"**Proposing Entity:** {proposing_agent_type}\n"
        proposal_md_content += "**Status:** pending_review\n"
        proposal_md_content += f"**Supporting Memory Shard IDs:** {', '.join(map(str, linked_shard_ids)) if linked_shard_ids else 'N/A'}\n\n"
        proposal_md_content += "## Proposed Changes/Rationale:\n"
        proposal_md_content += detailed_changes_md
        proposal_md_content += "\n\n---\n*Architect Review Required: If approved, manually apply changes to core document(s) (e.g., 00_Persona_Foundation.md) and update proposal status in DB to 'merged_to_core'.*"

        conn = self._get_db_connection()
        if not conn:
            return False, None, "Database connection failed."

        try:
            proposal_file_path.write_text(proposal_md_content, encoding="utf-8")
            logger.info(f"Proposal Markdown file saved: {proposal_file_path}")

            with conn:
                cursor = conn.cursor()
                cursor.execute(
                    """INSERT INTO persona_evolution_proposals 
                       (proposal_filename, summary, detailed_changes, proposing_agent_type, linked_memory_shard_ids) 
                       VALUES (?, ?, ?, ?, ?)""",
                    (
                        proposal_filename,
                        summary,
                        detailed_changes_md,
                        proposing_agent_type,
                        (
                            ",".join(map(str, linked_shard_ids))
                            if linked_shard_ids
                            else None
                        ),
                    ),
                )
                proposal_id = cursor.lastrowid
            msg = f"Persona evolution proposal (DB ID: {proposal_id}, File: {proposal_filename}) drafted successfully."
            logger.info(msg)
            return True, proposal_filename, msg
        except sqlite3.Error as e:
            msg = f"Database error drafting proposal: {e}"
            logger.error(msg)
            # Attempt to clean up file if DB insert failed
            if proposal_file_path.exists():
                proposal_file_path.unlink(missing_ok=True)
            return False, None, msg
        except OSError as e:
            msg = f"File system error drafting proposal: {e}"
            logger.error(msg)
            return False, None, msg
        finally:
            if conn:
                conn.close()

    def get_evolution_proposals(
        self, status_filter: Optional[str] = "pending_review"
    ) -> List[Dict[str, Any]]:
        """Retrieves persona evolution proposals, optionally filtered by status."""
        if not self.lcm_base_path:
            return []
        conn = self._get_db_connection()
        if not conn:
            return []

        query = "SELECT id, proposal_filename, summary, status, timestamp_proposed, proposing_agent_type FROM persona_evolution_proposals"
        params = []
        if status_filter:
            query += " WHERE status = ?"
            params.append(status_filter)
        query += " ORDER BY timestamp_proposed DESC"

        try:
            with conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                proposals = [dict(row) for row in cursor.fetchall()]
            return proposals
        except sqlite3.Error as e:
            logger.error(f"Database error fetching proposals: {e}")
            return []
        finally:
            if conn:
                conn.close()

    def update_proposal_status(
        self, proposal_id: int, new_status: str, architect_notes: Optional[str] = ""
    ) -> Tuple[bool, str]:
        """Updates the status and review notes of a persona evolution proposal."""
        if not self.lcm_base_path:
            return False, "LilyCoreMemory path not configured."
        conn = self._get_db_connection()
        if not conn:
            return False, "Database connection failed."

        allowed_statuses = [
            "pending_review",
            "approved_pending_merge",
            "merged_to_core",
            "rejected",
            "archived",
        ]
        if new_status not in allowed_statuses:
            return (
                False,
                f"Invalid status '{new_status}'. Allowed: {', '.join(allowed_statuses)}",
            )

        try:
            with conn:
                conn.execute(
                    """UPDATE persona_evolution_proposals 
                       SET status = ?, architect_review_notes = ?, timestamp_reviewed = ? 
                       WHERE id = ?""",
                    (
                        new_status,
                        architect_notes,
                        datetime.datetime.now().isoformat(),
                        proposal_id,
                    ),
                )
            msg = f"Proposal ID {proposal_id} status updated to '{new_status}'."
            logger.info(msg)
            return True, msg
        except sqlite3.Error as e:
            msg = f"Database error updating proposal status: {e}"
            logger.error(msg)
            return False, msg
        finally:
            if conn:
                conn.close()

    def assemble_lily_context_from_memory(
        self, include_shards: int = 3, fetch_all_shards: bool = False
    ) -> Tuple[Optional[str], str]:
        """
        Assembles the full context for Lily, including core persona documents
        and relevant Memory Shards from the SQLite database.
        """
        if not self.lcm_base_path:
            return None, "LilyCoreMemory base path not configured."

        context_parts = []
        files_loaded_count = 0
        shards_loaded_count = 0

        # 1. Persona Foundation
        persona_file = self.config.lcm_persona_foundation_file
        if persona_file and persona_file.is_file():
            context_parts.append(
                f"--- START: {persona_file.name} ---\n{persona_file.read_text(encoding='utf-8')}\n--- END: {persona_file.name} ---"
            )
            files_loaded_count += 1
        else:
            logger.warning(
                f"Core document '{persona_file}' not found. Context will be incomplete."
            )

        # 2. Interaction Principles
        principles_file = self.config.lcm_interaction_principles_file
        if principles_file and principles_file.is_file():
            context_parts.append(
                f"--- START: {principles_file.name} ---\n{principles_file.read_text(encoding='utf-8')}\n--- END: {principles_file.name} ---"
            )
            files_loaded_count += 1

        # 3. Key Directives
        directives_path = self.config.lcm_key_directives_dir
        if directives_path and directives_path.is_dir():
            directive_files = sorted(directives_path.glob("*.md"))
            if directive_files:
                context_parts.append(
                    f"\n--- START: Key Directives ({len(directive_files)} found) ---"
                )
            for directive_file in directive_files:
                context_parts.append(
                    f"\n--- START DIRECTIVE: {directive_file.name} ---\n{directive_file.read_text(encoding='utf-8')}\n--- END DIRECTIVE: {directive_file.name} ---"
                )
                files_loaded_count += 1

        # 4. Relevant Memory Shards from DB
        if include_shards > 0 or fetch_all_shards:
            context_parts.append(
                "\n--- START: Recent Key Memories & Insights (from Intelligent Memory DB) ---"
            )
            conn = self._get_db_connection()
            if conn:
                try:
                    with conn:
                        query = "SELECT id, shard_type, content, context_snippet, timestamp_created FROM memory_shards ORDER BY timestamp_created DESC"
                        params: List[Any] = []
                        if not fetch_all_shards and include_shards > 0:
                            query += " LIMIT ?"
                            params.append(include_shards)

                        shards = conn.execute(query, params).fetchall()
                        if shards:
                            for i, shard in enumerate(shards):
                                context_parts.append(
                                    f"\nMemory Shard Ref #{shard['id']} (Type: {shard['shard_type']}, Created: {shard['timestamp_created']}):\n"
                                    f"  Insight/Content: {shard['content']}\n"
                                    f"  Original Context Snippet: {shard['context_snippet'] if shard['context_snippet'] else 'N/A'}"
                                )
                            shards_loaded_count = len(shards)
                        else:
                            context_parts.append(
                                "\n(No relevant memory shards found in the database to include in this context assembly.)"
                            )
                except sqlite3.Error as e:
                    logger.error(f"Error querying memory shards for context: {e}")
                    context_parts.append(f"\n[Error loading memory shards: {e}]")
                finally:
                    if conn:
                        conn.close()
            else:
                context_parts.append(
                    "\n[Could not connect to Memory DB to fetch shards.]"
                )
            context_parts.append("--- END: Recent Key Memories & Insights ---")

        full_context = "\n\n".join(context_parts)

        # Save to a temporary file for easy copy-pasting by Architect
        context_output_filename = "lily_current_context_pac_generated.txt"
        scripts_dir = self.config.lcm_scripts_dir
        if not scripts_dir:
            logger.warning(
                "Scripts directory for LilyCoreMemory not configured. Cannot save context file."
            )
            return (
                full_context,
                f"Context assembled ({files_loaded_count} core files, {shards_loaded_count} shards). Output file not saved (scripts_dir not configured).",
            )

        context_file_path = scripts_dir / context_output_filename
        try:
            scripts_dir.mkdir(parents=True, exist_ok=True)
            context_file_path.write_text(full_context, encoding="utf-8")
            msg = f"Context assembled ({files_loaded_count} core files, {shards_loaded_count} shards). Saved to: {context_file_path}"
            logger.info(msg)
            return full_context, msg
        except OSError as e:
            msg = f"Context assembled ({files_loaded_count} core files, {shards_loaded_count} shards). ERROR saving context to file '{context_file_path}': {e}"
            logger.error(msg)
            return full_context, msg

    def get_persona_document_content(
        self, doc_type: str = "foundation"
    ) -> Optional[str]:
        """Helper to get content of core persona MD files."""
        if not self.lcm_base_path:
            return None

        file_to_read: Optional[Path] = None
        if doc_type == "foundation" and self.config.lcm_persona_foundation_file:
            file_to_read = self.config.lcm_persona_foundation_file
        elif doc_type == "principles" and self.config.lcm_interaction_principles_file:
            file_to_read = self.config.lcm_interaction_principles_file

        if file_to_read and file_to_read.is_file():
            try:
                return file_to_read.read_text(encoding="utf-8")
            except OSError as e:
                logger.error(f"Error reading {doc_type} document '{file_to_read}': {e}")
                return None
        logger.warning(
            f"{doc_type.capitalize()} document path not found or not a file: {file_to_read}"
        )
        return None


# Example usage (would be in lily_cmds.py):
# if __name__ == '__main__':
#     # This setup is conceptual for testing the handler directly.
#     # In pac_cli, ConfigManager is initialized in main.py and passed.
#     mock_npt_base_dir = Path(".").resolve().parent.parent # Assuming this script is in core/, up to NPTPAC/

#     # Create a dummy settings.toml if it doesn't exist for this test
#     dummy_config_dir = mock_npt_base_dir / "config"
#     dummy_config_dir.mkdir(parents=True, exist_ok=True)
#     dummy_settings_file = dummy_config_dir / "settings.toml"
#     if not dummy_settings_file.exists():
#         test_lcm_path = Path.home() / "Projects" / "ner-monorepo" / "Lily" / "LilyCoreMemory_Test" # Use a test path
#         test_lcm_path.mkdir(parents=True, exist_ok=True)
#         with open(dummy_settings_file, "w") as f:
#             f.write(f'[lily_core_memory]\nbase_path = "{str(test_lcm_path)}"\n')
#         print(f"Created dummy settings at {dummy_settings_file} for test.")


#     from config_manager import ConfigManager # Relative import for testing
#     try:
#         config = ConfigManager(npt_base_dir=mock_npt_base_dir)
#         handler = LilyPersonaHandler(config_manager=config)

#         if handler.lcm_base_path:
#             print(f"Handler using LCM path: {handler.lcm_base_path}")
#             # Test add log
#             # success, log_id, msg = handler.add_interaction_log("testlog_001.txt", "2025-05-22 10:00", "Test interaction")
#             # print(f"Add log: {success}, {log_id}, {msg}")
#             # if log_id:
#                 # Test add shards
#                 # shards_to_add = [
#                 #     {"shard_type": "architect_preference", "content": "Likes clear CLI output", "keywords": "cli,output"},
#                 #     {"shard_type": "key_topic_summary", "content": "Discussed LilyCoreMemory implementation", "keywords": "lilycorememory,design"}
#                 # ]
#                 # success, msg = handler.add_memory_shards(log_id, shards_to_add)
#                 # print(f"Add shards: {success}, {msg}")
#                 # handler.update_log_processed_status(log_id, "processed_manual")

#             # Test get context
#             # context, msg = handler.assemble_lily_context_from_memory(include_shards=2)
#             # print(f"\nContext Assembly: {msg}")
#             # if context: print("\n--- START CONTEXT ---\n", context[:1000] + "...", "\n--- END CONTEXT ---")
#             pass
#         else:
#             print("Could not test handler, LCM base path not set.")
#     except Exception as e:
#         print(f"Error during standalone test: {e}")
