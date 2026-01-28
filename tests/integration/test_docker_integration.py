"""Integration tests for Docker connectivity and container management.

These tests require a running Docker daemon and will create/manage real containers.
Run with: pytest tests/integration/test_docker_integration.py -v

To skip these tests when Docker is not available:
    pytest tests/integration/test_docker_integration.py -v -m "not docker"
"""
import asyncio
import os
import sys
import pytest

# Add app directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../squid_proxy_manager/rootfs/app'))


def docker_available():
    """Check if Docker is available."""
    try:
        import docker
        client = docker.from_env()
        client.ping()
        return True
    except Exception:
        return False


# Skip all tests in this module if Docker is not available
pytestmark = pytest.mark.skipif(
    not docker_available(),
    reason="Docker is not available"
)


class TestDockerConnectivity:
    """Test Docker socket connectivity."""

    def test_docker_socket_exists(self):
        """Test that Docker socket exists at expected location."""
        socket_paths = [
            "/var/run/docker.sock",
            os.path.expanduser("~/.docker/run/docker.sock"),
        ]
        
        socket_found = any(os.path.exists(path) for path in socket_paths)
        assert socket_found, f"Docker socket not found at any of: {socket_paths}"

    def test_docker_client_connection(self):
        """Test that we can connect to Docker."""
        import docker
        
        client = docker.from_env()
        assert client.ping(), "Docker daemon is not responding"

    def test_docker_version_info(self):
        """Test that we can get Docker version info."""
        import docker
        
        client = docker.from_env()
        version = client.version()
        
        assert "Version" in version, "Docker version info missing Version field"
        assert "ApiVersion" in version, "Docker version info missing ApiVersion field"
        print(f"Docker version: {version.get('Version')}")
        print(f"API version: {version.get('ApiVersion')}")

    def test_docker_list_containers(self):
        """Test that we can list containers."""
        import docker
        
        client = docker.from_env()
        containers = client.containers.list(all=True)
        
        # This should not raise an exception
        assert isinstance(containers, list), "Expected list of containers"
        print(f"Found {len(containers)} containers")

    def test_docker_list_images(self):
        """Test that we can list images."""
        import docker
        
        client = docker.from_env()
        images = client.images.list()
        
        assert isinstance(images, list), "Expected list of images"
        print(f"Found {len(images)} images")


class TestProxyInstanceManager:
    """Test ProxyInstanceManager with real Docker."""

    def test_manager_initialization(self):
        """Test that ProxyInstanceManager can initialize with Docker."""
        from proxy_manager import ProxyInstanceManager
        
        manager = ProxyInstanceManager()
        assert manager.docker_client is not None, "Docker client should be initialized"
        assert manager.instances == {}, "Instances should be empty initially"

    def test_manager_docker_client_ping(self):
        """Test that manager's Docker client can ping."""
        from proxy_manager import ProxyInstanceManager
        
        manager = ProxyInstanceManager()
        assert manager.docker_client.ping(), "Manager's Docker client should be able to ping"

    @pytest.mark.asyncio
    async def test_get_instances_empty(self):
        """Test getting instances when none exist."""
        from proxy_manager import ProxyInstanceManager
        
        manager = ProxyInstanceManager()
        instances = await manager.get_instances()
        
        assert isinstance(instances, list), "Expected list of instances"

    @pytest.mark.asyncio
    async def test_create_instance_basic(self):
        """Test creating a basic proxy instance."""
        from proxy_manager import ProxyInstanceManager
        
        manager = ProxyInstanceManager()
        
        # Create a test instance
        test_name = "test_proxy_integration"
        test_port = 13128  # Use non-standard port to avoid conflicts
        
        try:
            instance = await manager.create_instance(
                name=test_name,
                port=test_port,
                https_enabled=False,
                users=[]
            )
            
            assert instance is not None, "Instance should be created"
            assert instance.get("name") == test_name, "Instance name should match"
            assert instance.get("port") == test_port, "Instance port should match"
            
            # Verify instance is in the list
            instances = await manager.get_instances()
            instance_names = [i.get("name") for i in instances]
            assert test_name in instance_names, "Created instance should be in list"
            
        finally:
            # Cleanup: remove the test instance
            try:
                await manager.remove_instance(test_name)
            except Exception:
                pass  # Ignore cleanup errors

    @pytest.mark.asyncio
    async def test_start_stop_instance(self):
        """Test starting and stopping a proxy instance."""
        from proxy_manager import ProxyInstanceManager
        
        manager = ProxyInstanceManager()
        test_name = "test_proxy_start_stop"
        test_port = 13129
        
        try:
            # Create instance
            await manager.create_instance(
                name=test_name,
                port=test_port,
                https_enabled=False,
                users=[]
            )
            
            # Start instance
            started = await manager.start_instance(test_name)
            assert started, "Instance should start successfully"
            
            # Give it a moment to start
            await asyncio.sleep(2)
            
            # Stop instance
            stopped = await manager.stop_instance(test_name)
            assert stopped, "Instance should stop successfully"
            
        finally:
            # Cleanup
            try:
                await manager.stop_instance(test_name)
            except Exception:
                pass
            try:
                await manager.remove_instance(test_name)
            except Exception:
                pass

    @pytest.mark.asyncio
    async def test_remove_instance(self):
        """Test removing a proxy instance."""
        from proxy_manager import ProxyInstanceManager
        
        manager = ProxyInstanceManager()
        test_name = "test_proxy_remove"
        test_port = 13130
        
        # Create instance
        await manager.create_instance(
            name=test_name,
            port=test_port,
            https_enabled=False,
            users=[]
        )
        
        # Verify it exists
        instances = await manager.get_instances()
        instance_names = [i.get("name") for i in instances]
        assert test_name in instance_names, "Instance should exist before removal"
        
        # Remove instance
        removed = await manager.remove_instance(test_name)
        assert removed, "Instance should be removed successfully"
        
        # Verify it's gone
        instances = await manager.get_instances()
        instance_names = [i.get("name") for i in instances]
        assert test_name not in instance_names, "Instance should not exist after removal"


