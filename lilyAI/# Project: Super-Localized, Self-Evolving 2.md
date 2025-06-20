# Project: Super-Localized, Self-Evolving Omnitide Nexus (SLOEN) - Phase 1: Foundational Infrastructure

## Objective
Generate the core automation script (`setup_olodto.sh`) for the Omnitide Local LLM Deployment & Training Orchestrator (OLODTO). This script must be robust, cross-platform (Linux/macOS primary, with WSL compatibility), and inherently secure, preparing the host system for a local Llama 3 instance and the secure deployment of the Omnitide Remote Execution Agent (OREA).

## Key Requirements for `setup_olodto.sh`
1.  **OS & Hardware Detection:** Dynamically detect the operating system (Linux, macOS, WSL) and hardware (CPU, GPU - NVIDIA, AMD, Apple Silicon).
2.  **Dependency Installation:** Install essential tools and libraries:
    * `ollama` (for local LLM management)
    * `llama-cpp-python` (with appropriate GPU backend support)
    * `conda` (Miniconda recommended, or `venv` if `conda` is not preferred/available)
    * `bitsandbytes` (for quantization)
    * `unsloth` (for efficient fine-tuning, if GPU supports it)
    * `PyTorch` (with CUDA/ROCm/Metal support based on detected GPU)
    * `docker` and `docker-compose`
    * `nginx` (for secure API gateway)
    * `firejail` (for sandboxing)
    * `fail2ban` (for SSH brute-force protection)
    * `cryptsetup` (for disk encryption check/recommendation)
    * `gpg` (for key generation/signing)
3.  **System Optimization:** Configure OS-level settings for LLM performance (e.g., kernel parameters for large memory pages, GPU power management, disabling unnecessary services).
4.  **Secure Directory Setup:** Create and harden directories (`/opt/omnitide_nexus`, `/var/log/omnitide_nexus`) for models, training data, and logs, setting strict `chown`, `chmod`, and recommending `SELinux`/`AppArmor` profiles. Implement `inotify` watches for critical directories.
5.  **Nginx & SSL/TLS Configuration:** Auto-generate an `nginx.conf` for a reverse proxy, including:
    * Self-signed SSL/TLS certificates for initial secure local access.
    * Strong cipher suites and TLS 1.3 preference.
    * Mutual TLS (mTLS) configuration.
    * IP whitelisting for `/api/` endpoints (placeholder for your specific IP).
    * Basic rate limiting and WAF-like rules for `/api/`.
6.  **Service Management:** Generate `systemd` unit files (Linux) or `launchd` plists (macOS) for `ollama`, `nginx`, and future Nexus services, ensuring least privilege, auto-restart on failure, and secure logging.
7.  **SSH Hardening for OREA:** Configure SSH daemon settings (`sshd_config`) for a dedicated `omnitide_orea` user with restricted access (e.g., `ForceCommand`, `no-port-forwarding`, `no-X11-forwarding`), to enable secure remote execution from Lily. Generate SSH keys for this user.
8.  **Comprehensive Logging & Audit:** Ensure the script itself logs all actions, and sets up robust system logging for future Nexus components.
9.  **Idempotence & Self-Healing:** The script should be runnable multiple times without issues and attempt to correct configuration drifts.
10. **User Guidance:** Provide clear, concise prompts and instructions for the user (Architect) at each critical step, especially for actions requiring manual confirmation (e.g., `sudo` passwords, IP whitelisting).
11. **Security Checks:** Integrate checks for disk encryption status (recommend `cryptsetup`), and offer to configure basic firewall rules (`ufw` or `pfctl`).

## Output Format
A single, executable Bash script named `setup_olodto.sh`. The script should be heavily commented, robust, and include clear `echo` statements for user feedback.