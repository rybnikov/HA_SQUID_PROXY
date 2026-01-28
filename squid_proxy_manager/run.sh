#!/usr/bin/with-contenv bashio
# ==============================================================================
# Home Assistant Add-on: Squid Proxy Manager
# ==============================================================================

set -e

# Initialize
bashio::log.info "Starting Squid Proxy Manager..."

# Load configuration
LOG_LEVEL=$(bashio::config 'log_level' 'info')

# Export environment
export PYTHONUNBUFFERED=1
export LOG_LEVEL=${LOG_LEVEL}

# Ensure data directory exists
mkdir -p /data/squid_proxy_manager/{certs,logs}

# Check and build Squid Docker image if needed
bashio::log.info "Checking for Squid Docker image..."
if ! docker images -q squid-proxy-manager | grep -q .; then
    bashio::log.info "Squid Docker image not found, building it (this may take several minutes)..."
    if [ -f /app/Dockerfile.squid ]; then
        docker build -f /app/Dockerfile.squid -t squid-proxy-manager /app/ || {
            bashio::log.error "Failed to build Squid Docker image"
            bashio::log.warning "Proxy instances will not work until the image is built"
        }
    else
        bashio::log.error "Dockerfile.squid not found at /app/Dockerfile.squid"
    fi
else
    bashio::log.info "Squid Docker image already exists"
fi

# Start the manager
exec python3 /app/main.py
