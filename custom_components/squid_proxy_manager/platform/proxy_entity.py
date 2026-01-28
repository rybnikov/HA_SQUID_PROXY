"""Custom entity for proxy instance status."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from ..const import (
    ATTR_CERT_EXPIRY,
    ATTR_CONTAINER_ID,
    ATTR_HTTPS_ENABLED,
    ATTR_INSTANCE_NAME,
    ATTR_LAST_STARTED,
    ATTR_LAST_STOPPED,
    ATTR_PORT,
    ATTR_USER_COUNT,
    DOMAIN,
    STATE_ERROR,
    STATE_RUNNING,
    STATE_STOPPED,
    STATE_UNAVAILABLE,
)
from .coordinator import SquidProxyCoordinator

_LOGGER = logging.getLogger(__name__)


class SquidProxyEntity(CoordinatorEntity):
    """Entity representing a Squid proxy instance."""

    def __init__(
        self,
        coordinator: SquidProxyCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self.entry = entry
        self.instance_name = entry.data.get("instance_name", entry.entry_id)
        self._attr_unique_id = f"{DOMAIN}_{self.instance_name}"
        self._attr_name = f"Squid Proxy {self.instance_name}"
        self._attr_icon = "mdi:server-network"
        self._last_started: datetime | None = None
        self._last_stopped: datetime | None = None

    @property
    def state(self) -> str:
        """Return the state of the entity."""
        if not self.coordinator.data:
            return STATE_UNAVAILABLE

        state = self.coordinator.data.get("state", STATE_UNAVAILABLE)
        return state

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        if not self.coordinator.data:
            return {}

        data = self.coordinator.data
        attrs = {
            ATTR_INSTANCE_NAME: self.instance_name,
            ATTR_PORT: self.entry.data.get("port", 3128),
            ATTR_HTTPS_ENABLED: self.entry.data.get("https_enabled", False),
            ATTR_CONTAINER_ID: data.get("container_id"),
            ATTR_USER_COUNT: data.get("user_count", 0),
        }

        # Add certificate expiry if HTTPS is enabled
        if self.entry.data.get("https_enabled", False):
            cert_expiry = data.get("certificate_expiry")
            if cert_expiry:
                try:
                    attrs[ATTR_CERT_EXPIRY] = datetime.fromisoformat(cert_expiry).isoformat()
                except (ValueError, TypeError):
                    attrs[ATTR_CERT_EXPIRY] = cert_expiry

        # Track last started/stopped times
        if data.get("running") and self._last_started is None:
            self._last_started = datetime.utcnow()
        elif not data.get("running") and self._last_stopped is None:
            self._last_stopped = datetime.utcnow()

        if self._last_started:
            attrs[ATTR_LAST_STARTED] = self._last_started.isoformat()
        if self._last_stopped:
            attrs[ATTR_LAST_STOPPED] = self._last_stopped.isoformat()

        return attrs

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success and self.state != STATE_UNAVAILABLE
