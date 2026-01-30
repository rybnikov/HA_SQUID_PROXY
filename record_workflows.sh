#!/bin/bash
# Record UI workflows as GIFs for README documentation
# Usage: ./record_workflows.sh <addon_url>

set -e

ADDON_URL="${1:-http://localhost:8100}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🎬 Recording workflows from: $ADDON_URL"
echo ""

# Check if ffmpeg is installed
if ! command -v ffmpeg &> /dev/null; then
    echo "⚠️  ffmpeg not found. Install with:"
    echo "   brew install ffmpeg"
    echo ""
fi

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found"
    exit 1
fi

# Check if Playwright is installed
python3 -c "import playwright" 2>/dev/null || {
    echo "⚠️  Playwright not installed. Installing..."
    pip install playwright
    python3 -m playwright install chromium
}

# Run the recording script
python3 "$SCRIPT_DIR/record_workflows.py" "$ADDON_URL"
