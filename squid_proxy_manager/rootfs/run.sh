#!/usr/bin/with-contenv bashio
# ==============================================================================
# Home Assistant Add-on: Squid Proxy Manager
# ==============================================================================

set -e

# Initialize
bashio::log.info "=========================================="
bashio::log.info "Squid Proxy Manager - Startup Script"
bashio::log.info "=========================================="

# Load configuration
LOG_LEVEL=$(bashio::config 'log_level' 'info')
bashio::log.info "Configuration loaded: log_level=${LOG_LEVEL}"

# Export environment
export PYTHONUNBUFFERED=1
export LOG_LEVEL=${LOG_LEVEL}
bashio::log.info "Environment variables set: PYTHONUNBUFFERED=1, LOG_LEVEL=${LOG_LEVEL}"

# Ensure data directory exists
bashio::log.info "Creating data directories..."
mkdir -p /data/squid_proxy_manager/{certs,logs}
bashio::log.info "Data directories created: /data/squid_proxy_manager/{certs,logs}"

# Check Python availability
bashio::log.info "Checking Python installation..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    bashio::log.info "Python found: ${PYTHON_VERSION}"
else
    bashio::log.error "Python3 not found!"
    exit 1
fi

# Check if main.py exists
if [ ! -f "/app/main.py" ]; then
    bashio::log.error "Main application file not found: /app/main.py"
    exit 1
fi
bashio::log.info "Main application file found: /app/main.py"

# Build Squid Docker image if it doesn't exist
bashio::log.info "Checking for Squid proxy Docker image..."
if [ -f "/app/build_squid_image.sh" ]; then
    if /app/build_squid_image.sh; then
        bashio::log.info "✓ Squid proxy image ready"
    else
        bashio::log.warning "Failed to build Squid proxy image. Some features may not work."
    fi
else
    bashio::log.warning "build_squid_image.sh not found, skipping image build"
fi

# Start the manager
bashio::log.info "=========================================="
bashio::log.info "Starting Python application..."
bashio::log.info "=========================================="
exec python3 /app/main.py
