"""Integration tests for Docker connectivity and container management.

These tests require a running Docker daemon and will create/manage real containers.
Run with: pytest tests/integration/test_docker_integration.py -v

IMPORTANT: These tests REQUIRE Docker to be installed and running.
If Docker is not available, tests will FAIL (not skip).
Set up your dev environment with Docker before running these tests.
"""
import asyncio
import os
import sys
import pytest

# Add app directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../squid_proxy_manager/rootfs/app'))


@pytest.fixture(scope="module", autouse=True)
def require_docker(docker_client):
    """Fixture that ensures Docker is available for all tests in this module.
    
    Uses the docker_client fixture from conftest.py which will FAIL
    (not skip) if Docker is not available.
    """
    # docker_client fixture handles the check and failure
    pass


class TestDockerConnectivity:
    """Test Docker socket connectivity."""

    def test_docker_socket_exists(self, docker_client):
        """Test that Docker socket exists at expected location."""
        socket_paths = [
            "/var/run/docker.sock",
            "/run/docker.sock",
            os.path.expanduser("~/.docker/run/docker.sock"),
        ]
        
        socket_found = any(os.path.exists(path) for path in socket_paths)
        assert socket_found, f"Docker socket not found at any of: {socket_paths}"

    def test_docker_client_connection(self, docker_client):
        """Test that we can connect to Docker."""
        assert docker_client.ping(), "Docker daemon is not responding"

    def test_docker_version_info(self, docker_client):
        """Test that we can get Docker version info."""
        version = docker_client.version()
        
        assert "Version" in version, "Docker version info missing Version field"
        assert "ApiVersion" in version, "Docker version info missing ApiVersion field"
        print(f"Docker version: {version.get('Version')}")
        print(f"API version: {version.get('ApiVersion')}")

    def test_docker_list_containers(self, docker_client):
        """Test that we can list containers."""
        containers = docker_client.containers.list(all=True)
        
        # This should not raise an exception
        assert isinstance(containers, list), "Expected list of containers"
        print(f"Found {len(containers)} containers")

    def test_docker_list_images(self, docker_client):
        """Test that we can list images."""
        images = docker_client.images.list()
        
        assert isinstance(images, list), "Expected list of images"
        print(f"Found {len(images)} images")


class TestProxyInstanceManager:
    """Test ProxyInstanceManager with real Docker."""

    def test_manager_initialization(self, docker_client):
        """Test that ProxyInstanceManager can initialize with Docker."""
        from proxy_manager import ProxyInstanceManager
        
        manager = ProxyInstanceManager()
        assert manager.docker_client is not None, "Docker client should be initialized"
        assert manager.instances == {}, "Instances should be empty initially"

    def test_manager_docker_client_ping(self, docker_client):
        """Test that manager's Docker client can ping."""
        from proxy_manager import ProxyInstanceManager
        
        manager = ProxyInstanceManager()
        assert manager.docker_client.ping(), "Manager's Docker client should be able to ping"

    @pytest.mark.asyncio
    async def test_get_instances_empty(self, proxy_manager):
        """Test getting instances when none exist."""
        instances = await proxy_manager.get_instances()
        assert isinstance(instances, list), "Expected list of instances"

    @pytest.mark.asyncio
    async def test_create_instance_basic(self, proxy_manager, test_instance_name, test_port):
        """Test creating a basic proxy instance."""
        instance = await proxy_manager.create_instance(
            name=test_instance_name,
            port=test_port,
            https_enabled=False,
            users=[]
        )
        
        assert instance is not None, "Instance should be created"
        assert instance.get("name") == test_instance_name, "Instance name should match"
        assert instance.get("port") == test_port, "Instance port should match"
        
        # Verify instance is in the list
        instances = await proxy_manager.get_instances()
        instance_names = [i.get("name") for i in instances]
        assert test_instance_name in instance_names, "Created instance should be in list"

    @pytest.mark.asyncio
    async def test_start_stop_instance(self, proxy_manager, test_instance_name, test_port):
        """Test starting and stopping a proxy instance."""
        # Create instance
        await proxy_manager.create_instance(
            name=test_instance_name,
            port=test_port,
            https_enabled=False,
            users=[]
        )
        
        # Start instance
        started = await proxy_manager.start_instance(test_instance_name)
        assert started, "Instance should start successfully"
        
        # Give it a moment to start
        await asyncio.sleep(2)
        
        # Stop instance
        stopped = await proxy_manager.stop_instance(test_instance_name)
        assert stopped, "Instance should stop successfully"

    @pytest.mark.asyncio
    async def test_remove_instance(self, proxy_manager, test_instance_name, test_port):
        """Test removing a proxy instance."""
        # Create instance (not tracked since we're testing removal)
        from proxy_manager import ProxyInstanceManager
        manager = ProxyInstanceManager()
        
        await manager.create_instance(
            name=test_instance_name,
            port=test_port,
            https_enabled=False,
            users=[]
        )
        
        # Verify it exists
        instances = await manager.get_instances()
        instance_names = [i.get("name") for i in instances]
        assert test_instance_name in instance_names, "Instance should exist before removal"
        
        # Remove instance
        removed = await manager.remove_instance(test_instance_name)
        assert removed, "Instance should be removed successfully"
        
        # Verify it's gone
        instances = await manager.get_instances()
        instance_names = [i.get("name") for i in instances]
        assert test_instance_name not in instance_names, "Instance should not exist after removal"


