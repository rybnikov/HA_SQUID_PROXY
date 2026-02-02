#!/bin/bash
#
# Start the frontend in mock mode without backend dependency
# Usage:
#   ./run_frontend_mock.sh              # Start on default port 5173
#   ./run_frontend_mock.sh --port 8080  # Start on custom port
#   ./run_frontend_mock.sh --host       # Expose on network (0.0.0.0)
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="${SCRIPT_DIR}/squid_proxy_manager/frontend"

# Parse arguments
PORT=5173
HOST="localhost"

while [[ $# -gt 0 ]]; do
  case $1 in
    --port)
      PORT="$2"
      shift 2
      ;;
    --host)
      HOST="0.0.0.0"
      shift
      ;;
    *)
      echo "Unknown option: $1"
      echo "Usage: $0 [--port PORT] [--host]"
      exit 1
      ;;
  esac
done

cd "${FRONTEND_DIR}"

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
  echo "Installing frontend dependencies..."
  npm install
fi

echo "======================================"
echo "Starting frontend in MOCK MODE"
echo "======================================"
echo "URL: http://${HOST}:${PORT}"
echo "Mock data loaded from src/api/mockData.ts"
echo "Press Ctrl+C to stop"
echo "======================================"

# Start Vite dev server with mock mode enabled
VITE_MOCK_MODE=true npm run dev -- --port "${PORT}" --host "${HOST}"
