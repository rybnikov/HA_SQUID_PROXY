#!/usr/bin/env python3
"""Build Squid Docker image if it doesn't exist."""
import logging
import subprocess
import sys
from pathlib import Path

_LOGGER = logging.getLogger(__name__)

DOCKER_IMAGE_NAME = "squid-proxy-manager"
DOCKERFILE_PATH = Path("/app/Dockerfile.squid")


def check_image_exists() -> bool:
    """Check if Squid Docker image exists."""
    try:
        result = subprocess.run(
            ["docker", "images", "-q", DOCKER_IMAGE_NAME],
            capture_output=True,
            text=True,
            check=False,
        )
        return bool(result.stdout.strip())
    except Exception as ex:
        _LOGGER.error("Failed to check for Docker image: %s", ex)
        return False


def build_squid_image() -> bool:
    """Build the Squid Docker image from Dockerfile.squid."""
    if not DOCKERFILE_PATH.exists():
        _LOGGER.error("Dockerfile.squid not found at %s", DOCKERFILE_PATH)
        return False

    _LOGGER.info("Building Squid Docker image: %s", DOCKER_IMAGE_NAME)
    _LOGGER.info("This may take several minutes...")

    try:
        # Build the image
        result = subprocess.run(
            [
                "docker",
                "build",
                "-f",
                str(DOCKERFILE_PATH),
                "-t",
                DOCKER_IMAGE_NAME,
                str(DOCKERFILE_PATH.parent.parent),
            ],
            capture_output=False,  # Show output to user
            check=True,
        )

        _LOGGER.info("Successfully built Squid Docker image: %s", DOCKER_IMAGE_NAME)
        return True

    except subprocess.CalledProcessError as ex:
        _LOGGER.error("Failed to build Squid Docker image: %s", ex)
        return False
    except Exception as ex:
        _LOGGER.error("Unexpected error building Squid image: %s", ex)
        return False


def ensure_squid_image() -> bool:
    """Ensure Squid Docker image exists, building it if necessary."""
    if check_image_exists():
        _LOGGER.info("Squid Docker image %s already exists", DOCKER_IMAGE_NAME)
        return True

    _LOGGER.info("Squid Docker image %s not found, building it...", DOCKER_IMAGE_NAME)
    return build_squid_image()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    success = ensure_squid_image()
    sys.exit(0 if success else 1)
