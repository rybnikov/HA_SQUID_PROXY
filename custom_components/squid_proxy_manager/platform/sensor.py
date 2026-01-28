"""Sensor platform for Squid Proxy Manager."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from ..const import DOMAIN
from .coordinator import SquidProxyCoordinator
from .proxy_entity import SquidProxyEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Squid Proxy Manager sensor from a config entry."""
    # Get coordinator from hass.data (created in __init__.py)
    from ..const import DOMAIN

    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    # Fetch initial data so we have data when the entity is added
    await coordinator.async_config_entry_first_refresh()

    async_add_entities([SquidProxyEntity(coordinator, entry)])
