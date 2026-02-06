#!/bin/bash
# Record UI workflows as GIFs - Fully dockerized
# Usage:
#   ./record_workflows.sh            # Standalone mode (addon only)
#   ./record_workflows.sh --ha       # HA mode (requires HA already running via docker compose)
#   ./record_workflows.sh --start-ha # HA mode + auto-start addon & HA Core via docker compose
#
# All recording runs inside the Docker e2e-runner container.
# No local Playwright or ffmpeg needed - only Docker required.
#
# This script handles everything:
# 1. Starts addon (or addon+HA in --ha mode)
# 2. Waits for health checks
# 3. Records workflows via Docker e2e-runner
# 4. Stops services gracefully
# 5. Reports results

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
START_HA=0
HA_USERNAME="${HA_USERNAME:-admin}"
HA_PASSWORD="${HA_PASSWORD:-admin}"
HA_PANEL_PATH="${HA_PANEL_PATH:-squid-proxy-manager}"

# Docker compose URLs (container-to-container)
DOCKER_ADDON_URL="http://addon:8099"
DOCKER_HA_URL="http://ha-core:8123"

OS_NAME="$(uname -s)"
DOCKER_NETWORK_ARGS=()

# For standalone mode on macOS, e2e-runner reaches addon via host.docker.internal
if [ "$OS_NAME" = "Darwin" ]; then
    ADDON_PORT="${ADDON_URL##*:}"
    ADDON_PORT="${ADDON_PORT%%/*}"
    STANDALONE_DOCKER_ADDON_URL="http://host.docker.internal:${ADDON_PORT}"
else
    DOCKER_NETWORK_ARGS+=(--network host)
    STANDALONE_DOCKER_ADDON_URL="$ADDON_URL"
fi

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --ha)
            HA_MODE=1
            shift
            ;;
        --start-ha)
            HA_MODE=1
            START_HA=1
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

ha_compose() {
    docker compose -f "$REPO_ROOT/docker-compose.test.yaml" --profile ha "$@"
}

# Cleanup function
cleanup() {
    log_info "Cleaning up..."
    if [ "$START_HA" -eq 1 ]; then
        "$REPO_ROOT/run_addon_local.sh" stop --ha 2>/dev/null || true
    elif [ $HA_MODE -eq 1 ]; then
        # Restore localhost URLs for host browser access
        log_info "Restoring HA config to localhost URLs..."
        docker compose -f "$REPO_ROOT/docker-compose.test.yaml" --profile ha run --rm \
            ha-config-init > /dev/null 2>&1 || true
        docker compose -f "$REPO_ROOT/docker-compose.test.yaml" --profile ha restart ha-core > /dev/null 2>&1 || true
    elif [ -f "$REPO_ROOT/run_addon_local.sh" ]; then
        "$REPO_ROOT/run_addon_local.sh" stop 2>/dev/null || true
    fi
}

trap cleanup EXIT

echo ""
if [ $HA_MODE -eq 1 ]; then
    log_info "🎬 Recording Workflows - HA Mode (fully dockerized)"
else
    log_info "🎬 Recording Workflows - Standalone Mode (fully dockerized)"
fi
log_info "=========================================="
echo ""

# Check prerequisites (only Docker needed!)
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

log_success "Prerequisites met (no local Playwright/ffmpeg needed)"
echo ""

