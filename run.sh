#!/usr/bin/with-contenv bashio
set -euo pipefail

bashio::log.info "Preparing Squid proxy add-on"
python3 /app/main.py bootstrap

bashio::log.info "Starting management API and Squid"
exec python3 /app/main.py serve
