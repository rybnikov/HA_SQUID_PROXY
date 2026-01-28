# Development environment setup script for Squid Proxy Manager HA Integration (Windows PowerShell)

$ErrorActionPreference = "Stop"

Write-Host "🚀 Setting up development environment for Squid Proxy Manager..." -ForegroundColor Cyan

# Check if Python 3 is available
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✓ Found Python: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Python 3 is required but not installed. Please install Python 3.10 or later." -ForegroundColor Red
    exit 1
}

# Check if Docker is available
try {
    $dockerVersion = docker --version
    Write-Host "✓ Found Docker: $dockerVersion" -ForegroundColor Green
    
    # Check if Docker daemon is running
    docker info | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Docker daemon is running" -ForegroundColor Green
    } else {
        Write-Host "⚠️  Docker daemon is not running. Please start Docker." -ForegroundColor Yellow
    }
} catch {
    Write-Host "⚠️  Docker is not installed. You'll need Docker for testing the integration." -ForegroundColor Yellow
}

# Create virtual environment
Write-Host ""
Write-Host "Creating Python virtual environment..." -ForegroundColor Blue
if (Test-Path "venv") {
    Write-Host "⚠️  Virtual environment already exists. Skipping creation." -ForegroundColor Yellow
} else {
    python -m venv venv
    Write-Host "✓ Virtual environment created" -ForegroundColor Green
}

# Activate virtual environment
Write-Host ""
Write-Host "Activating virtual environment..." -ForegroundColor Blue
& "venv\Scripts\Activate.ps1"

# Upgrade pip
Write-Host ""
Write-Host "Upgrading pip..." -ForegroundColor Blue
python -m pip install --upgrade pip setuptools wheel --quiet

# Install development dependencies
Write-Host ""
Write-Host "Installing development dependencies..." -ForegroundColor Blue
pip install -q `
    pytest `
    pytest-asyncio `
    pytest-cov `
    pylint `
    black `
    mypy `
    ruff `
    pre-commit `
    docker `
    cryptography `
    bcrypt

Write-Host "✓ Development dependencies installed" -ForegroundColor Green

# Install integration dependencies
Write-Host ""
Write-Host "Installing integration dependencies..." -ForegroundColor Blue
pip install -q `
    homeassistant `
    voluptuous `
    aiohttp

Write-Host "✓ Integration dependencies installed" -ForegroundColor Green

# Create .gitignore if it doesn't exist
Write-Host ""
Write-Host "Setting up .gitignore..." -ForegroundColor Blue
if (-not (Test-Path ".gitignore")) {
    @"
# Python
__pycache__/
*.py[cod]
*`$py.class
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
"@ | Out-File -FilePath ".gitignore" -Encoding UTF8
    Write-Host "✓ .gitignore created" -ForegroundColor Green
} else {
    Write-Host "✓ .gitignore already exists" -ForegroundColor Green
}

# Create pre-commit config if it doesn't exist
Write-Host ""
Write-Host "Setting up pre-commit hooks..." -ForegroundColor Blue
if (-not (Test-Path ".pre-commit-config.yaml")) {
    @"
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
"@ | Out-File -FilePath ".pre-commit-config.yaml" -Encoding UTF8
    Write-Host "✓ .pre-commit-config.yaml created" -ForegroundColor Green
    
    # Install pre-commit hooks
    pre-commit install
    Write-Host "✓ Pre-commit hooks installed" -ForegroundColor Green
} else {
    Write-Host "✓ .pre-commit-config.yaml already exists" -ForegroundColor Green
    pre-commit install --install-hooks
}

# Create pytest configuration
Write-Host ""
Write-Host "Setting up pytest configuration..." -ForegroundColor Blue
if (-not (Test-Path "pytest.ini")) {
    @"
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
"@ | Out-File -FilePath "pytest.ini" -Encoding UTF8
    Write-Host "✓ pytest.ini created" -ForegroundColor Green
} else {
    Write-Host "✓ pytest.ini already exists" -ForegroundColor Green
}

# Create tests directory structure
Write-Host ""
Write-Host "Creating tests directory structure..." -ForegroundColor Blue
New-Item -ItemType Directory -Force -Path "tests\unit" | Out-Null
New-Item -ItemType Directory -Force -Path "tests\integration" | Out-Null
New-Item -ItemType File -Force -Path "tests\__init__.py" | Out-Null
New-Item -ItemType File -Force -Path "tests\unit\__init__.py" | Out-Null
New-Item -ItemType File -Force -Path "tests\integration\__init__.py" | Out-Null
Write-Host "✓ Tests directory structure created" -ForegroundColor Green

# Create pyproject.toml for tool configuration
Write-Host ""
Write-Host "Setting up tool configuration..." -ForegroundColor Blue
if (-not (Test-Path "pyproject.toml")) {
    @"
[tool.black]
line-length = 100
target-version = ['py310']
include = '\.pyi?`$'
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
"@ | Out-File -FilePath "pyproject.toml" -Encoding UTF8
    Write-Host "✓ pyproject.toml created" -ForegroundColor Green
} else {
    Write-Host "✓ pyproject.toml already exists" -ForegroundColor Green
}

# Create a simple test example
Write-Host ""
Write-Host "Creating example test file..." -ForegroundColor Blue
if (-not (Test-Path "tests\unit\test_const.py")) {
    @"
"""Unit tests for constants."""
from custom_components.squid_proxy_manager.const import DOMAIN, DEFAULT_PORT


def test_domain():
    """Test that DOMAIN is set correctly."""
    assert DOMAIN == "squid_proxy_manager"


def test_default_port():
    """Test that default port is valid."""
    assert DEFAULT_PORT >= 1024
    assert DEFAULT_PORT <= 65535
"@ | Out-File -FilePath "tests\unit\test_const.py" -Encoding UTF8
    Write-Host "✓ Example test file created" -ForegroundColor Green
} else {
    Write-Host "✓ Test files already exist" -ForegroundColor Green
}

Write-Host ""
Write-Host "✓ Development environment setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Activate the virtual environment: venv\Scripts\Activate.ps1" -ForegroundColor Cyan
Write-Host "2. Run tests: pytest" -ForegroundColor Cyan
Write-Host "3. Format code: black custom_components\" -ForegroundColor Cyan
Write-Host "4. Read DEVELOPMENT.md for more information" -ForegroundColor Cyan
Write-Host ""
