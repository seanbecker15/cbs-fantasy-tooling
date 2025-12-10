#!/bin/bash
# Script to run all tests using pytest
# Usage: ./scripts/test.sh

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "========================================"
echo "Running Tests"
echo "========================================"

# Check if virtual environment is activated
if [[ -z "${VIRTUAL_ENV}" ]]; then
    echo -e "${RED}Error: Virtual environment is not activated${NC}"
    echo "Please activate your virtual environment first:"
    echo "  source .venv/bin/activate"
    exit 1
fi

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo -e "${RED}Error: pytest is not installed${NC}"
    echo "Please install dev dependencies:"
    echo "  pip install -e '.[dev]'"
    exit 1
fi

# Run pytest
echo -e "${GREEN}Running pytest...${NC}"
echo ""

# Run pytest with coverage and verbose output
# Exit with pytest's exit code
pytest -v "$@"
exit_code=$?

echo ""
echo "========================================"
if [ $exit_code -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed${NC}"
elif [ $exit_code -eq 5 ]; then
    echo -e "${YELLOW}⚠ No tests found${NC}"
else
    echo -e "${RED}✗ Tests failed${NC}"
fi
echo "========================================"

exit $exit_code
