#!/bin/bash
# Build Squid proxy Docker image if it doesn't exist

set -e

DOCKER_IMAGE_NAME="squid-proxy-manager"
DOCKERFILE_PATH="/app/Dockerfile.squid"

echo "Checking for Squid proxy image: ${DOCKER_IMAGE_NAME}"

# Check if image exists
if docker images --format "{{.Repository}}" | grep -q "^${DOCKER_IMAGE_NAME}$"; then
    echo "Squid proxy image ${DOCKER_IMAGE_NAME} already exists"
    exit 0
fi

echo "Building Squid proxy image from ${DOCKERFILE_PATH}..."

# Build the image
if [ -f "${DOCKERFILE_PATH}" ]; then
    cd /app
    docker build -f "${DOCKERFILE_PATH}" -t "${DOCKER_IMAGE_NAME}" .
    echo "Successfully built Squid proxy image: ${DOCKER_IMAGE_NAME}"
else
    echo "ERROR: Dockerfile not found at ${DOCKERFILE_PATH}"
    exit 1
fi
