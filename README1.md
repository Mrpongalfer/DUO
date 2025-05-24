# Project Duo: Autonomous Agent Ecosystem (Omnitide Nexus)

## Overview

Project Duo is an experimental framework for building a self-evolving, autonomous software development and maintenance system. It currently consists of two core Python agents:

* **`exworkagent0.py` (Ex-Work Agent):** A general-purpose task execution agent that processes structured JSON instructions. It can manipulate files, run scripts, interact with Git, and call LLMs for analysis and code generation.
* **`scribe0.py` (Scribe Agent):** A specialized code validation and integration agent. It takes a codebase and new code, then applies a rigorous pipeline including virtual environment setup, dependency management, linting, formatting, type checking, AI-powered test generation, test execution, AI-powered code review, and Git commit integration.

These agents are designed to work in concert, potentially forming a "Metamorphic Loop" where they can iteratively improve themselves or other designated projects.

## Core Design Principles

The evolution of this system is guided by the **"Vector-Guided Ghost"** protocol:

* **Guiding Vectors & Philosophical Alignment Scorecard:** The system's long-term strategic direction is anchored by vector embeddings derived from the Nexus Edict Repository (NER). Each significant code change is assessed against these vectors, producing a multi-faceted scorecard that measures its alignment with core principles (e.g., TPC Standard, security protocols, specific persona traits).
* **Ghost in the Machine:** Tactical, short-term memory and context are embedded directly within the code being evolved (primarily as structured comments or docstrings), which are read and contributed to by LLM interactions during the improvement cycle.
* **Semantic Anchoring:** All autonomous evolution must remain semantically anchored to the foundational principles defined in the NER.

This approach aims to create a system that is not only self-improving but also value-aligned and explainable in its evolutionary trajectory.

## Current Status (As of May 24, 2025)

* Core agents (`exworkagent0.py`, `scribe0.py`) are functional and have passed initial integration tests via `test_runner.sh`.
* Environment setup for Python 3.11 (via `pyenv`) and Ollama (for LLM tasks) is stable.
* **Phase 1 ("Forging the Source of Truth") of the "Vector-Guided Ghost" protocol is complete:** The `vectorize_constitution.py` script has successfully generated `goal_*.npy` vector files from the NER, located in the `goal_vectors/` directory.

## Immediate Goals (Implementing the Metamorphic Loop)

1.  **Phase 2: Upgrade Scribe Agent:** Modify `scribe0.py` to include `--review-only` and `--no-commit` command-line flags to allow finer-grained control by an orchestrator.
2.  **Phase 3: Develop Orchestration Engine:**
    * Create `llm_code_generator.py`: A helper script to take an improvement suggestion and original code, then use an LLM to generate the new, improved code.
    * Create `metamorphosis.sh`: The main orchestrator script that implements the "Vector-Guided Ghost" loop, managing the interaction between Scribe, the code generator, and the alignment scorecard.
3.  **Demonstrate Self-Improvement:** Achieve a successful run of the `metamorphosis.sh` loop where one of the agents (or a test project) is improved based on this protocol.

## Key Components

* `duo/exworkagent0.py`: Ex-Work Agent.
* `duo/scribe0.py`: Scribe Agent.
* `duo/vectorize_constitution.py`: Tool to generate Goal Vectors from the NER.
* `duo/Rules/`: Contains local copies or references to NER documents (used by `vectorize_constitution.py`).
* `duo/goal_vectors/`: Stores the generated `.npy` Goal Vectors.
* `duo/llm_code_generator.py` (To be created)
* `duo/metamorphosis.sh` (To be created)
* `duo/test_runner.sh`: Script for integration testing of the agents.

## How to Run

1.  **Vectorize NER (One-time setup / when NER updates):**
    ```bash
    # Ensure Ollama is running with mxbai-embed-large model
    # Ensure NER_PATH environment variable points to your NER repository
    # (e.g., export NER_PATH="/home/pong/Projects/games/NPTPAC/ner_repository")
    python3 vectorize_constitution.py
    ```
2.  **Run Agent Tests (For development):**
    ```bash
    # Ensure Ollama is running with gemma:2b model (or as configured in test project's .scribe.toml)
    ./test_runner.sh
    ```
3.  **Run Metamorphic Loop (Once Phase 2 & 3 are complete):**
    ```bash
    # Ensure Ollama is running with appropriate models for generation & review
    ./metamorphosis.sh 
    ```
