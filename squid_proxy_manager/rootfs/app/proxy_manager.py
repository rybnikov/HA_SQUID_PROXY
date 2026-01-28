#!/usr/bin/env python3
"""Proxy instance management for the add-on."""
import asyncio
import logging
import os
from pathlib import Path
from typing import Any, Optional

import docker
from docker.errors import DockerException

_LOGGER = logging.getLogger(__name__)

# Paths
DATA_DIR = Path("/data")
CONFIG_DIR = DATA_DIR / "squid_proxy_manager"
CERTS_DIR = CONFIG_DIR / "certs"
LOGS_DIR = CONFIG_DIR / "logs"
DOCKER_SOCKET = "/var/run/docker.sock"
DOCKER_IMAGE_NAME = "squid-proxy-manager"


class ProxyInstanceManager:
    """Manages Squid proxy instances."""

    def __init__(self):
        """Initialize the manager."""
        self.docker_client: Optional[docker.DockerClient] = None
        self._connect_docker()
        self._ensure_squid_image()

    def _connect_docker(self):
        """Connect to Docker daemon."""
        try:
            self.docker_client = docker.DockerClient(base_url=f"unix://{DOCKER_SOCKET}")
            self.docker_client.ping()
            _LOGGER.info("Connected to Docker daemon")
        except Exception as ex:
            _LOGGER.error("Failed to connect to Docker: %s", ex)
            raise

    def _ensure_squid_image(self):
        """Ensure Squid proxy Docker image exists."""
        try:
            # Check if image exists
            try:
                self.docker_client.images.get(DOCKER_IMAGE_NAME)
                _LOGGER.info("Squid proxy image %s already exists", DOCKER_IMAGE_NAME)
                return
            except docker.errors.ImageNotFound:
                _LOGGER.warning(
                    "Squid proxy image %s not found. "
                    "Please build it using: docker build -f Dockerfile.squid -t %s .",
                    DOCKER_IMAGE_NAME,
                    DOCKER_IMAGE_NAME,
                )
                # Note: In production, the image should be pre-built or pulled
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
        users: Optional[list[dict[str, str]]] = None,
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
            sys.path.insert(0, '/app')
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
        cert_file: Optional[Path],
        key_file: Optional[Path],
        passwd_file: Optional[Path],
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
        container = await self._run_in_executor(
            self.docker_client.containers.create, **container_config
        )
        await self._run_in_executor(container.start)

        _LOGGER.info("Created and started container %s for instance %s", container.id, name)
        return container.id

    async def get_instances(self) -> list[dict[str, Any]]:
        """Get list of all proxy instances."""
        instances = []
        try:
            containers = await self._run_in_executor(
                self.docker_client.containers.list, all=True, filters={"name": "squid-proxy-"}
            )
            for container in containers:
                name = container.name.replace("squid-proxy-", "")
                instances.append({
                    "name": name,
                    "container_id": container.id,
                    "status": container.status,
                    "running": container.status == "running",
                })
        except Exception as ex:
            _LOGGER.error("Failed to get instances: %s", ex)
        return instances

    async def start_instance(self, name: str) -> bool:
        """Start a proxy instance."""
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
        try:
            container = await self._run_in_executor(
                self.docker_client.containers.get, f"squid-proxy-{name}"
            )
            await self._run_in_executor(container.remove, force=True)
            return True
        except Exception as ex:
            _LOGGER.error("Failed to remove instance %s: %s", name, ex)
            return False
