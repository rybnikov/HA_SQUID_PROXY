#!/bin/bash
# Record UI workflows as GIFs - Unified complete workflow
# Usage:
#   ./record_workflows.sh            # Standalone mode (addon only)
#   ./record_workflows.sh --ha       # HA mode (record from within Home Assistant)
#
# This script handles everything:
# 1. Stops any existing dev addon
# 2. Starts the dev addon
# 3. Waits for addon health check
# 4. Records workflows (Docker or local depending on mode)
# 5. Stops the addon gracefully
# 6. Reports results

set -e

REPO_ROOT="$(cd "$(dirname "$0")/../" && pwd)"
ADDON_URL="${ADDON_URL:-http://localhost:8099}"
ADDON_HEALTH_CHECK_URL="${ADDON_HEALTH_CHECK_URL:-${ADDON_URL%/}/health}"
MAX_HEALTH_CHECKS=60
HEALTH_CHECK_INTERVAL=2
GIFS_DIR="$REPO_ROOT/docs/gifs"
ADDON_DATA_DIR="${ADDON_DATA_DIR:-$REPO_ROOT/.local/addon-data}"
RECORDING_CLEAN_DATA="${RECORDING_CLEAN_DATA:-1}"

# HA mode settings
HA_MODE=0
HA_URL="${HA_URL:-http://localhost:8123}"
HA_USERNAME="${HA_USERNAME:-recorder}"
HA_PASSWORD="${HA_PASSWORD:-recorder123}"
HA_PANEL_PATH="${HA_PANEL_PATH:-squid-proxy-manager}"

OS_NAME="$(uname -s)"
DOCKER_ADDON_URL="$ADDON_URL"
DOCKER_NETWORK_ARGS=()

if [ "$OS_NAME" = "Darwin" ]; then
    ADDON_PORT="${ADDON_URL##*:}"
    ADDON_PORT="${ADDON_PORT%%/*}"
    if [[ "$ADDON_URL" == *"host.docker.internal"* ]]; then
        DOCKER_ADDON_URL="$ADDON_URL"
    else
        DOCKER_ADDON_URL="http://host.docker.internal:${ADDON_PORT}"
    fi
else
    DOCKER_NETWORK_ARGS+=(--network host)
fi

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --ha)
            HA_MODE=1
            shift
            ;;
        *)
            shift
            ;;
    esac
done

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

stop_containers_using_port() {
    local port="$1"
    local container_ids

    container_ids=$(docker ps -q --filter "publish=${port}")
    if [ -n "$container_ids" ]; then
        log_warning "Stopping containers publishing port ${port}..."
        echo "$container_ids" | xargs docker stop >/dev/null 2>&1 || true
        log_success "Stopped containers using port ${port}"
    fi
}

# Cleanup function
cleanup() {
    log_info "Cleaning up..."
    if [ -f "$REPO_ROOT/run_addon_local.sh" ]; then
        "$REPO_ROOT/run_addon_local.sh" stop 2>/dev/null || true
    fi
}

trap cleanup EXIT

echo ""
if [ $HA_MODE -eq 1 ]; then
    log_info "🎬 Recording Workflows - HA Mode (within Home Assistant)"
else
    log_info "🎬 Recording Workflows - Standalone Mode"
fi
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

if [ $HA_MODE -eq 1 ]; then
    # Check local Playwright and ffmpeg for HA mode
    if ! python3 -c "from playwright.async_api import async_playwright" 2>/dev/null; then
        log_error "Playwright not installed. Run: pip3 install playwright && playwright install chromium"
        exit 1
    fi
    log_success "Playwright available"

    if ! command -v ffmpeg &> /dev/null; then
        log_error "ffmpeg not found. Run: brew install ffmpeg"
        exit 1
    fi
    log_success "ffmpeg available"

    # Check HA Core is running
    if ! curl -sf "$HA_URL" > /dev/null 2>&1; then
        log_error "Home Assistant not reachable at $HA_URL"
        log_error "Start HA Core first, then re-run this script."
        exit 1
    fi
    log_success "Home Assistant is reachable at $HA_URL"
fi

log_success "Prerequisites met"
echo ""

# Step 1: Stop any existing addon
log_info "Step 1: Stop any existing dev addon..."

if "$REPO_ROOT/run_addon_local.sh" stop 2>/dev/null || true; then
    log_success "Existing addon stopped"
else
    log_warning "No existing addon to stop"
fi
stop_containers_using_port 3128
if [ "$RECORDING_CLEAN_DATA" = "1" ]; then
    log_info "Cleaning addon data directory..."
    rm -rf "$ADDON_DATA_DIR"
    mkdir -p "$ADDON_DATA_DIR"
    log_success "Addon data directory cleaned"
fi
echo ""

# Step 2: Start dev addon
log_info "Step 2: Starting dev addon..."

if ! "$REPO_ROOT/run_addon_local.sh" start > /tmp/addon_startup.log 2>&1; then
    if grep -q "port is already allocated" /tmp/addon_startup.log; then
        log_warning "Port conflict detected. Attempting cleanup and retry..."
        stop_containers_using_port 3128
        if ! "$REPO_ROOT/run_addon_local.sh" start > /tmp/addon_startup.log 2>&1; then
            log_error "Failed to start addon after cleanup"
            tail /tmp/addon_startup.log
            exit 1
        fi
    else
        log_error "Failed to start addon"
        tail /tmp/addon_startup.log
        exit 1
    fi
fi

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

# Step 4: Prepare for recording
if [ $HA_MODE -eq 0 ]; then
    log_info "Step 4: Preparing Docker container..."
    if ! docker compose -f "$REPO_ROOT/docker-compose.test.yaml" --profile e2e build e2e-runner > /dev/null 2>&1; then
        log_warning "Docker compose build had issues, continuing anyway..."
    fi
    log_success "Docker container ready"
else
    log_info "Step 4: HA mode - will run Playwright locally"
    log_success "Ready to record from HA at $HA_URL/$HA_PANEL_PATH"
fi
echo ""

# Step 5: Clean previous GIFs
log_info "Step 5: Cleaning previous GIFs..."
mkdir -p "$GIFS_DIR"
rm -f "$GIFS_DIR"/*.gif
log_success "Old GIFs removed"
echo ""

# Step 6: Record workflows
log_info "Step 6: Recording workflows..."

if [ $HA_MODE -eq 1 ]; then
    log_info "Running locally with Playwright (HA mode)..."
    echo ""
    HA_URL="$HA_URL" \
    HA_USERNAME="$HA_USERNAME" \
    HA_PASSWORD="$HA_PASSWORD" \
    HA_PANEL_PATH="$HA_PANEL_PATH" \
    ADDON_URL="$ADDON_URL" \
    REPO_ROOT="$REPO_ROOT" \
    python3 "$REPO_ROOT/pre_release_scripts/record_workflows_impl.py"
else
    log_info "Running in Docker with Playwright + ffmpeg..."
    echo ""
    docker compose -f "$REPO_ROOT/docker-compose.test.yaml" --profile e2e run --rm -T --no-deps \
        "${DOCKER_NETWORK_ARGS[@]}" \
        -e ADDON_URL="$DOCKER_ADDON_URL" \
        -e REPO_ROOT=/repo \
        e2e-runner \
        python /repo/pre_release_scripts/record_workflows_impl.py
fi

echo ""

# Step 7: Verify GIFs
log_info "Step 7: Verifying GIFs..."
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