# Start services
if [ $HA_MODE -eq 1 ]; then
    # HA mode: start or verify addon + HA Core via docker compose
    if [ "$START_HA" -eq 1 ]; then
        log_info "Step 1: Starting addon + HA Core via docker compose..."
        "$REPO_ROOT/run_addon_local.sh" start --ha
        log_success "Addon + HA Core started"
    else
        log_info "Step 1: Verifying HA stack is running..."
        if ! curl -sf "http://localhost:8123/manifest.json" > /dev/null 2>&1; then
            log_error "Home Assistant not reachable at http://localhost:8123"
            log_error "Start HA first: ./run_addon_local.sh start --ha"
            exit 1
        fi
        if ! curl -sf "$ADDON_HEALTH_CHECK_URL" > /dev/null 2>&1; then
            log_error "Addon not reachable at $ADDON_URL"
            exit 1
        fi
        log_success "HA stack is running"
    fi

    # Reconfigure HA for container-to-container recording:
    # 1. Copy panel JS to HA's www/ folder (serves as /local/) so module loads from same origin
    # 2. Set api_base to container URL (addon:8099) for API calls from the browser
    log_info "Copying panel JS to HA www/ folder (same-origin loading)..."
    HA_CONTAINER=$(docker compose -f "$REPO_ROOT/docker-compose.test.yaml" --profile ha ps -q ha-core)
    ADDON_CONTAINER=$(docker compose -f "$REPO_ROOT/docker-compose.test.yaml" --profile ha ps -q addon)
    docker exec "$HA_CONTAINER" mkdir -p /config/www
    docker cp "${ADDON_CONTAINER}:/app/static/panel/squid-proxy-panel.js" - | docker cp - "${HA_CONTAINER}:/config/www/"
    log_success "Panel JS copied to HA www/ folder"

    log_info "Reconfiguring HA with local module URL + container API base..."
    docker compose -f "$REPO_ROOT/docker-compose.test.yaml" --profile ha run --rm \
        -e ADDON_MODULE_URL="/local/squid-proxy-panel.js" \
        -e ADDON_API_BASE="$DOCKER_ADDON_URL/api" \
        -e SUPERVISOR_TOKEN="${SUPERVISOR_TOKEN:-dev_token}" \
        ha-config-init > /dev/null 2>&1
    log_success "HA config updated"

    log_info "Restarting HA Core to pick up new config..."
    docker compose -f "$REPO_ROOT/docker-compose.test.yaml" --profile ha restart ha-core > /dev/null 2>&1

    # Wait for HA to be healthy again
    attempt=0
    max_attempts=40
    while [ $attempt -lt $max_attempts ]; do
        if curl -sf "http://localhost:8123/manifest.json" &>/dev/null; then
            break
        fi
        attempt=$((attempt + 1))
        echo -n "."
        sleep 3
    done
    echo ""
    log_success "HA Core restarted with local panel JS"

    # Clean existing proxy instances for fresh recording
    if [ "$RECORDING_CLEAN_DATA" = "1" ]; then
        log_info "Cleaning proxy instances via API..."
        for instance in $(curl -sf "$ADDON_URL/api/instances" -H "Authorization: Bearer ${SUPERVISOR_TOKEN:-dev_token}" 2>/dev/null | python3 -c "import sys,json; [print(i['name']) for i in json.load(sys.stdin)]" 2>/dev/null); do
            curl -sf -X DELETE "$ADDON_URL/api/instances/$instance" -H "Authorization: Bearer ${SUPERVISOR_TOKEN:-dev_token}" > /dev/null 2>&1 || true
        done
        log_success "Existing proxy instances cleaned"
    fi
else
    # Standalone mode: start addon via docker run
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
fi
echo ""

# Build e2e-runner image
log_info "Step 4: Preparing Docker e2e-runner container..."
if [ $HA_MODE -eq 1 ]; then
    # HA mode: build via ha+e2e profiles
    if ! docker compose -f "$REPO_ROOT/docker-compose.test.yaml" --profile ha --profile e2e build e2e-runner > /dev/null 2>&1; then
        log_warning "Docker compose build had issues, continuing anyway..."
    fi
else
    if ! docker compose -f "$REPO_ROOT/docker-compose.test.yaml" --profile e2e build e2e-runner > /dev/null 2>&1; then
        log_warning "Docker compose build had issues, continuing anyway..."
    fi
fi
log_success "Docker container ready"
echo ""

# Clean previous GIFs
log_info "Step 5: Cleaning previous GIFs..."
mkdir -p "$GIFS_DIR"
rm -f "$GIFS_DIR"/*.gif
log_success "Old GIFs removed"
echo ""

# Record workflows
log_info "Step 6: Recording workflows..."

if [ $HA_MODE -eq 1 ]; then
    log_info "Running in Docker e2e-runner (HA mode, container-to-container)..."
    echo ""
    # Use docker compose with both profiles so e2e-runner can reach ha-core and addon
    # --no-deps: don't restart addon/ha-core (already running)
    docker compose -f "$REPO_ROOT/docker-compose.test.yaml" --profile ha --profile e2e run --rm -T --no-deps \
        -e HA_URL="$DOCKER_HA_URL" \
        -e HA_USERNAME="$HA_USERNAME" \
        -e HA_PASSWORD="$HA_PASSWORD" \
        -e HA_PANEL_PATH="$HA_PANEL_PATH" \
        -e ADDON_URL="$DOCKER_ADDON_URL" \
        -e REPO_ROOT=/repo \
        e2e-runner \
        python /repo/pre_release_scripts/record_workflows_impl.py
else
    log_info "Running in Docker e2e-runner (standalone mode)..."
    echo ""
    docker compose -f "$REPO_ROOT/docker-compose.test.yaml" --profile e2e run --rm -T --no-deps \
        "${DOCKER_NETWORK_ARGS[@]}" \
        -e ADDON_URL="$STANDALONE_DOCKER_ADDON_URL" \
        -e REPO_ROOT=/repo \
        e2e-runner \
        python /repo/pre_release_scripts/record_workflows_impl.py
fi

echo ""

# Verify GIFs
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
