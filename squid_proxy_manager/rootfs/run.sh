#!/usr/bin/with-contenv bashio
# ==============================================================================
# Home Assistant Add-on: Squid Proxy Manager
# ==============================================================================

set -e

# Fallback logging function in case bashio isn't available
log_info() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    if command -v bashio &> /dev/null 2>&1; then
        bashio::log.info "$@"
    else
        echo "[$timestamp] [INFO] $@" >&2
    fi
}

log_error() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    if command -v bashio &> /dev/null 2>&1; then
        bashio::log.error "$@"
    else
        echo "[$timestamp] [ERROR] $@" >&2
    fi
}

log_warning() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    if command -v bashio &> /dev/null 2>&1; then
        bashio::log.warning "$@"
    else
        echo "[$timestamp] [WARNING] $@" >&2
    fi
}

# Initialize
log_info "=========================================="
log_info "Squid Proxy Manager - Startup Script"
log_info "=========================================="
log_info "Script started at $(date)"
log_info "Working directory: $(pwd)"
log_info "User: $(whoami)"

# Load configuration
if command -v bashio &> /dev/null; then
    LOG_LEVEL=$(bashio::config 'log_level' 'info' || echo 'info')
else
    LOG_LEVEL='info'
fi
log_info "Configuration loaded: log_level=${LOG_LEVEL}"

# Export environment
export PYTHONUNBUFFERED=1
export LOG_LEVEL=${LOG_LEVEL}
log_info "Environment variables set: PYTHONUNBUFFERED=1, LOG_LEVEL=${LOG_LEVEL}"

# Ensure data directory exists
log_info "Creating data directories..."
mkdir -p /data/squid_proxy_manager/{certs,logs}
log_info "Data directories created: /data/squid_proxy_manager/{certs,logs}"

# Check Python availability
log_info "Checking Python installation..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    log_info "Python found: ${PYTHON_VERSION}"
else
    log_error "Python3 not found!"
    exit 1
fi

# Check if main.py exists
if [ ! -f "/app/main.py" ]; then
    log_error "Main application file not found: /app/main.py"
    exit 1
fi
log_info "Main application file found: /app/main.py"

# Build Squid Docker image if it doesn't exist
log_info "Checking for Squid proxy Docker image..."
if [ -f "/app/build_squid_image.sh" ]; then
    if /app/build_squid_image.sh; then
        log_info "✓ Squid proxy image ready"
    else
        log_warning "Failed to build Squid proxy image. Some features may not work."
    fi
else
    log_warning "build_squid_image.sh not found, skipping image build"
fi

# Start the manager
log_info "=========================================="
log_info "Starting Python application..."
log_info "Python path: $(which python3 2>&1 || echo 'not found')"
log_info "Python version: $(python3 --version 2>&1 || echo 'unknown')"
log_info "Main script: /app/main.py"
log_info "Script exists: $([ -f /app/main.py ] && echo 'yes' || echo 'no')"
log_info "=========================================="
log_info "Executing: python3 /app/main.py"
exec python3 /app/main.py
