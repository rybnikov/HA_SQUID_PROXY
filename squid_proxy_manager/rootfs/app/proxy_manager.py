#!/usr/bin/env python3
"""Proxy instance management for the add-on."""
import asyncio
import logging
import os
from pathlib import Path
from typing import Any

import docker

_LOGGER = logging.getLogger(__name__)

# Paths
DATA_DIR = Path("/data")
CONFIG_DIR = DATA_DIR / "squid_proxy_manager"
CERTS_DIR = CONFIG_DIR / "certs"
LOGS_DIR = CONFIG_DIR / "logs"
DOCKER_SOCKET_CANDIDATES = ["/var/run/docker.sock", "/run/docker.sock"]
DOCKER_IMAGE_NAME = "squid-proxy-manager"


def _detect_docker_base_url() -> str:
    """Detect Docker base URL from environment or socket paths."""
    env_host = os.getenv("DOCKER_HOST")
    if env_host:
        _LOGGER.info("Using DOCKER_HOST from environment: %s", env_host)
        return env_host

    # Check each candidate socket path
    for socket_path in DOCKER_SOCKET_CANDIDATES:
        path_obj = Path(socket_path)
        if path_obj.exists():
            # Check permissions
            readable = os.access(socket_path, os.R_OK)
            writable = os.access(socket_path, os.W_OK)
            _LOGGER.info(
                "Found Docker socket: %s (readable: %s, writable: %s)",
                socket_path,
                readable,
                writable,
            )
            if readable and writable:
                return f"unix://{socket_path}"
            else:
                _LOGGER.warning(
                    "Docker socket found but insufficient permissions: %s (r:%s w:%s)",
                    socket_path,
                    readable,
                    writable,
                )

    # Diagnostic: List what's in common directories
    _LOGGER.error("Docker socket not found. Checked paths: %s", ", ".join(DOCKER_SOCKET_CANDIDATES))

    # List contents of /var/run and /run for debugging
    for check_dir in ["/var/run", "/run"]:
        if Path(check_dir).exists():
            try:
                entries = list(Path(check_dir).iterdir())
                docker_related = [e.name for e in entries if "docker" in e.name.lower()]
                if docker_related:
                    _LOGGER.info(
                        "Found Docker-related entries in %s: %s",
                        check_dir,
                        ", ".join(docker_related),
                    )
            except Exception as ex:
                _LOGGER.debug("Could not list %s: %s", check_dir, ex)

    # Fall back to default path to keep error messages consistent
    _LOGGER.error(
        "Docker socket not accessible. Ensure 'docker_api: true' is set in config.yaml "
        "and the addon was installed/reinstalled after adding this setting."
    )
    return f"unix://{DOCKER_SOCKET_CANDIDATES[0]}"


