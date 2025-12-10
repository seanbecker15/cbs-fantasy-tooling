#!/bin/bash
# Script to run code formatting using black
# Usage: ./scripts/format.sh

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "========================================"
echo "Running Formatter (black)"
echo "========================================"

# Check if virtual environment is activated
if [[ -z "${VIRTUAL_ENV}" ]]; then
    echo -e "${RED}Error: Virtual environment is not activated${NC}"
    echo "Please activate your virtual environment first:"
    echo "  source .venv/bin/activate"
    exit 1
fi

# Check if black is installed
if ! command -v black &> /dev/null; then
    echo -e "${RED}Error: black is not installed${NC}"
    echo "Please install dev dependencies:"
    echo "  pip install -e '.[dev]'"
    exit 1
fi

# Run black
echo -e "${GREEN}Running black .${NC}"
echo ""

black .
exit_code=$?

echo ""
echo "========================================"
if [ $exit_code -eq 0 ]; then
    echo -e "${GREEN}✓ Formatting complete${NC}"
else
    echo -e "${RED}✗ Formatting failed${NC}"
fi
echo "========================================"

exit $exit_code
