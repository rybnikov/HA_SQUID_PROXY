#!/bin/bash
# Development environment setup - Docker only
# Only Docker is required. IDE plugins handle linting/formatting.

set -e

echo "🚀 Setting up development environment for Squid Proxy Manager..."
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is required but not installed.${NC}"
    echo "   Please install Docker: https://docs.docker.com/get-docker/"
    exit 1
fi
echo -e "${GREEN}✓${NC} Docker: $(docker --version | cut -d' ' -f3 | tr -d ',')"

# Check Docker Compose
if ! docker compose version &> /dev/null; then
    echo -e "${RED}❌ Docker Compose is required but not installed.${NC}"
    echo "   Please install Docker Compose: https://docs.docker.com/compose/install/"
    exit 1
fi
echo -e "${GREEN}✓${NC} Docker Compose: $(docker compose version --short)"

# Build test containers (pre-pull base images)
echo ""
echo "Building test containers (this may take a few minutes first time)..."
docker compose -f docker-compose.test.yaml --profile unit build test-runner

echo ""
echo -e "${GREEN}✓ Development environment ready!${NC}"
echo ""
echo "Usage:"
echo "  ./run_tests.sh          # Run ALL tests in Docker"
echo "  ./run_tests.sh unit     # Run unit + integration tests"
echo "  ./run_tests.sh e2e      # Run E2E tests with real Squid"
echo ""
echo -e "${YELLOW}IDE Setup (recommended):${NC}"
echo "  - Install Python extension for your IDE"
echo "  - Install Black formatter extension"
echo "  - Install Ruff linter extension"
echo ""
echo "See DEVELOPMENT.md for full documentation."
