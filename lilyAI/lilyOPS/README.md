
# LilyOPS: Autonomous Cognitive Infrastructure (ACI) v2.0 MVP Core

## Project Overview

LilyOPS is a next-generation, modular, and extensible platform for orchestrating autonomous cognitive agents and services. The ACI v2.0 MVP Core implements the foundational architecture for secure, robust, and scalable agent-based operations, following the **ACI_VSCODE_AGENT_GENESIS_PROTOCOL** and **SDSS (Self-Deconstructing Specification Script)** standards.

### Key Modules

- **ACLS MVP**: ACI Configuration & Local State Service
  - Secure management of sensitive secrets (API tokens, credentials) with OS keychain and encrypted fallback
  - General application configuration management (INI-based)
  - Centralized, configurable logging facility (console and rotating file)
- **EESRS MVP**: Externalized Evolution & State Repository Service
  - GitHub-based state repository integration for knowledge, persona, and sigil management
- **LISMS MVP**: Lily Invocation & Session Management Service
  - LLM session management (Ollama MVP)
  - Persona and session state orchestration
- **MCES MVP**: Macro & Command Execution Service
  - Macro/command definition and execution framework
- **AAS MVP**: Architect Authentication & Authorization Service (MVP placeholder)
- **Shared Components**: Common exceptions, types, and utilities

All modules are robust, production-quality, fully type-hinted, PEP 8 compliant, and include Google Style docstrings. The codebase is designed for extensibility and strict compliance with the Genesis Protocol and SDSS.

---

## Features

- Modular, service-oriented architecture
- Secure configuration and credential management (with fallback)
- GitHub-based state repository integration
- LLM session management (Ollama)
- Macro/command execution framework
- Centralized exception handling and logging
- Full type hints and Google Style docstring coverage
- SDSS-driven, protocol-compliant implementation

---

## Installation

**Requirements:**
- Python 3.11+
- See [Dependencies](#dependencies) below

**Install with PDM:**
```bash
pdm install
```

Or with pip:
```bash
pip install -r requirements.txt
```

---

## Usage

The ACI v2.0 MVP Core is designed as a library and service suite. Example usage and orchestrator entrypoints will be provided in future releases. For now, see the `aci_v2/` directory for module APIs and service classes. Each MVP module is SDSS-compliant and can be imported and used independently or as part of the orchestrator.

To run the ACLS MVP self-test:
```bash
python -m aci_v2.acls_mvp.service
```

---

## Project Structure

```
aci_v2/
  common_exceptions.py
  acls_mvp/
    __init__.py
    config_manager.py
    exceptions.py
    logging_manager.py
    secure_store.py
    service.py
  eesrs_mvp/
    __init__.py
    exceptions.py
    github_client.py
    service.py
  lisms_mvp/
    __init__.py
    exceptions.py
    service.py
    session_state.py
  mces_mvp/
    __init__.py
    exceptions.py
    models.py
    service.py
  aas_mvp/
    __init__.py
    exceptions.py
    service.py
src/
  lilyops/
tests/
```

---

## Dependencies

All non-standard dependencies are specified in `pyproject.toml`:

```
keyring >= 23.0.0
cryptography >= 3.4.0
ollama >= 0.1.0
PyGithub >= 1.55
textual >= 0.50.0
aiohttp >= 3.8.0
```

---

## Development & Contribution

- All code must be robust, type-hinted, PEP 8 compliant, and include Google Style docstrings.
- Follow the SDSS and ACI_VSCODE_AGENT_GENESIS_PROTOCOL for all contributions.
- Pull requests are welcome. Please ensure all tests pass and code is linted with `ruff`.

---


## Status

**Current State (as of June 2025):**

- The following modules are robust and SDSS-compliant: ACLS MVP, LISMS MVP, and shared components.
- The following modules are incomplete or non-compliant: EESRS MVP (missing/refactored methods), MCES MVP (models and service incomplete), AAS MVP (service methods missing).
- Core Orchestrator MVP and ICGS MVP TUI modules are not yet implemented.
- Project files (`pyproject.toml`, dependency lists) require review and update.
- The codebase is **not yet ready for final review or sign-off**. Further SDSS-aligned development is required for full compliance and completion.

**Do not consider this repository as a finalized or production-ready MVP until all modules are SDSS-compliant and the orchestrator/ICGS components are present.**

## License

MIT License. See [LICENSE](LICENSE) for details.

---


## Status

**Current State (as of June 2025):**

- The following modules are robust and SDSS-compliant: ACLS MVP, LISMS MVP, and shared components.
- The following modules are incomplete or non-compliant: EESRS MVP (missing/refactored methods), MCES MVP (models and service incomplete), AAS MVP (service methods missing).
- Core Orchestrator MVP and ICGS MVP TUI modules are not yet implemented.
- Project files (`pyproject.toml`, dependency lists) require review and update.
- The codebase is **not yet ready for final review or sign-off**. Further SDSS-aligned development is required for full compliance and completion.

**Do not consider this repository as a finalized or production-ready MVP until all modules are SDSS-compliant and the orchestrator/ICGS components are present.**
# lilyOPS
# lilyOPS
# lilyOPS
