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

# Build Squid Docker image if it doesn't exist
bashio::log.info "Checking for Squid proxy Docker image..."
if /app/build_squid_image.sh; then
    bashio::log.info "Squid proxy image ready"
else
    bashio::log.warning "Failed to build Squid proxy image. Some features may not work."
fi

# Start the manager
exec python3 /app/main.py
