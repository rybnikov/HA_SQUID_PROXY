# Development environment setup for HA Squid Proxy Manager
# OS: Windows (PowerShell 5.0+, requires winget or manual installation)
# Requirements: Docker, Node.js, Git

param(
    [switch]$SkipDocker = $false,
    [switch]$SkipNode = $false,
    [switch]$SkipGit = $false
)

# Colors (Windows 10+ Terminal)
$GREEN = "`e[32m"
$RED = "`e[31m"
$YELLOW = "`e[33m"
$BLUE = "`e[34m"
$RESET = "`e[0m"

# Utility functions
function Log-Success { Write-Host "$GREEN✓$RESET $args" }
function Log-Error { Write-Host "$RED✗$RESET $args" }
function Log-Info { Write-Host "$BLUE ℹ$RESET $args" }
function Log-Warning { Write-Host "$YELLOW⚠$RESET $args" }
function Log-Header { Write-Host "$BLUE$($args)$RESET" }

Write-Host ""
Write-Host "$BLUE╔════════════════════════════════════════════════════════════╗$RESET"
Write-Host "$BLUE║ HA Squid Proxy Manager - Development Setup (Windows)      ║$RESET"
Write-Host "$BLUE╚════════════════════════════════════════════════════════════╝$RESET"
Write-Host ""

# ============================================================================
# 1. Check & Install Docker
# ============================================================================
Log-Header "━━ Checking Docker"

$dockerInstalled = $null -ne (Get-Command docker -ErrorAction SilentlyContinue)

if ($dockerInstalled) {
    $dockerVersion = docker --version
    Log-Success "Docker: $dockerVersion"
} else {
    Log-Warning "Docker not found"
    Write-Host ""
    Log-Info "Install Docker Desktop for Windows:"
    Write-Host "  → https://docs.docker.com/desktop/install/windows-install/"
    Write-Host ""

    # Try winget if available
    $wingetInstalled = $null -ne (Get-Command winget -ErrorAction SilentlyContinue)
    if ($wingetInstalled) {
        Log-Info "Or install via winget:"
        Write-Host "  ${BLUE}winget install Docker.DockerDesktop$RESET"
        Write-Host ""
        $install = Read-Host "Install Docker Desktop now? (y/n)"
        if ($install -eq 'y') {
            winget install Docker.DockerDesktop
            Log-Success "Docker installation started. Please restart after installation."
            Start-Sleep -Seconds 3
        } else {
            exit 1
        }
    } else {
        exit 1
    }
}

# Check Docker daemon is running
$dockerRunning = $false
try {
    $null = docker info 2>$null
    $dockerRunning = $true
} catch {
    $dockerRunning = $false
}

if (-not $dockerRunning) {
    Log-Error "Docker daemon is not running"
    Log-Info "Start Docker Desktop from Start Menu"
    Write-Host "  Waiting 30 seconds before retry..."
    Start-Sleep -Seconds 30

    try {
        $null = docker info 2>$null
        Log-Success "Docker daemon is now running"
    } catch {
        Log-Error "Docker daemon still not running. Please start Docker Desktop manually."
        exit 1
    }
}

# Check Docker Compose
$composeInstalled = $false
try {
    $null = docker compose version 2>$null
    $composeInstalled = $true
} catch {
    $composeInstalled = $false
}

if ($composeInstalled) {
    $composeVersion = docker compose version --short
    Log-Success "Docker Compose: $composeVersion"
} else {
    Log-Error "Docker Compose not found (usually included in Docker Desktop)"
    exit 1
}

Write-Host ""

# ============================================================================
# 2. Check & Install Node.js / npm
# ============================================================================
Log-Header "━━ Checking Node.js / npm"

$nodeInstalled = $null -ne (Get-Command node -ErrorAction SilentlyContinue)

if ($nodeInstalled) {
    $nodeVersion = node --version
    $npmVersion = npm --version
    Log-Success "Node.js: $nodeVersion"
    Log-Success "npm: $npmVersion"
} else {
    Log-Warning "Node.js / npm not found"
    Write-Host ""

    $wingetInstalled = $null -ne (Get-Command winget -ErrorAction SilentlyContinue)
    if ($wingetInstalled) {
        Log-Info "Installing Node.js via winget..."
        winget install OpenJS.NodeJS
        Log-Success "Node.js installed"

        # Refresh environment
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")

        $nodeVersion = node --version
        $npmVersion = npm --version
        Log-Success "Node.js: $nodeVersion"
        Log-Success "npm: $npmVersion"
    } else {
        Log-Info "Install Node.js manually: https://nodejs.org/"
        exit 1
    }
}

