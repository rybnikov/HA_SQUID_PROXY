#!/bin/bash
# Development environment setup script for Squid Proxy Manager HA Integration

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
    echo "⚠️  Docker is not installed. You'll need Docker for testing the integration."
else
    DOCKER_VERSION=$(docker --version)
    echo "✓ Found Docker: ${DOCKER_VERSION}"
    
    # Check if Docker daemon is running
    if docker info &> /dev/null; then
        echo "✓ Docker daemon is running"
    else
        echo "⚠️  Docker daemon is not running. Please start Docker."
    fi
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
pip install -q \
    pytest \
    pytest-asyncio \
    pytest-cov \
    pylint \
    black \
    mypy \
    ruff \
    pre-commit \
    docker \
    cryptography \
    bcrypt

echo "✓ Development dependencies installed"

# Install integration dependencies (for testing)
echo ""
echo -e "${BLUE}Installing integration dependencies...${NC}"
pip install -q \
    homeassistant \
    voluptuous \
    aiohttp

echo "✓ Integration dependencies installed"

# Create .gitignore if it doesn't exist
echo ""
echo -e "${BLUE}Setting up .gitignore...${NC}"
if [ ! -f ".gitignore" ]; then
    cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
env/
ENV/
.venv
pip-log.txt
pip-delete-this-directory.txt

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# Testing
.pytest_cache/
.coverage
htmlcov/
.tox/
.hypothesis/

# Home Assistant
.config/
.storage/

# Docker
*.log
*.pid

# OS
.DS_Store
Thumbs.db

# Development
*.egg-info/
dist/
build/
EOF
    echo "✓ .gitignore created"
else
    echo "✓ .gitignore already exists"
fi

# Create pre-commit config if it doesn't exist
echo ""
echo -e "${BLUE}Setting up pre-commit hooks...${NC}"
if [ ! -f ".pre-commit-config.yaml" ]; then
    cat > .pre-commit-config.yaml << 'EOF'
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
      - id: check-json
      - id: check-merge-conflict
      - id: debug-statements
      - id: mixed-line-ending

  - repo: https://github.com/psf/black
    rev: 23.12.1
    hooks:
      - id: black
        language_version: python3

  - repo: https://github.com/charliermarsh/ruff-pre-commit
    rev: v0.1.9
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0
    hooks:
      - id: mypy
        additional_dependencies: [types-all]
EOF
    echo "✓ .pre-commit-config.yaml created"
    
    # Install pre-commit hooks
    pre-commit install
    echo "✓ Pre-commit hooks installed"
else
    echo "✓ .pre-commit-config.yaml already exists"
    pre-commit install --install-hooks
fi

# Create pytest configuration
echo ""
echo -e "${BLUE}Setting up pytest configuration...${NC}"
if [ ! -f "pytest.ini" ]; then
    cat > pytest.ini << 'EOF'
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
asyncio_mode = auto
addopts = 
    --verbose
    --strict-markers
    --cov=custom_components
    --cov-report=term-missing
    --cov-report=html
markers =
    integration: Integration tests
    unit: Unit tests
EOF
    echo "✓ pytest.ini created"
else
    echo "✓ pytest.ini already exists"
fi

# Create tests directory structure
echo ""
echo -e "${BLUE}Creating tests directory structure...${NC}"
mkdir -p tests/{unit,integration}
touch tests/__init__.py
touch tests/unit/__init__.py
touch tests/integration/__init__.py
echo "✓ Tests directory structure created"

# Create pyproject.toml for tool configuration
echo ""
echo -e "${BLUE}Setting up tool configuration...${NC}"
if [ ! -f "pyproject.toml" ]; then
    cat > pyproject.toml << 'EOF'
[tool.black]
line-length = 100
target-version = ['py310']
include = '\.pyi?$'
extend-exclude = '''
/(
  # directories
  \.eggs
  | \.git
  | \.hg
  | \.mypy_cache
  | \.tox
  | \.venv
  | venv
  | _build
  | buck-out
  | build
  | dist
)/
'''

