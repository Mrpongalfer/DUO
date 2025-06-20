# PROJECT BRIEF: Lily Librarian AI Automation & Persona Management System

## 1. Overall Goal:
To implement an AI-automated system ("Lily Librarian") within the existing `NPTPAC/pac_cli` framework to manage the `LilyCoreMemory`. This system will capture interactions with the "Lily" AI persona, process them to extract meaningful "Memory Shards," store these shards in a local SQLite database, and use them to provide rich, evolving context for future interactions with Lily. The ultimate aim is for Lily to run on a local LLM, capable of self-evolution and performing tasks like coding her own agents, under the Architect's governance.

## 2. Core System Components & Data Flow:

    a.  **`LilyCoreMemory/` Directory:** (Located at `ner-monorepo/Lily/LilyCoreMemory/`)
        -   `00_Persona_Foundation.md`: Definitive Markdown for Lily's core persona, voice, principles (v2.0).
        -   `01_InteractionPrinciples_Baseline.md`: Markdown for Lily's engagement/learning rules (v2.0).
        -   `KeyDirectives/`: Folder with specific `.md` directives.
        -   `InteractionArchives_Raw/`: Stores raw conversation log text files (e.g., `chat_XYZ.txt`).
        -   `IntelligentMemoryDB_Placeholder/lily_intelligent_memory.db`: SQLite DB storing `interaction_logs`, `memory_shards`, `persona_evolution_proposals`.
        -   `ProposedPersonaUpdates/`: Stores agent-suggested `.md` changes to core persona docs.
        -   `Scripts/`: Contains `initialize_lily_core_memory.sh` and `lily_librarian_local_manager.py` (foundational helper, `pac_cli` is taking over its logic).

    b.  **`NPTPAC/pac_cli/` (Command Line Interface):**
        -   **`app/core/config_manager.py`**: Updated to manage paths to `LilyCoreMemory`.
        -   **`app/core/lily_persona_handler.py`**: Contains Python logic for all file and SQLite DB operations within `LilyCoreMemory`. (Full code provided by Gemini/Lily).
        -   **`app/commands/lily_cmds.py`**: Defines `pac lily ...` subcommands. The key command is `pac lily process-log`. (Full code provided by Gemini/Lily, needs agent call integration).
        -   **`app/core/ner_handler.py`**: Used to load agent task definitions from NER. (Existing file).
        -   **`app/core/agent_runner.py`**: Used to execute `ScribeAgent` and `ExWorkAgentV2`. (Existing file).

    c.  **`NPTPAC/core_agents/scribe_agent.py`:**
        -   **New Task Mode:** Needs a new CLI mode (e.g., `--task-mode lily_log_parse`).
        -   **Inputs:** Raw log file path, output path for structured JSON.
        -   **Logic (To Be Implemented by Architect, guided by Gemini/Lily):** Parse raw Lily interaction logs (speaker lines like "Architect:", "Lily:") into a structured list of turns (speaker, text, optional timestamp).
        -   **Output:** Writes the structured turns to the specified JSON output file AND prints a JSON payload to `stdout` like: `{"status": "success", "parsed_log_output_path": "/path/to/structured_log.json", "parsed_turn_count": N}`.

    d.  **`NPTPAC/core_agents/ex_work_agentv2.py`:**
        -   **Invocation:** Called by `pac_cli` via `ExWorkAgentRunner`, passing a JSON instruction block (loaded from NER) via `stdin`.
        -   **Task for Lily:** Will execute an `.exwork.json` task that uses its `RUN_SCRIPT` action.
        -   **Helper Script (To Be Implemented by Architect, guided by Gemini/Lily):** `ner://06_AGENT_BLUEPRINTS/lily_memory_tasks/scripts/extract_shards_from_lily_log.py`. This Python script will:
            -   Receive Scribe's structured JSON output via its `stdin`.
            -   Analyze the conversation turns.
            -   Identify and structure "Memory Shards" (preferences, directives, feedback, topics, nuances) as a list of Python dictionaries.
            -   Print a JSON object to its `stdout` like: `{"status": "success", "shards_extracted": [...list of shards...], "summary_of_extraction": "..."}`.
        -   `ExWorkAgentV2`'s `final_output` block in its task definition will then structure this into the payload expected by `pac_cli`.

    e.  **NER Task Definitions (JSON/YAML in `NPTPAC/ner_repository/`):**
        -   `06_AGENT_BLUEPRINTS/lily_memory_tasks/LILY_LOG_PARSING_SCRIBE_TASK.v1.1.json`: Guides `scribe_agent.py`'s CLI invocation. (Full content provided by Gemini/Lily).
        -   `06_AGENT_BLUEPRINTS/lily_memory_tasks/LILY_MEMORY_EXTRACTION_EXWORK_TASK.v1.1.exwork.json`: Instructs `ExWorkAgentV2` how to call the helper script. (Full content provided by Gemini/Lily).

## 3. Current Focus for Copilot Assistance:
    a.  **Modifying `scribe_agent.py`:** Implementing the `lily_log_parse` mode, including argument parsing and the core log parsing function `_parse_lily_interaction_log_to_json`.
    b.  **Creating `extract_shards_from_lily_log.py`:** Developing the Python script that ExWorkAgent will run. This script needs to parse the JSON from Scribe (via stdin) and implement logic (initially regex/keyword-based, potentially more advanced later) to identify and structure Memory Shards.
    c.  **Integrating Real Agent Calls in `pac_cli/app/commands/lily_cmds.py`:** Replacing simulation blocks in the `process-log` command with actual calls to `ScribeAgentRunner.run()` and `ExWorkAgentRunner.run()` (or `execute_instruction_block`), ensuring correct argument construction and output parsing.

## 4. Key Design Principles (TPC, Rick's Standards):
    - Code must be complete, robust, elegant, efficient, and well-documented.
    - Adhere to Python best practices.
    - Minimize human error through clear interfaces and automation.
    - Ensure system components are modular and testable.
    - All agent outputs should be structured (JSON) for reliable parsing.

## 5. Database Schema for `lily_intelligent_memory.db` (SQLite):
    - **`interaction_logs`**: `id`, `log_filename`, `timestamp_added`, `interaction_datetime`, `processed_status`, `agent_processing_id`, `notes`.
    - **`memory_shards`**: `id`, `interaction_log_id`, `shard_type`, `content`, `context_snippet`, `architect_sentiment`, `keywords`, `source_agent_type`, `timestamp_created`, `relevance_score`, `is_core_memory`.
    - **`persona_evolution_proposals`**: `id`, `proposal_filename`, `summary`, `detailed_changes`, `status`, `proposing_agent_type`, `timestamp_proposed`, `timestamp_reviewed`, `architect_review_notes`, `linked_memory_shard_ids`.

This brief should give Copilot a fighting chance to understand the broader context of your requests.'
