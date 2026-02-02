#!/bin/bash
# Release preparation script - Updates version and generates GIFs
# Usage: ./prepare_release.sh VERSION
#
# Example: ./prepare_release.sh 1.4.8
#
# This script:
# 1. Validates version format
# 2. Updates version in all required files
# 3. Runs record_workflows.sh to update GIFs

set -e

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if version argument is provided
if [ $# -eq 0 ]; then
    log_error "Version argument is required"
    echo ""
    echo "Usage: $0 VERSION"
    echo ""
    echo "Example: $0 1.4.8"
    exit 1
fi

VERSION="$1"

# Validate version format (X.Y.Z)
if ! [[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    log_error "Invalid version format: $VERSION"
    echo "Version must be in format X.Y.Z (e.g., 1.4.8)"
    exit 1
fi

REPO_ROOT="$(cd "$(dirname "$0")/../" && pwd)"

echo ""
log_info "🚀 Release Preparation for v${VERSION}"
log_info "=========================================="
echo ""

# Files to update
CONFIG_YAML="$REPO_ROOT/squid_proxy_manager/config.yaml"
DOCKERFILE="$REPO_ROOT/squid_proxy_manager/Dockerfile"
PACKAGE_JSON="$REPO_ROOT/squid_proxy_manager/frontend/package.json"

# Step 1: Verify files exist
log_info "Step 1: Verifying files exist..."

for file in "$CONFIG_YAML" "$DOCKERFILE" "$PACKAGE_JSON"; do
    if [ ! -f "$file" ]; then
        log_error "File not found: $file"
        exit 1
    fi
done

log_success "All required files found"
echo ""

# Step 2: Update version in config.yaml
log_info "Step 2: Updating version in config.yaml..."

if grep -q "^version: " "$CONFIG_YAML"; then
    sed -i.bak "s/^version: .*/version: \"$VERSION\"/" "$CONFIG_YAML"
    rm -f "$CONFIG_YAML.bak"
    log_success "Updated config.yaml to version $VERSION"
else
    log_error "Could not find version line in config.yaml"
    exit 1
fi

echo ""

# Step 3: Update version in Dockerfile
log_info "Step 3: Updating version in Dockerfile..."

if grep -q "io.hass.version=" "$DOCKERFILE"; then
    sed -i.bak "s/io.hass.version=\"[^\"]*\"/io.hass.version=\"$VERSION\"/" "$DOCKERFILE"
    rm -f "$DOCKERFILE.bak"
    log_success "Updated Dockerfile to version $VERSION"
else
    log_error "Could not find io.hass.version in Dockerfile"
    exit 1
fi

echo ""

# Step 4: Update version in package.json
log_info "Step 4: Updating version in package.json..."

if grep -q "\"version\": " "$PACKAGE_JSON"; then
    sed -i.bak "s/\"version\": \"[^\"]*\"/\"version\": \"$VERSION\"/" "$PACKAGE_JSON"
    rm -f "$PACKAGE_JSON.bak"
    log_success "Updated package.json to version $VERSION"
else
    log_error "Could not find version in package.json"
    exit 1
fi

echo ""

# Step 5: Verify updates
log_info "Step 5: Verifying version updates..."

CONFIG_VERSION=$(grep "^version: " "$CONFIG_YAML" | sed 's/version: "\(.*\)"/\1/')
DOCKERFILE_VERSION=$(grep "io.hass.version=" "$DOCKERFILE" | sed 's/.*io.hass.version="\(.*\)".*/\1/')
PACKAGE_VERSION=$(grep "\"version\": " "$PACKAGE_JSON" | sed 's/.*"version": "\(.*\)".*/\1/')

if [ "$CONFIG_VERSION" != "$VERSION" ] || [ "$DOCKERFILE_VERSION" != "$VERSION" ] || [ "$PACKAGE_VERSION" != "$VERSION" ]; then
    log_error "Version mismatch detected:"
    echo "  config.yaml: $CONFIG_VERSION"
    echo "  Dockerfile: $DOCKERFILE_VERSION"
    echo "  package.json: $PACKAGE_VERSION"
    echo "  Expected: $VERSION"
    exit 1
fi

log_success "All versions updated to $VERSION"
echo ""

# Step 6: Record workflows (update GIFs)
log_info "Step 6: Recording workflows (updating GIFs)..."
log_warning "This may take a few minutes..."
echo ""

cd "$REPO_ROOT/pre_release_scripts"

if ! ./record_workflows.sh; then
    log_warning "Workflow recording failed or had issues"
    log_warning "You may need to run it manually: ./record_workflows.sh"
    echo ""
else
    log_success "Workflows recorded successfully"
    echo ""
fi

# Final summary
echo ""
log_success "=========================================="
log_success "🎉 Release preparation complete!"
log_success "=========================================="
echo ""
log_info "Version updated to: $VERSION"
log_info "Files modified:"
echo "  - squid_proxy_manager/config.yaml"
echo "  - squid_proxy_manager/Dockerfile"
echo "  - squid_proxy_manager/frontend/package.json"
echo "  - docs/gifs/*.gif (updated)"
echo ""
log_info "Next steps:"
echo "  1. Review changes: git diff"
echo "  2. Run tests: ./run_tests.sh"
echo "  3. Commit: git commit -am 'release: prepare v${VERSION}'"
echo "  4. Tag: git tag -a v${VERSION} -m 'Release v${VERSION}'"
echo "  5. Push: git push origin main --tags"
echo ""