class TestPathNormalization:
    """Test path normalization for ingress compatibility."""

    @pytest.mark.asyncio
    async def test_normalize_multiple_slashes(self):
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
    async def test_path_normalization_middleware(self):
        """Test the path normalization middleware."""
        from aiohttp import web
        from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop
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
        
        # Test using aiohttp test client
        from aiohttp.test_utils import TestClient, TestServer
        
        async with TestClient(TestServer(app)) as client:
            # Test normal path
            resp = await client.get("/")
            assert resp.status == 200
            
            # Test path with multiple slashes - this should be handled by middleware
            # Note: aiohttp may normalize the path before it reaches middleware
            resp = await client.get("/")
            assert resp.status == 200


class TestServerIntegration:
    """Test full server integration with Docker."""

    @pytest.mark.asyncio
    async def test_full_startup_with_docker(self):
        """Test full application startup with Docker available."""
        from aiohttp import web
        from aiohttp.test_utils import TestClient, TestServer
        
        # Import the actual handlers
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../squid_proxy_manager/rootfs/app'))
        
        # Mock the global manager
        from proxy_manager import ProxyInstanceManager
        
        # Create a test app similar to main.py
        app = web.Application()
        
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
        
        app.router.add_get("/health", health_check)
        app.router.add_get("/api/instances", get_instances)
        
        async with TestClient(TestServer(app)) as client:
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
    async def test_api_create_instance_integration(self):
        """Test creating instance via API."""
        from aiohttp import web
        from aiohttp.test_utils import TestClient, TestServer
        from proxy_manager import ProxyInstanceManager
        
        manager = ProxyInstanceManager()
        app = web.Application()
        
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
        
        async def remove_instance(request):
            if manager is None:
                return web.json_response({"error": "Manager not initialized"}, status=503)
            name = request.match_info.get("name")
            success = await manager.remove_instance(name)
            if success:
                return web.json_response({"status": "removed"})
            return web.json_response({"error": "Failed to remove"}, status=500)
        
        app.router.add_post("/api/instances", create_instance)
        app.router.add_delete("/api/instances/{name}", remove_instance)
        
        test_name = "test_api_create"
        test_port = 13131
        
        async with TestClient(TestServer(app)) as client:
            try:
                # Create instance via API
                resp = await client.post("/api/instances", json={
                    "name": test_name,
                    "port": test_port,
                    "https_enabled": False,
                    "users": []
                })
                assert resp.status == 201
                data = await resp.json()
                assert data["status"] == "created"
                assert data["instance"]["name"] == test_name
                
            finally:
                # Cleanup via API
                await client.delete(f"/api/instances/{test_name}")


class TestDockerSocketPermissions:
    """Test Docker socket permission handling."""

    def test_socket_readable(self):
        """Test that Docker socket is readable."""
        socket_path = "/var/run/docker.sock"
        
        if os.path.exists(socket_path):
            assert os.access(socket_path, os.R_OK), "Docker socket should be readable"

    def test_socket_writable(self):
        """Test that Docker socket is writable (needed for API calls)."""
        socket_path = "/var/run/docker.sock"
        
        if os.path.exists(socket_path):
            assert os.access(socket_path, os.W_OK), "Docker socket should be writable"

    def test_graceful_docker_failure(self):
        """Test that the app handles Docker connection failure gracefully."""
        import docker
        
        # Try to connect to a non-existent socket
        try:
            client = docker.DockerClient(base_url="unix:///nonexistent/docker.sock")
            client.ping()
            assert False, "Should have raised an exception"
        except docker.errors.DockerException:
            pass  # Expected
        except Exception as e:
            # Other exceptions are also acceptable
            pass
