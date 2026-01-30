#!/bin/bash
# Local development runner for Squid Proxy Manager addon
# Runs the addon container with mounted data directory for manual testing

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
ADDON_NAME="squid-proxy-manager-local"
ADDON_PORT="${ADDON_PORT:-8099}"
BUILD_ARCH="${BUILD_ARCH:-aarch64}"
DATA_DIR="${DATA_DIR:-.local/addon-data}"
LOG_DIR="${LOG_DIR:-.local/addon-logs}"

# Help text
show_help() {
  cat << EOF
${BLUE}Squid Proxy Manager - Local Development Runner${NC}

${GREEN}Usage:${NC}
  ./run_addon_local.sh [COMMAND] [OPTIONS]

${GREEN}Commands:${NC}
  start     Build and start addon container (default)
  stop      Stop running addon container
  restart   Stop and start addon container
  logs      Show addon logs (follow mode)
  shell     Open shell in running container
  clean     Remove container and data
  status    Show container status

${GREEN}Options:${NC}
  --port PORT           Set addon port (default: 8099)
  --arch ARCH           Set build architecture: aarch64, armv7, armhf, amd64, i386
                        (default: aarch64)
  --no-rebuild          Don't rebuild image, use existing
  --help                Show this help message

${GREEN}Examples:${NC}
  ./run_addon_local.sh start                    # Start on default port 8099
  ./run_addon_local.sh start --port 8100       # Start on port 8100
  ./run_addon_local.sh logs                    # Follow logs
  ./run_addon_local.sh restart                 # Restart container
  ./run_addon_local.sh clean                   # Remove container & data

${GREEN}Access:${NC}
  Web UI:     http://localhost:${ADDON_PORT}
  API:        http://localhost:${ADDON_PORT}/api
  Health:     http://localhost:${ADDON_PORT}/health

  Data Dir:   ${DATA_DIR}/
  Logs:       ${LOG_DIR}/

EOF
}

# Parse arguments
COMMAND="${1:-start}"
REBUILD="true"

while [[ $# -gt 0 ]]; do
  case $1 in
    --port)
      ADDON_PORT="$2"
      shift 2
      ;;
    --arch)
      BUILD_ARCH="$2"
      shift 2
      ;;
    --no-rebuild)
      REBUILD="false"
      shift
      ;;
    --help|-h)
      show_help
      exit 0
      ;;
    start|stop|restart|logs|shell|clean|status)
      COMMAND="$1"
      shift
      ;;
    *)
      echo -e "${RED}Unknown option: $1${NC}"
      show_help
      exit 1
      ;;
  esac
done

# Helper functions
info() {
  echo -e "${BLUE}ℹ ${NC}$1"
}

success() {
  echo -e "${GREEN}✓ ${NC}$1"
}

warning() {
  echo -e "${YELLOW}⚠ ${NC}$1"
}

error() {
  echo -e "${RED}✗ ${NC}$1"
}

check_docker() {
  if ! command -v docker &> /dev/null; then
    error "Docker is not installed or not in PATH"
    exit 1
  fi

  if ! docker ps &> /dev/null; then
    error "Docker daemon is not running. Please start Docker Desktop or daemon."
    exit 1
  fi

  success "Docker is available"
}

build_image() {
  info "Building addon image for architecture: ${BUILD_ARCH}"
  info "Context: ./squid_proxy_manager"

  docker build \
    -f squid_proxy_manager/Dockerfile \
    --build-arg BUILD_ARCH="${BUILD_ARCH}" \
    -t "${ADDON_NAME}:latest" \
    ./squid_proxy_manager

  success "Image built: ${ADDON_NAME}:latest"
}

create_data_dirs() {
  mkdir -p "${DATA_DIR}"
  mkdir -p "${LOG_DIR}"
  success "Data directories created"
}

