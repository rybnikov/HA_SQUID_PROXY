"""Service handler for Squid Proxy Manager."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.helpers import config_validation as cv

from ..const import (
    DOMAIN,
    SERVICE_ADD_USER,
    SERVICE_GET_USERS,
    SERVICE_REMOVE_USER,
    SERVICE_RESTART_INSTANCE,
    SERVICE_START_INSTANCE,
    SERVICE_STOP_INSTANCE,
    SERVICE_UPDATE_CERTIFICATE,
)
from ..security.auth_manager import AuthManager
from ..security.cert_manager import CertificateManager
from ..security.security_utils import validate_password, validate_username

_LOGGER = logging.getLogger(__name__)

SERVICE_SCHEMA_START = cv.make_entity_service_schema({})
SERVICE_SCHEMA_STOP = cv.make_entity_service_schema({})
SERVICE_SCHEMA_RESTART = cv.make_entity_service_schema({})
SERVICE_SCHEMA_ADD_USER = cv.make_entity_service_schema(
    {
        cv.Required("username"): cv.string,
        cv.Required("password"): cv.string,
    }
)
SERVICE_SCHEMA_REMOVE_USER = cv.make_entity_service_schema(
    {
        cv.Required("username"): cv.string,
    }
)
SERVICE_SCHEMA_UPDATE_CERT = cv.make_entity_service_schema(
    {
        cv.Optional("certificate_path"): cv.string,
        cv.Optional("key_path"): cv.string,
    }
)
SERVICE_SCHEMA_GET_USERS = cv.make_entity_service_schema({})


async def async_setup_services(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Set up services for Squid Proxy Manager."""
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}

    async def handle_start_instance(call: ServiceCall) -> None:
        """Handle start_instance service call."""
        entity_ids = call.data.get("entity_id", [])
        for entity_id in entity_ids:
            await _handle_instance_action(hass, entity_id, "start")

    async def handle_stop_instance(call: ServiceCall) -> None:
        """Handle stop_instance service call."""
        entity_ids = call.data.get("entity_id", [])
        for entity_id in entity_ids:
            await _handle_instance_action(hass, entity_id, "stop")

    async def handle_restart_instance(call: ServiceCall) -> None:
        """Handle restart_instance service call."""
        entity_ids = call.data.get("entity_id", [])
        for entity_id in entity_ids:
            await _handle_instance_action(hass, entity_id, "restart")

    async def handle_add_user(call: ServiceCall) -> None:
        """Handle add_user service call."""
        entity_ids = call.data.get("entity_id", [])
        username = call.data.get("username")
        password = call.data.get("password")

        if not username or not password:
            _LOGGER.error("Username and password are required")
            return

        # Validate username and password
        is_valid, error = validate_username(username)
        if not is_valid:
            _LOGGER.error("Invalid username: %s", error)
            return

        is_valid, error = validate_password(password)
        if not is_valid:
            _LOGGER.error("Invalid password: %s", error)
            return

        for entity_id in entity_ids:
            await _handle_add_user(hass, entity_id, username, password)

    async def handle_remove_user(call: ServiceCall) -> None:
        """Handle remove_user service call."""
        entity_ids = call.data.get("entity_id", [])
        username = call.data.get("username")

        if not username:
            _LOGGER.error("Username is required")
            return

        for entity_id in entity_ids:
            await _handle_remove_user(hass, entity_id, username)

    async def handle_update_certificate(call: ServiceCall) -> None:
        """Handle update_certificate service call."""
        entity_ids = call.data.get("entity_id", [])
        cert_path = call.data.get("certificate_path")
        key_path = call.data.get("key_path")

        for entity_id in entity_ids:
            await _handle_update_certificate(hass, entity_id, cert_path, key_path)

    async def handle_get_users(call: ServiceCall) -> None:
        """Handle get_users service call."""
        entity_ids = call.data.get("entity_id", [])
        for entity_id in entity_ids:
            users = await _handle_get_users(hass, entity_id)
            _LOGGER.info("Users for %s: %s", entity_id, users)

    # Register services
    hass.services.async_register(
        DOMAIN,
        SERVICE_START_INSTANCE,
        handle_start_instance,
        schema=SERVICE_SCHEMA_START,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_STOP_INSTANCE,
        handle_stop_instance,
        schema=SERVICE_SCHEMA_STOP,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_RESTART_INSTANCE,
        handle_restart_instance,
        schema=SERVICE_SCHEMA_RESTART,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_ADD_USER,
        handle_add_user,
        schema=SERVICE_SCHEMA_ADD_USER,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_REMOVE_USER,
        handle_remove_user,
        schema=SERVICE_SCHEMA_REMOVE_USER,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_UPDATE_CERTIFICATE,
        handle_update_certificate,
        schema=SERVICE_SCHEMA_UPDATE_CERT,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_GET_USERS,
        handle_get_users,
        schema=SERVICE_SCHEMA_GET_USERS,
    )


