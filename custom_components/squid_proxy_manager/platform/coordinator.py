"""DataUpdateCoordinator for polling Docker container status."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from ..const import DEFAULT_UPDATE_INTERVAL, DOMAIN
from ..security.auth_manager import AuthManager
from ..security.cert_manager import CertificateManager

_LOGGER = logging.getLogger(__name__)


class SquidProxyCoordinator(DataUpdateCoordinator):
    """Coordinator for updating proxy instance data."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{entry.data.get('instance_name', entry.entry_id)}",
            update_interval=DEFAULT_UPDATE_INTERVAL,
        )
        self.entry = entry
        self.instance_name = entry.data.get("instance_name", entry.entry_id)

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from Docker and update entity state."""
        try:
            # Get Docker manager from hass.data
            if DOMAIN not in self.hass.data or self.entry.entry_id not in self.hass.data[DOMAIN]:
                return {
                    "state": "unavailable",
                    "container_id": None,
                    "running": False,
                }

            docker_manager = self.hass.data[DOMAIN][self.entry.entry_id].get("docker_manager")
            if not docker_manager:
                return {
                    "state": "unavailable",
                    "container_id": None,
                    "running": False,
                }

            # Get container status
            status = await docker_manager.get_container_status()

            if status is None:
                return {
                    "state": "unavailable",
                    "container_id": None,
                    "running": False,
                }

            # Get user count
            user_count = 0
            try:
                from pathlib import Path

                config_dir = Path(self.hass.config.config_dir)
                instance_dir = config_dir / "squid_proxy_manager" / self.instance_name
                passwd_file = instance_dir / "passwd"

                if passwd_file.exists():
                    auth_manager = AuthManager(passwd_file)
                    user_count = auth_manager.get_user_count()
            except Exception as ex:
                _LOGGER.warning("Failed to get user count: %s", ex)

            # Get certificate expiry
            cert_expiry = None
            if self.entry.data.get("https_enabled", False):
                try:
                    from pathlib import Path

                    config_dir = Path(self.hass.config.config_dir)
                    certs_dir = config_dir / "squid_proxy_manager" / "certs"
                    cert_manager = CertificateManager(certs_dir, self.instance_name)
                    cert_expiry = cert_manager.get_certificate_expiry()
                except Exception as ex:
                    _LOGGER.warning("Failed to get certificate expiry: %s", ex)

            # Determine state
            if status["running"]:
                state = "running"
            elif status["status"] == "exited":
                state = "stopped"
            else:
                state = "error"

            return {
                "state": state,
                "container_id": status["id"],
                "running": status["running"],
                "container_status": status["status"],
                "user_count": user_count,
                "certificate_expiry": cert_expiry.isoformat() if cert_expiry else None,
                "last_updated": datetime.utcnow().isoformat(),
            }

        except Exception as ex:
            _LOGGER.error("Error updating proxy instance data: %s", ex)
            raise UpdateFailed(f"Error communicating with Docker: {ex}") from ex
