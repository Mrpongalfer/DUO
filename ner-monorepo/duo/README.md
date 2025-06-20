# Duo: Autonomous Self-Improving Agent System (ACI v2.0 MVP)

## Overview

**Duo** is a production-grade, self-evolving agent ecosystem designed for autonomous software development, maintenance, and continuous improvement. It implements the Vector-Guided Ghost protocol and Drake v0.3 Protocol, ensuring robust error handling, compliance with TPC standards, and seamless LLM (Ollama/gemma:2b) integration. The system is driven by a Metamorphic Loop for perpetual self-improvement and is guided by a Self-Deconstructing Specification Script (SDSS) for the ACI v2.0 MVP.

---

## Core Components

### 1. Ex-Work Agent (`exworkagent0.py`)
- **Purpose:** Executes structured JSON commands for file operations, script execution, LLM calls, and dynamic handler registration.
- **Features:**
  - Dynamic learning from failures (`learn_from_failures`)
  - Robust error handling and logging
  - CLI interface for interactive and automated workflows
  - Git integration and DevOps tool support
  - LLM integration (Ollama/gemma:2b)

### 2. Scribe Agent (`scribe0.py`)
- **Purpose:** Automated code validation, review, and integration pipeline.
- **Features:**
  - Validation gauntlet: venv setup, dependency audit, lint, format, type check, AI test generation, test execution, AI review
  - Flags: `--review-only`, `--no-commit` for flexible operation
  - Dynamic learning and error adaptation
  - JSON reporting and Git commit integration

### 3. Metamorphic Loop (`metamorphosis.sh`)
- **Purpose:** Orchestrates perpetual self-improvement cycles between agents, ensuring continuous code evolution and alignment with guiding protocols.
- **Checks:**
  - Ollama service and model availability
  - Git repository initialization
  - Presence of Scribe and code generator scripts

### 4. LEMS MVP Module (`aci_v2/lems_mvp/`)
- **Purpose:** Implements the ACI v2.0 MVP logic as defined by the SDSS.
- **Files:** `__init__.py`, `exceptions.py`, `models.py`, `service.py`
- **Design:** Strictly follows the SDSS (see `lilyOPS/ACI_v2_MVP_C-SDSS.md`)

### 5. SDSS (Self-Deconstructing Specification Script)
- **Location:** `lilyOPS/ACI_v2_MVP_C-SDSS.md`
- **Role:** The canonical, multi-chunk specification for the ACI v2.0 MVP. All modules are implemented block-by-block per SDSS `// AGENT_ACTION:` directives.

### 6. Vector-Guided Ghost Protocol
- **Vector Embeddings:**
  - All code changes are semantically anchored to guiding vectors from the Nexus Edict Repository (NER), with embeddings stored in `goal_vectors/`.
  - Alignment is scored and tracked for every major change.
- **Ghost in the Machine:**
  - Short-term context and memory are embedded in code comments/docstrings, accessible to LLMs during improvement cycles.

---

## Usage

### Prerequisites
- Python 3.11+
- [Ollama](https://ollama.com/) running with `gemma:2b` model
- Docker (optional, for containerized runs)

### Running Agents

**Ex-Work Agent:**
```bash
python exworkagent0.py --interactive
```

**Scribe Agent:**
```bash
python scribe0.py --interactive
```

**Metamorphic Loop:**
```bash
./metamorphosis.sh
```

### Docker
To build and run in Docker:
```bash
docker build -t duo-agents .
docker run -it duo-agents
```

---

## Development & Testing

- Install dependencies:
  ```bash
  pip install -r requirements.txt
  ```
- Run tests:
  ```bash
  ./test_runner.sh
  # or
  python -m pytest
  ```
- Lint/format:
  ```bash
  ruff check .
  black .
  mypy .
  ```

---

## Architecture & Protocols

- **Vector-Guided Ghost Protocol:**
  - See `vectorize_constitution.py` and `goal_vectors/` for vectorization logic and embeddings.
- **Drake v0.3 Protocol:**
  - Embedded in agent logic and SDSS compliance.
- **Genesis Protocol:**
  - All SDSS-driven implementation and validation is performed as per Genesis Protocol.

---

## Repository Structure

- `exworkagent0.py` — Ex-Work Agent (task execution, learning)
- `scribe0.py` — Scribe Agent (validation, review, integration)
- `llm_code_generator.py` — LLM-powered code improvement
- `metamorphosis.sh` — Metamorphic Loop orchestrator
- `aci_v2/lems_mvp/` — ACI v2.0 MVP implementation
- `lilyOPS/ACI_v2_MVP_C-SDSS.md` — Full SDSS specification
- `goal_vectors/` — Vector embeddings for guiding principles
- `vectorize_constitution.py` — NER vectorization utility
- `test_runner.sh`, `setup_xonsh.sh` — Test and environment setup scripts
- `Dockerfile` — Containerization
- `.gitignore` — Excludes venvs, test artifacts, and sensitive files

---

## Contributing
- Follow TPC and project protocols (see `Rules/` and SDSS).
- All major changes must be SDSS-compliant and vector-aligned.

## License
MIT License

---

*For more details, see the SDSS (`lilyOPS/ACI_v2_MVP_C-SDSS.md`) and the embedded documentation in each agent/module.*