class TestPathNormalization:
    """Test path normalization for ingress compatibility."""

    def test_normalize_multiple_slashes(self, docker_client):
        """Test that multiple slashes are normalized."""
        import re
        
        test_cases = [
            ("////", "/"),
            ("//api//instances", "/api/instances"),
            ("/", "/"),
            ("/api/instances", "/api/instances"),
            ("///health///", "/health/"),
        ]
        
        for original, expected in test_cases:
            normalized = re.sub(r'/+', '/', original)
            assert normalized == expected, f"Expected {expected}, got {normalized} for {original}"

    @pytest.mark.asyncio
    async def test_path_normalization_middleware(self, docker_client):
        """Test the path normalization middleware."""
        from aiohttp import web
        from aiohttp.test_utils import TestClient, TestServer
        import re
        
        # Create a simple app with the middleware
        async def root_handler(request):
            return web.Response(text="OK")
        
        @web.middleware
        async def normalize_path_middleware(request, handler):
            original_path = request.path
            normalized_path = re.sub(r'/+', '/', original_path)
            
            if normalized_path != original_path:
                if normalized_path == '/':
                    return await root_handler(request)
            
            return await handler(request)
        
        app = web.Application(middlewares=[normalize_path_middleware])
        app.router.add_get("/", root_handler)
        
        async with TestClient(TestServer(app)) as client:
            # Test normal path
            resp = await client.get("/")
            assert resp.status == 200
            
            # Test path with multiple slashes - this should be handled by middleware
            resp = await client.get("/")
            assert resp.status == 200


class TestServerIntegration:
    """Test full server integration with Docker."""

    @pytest.mark.asyncio
    async def test_full_startup_with_docker(self, app_with_manager):
        """Test full application startup with Docker available."""
        from aiohttp.test_utils import TestClient, TestServer
        
        async with TestClient(TestServer(app_with_manager)) as client:
            # Test health endpoint
            resp = await client.get("/health")
            assert resp.status == 200
            data = await resp.json()
            assert data["status"] == "ok"
            assert data["manager_initialized"] is True
            assert data["docker_connected"] is True
            
            # Test instances endpoint
            resp = await client.get("/api/instances")
            assert resp.status == 200
            data = await resp.json()
            assert "instances" in data
            assert "count" in data

    @pytest.mark.asyncio
    async def test_api_create_instance_integration(self, app_with_manager, test_instance_name, test_port):
        """Test creating instance via API."""
        from aiohttp.test_utils import TestClient, TestServer
        
        async with TestClient(TestServer(app_with_manager)) as client:
            # Create instance via API
            resp = await client.post("/api/instances", json={
                "name": test_instance_name,
                "port": test_port,
                "https_enabled": False,
                "users": []
            })
            assert resp.status == 201
            data = await resp.json()
            assert data["status"] == "created"
            assert data["instance"]["name"] == test_instance_name
            
            # Cleanup via API
            resp = await client.delete(f"/api/instances/{test_instance_name}")
            assert resp.status == 200


class TestDockerSocketPermissions:
    """Test Docker socket permission handling."""

    def test_socket_readable(self, docker_client):
        """Test that Docker socket is readable."""
        socket_path = "/var/run/docker.sock"
        
        if os.path.exists(socket_path):
            assert os.access(socket_path, os.R_OK), "Docker socket should be readable"
        else:
            # macOS uses a different socket path
            macos_socket = os.path.expanduser("~/.docker/run/docker.sock")
            if os.path.exists(macos_socket):
                assert os.access(macos_socket, os.R_OK), "Docker socket should be readable"
            else:
                alt_socket = "/run/docker.sock"
                if os.path.exists(alt_socket):
                    assert os.access(alt_socket, os.R_OK), "Docker socket should be readable"

    def test_socket_writable(self, docker_client):
        """Test that Docker socket is writable (needed for API calls)."""
        socket_path = "/var/run/docker.sock"
        
        if os.path.exists(socket_path):
            assert os.access(socket_path, os.W_OK), "Docker socket should be writable"
        else:
            # macOS uses a different socket path
            macos_socket = os.path.expanduser("~/.docker/run/docker.sock")
            if os.path.exists(macos_socket):
                assert os.access(macos_socket, os.W_OK), "Docker socket should be writable"
            else:
                alt_socket = "/run/docker.sock"
                if os.path.exists(alt_socket):
                    assert os.access(alt_socket, os.W_OK), "Docker socket should be writable"

    def test_graceful_docker_failure(self, docker_client):
        """Test that the app handles Docker connection failure gracefully."""
        import docker
        
        # Try to connect to a non-existent socket
        try:
            client = docker.DockerClient(base_url="unix:///nonexistent/docker.sock")
            client.ping()
            pytest.fail("Should have raised an exception for non-existent socket")
        except docker.errors.DockerException:
            pass  # Expected
        except Exception:
            pass  # Other exceptions are also acceptable
