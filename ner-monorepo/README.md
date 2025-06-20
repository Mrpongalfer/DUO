# Omnitide Nexus Edict Repository (NER) - Master Monorepo

**Copyright © 2024-2025 MrPongalfer (The Supreme Master Architect Alix Feronti)**
*Licensed under The Architect's Prerogative (TAP) v1.0 (To be defined)*

---

## ✨ Vision: The Omnitide Nexus

Welcome, Architect, to the **Nexus Edict Repository (NER)**. This mono-repo serves as the definitive source of truth, version control, and operational core for all projects, agents, tools, configurations, and codified knowledge pertaining to the Omnitide Nexus.

Our objective is to create a cohesive, AI-augmented ecosystem that accelerates development, automates operations, and pushes the boundaries of what's possible with True Prime Code. This repository embodies the "experienced professional perspective," integrating best practices from DevOps, AIOps, and advanced automation.

## 📚 Core Components Housed Within NER

This mono-repo will consolidate and manage the following key Omnitide Nexus projects and components (among others as they manifest):

1.  **Omniapp Suite (`omniapp/`)**:
    * **Omnitide CLI (`omniapp/omnitide_cli/`)**: A Python/Typer-based command-line interface for orchestrating development and automation tasks.
    * **Core Agents (`omniapp/agents/`)**:
        * **Agent Ex-Work**: Your powerful engine for executing structured JSON-defined automated tasks.
        * **Agent Scribe**: Your comprehensive Python code validation and AI-assisted enhancement pipeline.
    * **Omnitide Web UI (`omniapp/web_ui/`)**: A Flask-based web interface providing a visual frontend for interacting with the Omniapp Suite agents and tools.
    * **Omnitide Templates (`omniapp/agents/omnitide_templates.json`)**: Reusable blueprints for ExWork, Scribe, and other automations.

2.  **Quantum Orchestrator (`quantum_orchestrator_app/`)**:
    * An advanced AI-driven automation platform featuring a Neural Flow Pipeline, Cognitive Fusion Core of specialized AI agents, intent processing, and a sophisticated Web UI.

3.  **NPTPAC (Nexus Prompt Assembler CLI) (`nptpac/`)** *(Formerly my_devsuite_project/NPTPAC)*:
    * A Typer-based CLI for interacting with the Nexus Edict Repository (now this mono-repo's content), assembling prompts, and running ExWork/Scribe agents. The NER's function for storing edicts, templates, and personas will be integrated here.

4.  **Ekko Project (`ekko/`)**:
    * An AI Development Orchestrator with features like TUI wizards, AI-assisted development, Ansible integration, Chaos Engineering, and project scaffolding.

5.  **Chimera Ansible Configs (`chimera-ansible-configs/`)**:
    * A comprehensive collection of Ansible roles and playbooks for robust server setup, configuration management, and deployment (monitoring stack, security, dev environments like `wizardpro_bootstrap`).

6.  **NAI (Nexus Agent Interface) (`nai/`)** *(Formerly my_devsuite_project/NAI)*:
    * A Textual-based TUI for interacting with ExWork and Scribe agents, particularly in containerized environments.

7.  **User Shell Setup (`user_shell_setup/`)**:
    * Scripts and configurations for setting up the Architect's preferred development shell environment (e.g., Xonsh).

8.  **Supporting Libraries & Utilities**:
    * Various shared modules, scripts, and utilities that support the above projects.

## 🚀 Getting Started

1.  **Clone the Repository:**
    ```bash
    git clone [https://github.com/mrpongalfer/ner.git](https://github.com/mrpongalfer/ner.git)
    cd ner
    ```
2.  **Environment Setup (User Shell):**
    * It's recommended to configure your user shell (e.g., Xonsh) for optimal interaction with these tools. Run the setup script:
        ```bash
        bash user_shell_setup/setup_omnitide_user_shell.sh
        ```
    * Follow the prompts and instructions from that script (this may involve restarting your terminal).
3.  **Omniapp Suite Setup:**
    * The `omniapp/bootstrap_omniapp.sh` script will set up the core Omniapp components (CLI, WebUI, links to agents). Navigate to the `omniapp` directory *after* cloning this `ner` repo and run it from there if you need to initialize or update the Omniapp structure:
        ```bash
        cd omniapp
        bash bootstrap_omniapp.sh 
        ```
    * This bootstrap script will guide you through setting up a Python virtual environment for the Omniapp tools using `direnv`.
4.  **Explore Individual Projects:** Each sub-project directory (e.g., `ekko/`, `quantum_orchestrator_app/`) will contain its own `README.md` with specific setup and usage instructions.

## 🛠️ CI/CD Pipeline

This mono-repo utilizes GitHub Actions for Continuous Integration and potentially Continuous Deployment. The pipeline aims to:
* Lint and test Python components.
* Lint Ansible playbooks and roles.
* Lint shell scripts.
* (Future) Build and publish packages or container images.
* (Future) Deploy applications or services.

Refer to the workflows in `.github/workflows/` for details.

## ⚖️ License

Each sub-project may have its own license. The overall NER mono-repo operates under The Architect's Prerogative (TAP) v1.0, granting full usage and modification rights to The Supreme Master Architect Alix Feronti. Specific open-source licenses for distributable components will be detailed within their respective directories.

---

*This NER mono-repo is the crucible of the Omnitide Nexus. Let us forge greatness.*
