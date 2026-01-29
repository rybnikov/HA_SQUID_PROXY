"""Shared fixtures and configuration for integration tests.

Integration tests require Docker to be installed and running.
Tests will FAIL (not skip) if Docker is unavailable.
"""
import os
import sys
from typing import Any

import pytest

# Add app directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../squid_proxy_manager/rootfs/app"))


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "docker: marks tests as requiring Docker (deselect with '-m \"not docker\"')"
    )


@pytest.fixture(scope="session")
def docker_client():
    """Provide a Docker client for tests.

    This fixture will FAIL the test if Docker is not available,
    rather than skipping it.
    """
    try:
        import docker
    except ImportError:
        pytest.fail("Docker Python package not installed.\n" "Run: pip install docker")

    try:
        client = docker.from_env()
        client.ping()
        return client
    except docker.errors.DockerException as e:
        pytest.fail(
            f"Docker is not available: {e}\n\n"
            "Integration tests REQUIRE Docker to be installed and running.\n"
            "Please ensure:\n"
            "  1. Docker is installed: https://docs.docker.com/get-docker/\n"
            "  2. Docker daemon is running\n"
            "  3. Run: docker ps (to verify)\n"
            "  4. Run: ./setup_dev.sh (to verify environment)"
        )


@pytest.fixture(scope="session", autouse=True)
def ensure_squid_image(docker_client):
    """Ensure the Squid proxy Docker image exists for tests.

    Builds a scratch-based test image if it doesn't exist.
    """
    from pathlib import Path

    import docker

    DOCKER_IMAGE_NAME = "squid-proxy-manager"
    project_root = Path(__file__).parent.parent.parent
    test_dockerfile = project_root / "tests" / "integration" / "Dockerfile.squid.test"

    # Check if image exists
    try:
        docker_client.images.get(DOCKER_IMAGE_NAME)
        print(f"✓ Squid proxy image {DOCKER_IMAGE_NAME} already exists")
        return
    except (docker.errors.ImageNotFound, docker.errors.NotFound):
        pass

    # Build the scratch-based test image
    if not test_dockerfile.exists():
        print(f"Warning: Test Dockerfile not found at {test_dockerfile}")
        return

    print(f"Building scratch-based Squid proxy image {DOCKER_IMAGE_NAME}...")
    print("This uses a minimal scratch base with Squid binaries from Alpine")

    try:
        image, logs = docker_client.images.build(
            path=str(test_dockerfile.parent),
            dockerfile=str(test_dockerfile.name),
            tag=DOCKER_IMAGE_NAME,
            rm=True,
        )
        print(f"✓ Successfully built scratch-based Squid Docker image: {DOCKER_IMAGE_NAME}")
    except docker.errors.BuildError as ex:
        print(f"✗ Failed to build scratch-based test image: {ex}")
        # Print build logs for debugging
        if hasattr(ex, "build_log"):
            for log_entry in ex.build_log:
                if "stream" in log_entry:
                    print(log_entry["stream"], end="")
        raise
    except Exception as ex:
        print(f"✗ Unexpected error building test image: {ex}")
        raise


@pytest.fixture(scope="session")
def squid_image_available(docker_client):
    """Check if the Squid proxy Docker image is available.

    Returns True if available, False otherwise.
    Tests that require the image should use this fixture and fail if False.
    """
    import docker

    DOCKER_IMAGE_NAME = "squid-proxy-manager"

    try:
        docker_client.images.get(DOCKER_IMAGE_NAME)
        return True
    except (docker.errors.ImageNotFound, docker.errors.NotFound):
        return False


@pytest.fixture
def test_instance_name():
    """Provide a unique test instance name."""
    import uuid

    return f"test_proxy_{uuid.uuid4().hex[:8]}"


@pytest.fixture
def test_port():
    """Provide a test port that's unlikely to conflict."""
    import random

    return random.randint(20000, 30000)


