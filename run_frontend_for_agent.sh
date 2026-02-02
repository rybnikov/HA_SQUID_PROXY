#!/bin/bash
#
# Agent-friendly script to start frontend, connect with Playwright, and capture screenshots
# This script is designed for use by coding agents and sub-agents
#
# Usage:
#   ./run_frontend_for_agent.sh            # Start server and wait
#   ./run_frontend_for_agent.sh --stop     # Stop background server
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="${SCRIPT_DIR}/squid_proxy_manager/frontend"
PID_FILE="/tmp/frontend_mock_server.pid"
PORT=5173

# Stop function
stop_server() {
  if [ -f "${PID_FILE}" ]; then
    PID=$(cat "${PID_FILE}")
    if ps -p "${PID}" > /dev/null 2>&1; then
      echo "Stopping frontend server (PID: ${PID})..."
      kill "${PID}" 2>/dev/null || true
      sleep 2
      # Force kill if still running
      if ps -p "${PID}" > /dev/null 2>&1; then
        kill -9 "${PID}" 2>/dev/null || true
      fi
    fi
    rm -f "${PID_FILE}"
    echo "Frontend server stopped."
  else
    echo "No PID file found. Server may not be running."
  fi
}

# Check for stop command
if [ "$1" = "--stop" ]; then
  stop_server
  exit 0
fi

# Check if already running
if [ -f "${PID_FILE}" ]; then
  PID=$(cat "${PID_FILE}")
  if ps -p "${PID}" > /dev/null 2>&1; then
    echo "Frontend server is already running (PID: ${PID})"
    echo "URL: http://localhost:${PORT}"
    exit 0
  else
    # Stale PID file
    rm -f "${PID_FILE}"
  fi
fi

cd "${FRONTEND_DIR}"

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
  echo "Installing frontend dependencies..."
  npm install
fi

echo "======================================"
echo "Starting frontend in MOCK MODE"
echo "======================================"
echo "URL: http://localhost:${PORT}"
echo "PID file: ${PID_FILE}"
echo "To stop: ./run_frontend_for_agent.sh --stop"
echo "======================================"

# Start server in background
VITE_MOCK_MODE=true npm run dev -- --port "${PORT}" --host localhost > /tmp/frontend_mock_server.log 2>&1 &
SERVER_PID=$!

# Save PID
echo "${SERVER_PID}" > "${PID_FILE}"

echo "Server started with PID: ${SERVER_PID}"
echo "Waiting for server to be ready..."

# Wait for server to be responsive
MAX_WAIT=30
COUNTER=0
until curl -s "http://localhost:${PORT}" > /dev/null 2>&1; do
  COUNTER=$((COUNTER + 1))
  if [ ${COUNTER} -ge ${MAX_WAIT} ]; then
    echo "ERROR: Server did not start within ${MAX_WAIT} seconds"
    echo "Check logs at /tmp/frontend_mock_server.log"
    stop_server
    exit 1
  fi
  echo "Waiting... (${COUNTER}/${MAX_WAIT})"
  sleep 1
done

echo "✓ Frontend server is ready!"
echo "✓ URL: http://localhost:${PORT}"
echo ""
echo "Server is running in background. Use Playwright MCP to connect."
echo "To stop: ./run_frontend_for_agent.sh --stop"
