"""The Squid Proxy Manager integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DOMAIN
from .docker.docker_manager import DockerManager
from .platform.coordinator import SquidProxyCoordinator
from .services.service_handler import async_setup_services

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]  # We'll use sensor platform for proxy entities


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up the Squid Proxy Manager component."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Squid Proxy Manager from a config entry."""
    _LOGGER.info("Setting up Squid Proxy Manager entry: %s", entry.entry_id)

    # Initialize Docker manager
    try:
        docker_manager = DockerManager(hass, entry)
        await docker_manager.async_validate()
    except Exception as ex:
        _LOGGER.error("Failed to initialize Docker manager: %s", ex)
        raise ConfigEntryNotReady(
            f"Docker is not available. Please ensure Docker is installed and running: {ex}"
        ) from ex

    # Create coordinator
    coordinator = SquidProxyCoordinator(hass, entry)

    # Store docker manager and coordinator in hass.data
    hass.data[DOMAIN][entry.entry_id] = {
        "docker_manager": docker_manager,
        "coordinator": coordinator,
        "entry": entry,
    }

    # Forward to platform
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register services
    await async_setup_services(hass, entry)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.info("Unloading Squid Proxy Manager entry: %s", entry.entry_id)

    # Unload platform
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    # Clean up Docker manager
    if entry.entry_id in hass.data[DOMAIN]:
        docker_manager = hass.data[DOMAIN][entry.entry_id].get("docker_manager")
        if docker_manager:
            try:
                await docker_manager.async_cleanup()
            except Exception as ex:
                _LOGGER.error("Error during cleanup: %s", ex)
        del hass.data[DOMAIN][entry.entry_id]

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
