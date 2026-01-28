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

# Start the manager
exec python3 /app/main.py
