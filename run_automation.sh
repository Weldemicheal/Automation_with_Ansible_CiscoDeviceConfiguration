#!/bin/bash
# One-click automation script

set -e  # Exit on error

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Network Automation Suite v2.0${NC}"
echo -e "${BLUE}========================================${NC}"

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv .venv
fi

# Activate virtual environment
echo -e "${YELLOW}Activating virtual environment...${NC}"
source .venv/bin/activate

# Install requirements
echo -e "${YELLOW}Installing Python requirements...${NC}"
pip install -r requirements.txt

# Install Ansible collections
echo -e "${YELLOW}Installing Ansible collections...${NC}"
ansible-galaxy collection install -r requirements.yml

# Run automation
echo -e "${YELLOW}Running network automation...${NC}"
if [ "$1" == "--dry-run" ]; then
    python network_automation.py --dry-run
else
    python network_automation.py
fi

# Deactivate virtual environment
deactivate

echo -e "${GREEN}Automation completed!${NC}"