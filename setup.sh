#!/bin/bash

echo "Setting up Network Automation Environment..."

# Install Python requirements
pip3 install -r requirements.txt

# Install Ansible collections
ansible-galaxy collection install -r requirements.yml

# Create directory structure
mkdir -p group_vars/all
mkdir -p host_vars
mkdir -p backups

# Create vault password file (optional)
echo "Enter vault password: "
read -s VAULT_PASS
echo $VAULT_PASS > .vault_pass

# Set permissions
chmod 600 .vault_pass

echo "Setup complete!"
echo "To run the automation:"
echo "  python3 network_automation.py --playbook configure_network.yml"