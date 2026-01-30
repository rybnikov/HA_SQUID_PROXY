#!/bin/bash
# Record UI workflows as GIFs for README documentation
# IMPORTANT: Runs STRICTLY in Docker - no local tools needed!
# Usage: ./record_workflows.sh <addon_url>
# Handles all waits, retries, and dependencies inside Docker container

set -e

ADDON_URL="${1:-http://localhost:8100}"
REPO_ROOT="$(cd "$(dirname "$0")/../" && pwd)"

echo "🎬 Recording workflows from: $ADDON_URL"
echo "🐳 Running in Docker container (e2e-runner image)"
echo "⏱️  Docker container handles all waiting and retries"
echo ""

# Check Docker is running
if ! docker ps &> /dev/null; then
    echo "❌ Docker is not running. Please start Docker Desktop."
    exit 1
fi

# Check docker-compose
if ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose not found. Please install Docker Desktop."
    exit 1
fi

# Build e2e-runner image if needed
echo "📦 Preparing Docker container..."
docker compose -f "$REPO_ROOT/docker-compose.test.yaml" --profile e2e build e2e-runner > /dev/null 2>&1 || true

# Run recording in Docker container
echo "▶️  Starting workflow recording..."
echo ""

docker compose -f "$REPO_ROOT/docker-compose.test.yaml" \
  --profile e2e \
  run --rm \
  -v "$REPO_ROOT:/repo" \
  -e ADDON_URL="$ADDON_URL" \
  e2e-runner \
  python /repo/pre_release_scripts/record_workflows_impl.py

echo ""
echo "✅ Recording complete! GIFs saved to docs/gifs/"
echo "Check: ls -lh $REPO_ROOT/docs/gifs/"
