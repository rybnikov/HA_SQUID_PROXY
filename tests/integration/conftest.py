"""Shared fixtures and configuration for integration tests.

Integration tests require Docker to be installed and running.
Tests will FAIL (not skip) if Docker is unavailable.
"""
import os
import sys
import pytest

# Add app directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../squid_proxy_manager/rootfs/app'))


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
        pytest.fail(
            "Docker Python package not installed.\n"
            "Run: pip install docker"
        )
    
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
    from proxy_manager import ProxyInstanceManager
    
    manager = ProxyInstanceManager()
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


@pytest.fixture
def app_with_manager(docker_client):
    """Provide an aiohttp app with ProxyInstanceManager.
    
    Requires Docker to be available.
    """
    from aiohttp import web
    from proxy_manager import ProxyInstanceManager
    
    manager = ProxyInstanceManager()
    
    async def health_check(request):
        return web.json_response({
            "status": "ok",
            "manager_initialized": manager is not None,
            "docker_connected": manager.docker_client is not None if manager else False
        })
    
    async def get_instances(request):
        if manager is None:
            return web.json_response({"error": "Manager not initialized"}, status=503)
        instances = await manager.get_instances()
        return web.json_response({"instances": instances, "count": len(instances)})
    
    async def create_instance(request):
        if manager is None:
            return web.json_response({"error": "Manager not initialized"}, status=503)
        try:
            data = await request.json()
            instance = await manager.create_instance(
                name=data.get("name"),
                port=data.get("port", 3128),
                https_enabled=data.get("https_enabled", False),
                users=data.get("users", [])
            )
            return web.json_response({"status": "created", "instance": instance}, status=201)
        except Exception as ex:
            return web.json_response({"error": str(ex)}, status=500)
    
    async def delete_instance(request):
        if manager is None:
            return web.json_response({"error": "Manager not initialized"}, status=503)
        name = request.match_info.get("name")
        success = await manager.remove_instance(name)
        if success:
            return web.json_response({"status": "removed"})
        return web.json_response({"error": "Failed to remove"}, status=500)
    
    app = web.Application()
    app.router.add_get("/health", health_check)
    app.router.add_get("/api/instances", get_instances)
    app.router.add_post("/api/instances", create_instance)
    app.router.add_delete("/api/instances/{name}", delete_instance)
    
    app["manager"] = manager
    
    return app
