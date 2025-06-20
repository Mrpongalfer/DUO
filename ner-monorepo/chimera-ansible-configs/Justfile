# Simple Task Runner Configuration - Managed by Chimera
# Usage: just <task_name>

# Default variables (can be overridden)
inventory_file := "inventory/hosts_generated"
main_playbook := "site.yml"
vault_arg := "--ask-vault-pass" # Remove this if vault_password_file is configured and working

# Lint the entire project
lint:
    yamllint .
    ansible-lint

# Check playbook syntax
syntax_check:
    ansible-playbook -i {{inventory_file}} {{main_playbook}} --syntax-check

# Run playbook in check mode (dry run)
check:
    ansible-playbook -i {{inventory_file}} {{main_playbook}} {{vault_arg}} --ask-become-pass --check

# Apply the full configuration
apply:
    ansible-playbook -i {{inventory_file}} {{main_playbook}} {{vault_arg}} --ask-become-pass

# Run playbook with specific tags
apply_tags tags:
    ansible-playbook -i {{inventory_file}} {{main_playbook}} {{vault_arg}} --ask-become-pass --tags "{{tags}}"

# View vault-encrypted file (requires vault password)
view_vault file:
    ansible-vault view {{vault_arg}} {{file}}

# Edit vault-encrypted file (requires vault password)
edit_vault file:
    ansible-vault edit {{vault_arg}} {{file}}

# Encrypt file with vault
encrypt file:
    ansible-vault encrypt {{vault_arg}} {{file}}

# Decrypt file with vault
decrypt file:
    ansible-vault decrypt {{vault_arg}} {{file}}

# Show Ansible inventory graph (requires ansible-inventory-grapher)
# graph:
#   ansible-inventory -i {{inventory_file}} --graph

# Default task
default: lint syntax_check


# Run Goss infrastructure validation tests
test_infra:
    ansible-playbook -i {{inventory_file}} test_infra.yml {{vault_arg}} --ask-become-pass
