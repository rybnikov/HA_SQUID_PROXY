#!/usr/bin/with-contenv bashio
# ==============================================================================
# Home Assistant Add-on: Squid Proxy Manager
# ==============================================================================

set -e

# Initialize
bashio::log.info "Starting Squid Proxy Manager..."

# Load configuration
CONFIG_PATH=/data/options.json
INSTANCES=$(bashio::config 'instances')
LOG_LEVEL=$(bashio::config 'log_level' 'info')

# Export environment
export PYTHONUNBUFFERED=1
export LOG_LEVEL=${LOG_LEVEL}

# Start the manager
exec python3 /app/main.py
