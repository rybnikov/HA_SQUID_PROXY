# Development environment setup script for Squid Proxy Manager HA Integration (Windows PowerShell)
# This script sets up a complete development environment from scratch.

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
} catch {
    Write-Host "⚠️  Docker is REQUIRED for E2E tests." -ForegroundColor Yellow
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
pip install `
    pytest `
    pytest-asyncio `
    pytest-cov `
    pytest-playwright `
    playwright `
    black `
    mypy `
    ruff `
    bandit `
    safety `
    pre-commit `
    aiohttp `
    cryptography `
    bcrypt `
    requests `
    types-requests `
    types-setuptools

# Install Playwright browsers
Write-Host ""
Write-Host "Installing Playwright browsers..." -ForegroundColor Blue
playwright install chromium

Write-Host "✓ Development dependencies installed" -ForegroundColor Green

# Setup pre-commit hooks
Write-Host ""
Write-Host "Setting up pre-commit hooks..." -ForegroundColor Blue
pre-commit install
Write-Host "✓ Pre-commit hooks installed" -ForegroundColor Green

Write-Host ""
Write-Host "✓ Development environment setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Activate the virtual environment: venv\Scripts\Activate.ps1" -ForegroundColor Cyan
Write-Host "2. Run unit/integration tests: ./run_tests.sh" -ForegroundColor Cyan
Write-Host "3. Run E2E tests (requires Docker): docker compose -f docker-compose.test.yaml up --build --exit-code-from tester" -ForegroundColor Cyan
Write-Host "4. Read DEVELOPMENT.md for more information" -ForegroundColor Cyan
Write-Host ""