start_container() {
  # Check if already running
  if docker ps -a --format '{{.Names}}' | grep -q "^${ADDON_NAME}\$"; then
    warning "Container '${ADDON_NAME}' already exists"
    if docker ps --format '{{.Names}}' | grep -q "^${ADDON_NAME}\$"; then
      warning "Container is already running. Use 'restart' to restart."
      return 1
    else
      info "Removing stopped container..."
      docker rm "${ADDON_NAME}"
    fi
  fi

  info "Starting addon container on port ${ADDON_PORT}..."

  docker run -d \
    --name "${ADDON_NAME}" \
    -p "${ADDON_PORT}:8099" \
    -p "3128-3160:3128-3160" \
    -v "$(pwd)/${DATA_DIR}:/data" \
    -e "SUPERVISOR_TOKEN=dev_token" \
    -e "LOG_LEVEL=debug" \
    --health-cmd="curl -f http://localhost:8099/health" \
    --health-interval=5s \
    --health-timeout=5s \
    --health-retries=10 \
    --health-start-period=10s \
    "${ADDON_NAME}:latest"

  # Wait for health check
  info "Waiting for addon to be healthy..."
  local max_attempts=30
  local attempt=0

  while [ $attempt -lt $max_attempts ]; do
    if docker exec "${ADDON_NAME}" curl -f http://localhost:8099/health &> /dev/null; then
      success "Addon is healthy!"
      break
    fi
    attempt=$((attempt + 1))
    if [ $attempt -lt $max_attempts ]; then
      echo -n "."
      sleep 1
    fi
  done

  if [ $attempt -eq $max_attempts ]; then
    warning "Addon health check timeout - may not be ready yet"
  fi

  echo ""
  success "Container started: ${ADDON_NAME}"
}

stop_container() {
  if ! docker ps -a --format '{{.Names}}' | grep -q "^${ADDON_NAME}\$"; then
    warning "Container '${ADDON_NAME}' is not running"
    return 0
  fi

  info "Stopping container..."
  docker stop "${ADDON_NAME}" 2>/dev/null || true
  success "Container stopped"
}

restart_container() {
  stop_container
  sleep 1
  start_container
}

show_logs() {
  if ! docker ps -a --format '{{.Names}}' | grep -q "^${ADDON_NAME}\$"; then
    error "Container '${ADDON_NAME}' does not exist"
    exit 1
  fi

  info "Showing addon logs (Ctrl+C to stop)..."
  docker logs -f "${ADDON_NAME}"
}

open_shell() {
  if ! docker ps --format '{{.Names}}' | grep -q "^${ADDON_NAME}\$"; then
    error "Container '${ADDON_NAME}' is not running"
    exit 1
  fi

  info "Opening shell in container..."
  docker exec -it "${ADDON_NAME}" /bin/bash
}

clean_container() {
  warning "This will remove the container and all local data!"
  read -p "Are you sure? (y/N) " -n 1 -r
  echo
  if [[ $REPLY =~ ^[Yy]$ ]]; then
    stop_container
    if docker ps -a --format '{{.Names}}' | grep -q "^${ADDON_NAME}\$"; then
      info "Removing container..."
      docker rm "${ADDON_NAME}"
      success "Container removed"
    fi

    if [ -d "${DATA_DIR}" ]; then
      info "Removing data directory..."
      rm -rf "${DATA_DIR}"
      success "Data directory removed"
    fi
  else
    warning "Cleanup cancelled"
  fi
}

show_status() {
  if docker ps --format '{{.Names}}' | grep -q "^${ADDON_NAME}\$"; then
    success "Container is running"
    docker ps --filter "name=${ADDON_NAME}" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
  elif docker ps -a --format '{{.Names}}' | grep -q "^${ADDON_NAME}\$"; then
    warning "Container exists but is stopped"
    docker ps -a --filter "name=${ADDON_NAME}" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
  else
    warning "Container does not exist"
  fi
}

# Main execution
main() {
  case "${COMMAND}" in
    start)
      check_docker
      if [ "${REBUILD}" = "true" ]; then
        build_image
      fi
      create_data_dirs
      start_container
      echo ""
      info "Addon is running!"
      info "Web UI: ${GREEN}http://localhost:${ADDON_PORT}${NC}"
      info "API: ${GREEN}http://localhost:${ADDON_PORT}/api${NC}"
      info "Data: ${GREEN}$(pwd)/${DATA_DIR}${NC}"
      info "View logs: ${GREEN}./run_addon_local.sh logs${NC}"
      echo ""
      ;;

    stop)
      check_docker
      stop_container
      ;;

    restart)
      check_docker
      restart_container
      ;;

    logs)
      check_docker
      show_logs
      ;;

    shell)
      check_docker
      open_shell
      ;;

    clean)
      check_docker
      clean_container
      ;;

    status)
      check_docker
      show_status
      ;;

    *)
      error "Unknown command: ${COMMAND}"
      show_help
      exit 1
      ;;
  esac
}

# Run main function
main