@pytest.fixture
async def proxy_manager(docker_client):
    """Provide a ProxyInstanceManager instance.

    Requires Docker to be available.
    Cleans up any created instances after the test.
    """
    import tempfile
    from pathlib import Path
    from unittest.mock import patch

    from proxy_manager import ProxyInstanceManager

    # Use temporary directory for /data
    tmpdir = tempfile.mkdtemp()
    tmp_path = Path(tmpdir)
    config_dir = tmp_path / "squid_proxy_manager"
    certs_dir = config_dir / "certs"
    logs_dir = config_dir / "logs"

    # Create directories
    certs_dir.mkdir(parents=True)
    logs_dir.mkdir(parents=True)

    # Patch paths
    with patch("proxy_manager.DATA_DIR", tmp_path), patch(
        "proxy_manager.CONFIG_DIR", config_dir
    ), patch("proxy_manager.CERTS_DIR", certs_dir), patch(
        "proxy_manager.LOGS_DIR", logs_dir
    ), patch(
        "proxy_manager.ProxyInstanceManager._detect_host_data_dir"
    ):
        manager = ProxyInstanceManager()
        # Set host_data_dir to the actual local temp path so Docker can mount it
        manager.host_data_dir = str(tmp_path)

        created_instances = []

        # Store original create method
        original_create = manager.create_instance

        async def tracked_create(*args, **kwargs):
            """Track created instances for cleanup."""
            instance = await original_create(*args, **kwargs)
            if instance and instance.get("name"):
                created_instances.append(instance["name"])
            return instance

        manager.create_instance = tracked_create

        yield manager

        # Cleanup: remove all created instances
        for name in created_instances:
            try:
                await manager.stop_instance(name)
            except Exception:
                pass
            try:
                await manager.remove_instance(name)
            except Exception:
                pass

    # Cleanup temp directory
    import shutil

    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def app_with_manager(docker_client):
    """Provide an aiohttp app with ProxyInstanceManager.

    Requires Docker to be available.
    """
    import shutil
    import tempfile
    from pathlib import Path
    from unittest.mock import patch

    from aiohttp import web
    from proxy_manager import ProxyInstanceManager

    # Use temporary directory for /data
    tmpdir = tempfile.mkdtemp()
    tmp_path = Path(tmpdir)
    config_dir = tmp_path / "squid_proxy_manager"
    certs_dir = config_dir / "certs"
    logs_dir = config_dir / "logs"

    # Create directories
    certs_dir.mkdir(parents=True)
    logs_dir.mkdir(parents=True)

    # Start patches (they'll stay active for the fixture lifetime)
    patches: list[Any] = [
        patch("proxy_manager.DATA_DIR", tmp_path),
        patch("proxy_manager.CONFIG_DIR", config_dir),
        patch("proxy_manager.CERTS_DIR", certs_dir),
        patch("proxy_manager.LOGS_DIR", logs_dir),
        patch("proxy_manager.ProxyInstanceManager._detect_host_data_dir"),
    ]
    for p in patches:
        p.start()

    try:
        from typing import cast

        manager = ProxyInstanceManager()
        # Set host_data_dir to the actual local temp path so Docker can mount it
        manager.host_data_dir = str(tmp_path)

        async def health_check(request):
            m = cast(ProxyInstanceManager, manager)
            return web.json_response(
                {
                    "status": "ok",
                    "manager_initialized": m is not None,
                    "docker_connected": m.docker_client is not None
                    if m and m.docker_client
                    else False,
                }
            )

        async def get_instances(request):
            m = cast(ProxyInstanceManager, manager)
            if m is None:
                return web.json_response({"error": "Manager not initialized"}, status=503)
            instances = await m.get_instances()
            return web.json_response({"instances": instances, "count": len(instances)})

        async def create_instance(request):
            m = cast(ProxyInstanceManager, manager)
            if m is None:
                return web.json_response({"error": "Manager not initialized"}, status=503)
            try:
                data = await request.json()
                instance = await m.create_instance(
                    name=data.get("name"),
                    port=data.get("port", 3128),
                    https_enabled=data.get("https_enabled", False),
                    users=data.get("users", []),
                )
                return web.json_response({"status": "created", "instance": instance}, status=201)
            except Exception as ex:
                return web.json_response({"error": str(ex)}, status=500)

        async def delete_instance(request):
            m = cast(ProxyInstanceManager, manager)
            if m is None:
                return web.json_response({"error": "Manager not initialized"}, status=503)
            name = request.match_info.get("name")
            success = await m.remove_instance(name)
            if success:
                return web.json_response({"status": "removed"})
            return web.json_response({"error": "Failed to remove"}, status=500)

        from aiohttp.web import AppKey

        MANAGER_KEY = AppKey("manager", t=type(manager))

        app = web.Application()
        app.router.add_get("/health", health_check)
        app.router.add_get("/api/instances", get_instances)
        app.router.add_post("/api/instances", create_instance)
        app.router.add_delete("/api/instances/{name}", delete_instance)

        app[MANAGER_KEY] = manager

        yield app
    finally:
        # Stop patches and cleanup
        for p in patches:
            p.stop()
        shutil.rmtree(tmpdir, ignore_errors=True)
