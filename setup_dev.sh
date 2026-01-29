#!/bin/bash
# Development environment setup script for HA Squid Proxy Manager
# This script sets up a complete development environment from scratch.

set -e  # Exit on error

echo "🚀 Setting up development environment for Squid Proxy Manager..."

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed. Please install Python 3.10 or later."
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "✓ Found Python ${PYTHON_VERSION}"

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is REQUIRED for E2E tests."
    echo "   Please install Docker: https://docs.docker.com/get-docker/"
    # Don't exit here, still allow local dev setup
else
    echo "✓ Found Docker: $(docker --version)"
fi

# Create virtual environment
echo ""
echo -e "${BLUE}Creating Python virtual environment...${NC}"
if [ -d "venv" ]; then
    echo "⚠️  Virtual environment already exists. Skipping creation."
else
    python3 -m venv venv
    echo "✓ Virtual environment created"
fi

# Activate virtual environment
echo ""
echo -e "${BLUE}Activating virtual environment...${NC}"
source venv/bin/activate

# Upgrade pip
echo ""
echo -e "${BLUE}Upgrading pip...${NC}"
pip install --upgrade pip setuptools wheel

# Install development dependencies
echo ""
echo -e "${BLUE}Installing development dependencies...${NC}"
pip install \
    pytest \
    pytest-asyncio \
    pytest-cov \
    pytest-playwright \
    playwright \
    black \
    mypy \
    ruff \
    bandit \
    safety \
    pre-commit \
    aiohttp \
    cryptography \
    bcrypt \
    requests \
    types-requests \
    types-setuptools

# Install Playwright browsers
echo ""
echo -e "${BLUE}Installing Playwright browsers...${NC}"
playwright install chromium

echo "✓ Development dependencies installed"

# Install pre-commit hooks
echo ""
echo -e "${BLUE}Setting up pre-commit hooks...${NC}"
pre-commit install
echo "✓ Pre-commit hooks installed"

echo ""
echo -e "${GREEN}✓ Development environment setup complete!${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Activate the virtual environment: ${BLUE}source venv/bin/activate${NC}"
echo "2. Run unit/integration tests: ${BLUE}./run_tests.sh${NC}"
echo "3. Run E2E tests (requires Docker): ${BLUE}docker compose -f docker-compose.test.yaml up --build --exit-code-from tester${NC}"
echo "4. Read DEVELOPMENT.md for more information"
echo ""
