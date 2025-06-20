#!/bin/bash
set -eo pipefail

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# ====================
# PYTHON ENVIRONMENT CHECK
# ====================
check_python() {
    echo -e "\n${YELLOW}=== PYTHON ENVIRONMENT ===${NC}"
    if command -v python3 &>/dev/null; then
        echo -e "${GREEN}✔ Found python3 at $(which python3)${NC}"
        PYTHON_CMD="python3"
    elif command -v python &>/dev/null; then
        echo -e "${YELLOW}⚠ Found python (v2) at $(which python) - may cause issues${NC}"
        PYTHON_CMD="python"
    else
        echo -e "${RED}✖ Python not found! Install with:${NC}"
        echo "sudo apt update && sudo apt install python3 python3-pip"
        exit 1
    fi
}

# ====================
# SYSTEM AUDIT
# ====================
echo -e "\n${YELLOW}=== EKKO SYSTEM DIAGNOSTICS ===${NC}"

# 1. Verify CLI tool exists
if [[ ! -f "ekko-cli.sh" ]]; then
    echo -e "${RED}✖ Missing ekko-cli.sh${NC}"
    echo "Download it with:"
    echo "wget https://raw.githubusercontent.com/mrpongalfer/ekko/main/ekko-cli.sh"
    echo "chmod +x ekko-cli.sh"
    exit 1
else
    echo -e "${GREEN}✔ Found ekko-cli.sh${NC}"
    chmod +x ekko-cli.sh >/dev/null 2>&1
fi

# 2. Test Python environment
check_python

# 3. Test project generation
TEST_PROJECT="ekko_test_project_$RANDOM"
./ekko-cli.sh "$TEST_PROJECT" sample "Test requirement" 2>/dev/null

if [[ -d "$TEST_PROJECT" ]]; then
    echo -e "${GREEN}✔ Project generation works${NC}"

    # Patch validate.sh to use detected Python
    sed -i "s/python/$PYTHON_CMD/" "$TEST_PROJECT/scripts/validate.sh"

    # Verify critical files
    for file in "src/sample.py" "tests/test_sample.py" "scripts/validate.sh"; do
        if [[ ! -f "$TEST_PROJECT/$file" ]]; then
            echo -e "${RED}✖ Missing generated file: $file${NC}"
        fi
    done
else
    echo -e "${RED}✖ Project generation failed${NC}"
fi

# ====================
# FUNCTIONAL DEMO
# ====================
echo -e "\n${YELLOW}=== HANDS-ON DEMO ===${NC}"

# Create sample implementation
cat > "$TEST_PROJECT/src/sample.py" << 'EOD'
def execute():
    """Working implementation"""
    return {"status": "VALID", "test": "passed"}
EOD

# Install pytest if missing
if ! $PYTHON_CMD -m pytest --version &>/dev/null; then
    echo -e "${YELLOW}Installing pytest...${NC}"
    $PYTHON_CMD -m pip install pytest --user
fi

# Run validation
echo -e "${YELLOW}Running tests...${NC}"
cd "$TEST_PROJECT"
if ./scripts/validate.sh; then
    echo -e "${GREEN}✔ Tests passed successfully${NC}"
else
    echo -e "${RED}✖ Test validation failed${NC}"
    echo "Debug with:"
    echo "cd $TEST_PROJECT && $PYTHON_CMD -m pytest -v"
fi
cd ..

# ====================
# USAGE GUIDE
# ====================
echo -e "\n${YELLOW}=== HOW TO USE EKKO ===${NC}"
cat << 'EOD'
1. Create new project:
   ./ekko-cli.sh <PROJECT_NAME> <MODULE_NAME> "TEST_REQ_1" "TEST_REQ_2"

2. Implement functionality:
   nano <PROJECT_NAME>/src/<MODULE_NAME>.py

3. Run validation:
   cd <PROJECT_NAME> && ./scripts/validate.sh

4. Iterate until tests pass.

Example Workflow:
./ekko-cli.sh CryptoExchange transaction "Atomic swaps" "Fraud detection"
nano CryptoExchange/src/transaction.py  # Implement logic
cd CryptoExchange && ./scripts/validate.sh
EOD

# Cleanup
rm -rf "$TEST_PROJECT"
echo -e "\n${GREEN}Diagnostic complete. Cleaned up test project.${NC}"
