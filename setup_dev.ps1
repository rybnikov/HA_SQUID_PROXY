# Development environment setup - Docker only
# Only Docker is required. IDE plugins handle linting/formatting.

$ErrorActionPreference = "Stop"

Write-Host "🚀 Setting up development environment for Squid Proxy Manager..." -ForegroundColor Cyan
Write-Host ""

# Check Docker
try {
    $dockerVersion = (docker --version) -replace 'Docker version ', '' -replace ',.*', ''
    Write-Host "✓ Docker: $dockerVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Docker is required but not installed." -ForegroundColor Red
    Write-Host "   Please install Docker: https://docs.docker.com/get-docker/" -ForegroundColor Yellow
    exit 1
}

# Check Docker Compose
try {
    $composeVersion = docker compose version --short
    Write-Host "✓ Docker Compose: $composeVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Docker Compose is required but not installed." -ForegroundColor Red
    Write-Host "   Please install Docker Compose: https://docs.docker.com/compose/install/" -ForegroundColor Yellow
    exit 1
}

# Build test containers
Write-Host ""
Write-Host "Building test containers (this may take a few minutes first time)..." -ForegroundColor Blue
docker compose -f docker-compose.test.yaml --profile unit build test-runner

Write-Host ""
Write-Host "✓ Development environment ready!" -ForegroundColor Green
Write-Host ""
Write-Host "Usage:" -ForegroundColor Cyan
Write-Host "  ./run_tests.sh          # Run ALL tests in Docker"
Write-Host "  ./run_tests.sh unit     # Run unit + integration tests"
Write-Host "  ./run_tests.sh e2e      # Run E2E tests with real Squid"
Write-Host ""
Write-Host "IDE Setup (recommended):" -ForegroundColor Yellow
Write-Host "  - Install Python extension for your IDE"
Write-Host "  - Install Black formatter extension"
Write-Host "  - Install Ruff linter extension"
Write-Host ""
Write-Host "See DEVELOPMENT.md for full documentation."
