#!/bin/bash
# Script to run linting using ruff
# Usage: ./scripts/lint.sh

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "========================================"
echo "Running Linter (ruff)"
echo "========================================"

# Check if virtual environment is activated
if [[ -z "${VIRTUAL_ENV}" ]]; then
    echo -e "${RED}Error: Virtual environment is not activated${NC}"
    echo "Please activate your virtual environment first:"
    echo "  source .venv/bin/activate"
    exit 1
fi

# Check if ruff is installed
if ! command -v ruff &> /dev/null; then
    echo -e "${RED}Error: ruff is not installed${NC}"
    echo "Please install dev dependencies:"
    echo "  pip install -e '.[dev]'"
    exit 1
fi

# Run ruff check with auto-fix
echo -e "${GREEN}Running ruff check --fix .${NC}"
echo ""

ruff check --fix .
exit_code=$?

echo ""
echo "========================================"
if [ $exit_code -eq 0 ]; then
    echo -e "${GREEN}✓ Linting passed${NC}"
else
    echo -e "${RED}✗ Linting failed${NC}"
fi
echo "========================================"

exit $exit_code
