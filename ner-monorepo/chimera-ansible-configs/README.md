# Chimera Ansible Configs: Monitoring Stack Deployment

**Project Status (As of: 2025-04-25):** Core observability stack (Prometheus, Loki, Grafana, Node Exporter, Promtail) successfully deployed via Ansible and Docker. Loki configuration stabilized. Ready for Grafana data source configuration and dashboard import.

## Purpose

This Ansible project automates the deployment and configuration of:
1.  A baseline secure operating environment (common packages, users, timezone, SSH hardening, UFW firewall).
2.  The Docker runtime environment.
3.  A containerized observability stack including Prometheus (metrics), Loki (logs), Grafana (visualization), Node Exporter (system metrics), and Promtail (log shipping).

## Managed Infrastructure

* **Control Node:** `192.168.0.96` (`pong` @ pop-os) - Where Ansible commands are run.
* **Target Hosts:** Defined in `inventory/hosts_generated`.
    * `[server]` group: `192.168.0.95` (`aiseed`) - Runs Prometheus, Loki, Grafana containers.
    * `[clients]` group: `192.168.0.96` (`pong`) - Runs Node Exporter, Promtail.
* **Note:** Node Exporter and Promtail run on *all* hosts defined in the `all` group (currently server and client).

## Core Technologies

* **Automation:** Ansible (Core 2.17.10)
* **Containerization:** Docker, Docker Compose (v2 Plugin)
* **Metrics:** Prometheus, Node Exporter
* **Logs:** Loki, Promtail
* **Visualization:** Grafana
* **Security:** UFW (Firewall), SSH Hardening (via template)

## Project Structure

* `site.yml`: Main playbook defining execution flow across host groups.
* `inventory/`: Contains host definitions (`hosts_generated`) and group/host variables (`group_vars/`). Vault secrets are in `inventory/group_vars/all/vault.yml`.
* `roles/`: Contains discrete Ansible roles for each component (common, security, docker, prometheus, loki, grafana, etc.). Each role has tasks, templates, handlers, vars, defaults.
* `vars/`: Contains common variable files (e.g., `common_packages.yml`) - though current setup primarily uses vars defined directly in `site.yml`.
* `ansible.cfg`: Ansible configuration settings (inventory path, SSH settings).

## Prerequisites

* Python 3.10+ with `venv`.
* Ansible virtual environment (`~/ansible_venv`) activated (`source ~/ansible_venv/bin/activate`).
* Required packages installed in venv (`pip install -r requirements.txt` if one exists, or manually installed: `ansible-core==2.17.10`, `PyYAML`, etc.).
* Required Ansible collections installed (`ansible-galaxy collection install community.docker community.general`).
* Git installed on the control node.
* SSH key-based access configured from control node (`pong`) to targets (`aiseed`, `pong`) for the specified `ansible_user` in the inventory.
* Ansible Vault password available for decryption.

## How to Run

1.  Navigate to the project directory: `cd ~/Projects/chimera-ansible-configs`
2.  Activate the virtual environment: `source ~/ansible_venv/bin/activate`
3.  Execute the playbook:
    ```bash
    ansible-playbook site.yml --ask-vault-pass --ask-become-pass
    ```
4.  Enter the BECOME (sudo) password and Vault password when prompted.

## Key Services & Access Points (on Server: 192.168.0.95)

* **Prometheus:** `http://192.168.0.95:9091`
* **Grafana:** `http://192.168.0.95:3000` (Login: `admin` / Password from `grafana_admin_password` var or default `ChangeMePlease!`)
* **Loki:** `http://192.168.0.95:3100` (Check readiness: `http://192.168.0.95:3100/ready`)
* **Node Exporter:** Port `9100` (on both `192.168.0.95` and `192.168.0.96`)

## Next Steps / Configuration

1.  **Configure Grafana Data Sources:** Manually add Prometheus (`http://prometheus:9090`) and Loki (`http://loki:3100`) via the Grafana UI (Connections -> Data Sources). Use the service names as Grafana runs in the same Docker network.
2.  **Import Grafana Dashboards:** Import a Node Exporter dashboard (e.g., ID `1860`) to visualize system metrics.
3.  **(Optional Cleanuo):** Apply the Prometheus task file cleanup mentioned previously.
4.  **Deploy Applications:** Add roles for desired applications (e.g., LLM web app) to `site.yml` and run the playbook.
