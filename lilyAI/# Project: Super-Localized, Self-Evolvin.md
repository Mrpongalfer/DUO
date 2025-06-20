# Project: Super-Localized, Self-Evolving Omnitide Nexus (SLOEN) - Phase 2: Knowledge Ingestion & Fine-Tuning Pipeline (OCKIFT-P)

## Objective
Generate a secure, local Python FastAPI application that acts as the core knowledge ingestion and fine-tuning pipeline for the Omnitide Nexus. This application will connect to the Omnitide Codex, prepare data, and orchestrate the continuous fine-tuning of the local Llama 3 model, embedding advanced OpSec measures.

## Key Requirements for OCKIFT-P FastAPI Application
1.  **Project Structure:** Create a Python project with a `main.py` for the FastAPI app, a `requirements.txt`, and a `fine_tuning_scripts/` directory.
2.  **FastAPI Application (`main.py`):**
    * **Initialization:** Basic FastAPI app setup.
    * **Secure Omnitide Codex Connector (`/ingest` endpoint):**
        * Accepts POST requests for `text`, `code`, or `json` content (representing new/updated Codex entries).
        * **Authentication:** Requires JWT token validation (placeholder for secret key or dynamic key validation with Lily Core).
        * **Encryption:** All communication should be assumed to be over mTLS (handled by Nginx from Pass 1), but ensure application-level data handling is secure.
        * **Data Validation:** Use Pydantic models for strict input validation.
        * **Data Processing:**
            * Performs advanced data preprocessing:
                * Sanitization (remove HTML/script tags, control characters).
                * De-duplication (basic hash-based for simplicity).
                * Semantic chunking (e.g., using `langchain` text splitters for large documents, or a custom tokenizer-aware splitter for code) to fit Llama 3 context windows.
                * Anonymization/Pseudonymization (placeholder functions for sensitive data if present).
            * Formats processed data into `JSONL` instruction-tuning format: `{"instruction": "...", "input": "...", "output": "..."}`.
            * Appends data to a secure, version-controlled dataset file (e.g., `/opt/omnitide_nexus/datasets/omnitide_codex.jsonl`).
            * Cryptographically signs each appended entry (e.g., using `gpg` or `PyCryptodome` for HMAC) to ensure data integrity and prevent tampering.
    * **Fine-Tuning Orchestrator (`/fine_tune` endpoint):**
        * Accepts POST requests to trigger a fine-tuning job.
        * **Authentication:** Requires stronger JWT token validation (e.g., from Lily Core itself).
        * **Asynchronous Job:** Triggers a background process (e.g., using `asyncio` or `subprocess.Popen`) to run the fine-tuning script.
        * **Hyperparameter Management:** Accepts optional parameters for learning rate, batch size, LoRA rank/alpha, epochs. Implements a basic logic to adjust these based on validation loss/perplexity (placeholder for full optimization logic).
        * **Quantization & Pruning:** After successful fine-tuning, automatically triggers scripts to quantize (INT8/INT4) and prune the new model.
        * **Model Versioning:** Stores fine-tuned models in `/opt/omnitide_nexus/models/` with versioning (e.g., `llama3_omnitide_vX.Y.Z.gguf`).
        * **Rollback Mechanism:** Provides an endpoint `/rollback` to revert to a previous model version.
    * **Status Endpoint (`/status`):** Provides real-time status of ingestion and fine-tuning jobs.
3.  **Fine-Tuning Scripts (`fine_tuning_scripts/train.py`):**
    * A Python script that takes the generated `JSONL` dataset and fine-tunes Llama 3 using `llama-cpp-python`'s training capabilities (or `transformers`/`PEFT`/`Unsloth` if using a full PyTorch setup).
    * Includes logic for loading the base Llama 3 model, applying LoRA, training, and saving the fine-tuned adapter/model.
    * Integrates adversarial training techniques (e.g., generating adversarial examples during validation and using them to improve model robustness, or incorporating libraries for robust training) as part of the training loop.
    * Logs detailed training metrics to `/var/log/omnitide_nexus/`.
4.  **Requirements File:** A `requirements.txt` listing all Python dependencies.
5.  **Docker Integration:** Include a `Dockerfile` for the OCKIFT-P application, ensuring it runs with least privilege in a container.

## Output Format
A `tar.gz` archive containing the complete Python project structure (`ockiftp_project.tar.gz`).