Write-Host ""

# ============================================================================
# 3. Check & Install Git
# ============================================================================
Log-Header "━━ Checking Git"

$gitInstalled = $null -ne (Get-Command git -ErrorAction SilentlyContinue)

if ($gitInstalled) {
    $gitVersion = git --version
    Log-Success "$gitVersion"
} else {
    Log-Warning "Git not found"
    Write-Host ""

    $wingetInstalled = $null -ne (Get-Command winget -ErrorAction SilentlyContinue)
    if ($wingetInstalled) {
        Log-Info "Installing Git via winget..."
        winget install Git.Git
        Log-Success "Git installed"

        # Refresh environment
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
    } else {
        Log-Info "Install Git manually: https://git-scm.com/download/win"
    }
}

Write-Host ""

# ============================================================================
# 4. Check Python (informational only)
# ============================================================================
Log-Header "━━ Python Configuration"

$pythonInstalled = $null -ne (Get-Command python -ErrorAction SilentlyContinue)

if ($pythonInstalled) {
    $pythonVersion = python --version
    Log-Info "Python: $pythonVersion (runs in Docker, not needed locally)"
} else {
    Log-Info "Python not installed locally (runs in Docker, not needed)"
}

Write-Host ""

# ============================================================================
# 5. Install Frontend Dependencies
# ============================================================================
Log-Header "━━ Installing Frontend Dependencies"

if (Test-Path "squid_proxy_manager/frontend/package.json") {
    Log-Info "Running: npm install --prefix squid_proxy_manager/frontend"
    npm install --prefix squid_proxy_manager/frontend
    Log-Success "Frontend dependencies installed"
} else {
    Log-Warning "package.json not found in frontend directory"
}

Write-Host ""

# ============================================================================
# 6. Build Test Containers
# ============================================================================
Log-Header "━━ Building Test Containers"

Log-Info "This may take 2-5 minutes on first run..."
Log-Info "Building: test-runner image"

$buildOutput = docker compose -f docker-compose.test.yaml --profile unit build test-runner 2>&1

if ($LASTEXITCODE -eq 0) {
    Log-Success "Test containers built successfully"
} else {
    Log-Error "Failed to build test containers"
    Write-Host $buildOutput
    exit 1
}

Write-Host ""

# ============================================================================
# 7. Display Summary & Next Steps
# ============================================================================
Write-Host "$GREEN╔════════════════════════════════════════════════════════════╗$RESET"
Write-Host "$GREEN║ ✓ Development Environment Ready                            ║$RESET"
Write-Host "$GREEN╚════════════════════════════════════════════════════════════╝$RESET"
Write-Host ""

Write-Host "$YELLOW`N`tNext Steps:$RESET"
Write-Host ""
Write-Host "  1. Run all tests:"
Write-Host "     $BLUE.\run_tests.sh$RESET"
Write-Host ""
Write-Host "  2. Or run specific test suite:"
Write-Host "     $BLUE.\run_tests.sh unit$RESET      # Unit + integration tests (fast)"
Write-Host "     $BLUE.\run_tests.sh e2e$RESET       # E2E tests with real Squid"
Write-Host ""
Write-Host "  3. Start frontend development:"
Write-Host "     $BLUE npm run dev --prefix squid_proxy_manager/frontend$RESET"
Write-Host ""
Write-Host "  4. IDE Setup (recommended):"
Write-Host "     - Install Python extension (ms-python.python)"
Write-Host "     - Install Black Formatter (ms-python.black-formatter)"
Write-Host "     - Install Ruff (charliermarsh.ruff)"
Write-Host "     - See DEVELOPMENT.md for full IDE setup"
Write-Host ""
Write-Host "$YELLOW`tDocumentation:$RESET"
Write-Host "  - $BLUE DEVELOPMENT.md$RESET    Feature development guide"
Write-Host "  - $BLUE REQUIREMENTS.md$RESET   Project requirements & scenarios"
Write-Host "  - $BLUE TEST_PLAN.md$RESET      Testing procedures & coverage"
Write-Host ""
