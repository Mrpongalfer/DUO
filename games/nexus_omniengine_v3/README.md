# Omnitide Nexus Omniengine v3

## Overview
This is the canonical, deduplicated source for the Omnitide Nexus Omniengine v3. It contains all core agents, configs, docs, tests, and GUI for the Nexus system.

## Structure
- `core/` — Main agent logic, including `ai_agent_forge` and `visual_automation_studio`.
- `ansible/` — Ansible playbooks and inventory for agent deployment.
- `config/` — Main and user config files.
- `docs/` — Architecture and documentation.
- `gui/` — Web UI (Flask app, static, templates).
- `tests/` — Unit and integration tests.
- `tools/` — Utility scripts.

## Usage
- All code is Python 3.11+.
- Use the main menu or orchestrators in the root monorepo for agent management.
- See `README.md` in the monorepo root for global setup and orchestration.

## Notes
- All legacy, duplicate, and cache files have been removed.
- This folder is now the single source of truth for the Nexus Omniengine.
