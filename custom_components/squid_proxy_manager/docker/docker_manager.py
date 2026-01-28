"""Docker container lifecycle management."""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

import docker
from docker.errors import DockerException

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from ..const import (
    CONTAINER_CERT_DIR,
    CONTAINER_CONFIG_DIR,
    CONTAINER_LOG_DIR,
    CONTAINER_PASSWD_FILE,
    DOCKER_IMAGE_NAME,
    DOCKER_NETWORK_MODE,
    DOCKER_SOCKET,
    DOCKER_UID,
    DOCKER_GID,
    DEFAULT_MEMORY_LIMIT,
    DEFAULT_CPU_LIMIT,
    PATH_CONFIG_DIR,
    PATH_LOGS_DIR,
)
from .squid_config import SquidConfigGenerator

_LOGGER = logging.getLogger(__name__)


class DockerManager:
    """Manages Docker containers for proxy instances."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry | None) -> None:
        """Initialize Docker manager.

        Args:
            hass: Home Assistant instance
            entry: Config entry for this proxy instance (can be None for validation)
        """
        self.hass = hass
        self.entry = entry
        if entry:
            self.instance_name = entry.data.get("instance_name", entry.entry_id) if entry.data else entry.entry_id
        else:
            self.instance_name = "validation"
        self.docker_client: docker.DockerClient | None = None
        self.container_name = f"squid-proxy-{self.instance_name}" if entry else "validation"

    async def async_validate(self) -> None:
        """Validate Docker is available and accessible.

        Raises:
            DockerException: If Docker is not available
        """
        try:
            # Run in executor since docker library is synchronous
            await self.hass.async_add_executor_job(self._connect_docker)
        except Exception as ex:
            raise DockerException(f"Docker is not available: {ex}") from ex

    def _connect_docker(self) -> None:
        """Connect to Docker daemon."""
        try:
            self.docker_client = docker.DockerClient(base_url=f"unix://{DOCKER_SOCKET}")
            # Test connection
            self.docker_client.ping()
            _LOGGER.info("Connected to Docker daemon")
        except Exception as ex:
            _LOGGER.error("Failed to connect to Docker: %s", ex)
            raise

    async def _run_in_executor(self, func, *args, **kwargs):
        """Run a synchronous function in executor."""
        return await self.hass.async_add_executor_job(func, *args, **kwargs)

    def _get_config_paths(self) -> tuple[Path, Path, Path, Path]:
        """Get paths for instance configuration.

        Returns:
            Tuple of (config_dir, config_file, logs_dir, instance_dir)
        """
        config_dir = Path(self.hass.config.config_dir)
        instance_dir = config_dir / PATH_CONFIG_DIR / self.instance_name
        config_file = instance_dir / "squid.conf"
        logs_dir = config_dir / PATH_LOGS_DIR / self.instance_name
        return (instance_dir, config_file, logs_dir, instance_dir)

    async def create_container(
        self,
        port: int,
        https_enabled: bool,
        cert_file: Path | None = None,
        key_file: Path | None = None,
        passwd_file: Path | None = None,
    ) -> str:
        """Create and start a Docker container for the proxy instance.

        Args:
            port: Port number for the proxy
            https_enabled: Whether HTTPS is enabled
            cert_file: Path to certificate file (if HTTPS enabled)
            key_file: Path to private key file (if HTTPS enabled)
            passwd_file: Path to password file

        Returns:
            Container ID

        Raises:
            DockerException: If container creation fails
        """
        try:
            instance_dir, config_file, logs_dir, _ = self._get_config_paths()

            # Generate Squid configuration
            config_gen = SquidConfigGenerator(self.instance_name, port, https_enabled)
            await self._run_in_executor(config_gen.generate_config, config_file)

            # Prepare volumes
            volumes = {
                str(config_file): {"bind": f"{CONTAINER_CONFIG_DIR}/squid.conf", "mode": "ro"},
                str(logs_dir): {"bind": CONTAINER_LOG_DIR, "mode": "rw"},
            }

            if passwd_file and passwd_file.exists():
                volumes[str(passwd_file)] = {"bind": CONTAINER_PASSWD_FILE, "mode": "ro"}

            if https_enabled and cert_file and cert_file.exists():
                cert_dir = cert_file.parent
                volumes[str(cert_dir)] = {"bind": CONTAINER_CERT_DIR, "mode": "ro"}

            # Port bindings
            port_bindings = {f"{port}/tcp": port}

            # Container configuration
            container_config = {
                "image": DOCKER_IMAGE_NAME,
                "name": self.container_name,
                "ports": port_bindings,
                "volumes": volumes,
                "network_mode": DOCKER_NETWORK_MODE,
                "user": f"{DOCKER_UID}:{DOCKER_GID}",
                "mem_limit": DEFAULT_MEMORY_LIMIT,
                "cpu_quota": int(DEFAULT_CPU_LIMIT * 100000),
                "cpu_period": 100000,
                "restart_policy": {"Name": "unless-stopped"},
                "security_opt": ["no-new-privileges:true"],
                "cap_drop": ["ALL"],
                "cap_add": ["NET_BIND_SERVICE"],  # Needed for binding to ports < 1024
                "read_only": False,  # Squid needs to write to /var/log and /var/run
                "tmpfs": {
                    "/tmp": "noexec,nosuid,size=100m",
                    "/var/run": "noexec,nosuid,size=10m",
                },
                "command": ["-N", "-f", f"{CONTAINER_CONFIG_DIR}/squid.conf"],
            }

            # Create container
            container = await self._run_in_executor(
                self.docker_client.containers.create, **container_config
            )

            _LOGGER.info("Created container %s for instance %s", container.id, self.instance_name)

            # Start container
            await self._run_in_executor(container.start)

            _LOGGER.info("Started container %s", container.id)
            return container.id

        except Exception as ex:
            _LOGGER.error("Failed to create container for %s: %s", self.instance_name, ex)
            raise DockerException(f"Container creation failed: {ex}") from ex

    async def start_container(self) -> bool:
        """Start an existing container.

        Returns:
            True if started successfully, False otherwise
        """
        try:
            container = await self._run_in_executor(
                self.docker_client.containers.get, self.container_name
            )
            await self._run_in_executor(container.start)
            _LOGGER.info("Started container %s", self.container_name)
            return True
        except Exception as ex:
            _LOGGER.error("Failed to start container %s: %s", self.container_name, ex)
            return False

    async def stop_container(self) -> bool:
        """Stop a running container.

        Returns:
            True if stopped successfully, False otherwise
        """
        try:
            container = await self._run_in_executor(
                self.docker_client.containers.get, self.container_name
            )
            await self._run_in_executor(container.stop, timeout=10)
            _LOGGER.info("Stopped container %s", self.container_name)
            return True
        except Exception as ex:
            _LOGGER.error("Failed to stop container %s: %s", self.container_name, ex)
            return False

    async def restart_container(self) -> bool:
        """Restart a container.

        Returns:
            True if restarted successfully, False otherwise
        """
        try:
            container = await self._run_in_executor(
                self.docker_client.containers.get, self.container_name
            )
            await self._run_in_executor(container.restart, timeout=10)
            _LOGGER.info("Restarted container %s", self.container_name)
            return True
        except Exception as ex:
            _LOGGER.error("Failed to restart container %s: %s", self.container_name, ex)
            return False

    async def remove_container(self) -> bool:
        """Remove a container.

        Returns:
            True if removed successfully, False otherwise
        """
        try:
            container = await self._run_in_executor(
                self.docker_client.containers.get, self.container_name
            )
            await self._run_in_executor(container.remove, force=True)
            _LOGGER.info("Removed container %s", self.container_name)
            return True
        except docker.errors.NotFound:
            _LOGGER.debug("Container %s not found, already removed", self.container_name)
            return True
        except Exception as ex:
            _LOGGER.error("Failed to remove container %s: %s", self.container_name, ex)
            return False

    async def get_container_status(self) -> dict[str, Any] | None:
        """Get container status.

        Returns:
            Dictionary with status information or None if container doesn't exist
        """
        try:
            container = await self._run_in_executor(
                self.docker_client.containers.get, self.container_name
            )
            container.reload()

            return {
                "id": container.id,
                "status": container.status,
                "running": container.status == "running",
                "created": container.attrs.get("Created"),
            }
        except docker.errors.NotFound:
            return None
        except Exception as ex:
            _LOGGER.error("Failed to get container status: %s", ex)
            return None

    async def check_port_conflict(self, port: int) -> bool:
        """Check if a port is already in use by another container.

        Args:
            port: Port number to check

        Returns:
            True if port is in use, False otherwise
        """
        try:
            containers = await self._run_in_executor(self.docker_client.containers.list, all=True)
            for container in containers:
                if container.name == self.container_name:
                    continue  # Skip our own container
                ports = container.attrs.get("NetworkSettings", {}).get("Ports", {})
                for port_binding in ports.values():
                    if port_binding:
                        for binding in port_binding:
                            if binding.get("HostPort") == str(port):
                                return True
            return False
        except Exception as ex:
            _LOGGER.error("Failed to check port conflict: %s", ex)
            return False

    async def async_cleanup(self) -> None:
        """Clean up Docker resources."""
        if self.docker_client:
            try:
                await self._run_in_executor(self.docker_client.close)
            except Exception as ex:
                _LOGGER.error("Error closing Docker client: %s", ex)
            finally:
                self.docker_client = None
