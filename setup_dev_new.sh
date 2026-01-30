#!/bin/bash
# Development environment setup for HA Squid Proxy Manager
# OS: macOS, Linux (Ubuntu, Debian, etc.)
# Requirements: Docker, Node.js, Git (will check and guide installation)

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Utility functions
log_success() { echo -e "${GREEN}✓${NC} $1"; }
log_error() { echo -e "${RED}✗${NC} $1"; }
log_info() { echo -e "${BLUE}ℹ${NC} $1"; }
log_warning() { echo -e "${YELLOW}⚠${NC} $1"; }

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║ HA Squid Proxy Manager - Development Setup (macOS/Linux)  ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Detect OS
if [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
    PACKAGE_MANAGER="brew"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
    # Detect Linux distribution
    if command -v apt-get &> /dev/null; then
        PACKAGE_MANAGER="apt"
    elif command -v yum &> /dev/null; then
        PACKAGE_MANAGER="yum"
    else
        PACKAGE_MANAGER="unknown"
    fi
else
    log_error "Unsupported OS: $OSTYPE"
    exit 1
fi

log_info "Detected OS: $OS (Package manager: $PACKAGE_MANAGER)"
echo ""

# ============================================================================
# 1. Check & Install Docker
# ============================================================================
echo -e "${BLUE}━━ Checking Docker${NC}"

if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version | cut -d' ' -f3 | tr -d ',')
    log_success "Docker: $DOCKER_VERSION"
else
    log_error "Docker is required but not installed"
    echo ""
    if [[ "$OS" == "macos" ]]; then
        log_info "Install Docker Desktop for macOS:"
        echo "  → https://docs.docker.com/desktop/install/mac-install/"
    else
        log_info "Install Docker for Linux:"
        echo "  → https://docs.docker.com/engine/install/ubuntu/"
    fi
    exit 1
fi

# Check Docker Compose (usually included in Docker Desktop)
if docker compose version &> /dev/null; then
    COMPOSE_VERSION=$(docker compose version --short)
    log_success "Docker Compose: $COMPOSE_VERSION"
else
    log_error "Docker Compose not found"
    exit 1
fi

# Test Docker daemon is running
if ! docker info &> /dev/null; then
    log_error "Docker daemon is not running"
    if [[ "$OS" == "macos" ]]; then
        log_info "Start Docker Desktop from Applications folder"
    else
        log_info "Start Docker daemon: sudo systemctl start docker"
    fi
    exit 1
fi

echo ""

# ============================================================================
# 2. Check & Install Node.js / npm
# ============================================================================
echo -e "${BLUE}━━ Checking Node.js / npm${NC}"

if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    NPM_VERSION=$(npm --version)
    log_success "Node.js: $NODE_VERSION"
    log_success "npm: $NPM_VERSION"
else
    log_warning "Node.js / npm not found"
    echo ""

    if [[ "$OS" == "macos" ]]; then
        log_info "Installing Node.js via Homebrew..."
        if ! command -v brew &> /dev/null; then
            log_error "Homebrew not installed"
            echo "Install Homebrew: https://brew.sh/"
            exit 1
        fi
        brew install node
    elif [[ "$PACKAGE_MANAGER" == "apt" ]]; then
        log_info "Installing Node.js via apt..."
        sudo apt update
        sudo apt install -y nodejs npm
    elif [[ "$PACKAGE_MANAGER" == "yum" ]]; then
        log_info "Installing Node.js via yum..."
        sudo yum install -y nodejs npm
    else
        log_error "Unknown package manager. Install Node.js manually: https://nodejs.org/"
        exit 1
    fi

    log_success "Node.js installed"
    NODE_VERSION=$(node --version)
    NPM_VERSION=$(npm --version)
    log_success "Node.js: $NODE_VERSION"
    log_success "npm: $NPM_VERSION"
fi

echo ""

