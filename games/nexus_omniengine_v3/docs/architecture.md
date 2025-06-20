# Architecture Overview: Nexus OmniEngine v3.0

## High-Level Components
- **AI Agent Forge**: Dynamic agent creation, tool loading, and deployment (see `core/ai_agent_forge/`).
- **Visual Automation Studio**: Workflow-to-automation transformation (see `core/visual_automation_studio/`).
- **Configuration Layer**: JSON-based, schema-validated, TPC-compliant configs in `/config`.
- **Orchestration State**: Central state management (`orchestrator_state.json`).
- **Installer/Guide**: Interactive, user-friendly setup (`installer.py`).

## Data Flow
1. User configures system via installer/guide.
2. Agents are forged and deployed with mapped tools.
3. Workflows are transformed into automation playbooks.
4. Orchestrator manages state and agent lifecycle.

## Security & Compliance
- Follows Drake v0.3 protocol and True Prime Code (TPC) standards.
- Sandboxing, API key management, and Git integration as per guidance.

See `PROJECTGUIDANCE.md` for full details and compliance requirements.