async def _handle_instance_action(
    hass: HomeAssistant, entity_id: str, action: str
) -> None:
    """Handle instance start/stop/restart action."""
    try:
        # Find the entry for this entity
        entry = _get_entry_for_entity(hass, entity_id)
        if not entry:
            _LOGGER.error("No entry found for entity %s", entity_id)
            return

        if DOMAIN not in hass.data or entry.entry_id not in hass.data[DOMAIN]:
            _LOGGER.error("Entry data not found for %s", entity_id)
            return

        docker_manager = hass.data[DOMAIN][entry.entry_id].get("docker_manager")
        if not docker_manager:
            _LOGGER.error("Docker manager not found for %s", entity_id)
            return

        if action == "start":
            success = await docker_manager.start_container()
        elif action == "stop":
            success = await docker_manager.stop_container()
        elif action == "restart":
            success = await docker_manager.restart_container()
        else:
            _LOGGER.error("Unknown action: %s", action)
            return

        if success:
            # Trigger coordinator update
            coordinator = hass.data[DOMAIN][entry.entry_id].get("coordinator")
            if coordinator:
                await coordinator.async_request_refresh()
        else:
            _LOGGER.error("Failed to %s container for %s", action, entity_id)

    except Exception as ex:
        _LOGGER.error("Error handling %s action for %s: %s", action, entity_id, ex)


async def _handle_add_user(
    hass: HomeAssistant, entity_id: str, username: str, password: str
) -> None:
    """Handle add user action."""
    try:
        entry = _get_entry_for_entity(hass, entity_id)
        if not entry:
            _LOGGER.error("No entry found for entity %s", entity_id)
            return

        if DOMAIN not in hass.data or entry.entry_id not in hass.data[DOMAIN]:
            _LOGGER.error("Entry data not found for %s", entity_id)
            return

        instance_name = entry.data.get("instance_name", entry.entry_id)
        config_dir = Path(hass.config.config_dir)
        instance_dir = config_dir / "squid_proxy_manager" / instance_name
        passwd_file = instance_dir / "passwd"

        auth_manager = AuthManager(passwd_file)
        success = auth_manager.add_user(username, password)

        if success:
            # Trigger coordinator update
            coordinator = hass.data[DOMAIN][entry.entry_id].get("coordinator")
            if coordinator:
                await coordinator.async_request_refresh()
        else:
            _LOGGER.warning("User %s already exists for %s", username, entity_id)

    except Exception as ex:
        _LOGGER.error("Error adding user to %s: %s", entity_id, ex)


async def _handle_remove_user(
    hass: HomeAssistant, entity_id: str, username: str
) -> None:
    """Handle remove user action."""
    try:
        entry = _get_entry_for_entity(hass, entity_id)
        if not entry:
            _LOGGER.error("No entry found for entity %s", entity_id)
            return

        if DOMAIN not in hass.data or entry.entry_id not in hass.data[DOMAIN]:
            _LOGGER.error("Entry data not found for %s", entity_id)
            return

        instance_name = entry.data.get("instance_name", entry.entry_id)
        config_dir = Path(hass.config.config_dir)
        instance_dir = config_dir / "squid_proxy_manager" / instance_name
        passwd_file = instance_dir / "passwd"

        auth_manager = AuthManager(passwd_file)
        success = auth_manager.remove_user(username)

        if success:
            # Trigger coordinator update
            coordinator = hass.data[DOMAIN][entry.entry_id].get("coordinator")
            if coordinator:
                await coordinator.async_request_refresh()
        else:
            _LOGGER.warning("User %s does not exist for %s", username, entity_id)

    except Exception as ex:
        _LOGGER.error("Error removing user from %s: %s", entity_id, ex)


