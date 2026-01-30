#!/bin/bash
# Record UI workflows as GIFs for README documentation
# IMPORTANT: Runs STRICTLY in Docker - no local tools needed!
# Usage: ./record_workflows.sh <addon_url>

set -e

ADDON_URL="${1:-http://addon:8099}"

echo "🎬 Recording workflows from: $ADDON_URL"
echo "🐳 Running in Docker container (e2e-runner image)"
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
docker compose -f docker-compose.test.yaml --profile e2e build e2e-runner > /dev/null 2>&1

# Run recording in Docker container
echo "▶️  Starting workflow recording..."
echo ""

docker compose -f docker-compose.test.yaml \
  --profile e2e \
  run --rm e2e-runner \
  python /app/record_workflows.py "$ADDON_URL"

echo ""
echo "✅ Recording complete! GIFs saved to docs/gifs/"
