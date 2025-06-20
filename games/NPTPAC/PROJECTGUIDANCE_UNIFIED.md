# OMNITIDE NEXUS: UNIFIED SYSTEM INSTRUCTIONS (v2025-05-22)

## Overview
This document provides comprehensive guidance for the unified Omnitide Nexus Protocol Toolkit (NPT) system, with all automation, agent, and knowledge assets consolidated in `NPTPAC/ner_repository`. It supersedes all legacy project documentation (except Lily, which remains pristine and unmodified).

## Table of Contents
1. [Repository Structure](#repository-structure)
2. [Integration & Usage](#integration--usage)
3. [Agent Orchestration & Evolution](#agent-orchestration--evolution)
4. [Knowledge Asset Management](#knowledge-asset-management)
5. [Compliance & Protocols](#compliance--protocols)
6. [Legacy Project Migration](#legacy-project-migration)
7. [Troubleshooting & Support](#troubleshooting--support)

---

## Repository Structure

- **00_CORE_EDICTS/**: Foundational edicts and operational mandates.
- **01_ONAP_R3_COMPONENTS/**: LLM imprinting and ONAP activation prompts.
- **02_TPC_STANDARD/**: TPC standards and compliance docs.
- **03_CORE_TEAM_PERSONAS/**: Core Team persona profiles.
- **04_INTERACTION_GUIDES/**: Best practices for AI agent interaction.
- **05_PROJECT_SUMMARIES/**: Overviews of key projects/components.
- **06_AGENT_BLUEPRINTS/**: Unified blueprints, templates, scripts, and docs for all agents (ExWorkAgent, Scribe, Quantum Orchestrator, ODA, Ekko, etc.).
- **07_SECURITY_TOOLS/**: Security tools and templates.
- **08_INNOVATION_SHOWCASE/**: Experimental tools, hackathon resources, and POCs.

## Integration & Usage

- **All new automation, agent logic, and orchestration must reference and extend from the assets in `ner_repository`.**
- Use the blueprints and templates in `06_AGENT_BLUEPRINTS/` for rapid agent deployment, extension, or evolution.
- For security, compliance, and operational mandates, always consult `00_CORE_EDICTS/` and `02_TPC_STANDARD/`.
- For Core Team simulation or feedback, use the persona profiles in `03_CORE_TEAM_PERSONAS/`.
- For advanced orchestration (multi-agent, meta-generative, etc.), see the Quantum Orchestrator prompts in `06_AGENT_BLUEPRINTS/quantum_orchestrator_prompts/`.

## Agent Orchestration & Evolution

- **All agent evolution and code generation must be TPC-compliant and reference the latest blueprints.**
- Modular orchestration is supported: agents can be composed, extended, or replaced using the unified templates.
- Feedback loops and self-evolution logic are documented in the relevant agent blueprint folders.
- Lily’s persona and logic are never to be modified except via explicit Architect approval and the Lily Librarian protocol.

## Knowledge Asset Management

- All knowledge, templates, and blueprints are versioned and indexed in `ner_repository`.
- When adding new assets, update the relevant subfolder README and the main `ner_repository/README.md`.
- Redundant or legacy assets must be removed after successful migration and verification.

## Compliance & Protocols

- **Drake v0.3 protocol and TPC standards are strictly enforced.**
- All operational mandates, security requirements, and code generation standards are codified in `00_CORE_EDICTS/` and `02_TPC_STANDARD/`.
- Lily’s operational integrity and persona are protected by immutable directives.

## Legacy Project Migration

- All unique, non-Lily knowledge assets from legacy projects have been migrated to `ner_repository`.
- Legacy folders (chimera-ansible-configs, ekko, gotted, NAI, ODA, quantum_orchestrator_app, wizardpro2, etc.) should be archived or deleted after verification.
- All future development must occur within the unified NPTPAC structure.

## Troubleshooting & Support

- For issues with agent orchestration, consult the relevant blueprint and the `README.md` in each subfolder.
- For compliance or protocol questions, refer to `00_CORE_EDICTS/` and `02_TPC_STANDARD/`.
- For advanced integration or meta-generative automation, see the Quantum Orchestrator prompts and blueprints.
- For Lily-specific issues, consult the Lily Librarian documentation (Lily’s core is never to be modified directly).

---

**This document is the authoritative operational guide for the unified Omnitide Nexus system. All contributors and agents must adhere to its mandates.**
