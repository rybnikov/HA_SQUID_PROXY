#!/usr/bin/env bash
set -euo pipefail

# DEPRECATED: Use './run_addon_local.sh start --ha' instead.
# This script is kept for manual HA Core dev repo setups only.

# Configure Home Assistant Core to load Squid Proxy Manager as a true HA custom panel.
# This enables rendering in HA frontend runtime, where ha-* components are available.

CORE_PATH="${1:-../core}"
CORE_CONFIGURATION="$CORE_PATH/config/configuration.yaml"
URL_PATH="${2:-squid-proxy-manager}"
MODULE_URL="${3:-http://localhost:8099/panel/squid-proxy-panel.js}"
API_BASE="${4:-http://localhost:8099/api}"
SUPERVISOR_TOKEN="${5:-dev_token}"

if [[ ! -d "$CORE_PATH" ]]; then
  echo "ERROR: Home Assistant Core path not found: $CORE_PATH" >&2
  exit 1
fi

mkdir -p "$CORE_PATH/config"
if [[ ! -f "$CORE_CONFIGURATION" ]]; then
  cat > "$CORE_CONFIGURATION" <<'YAML'
default_config:
YAML
fi

python3 - <<'PY' "$CORE_CONFIGURATION" "$URL_PATH" "$MODULE_URL" "$API_BASE" "$SUPERVISOR_TOKEN"
import pathlib
import sys

config_path = pathlib.Path(sys.argv[1])
url_path = sys.argv[2]
module_url = sys.argv[3]
api_base = sys.argv[4]
supervisor_token = sys.argv[5]

text = config_path.read_text(encoding="utf-8")

panel_block = f"""
panel_custom:
  - name: squid-proxy-panel
    sidebar_title: Squid Proxy Manager
    sidebar_icon: mdi:server-network
    url_path: {url_path}
    module_url: {module_url}
    config:
      app_basename: /{url_path}
      api_base: {api_base}
      supervisor_token: {supervisor_token}
"""

if "panel_custom:" in text and "name: squid-proxy-panel" in text:
    print("panel_custom entry already present; leaving configuration unchanged.")
    raise SystemExit(0)

if not text.endswith("\n"):
    text += "\n"

text += panel_block
config_path.write_text(text, encoding="utf-8")
print(f"Updated {config_path} with Squid Proxy Manager panel_custom entry.")
PY

cat <<EOF
Configured HA custom panel in: $CORE_CONFIGURATION

Next steps:
1) Restart Home Assistant Core
2) Open: http://localhost:8123/$URL_PATH
3) Sidebar should now show "Squid Proxy Manager" as native panel
EOF