[tool.ruff]
line-length = 100
target-version = "py310"
select = [
    "E",  # pycodestyle errors
    "W",  # pycodestyle warnings
    "F",  # pyflakes
    "I",  # isort
    "B",  # flake8-bugbear
    "C4", # flake8-comprehensions
    "UP", # pyupgrade
]
ignore = [
    "E501",  # line too long (handled by black)
    "B008",  # do not perform function calls in argument defaults
]

[tool.ruff.per-file-ignores]
"__init__.py" = ["F401"]  # unused imports

[tool.mypy]
python_version = "3.10"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = false
disallow_incomplete_defs = false
check_untyped_defs = true
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
warn_no_return = true
follow_imports = "normal"
ignore_missing_imports = true

[[tool.mypy.overrides]]
module = [
    "homeassistant.*",
    "voluptuous.*",
    "docker.*",
]
ignore_missing_imports = true
EOF
    echo "✓ pyproject.toml created"
else
    echo "✓ pyproject.toml already exists"
fi

# Create a simple test example
echo ""
echo -e "${BLUE}Creating example test file...${NC}"
if [ ! -f "tests/unit/test_const.py" ]; then
    cat > tests/unit/test_const.py << 'EOF'
"""Unit tests for constants."""
from custom_components.squid_proxy_manager.const import DOMAIN, DEFAULT_PORT


def test_domain():
    """Test that DOMAIN is set correctly."""
    assert DOMAIN == "squid_proxy_manager"


def test_default_port():
    """Test that default port is valid."""
    assert DEFAULT_PORT >= 1024
    assert DEFAULT_PORT <= 65535
EOF
    echo "✓ Example test file created"
else
    echo "✓ Test files already exist"
fi

# Create development README
echo ""
echo -e "${BLUE}Creating development documentation...${NC}"
if [ ! -f "DEVELOPMENT.md" ]; then
    cat > DEVELOPMENT.md << 'EOF'
# Development Guide

## Setup

Run the setup script to initialize the development environment:

```bash
./setup_dev.sh
```

Or on Windows:

```powershell
.\setup_dev.ps1
```

## Virtual Environment

Activate the virtual environment:

```bash
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate  # Windows
```

## Running Tests

Run all tests:

```bash
pytest
```

Run with coverage:

```bash
pytest --cov=custom_components --cov-report=html
```

Run specific test file:

```bash
pytest tests/unit/test_const.py
```

## Code Quality

Format code with Black:

```bash
black custom_components/
```

Lint with Ruff:

```bash
ruff check custom_components/
```

Type checking with mypy:

```bash
mypy custom_components/
```

Run all checks:

```bash
pre-commit run --all-files
```

## Testing with Home Assistant

1. Copy the integration to your Home Assistant `custom_components` directory
2. Restart Home Assistant
3. Add the integration via the UI

## Docker Testing

Build the Docker image:

```bash
docker build -f custom_components/squid_proxy_manager/docker/Dockerfile.scratch -t squid-proxy-manager .
```

## Project Structure

```
SuidManagerHA/
├── custom_components/
│   └── squid_proxy_manager/  # Integration code
├── tests/                    # Test files
├── venv/                     # Virtual environment
├── setup_dev.sh              # Setup script
└── DEVELOPMENT.md           # This file
```

## Contributing

1. Create a feature branch
2. Make your changes
3. Run tests and linting
4. Commit with descriptive messages
5. Push and create a pull request
EOF
    echo "✓ DEVELOPMENT.md created"
else
    echo "✓ DEVELOPMENT.md already exists"
fi

echo ""
echo -e "${GREEN}✓ Development environment setup complete!${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Activate the virtual environment: ${BLUE}source venv/bin/activate${NC}"
echo "2. Run tests: ${BLUE}pytest${NC}"
echo "3. Format code: ${BLUE}black custom_components/${NC}"
echo "4. Read DEVELOPMENT.md for more information"
echo ""
