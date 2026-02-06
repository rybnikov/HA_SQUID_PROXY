#!/bin/sh
# Generate Home Assistant configuration and pre-seed storage for dev environment.
# Runs as an Alpine init container before HA Core starts.
# Idempotent: overwrites config on every run.

set -e

CONFIG_DIR="/config"
STORAGE_DIR="${CONFIG_DIR}/.storage"

ADDON_MODULE_URL="${ADDON_MODULE_URL:-http://localhost:8099/panel/squid-proxy-panel.js}"
ADDON_API_BASE="${ADDON_API_BASE:-http://localhost:8099/api}"
SUPERVISOR_TOKEN="${SUPERVISOR_TOKEN:-dev_token}"

echo "=== HA Config Init ==="
echo "  Module URL:  ${ADDON_MODULE_URL}"
echo "  API Base:    ${ADDON_API_BASE}"
echo "  Token:       ${SUPERVISOR_TOKEN:0:4}****"

# Write configuration.yaml
# DEV ONLY: supervisor_token is embedded in config for local dev panel_custom.
# Production addon uses HA ingress auth (X-Ingress-Path), not token in config.
cat > "${CONFIG_DIR}/configuration.yaml" <<YAML
default_config:

panel_custom:
  - name: squid-proxy-panel
    sidebar_title: Squid Proxy Manager
    sidebar_icon: mdi:server-network
    url_path: squid-proxy-manager
    module_url: ${ADDON_MODULE_URL}
    config:
      app_basename: /squid-proxy-manager
      api_base: ${ADDON_API_BASE}
      supervisor_token: ${SUPERVISOR_TOKEN}
YAML

echo "  Wrote ${CONFIG_DIR}/configuration.yaml"

# Copy pre-seeded storage files
mkdir -p "${STORAGE_DIR}"
for f in /seed/storage/*; do
  fname="$(basename "$f")"
  cp "$f" "${STORAGE_DIR}/${fname}"
  echo "  Copied .storage/${fname}"
done

echo "=== HA Config Init Complete ==="
