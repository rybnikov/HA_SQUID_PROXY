#!/bin/bash
# Record UI workflows as GIFs - Unified complete workflow
# IMPORTANT: Single command, no parameters needed!
# Usage: ./record_workflows.sh
# 
# This ONE script handles everything:
# 1. Stops any existing dev addon
# 2. Starts the dev addon
# 3. Waits for addon health check
# 4. Runs Docker container to record workflows
# 5. Stops the addon gracefully
# 6. Reports results

set -e

REPO_ROOT="$(cd "$(dirname "$0")/../" && pwd)"
ADDON_URL="http://localhost:8100"
ADDON_HEALTH_CHECK_URL="http://localhost:8100/health"
MAX_HEALTH_CHECKS=60
HEALTH_CHECK_INTERVAL=2

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Cleanup function
cleanup() {
    log_info "Cleaning up..."
    if [ -f "$REPO_ROOT/run_addon_local.sh" ]; then
        "$REPO_ROOT/run_addon_local.sh" stop 2>/dev/null || true
        sleep 2
    fi
}

trap cleanup EXIT

echo ""
log_info "🎬 Recording Workflows - Unified Pipeline"
log_info "=========================================="
echo ""

# Check prerequisites
log_info "Checking prerequisites..."

if ! command -v docker &> /dev/null; then
    log_error "Docker not found. Please install Docker Desktop."
    exit 1
fi

if ! docker ps &> /dev/null; then
    log_error "Docker is not running. Please start Docker Desktop."
    exit 1
fi

log_success "Docker is available"

if ! command -v curl &> /dev/null; then
    log_error "curl not found. Please install curl."
    exit 1
fi

log_success "Prerequisites met"
echo ""

# Step 1: Stop any existing addon
log_info "Step 1: Stop any existing dev addon..."

if "$REPO_ROOT/run_addon_local.sh" stop 2>/dev/null || true; then
    sleep 2
    log_success "Existing addon stopped"
else
    log_warning "No existing addon to stop"
fi
echo ""

# Step 2: Start dev addon
log_info "Step 2: Starting dev addon..."

if ! "$REPO_ROOT/run_addon_local.sh" start > /tmp/addon_startup.log 2>&1; then
    log_error "Failed to start addon"
    tail /tmp/addon_startup.log
    exit 1
fi

sleep 5

# Step 3: Wait for addon health
log_info "Step 3: Waiting for addon health check..."

HEALTH_CHECKS=0
ADDON_READY=0

while [ $HEALTH_CHECKS -lt $MAX_HEALTH_CHECKS ]; do
    if curl -sf "$ADDON_HEALTH_CHECK_URL" > /dev/null 2>&1; then
        log_success "Addon is healthy!"
        ADDON_READY=1
        break
    fi
    
    HEALTH_CHECKS=$((HEALTH_CHECKS + 1))
    PCT=$((HEALTH_CHECKS * 100 / MAX_HEALTH_CHECKS))
    printf "\r  Health check: %d%% (%d/%d)" $PCT $HEALTH_CHECKS $MAX_HEALTH_CHECKS
    sleep $HEALTH_CHECK_INTERVAL
done

echo ""
echo ""

if [ $ADDON_READY -eq 0 ]; then
    log_error "Addon did not become healthy within timeout"
    exit 1
fi

# Step 4: Build Docker image
log_info "Step 4: Preparing Docker container..."

if ! docker compose -f "$REPO_ROOT/docker-compose.test.yaml" --profile e2e build e2e-runner > /dev/null 2>&1; then
    log_warning "Docker compose build had issues, continuing anyway..."
fi

log_success "Docker container ready"
echo ""

# Step 5: Record workflows (runs in Docker)
log_info "Step 5: Recording workflows..."
log_info "This runs in Docker with Playwright + ffmpeg"
echo ""

docker run --rm \
  --network host \
  -v "$REPO_ROOT:/repo" \
  -e ADDON_URL="$ADDON_URL" \
  -e REPO_ROOT=/repo \
  ha_squid_proxy-e2e-runner \
  python /repo/pre_release_scripts/record_workflows_impl.py

echo ""

# Step 6: Verify GIFs
log_info "Step 6: Verifying GIFs..."

GIFS_DIR="$REPO_ROOT/docs/gifs"
GIF_COUNT=$(find "$GIFS_DIR" -name "*.gif" -type f 2>/dev/null | wc -l)

if [ $GIF_COUNT -eq 0 ]; then
    log_warning "No GIFs found (recording may have had issues)"
else
    log_success "Found $GIF_COUNT GIF file(s)"
    echo ""
    ls -lh "$GIFS_DIR"/*.gif 2>/dev/null | tail -5
fi

echo ""
log_success "=========================================="
log_success "🎉 Recording pipeline complete!"
log_success "GIFs: $GIFS_DIR"
log_success "=========================================="
echo ""