# ============================================================================
# 3. Check & Install Git
# ============================================================================
echo -e "${BLUE}━━ Checking Git${NC}"

if command -v git &> /dev/null; then
    GIT_VERSION=$(git --version)
    log_success "$GIT_VERSION"
else
    log_warning "Git not found. Installing..."

    if [[ "$OS" == "macos" ]]; then
        if ! command -v brew &> /dev/null; then
            log_error "Homebrew required. Install: https://brew.sh/"
            exit 1
        fi
        brew install git
    elif [[ "$PACKAGE_MANAGER" == "apt" ]]; then
        sudo apt update
        sudo apt install -y git
    elif [[ "$PACKAGE_MANAGER" == "yum" ]]; then
        sudo yum install -y git
    fi

    log_success "Git installed"
fi

echo ""

# ============================================================================
# 4. Check Python (informational only, runs in Docker)
# ============================================================================
echo -e "${BLUE}━━ Python Configuration${NC}"

if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    log_info "Python: $PYTHON_VERSION (runs in Docker, not needed locally)"
else
    log_info "Python not installed locally (runs in Docker, not needed)"
fi

echo ""

# ============================================================================
# 5. Install Frontend Dependencies
# ============================================================================
echo -e "${BLUE}━━ Installing Frontend Dependencies${NC}"

if [ -f "squid_proxy_manager/frontend/package.json" ]; then
    log_info "Running: npm install --prefix squid_proxy_manager/frontend"
    npm install --prefix squid_proxy_manager/frontend
    log_success "Frontend dependencies installed"
else
    log_warning "package.json not found in frontend directory"
fi

echo ""

# ============================================================================
# 6. Build Test Containers
# ============================================================================
echo -e "${BLUE}━━ Building Test Containers${NC}"

log_info "This may take 2-5 minutes on first run..."
log_info "Building: test-runner image"

if docker compose -f docker-compose.test.yaml --profile unit build test-runner; then
    log_success "Test containers built successfully"
else
    log_error "Failed to build test containers"
    exit 1
fi

echo ""

# ============================================================================
# 7. Run Quick Verification
# ============================================================================
echo -e "${BLUE}━━ Running Verification${NC}"

log_info "Running quick test to verify setup..."

if docker compose -f docker-compose.test.yaml --profile unit run --rm test-runner \
    pytest tests/unit/test_proxy_manager.py::test_create_instance_basic -v &> /dev/null; then
    log_success "Setup verification passed"
else
    log_warning "Some tests may need Docker daemon or full setup"
fi

echo ""

# ============================================================================
# 8. Display Summary & Next Steps
# ============================================================================
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║ ✓ Development Environment Ready                            ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${YELLOW}Next Steps:${NC}"
echo ""
echo "  1. Run all tests:"
echo "     ${BLUE}./run_tests.sh${NC}"
echo ""
echo "  2. Or run specific test suite:"
echo "     ${BLUE}./run_tests.sh unit${NC}      # Unit + integration tests (fast)"
echo "     ${BLUE}./run_tests.sh e2e${NC}       # E2E tests with real Squid"
echo ""
echo "  3. Start frontend development:"
echo "     ${BLUE}npm run dev --prefix squid_proxy_manager/frontend${NC}"
echo ""
echo "  4. IDE Setup (recommended):"
echo "     - Install Python extension (ms-python.python)"
echo "     - Install Black Formatter (ms-python.black-formatter)"
echo "     - Install Ruff (charliermarsh.ruff)"
echo "     - See DEVELOPMENT.md for full IDE setup"
echo ""
echo -e "${YELLOW}Documentation:${NC}"
echo "  - ${BLUE}DEVELOPMENT.md${NC}    Feature development guide"
echo "  - ${BLUE}REQUIREMENTS.md${NC}   Project requirements & scenarios"
echo "  - ${BLUE}TEST_PLAN.md${NC}      Testing procedures & coverage"
echo ""