class ProxyInstanceManager:
    """Manages Squid proxy instances."""

    def __init__(self):
        """Initialize the manager."""
        self.docker_client: docker.DockerClient | None = None
        self._connect_docker()
        self._ensure_squid_image()

    def _connect_docker(self):
        """Connect to Docker daemon."""
        try:
            base_url = _detect_docker_base_url()
            _LOGGER.info("Attempting to connect to Docker at: %s", base_url)
            self.docker_client = docker.DockerClient(base_url=base_url)
            self.docker_client.ping()
            _LOGGER.info("✓ Successfully connected to Docker daemon")
        except FileNotFoundError as ex:
            _LOGGER.error(
                "✗ Docker socket file not found: %s\n"
                "This usually means 'docker_api: true' is not enabled or the addon needs a fresh install.\n"
                "Solution: Ensure config.yaml has 'docker_api: true' and reinstall the addon completely.",
                ex,
            )
            raise
        except Exception as ex:
            _LOGGER.error(
                "✗ Failed to connect to Docker daemon: %s\n"
                "Socket path: %s\n"
                "Check that 'docker_api: true' is set in config.yaml",
                ex,
                base_url,
            )
            raise

    def _ensure_squid_image(self):
        """Ensure Squid proxy Docker image exists."""
        if not self.docker_client:
            _LOGGER.warning("Docker client not available, cannot check for Squid image")
            return

        try:
            # Check if image exists
            self.docker_client.images.get(DOCKER_IMAGE_NAME)
            _LOGGER.info("Squid proxy image %s already exists", DOCKER_IMAGE_NAME)
            return
        except docker.errors.ImageNotFound:
            _LOGGER.info(
                "Squid proxy image %s not found. It should be built during add-on startup.",
                DOCKER_IMAGE_NAME,
            )
            # The image should be built by run.sh during startup
            # If it's still not here, log a warning
            _LOGGER.warning(
                "Squid proxy image %s not found. "
                "The image should be built automatically during add-on startup. "
                "If this persists, check add-on logs for build errors.",
                DOCKER_IMAGE_NAME,
            )
        except Exception as ex:
            _LOGGER.warning("Could not check for Squid image: %s", ex)

    def _run_in_executor(self, func, *args, **kwargs):
        """Run a synchronous function in executor."""
        loop = asyncio.get_event_loop()
        if kwargs:
            # Wrap function to pass kwargs
            def wrapped_func():
                return func(*args, **kwargs)

            return loop.run_in_executor(None, wrapped_func)
        return loop.run_in_executor(None, lambda: func(*args))

    async def create_instance(
        self,
        name: str,
        port: int,
        https_enabled: bool = False,
        users: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        """Create a new proxy instance.

        Args:
            name: Instance name
            port: Port number
            https_enabled: Whether HTTPS is enabled
            users: List of users with username/password

        Returns:
            Dictionary with instance information
        """
        try:
            # Create directories
            instance_dir = CONFIG_DIR / name
            instance_dir.mkdir(parents=True, exist_ok=True)
            (LOGS_DIR / name).mkdir(parents=True, exist_ok=True)

            # Generate Squid configuration
            import sys

            sys.path.insert(0, "/app")
            from squid_config import SquidConfigGenerator

            config_gen = SquidConfigGenerator(name, port, https_enabled)
            config_file = instance_dir / "squid.conf"
            config_gen.generate_config(config_file)

            # Handle HTTPS certificate
            cert_file = None
            key_file = None
            if https_enabled:
                from cert_manager import CertificateManager

                cert_manager = CertificateManager(CERTS_DIR, name)
                cert_file, key_file = await cert_manager.generate_certificate()

            # Create password file
            passwd_file = instance_dir / "passwd"
            if users:
                from auth_manager import AuthManager

                auth_manager = AuthManager(passwd_file)
                for user in users:
                    try:
                        auth_manager.add_user(user["username"], user["password"])
                    except ValueError as ex:
                        _LOGGER.warning("Failed to add user %s: %s", user.get("username"), ex)
            else:
                # Create empty password file if no users
                passwd_file.touch()
                passwd_file.chmod(0o600)

            # Create Docker container
            container_id = await self._create_container(
                name, port, https_enabled, cert_file, key_file, passwd_file
            )

            return {
                "name": name,
                "port": port,
                "https_enabled": https_enabled,
                "container_id": container_id,
                "status": "running",
            }

        except Exception as ex:
            _LOGGER.error("Failed to create instance %s: %s", name, ex)
            raise

    async def _create_container(
        self,
        name: str,
        port: int,
        https_enabled: bool,
        cert_file: Path | None,
        key_file: Path | None,
        passwd_file: Path | None,
    ) -> str:
        """Create Docker container for proxy instance."""
        instance_dir = CONFIG_DIR / name
        logs_dir = LOGS_DIR / name

        # Prepare volumes
        volumes = {
            str(instance_dir / "squid.conf"): {
                "bind": "/etc/squid/squid.conf",
                "mode": "ro",
            },
            str(logs_dir): {"bind": "/var/log/squid", "mode": "rw"},
        }

        if passwd_file and passwd_file.exists():
            volumes[str(passwd_file)] = {"bind": "/etc/squid/passwd", "mode": "ro"}

        if https_enabled and cert_file and cert_file.exists():
            cert_dir = cert_file.parent
            volumes[str(cert_dir)] = {"bind": "/etc/squid/ssl_cert", "mode": "ro"}

        # Container configuration
        container_config = {
            "image": DOCKER_IMAGE_NAME,
            "name": f"squid-proxy-{name}",
            "ports": {f"{port}/tcp": port},
            "volumes": volumes,
            "network_mode": "bridge",
            "user": "1000:1000",
            "mem_limit": "512m",
            "restart_policy": {"Name": "unless-stopped"},
            "security_opt": ["no-new-privileges:true"],
            "cap_drop": ["ALL"],
            "cap_add": ["NET_BIND_SERVICE"],
            "command": ["-N", "-f", "/etc/squid/squid.conf"],
        }

        # Create and start container
        if not self.docker_client:
            raise RuntimeError("Docker client not available")
        container = await self._run_in_executor(
            self.docker_client.containers.create, **container_config
        )
        await self._run_in_executor(container.start)

        _LOGGER.info("Created and started container %s for instance %s", container.id, name)
        return str(container.id)

    async def get_instances(self) -> list[dict[str, Any]]:
        """Get list of all proxy instances."""
        instances: list[dict[str, Any]] = []
        if not self.docker_client:
            return instances
        try:
            containers = await self._run_in_executor(
                self.docker_client.containers.list, all=True, filters={"name": "squid-proxy-"}
            )
            for container in containers:
                name = container.name.replace("squid-proxy-", "")
                instances.append(
                    {
                        "name": name,
                        "container_id": container.id,
                        "status": container.status,
                        "running": container.status == "running",
                    }
                )
        except Exception as ex:
            _LOGGER.error("Failed to get instances: %s", ex)
        return instances

    async def start_instance(self, name: str) -> bool:
        """Start a proxy instance."""
        if not self.docker_client:
            _LOGGER.error("Docker client not available")
            return False
        try:
            container = await self._run_in_executor(
                self.docker_client.containers.get, f"squid-proxy-{name}"
            )
            await self._run_in_executor(container.start)
            return True
        except Exception as ex:
            _LOGGER.error("Failed to start instance %s: %s", name, ex)
            return False

    async def stop_instance(self, name: str) -> bool:
        """Stop a proxy instance."""
        if not self.docker_client:
            _LOGGER.error("Docker client not available")
            return False
        try:
            container = await self._run_in_executor(
                self.docker_client.containers.get, f"squid-proxy-{name}"
            )
            await self._run_in_executor(container.stop, timeout=10)
            return True
        except Exception as ex:
            _LOGGER.error("Failed to stop instance %s: %s", name, ex)
            return False

    async def remove_instance(self, name: str) -> bool:
        """Remove a proxy instance."""
        if not self.docker_client:
            _LOGGER.error("Docker client not available")
            return False
        try:
            container = await self._run_in_executor(
                self.docker_client.containers.get, f"squid-proxy-{name}"
            )
            await self._run_in_executor(container.remove, force=True)
            return True
        except Exception as ex:
            _LOGGER.error("Failed to remove instance %s: %s", name, ex)
            return False