async def _handle_update_certificate(
    hass: HomeAssistant,
    entity_id: str,
    cert_path: str | None,
    key_path: str | None,
) -> None:
    """Handle update certificate action."""
    try:
        entry = _get_entry_for_entity(hass, entity_id)
        if not entry:
            _LOGGER.error("No entry found for entity %s", entity_id)
            return

        if DOMAIN not in hass.data or entry.entry_id not in hass.data[DOMAIN]:
            _LOGGER.error("Entry data not found for %s", entity_id)
            return

        if not entry.data.get("https_enabled", False):
            _LOGGER.error("HTTPS is not enabled for %s", entity_id)
            return

        docker_manager = hass.data[DOMAIN][entry.entry_id].get("docker_manager")
        if not docker_manager:
            _LOGGER.error("Docker manager not found for %s", entity_id)
            return

        instance_name = entry.data.get("instance_name", entry.entry_id)
        config_dir = Path(hass.config.config_dir)
        certs_dir = config_dir / "squid_proxy_manager" / "certs"

        cert_manager = CertificateManager(certs_dir, instance_name)

        if cert_path and key_path:
            # Use existing certificate
            cert_file = Path(cert_path)
            key_file = Path(key_path)
            cert_manager.use_existing_certificate(cert_file, key_file)
        else:
            # Generate new certificate
            await cert_manager.generate_certificate()

        # Restart container to apply new certificate
        await docker_manager.restart_container()

        # Trigger coordinator update
        coordinator = hass.data[DOMAIN][entry.entry_id].get("coordinator")
        if coordinator:
            await coordinator.async_request_refresh()

    except Exception as ex:
        _LOGGER.error("Error updating certificate for %s: %s", entity_id, ex)


async def _handle_get_users(hass: HomeAssistant, entity_id: str) -> list[str]:
    """Handle get users action."""
    try:
        entry = _get_entry_for_entity(hass, entity_id)
        if not entry:
            _LOGGER.error("No entry found for entity %s", entity_id)
            return []

        if DOMAIN not in hass.data or entry.entry_id not in hass.data[DOMAIN]:
            _LOGGER.error("Entry data not found for %s", entity_id)
            return []

        instance_name = entry.data.get("instance_name", entry.entry_id)
        config_dir = Path(hass.config.config_dir)
        instance_dir = config_dir / "squid_proxy_manager" / instance_name
        passwd_file = instance_dir / "passwd"

        auth_manager = AuthManager(passwd_file)
        return auth_manager.get_users()

    except Exception as ex:
        _LOGGER.error("Error getting users for %s: %s", entity_id, ex)
        return []


def _get_entry_for_entity(hass: HomeAssistant, entity_id: str) -> ConfigEntry | None:
    """Get config entry for an entity ID."""
    # Extract instance name from entity_id
    # Format: sensor.squid_proxy_<instance_name>
    if not entity_id.startswith("sensor."):
        return None

    # Remove sensor. prefix and find matching entry
    entity_name = entity_id.replace("sensor.", "")

    # Find matching entry by checking entity unique_id
    if DOMAIN not in hass.data:
        return None

    for entry_id, data in hass.data[DOMAIN].items():
        entry = data.get("entry")
        if not entry:
            continue

        # Check if this entry matches the entity
        # The entity unique_id is DOMAIN_instance_name
        instance_name = entry.data.get("instance_name", entry.entry_id)
        expected_unique_id = f"{DOMAIN}_{instance_name}"

        if entity_name == expected_unique_id or entity_name.startswith(f"{DOMAIN}_"):
            return entry

    return None
