"""Config flow for Squid Proxy Manager."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import (
    DEFAULT_PORT,
    DOMAIN,
    ERROR_CERT_GENERATION_FAILED,
    ERROR_CONTAINER_CREATION_FAILED,
    ERROR_DOCKER_NOT_AVAILABLE,
    ERROR_INVALID_PORT,
    ERROR_INVALID_USERNAME,
    ERROR_PORT_IN_USE,
    ERROR_WEAK_PASSWORD,
    STEP_CERTIFICATE,
    STEP_INITIAL_USER,
    STEP_INSTANCE_NAME,
    STEP_PORT,
    STEP_REVIEW,
    STEP_USER,
)
from .docker.docker_manager import DockerManager
from .security.auth_manager import AuthManager
from .security.cert_manager import CertificateManager
from .security.security_utils import validate_password, validate_port, validate_username

_LOGGER = logging.getLogger(__name__)


async def validate_docker(hass: HomeAssistant) -> None:
    """Validate Docker is available."""
    try:
        import docker
        docker_client = docker.DockerClient(base_url="unix:///var/run/docker.sock")
        docker_client.ping()
        docker_client.close()
    except Exception as ex:
        _LOGGER.error("Docker validation failed: %s", ex)
        raise CannotConnect from ex


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""


class SquidProxyManagerConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Squid Proxy Manager."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize config flow."""
        self.data: dict[str, Any] = {}
        self.docker_manager: DockerManager | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            # Validate Docker is available
            try:
                await validate_docker(self.hass)
            except CannotConnect:
                return self.async_abort(reason="docker_unavailable")

            return self.async_show_form(
                step_id=STEP_USER,
                data_schema=vol.Schema(
                    {
                        vol.Required("instance_name"): str,
                    }
                ),
            )

        # Check if instance name already exists
        await self.async_set_unique_id(user_input["instance_name"])
        self._abort_if_unique_id_configured()

        self.data = user_input
        return await self.async_step_instance_name()

    async def async_step_instance_name(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle instance name configuration."""
        if user_input is None:
            return self.async_show_form(
                step_id=STEP_INSTANCE_NAME,
                data_schema=vol.Schema(
                    {
                        vol.Required("instance_name", default=self.data.get("instance_name", "")): str,
                        vol.Optional("description"): str,
                    }
                ),
            )

        self.data.update(user_input)
        return await self.async_step_port()

    async def async_step_port(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle port configuration."""
        errors = {}

        if user_input is not None:
            port = user_input.get("port", DEFAULT_PORT)
            try:
                port_int = int(port)
                is_valid, error = validate_port(port_int)
                if not is_valid:
                    errors["base"] = ERROR_INVALID_PORT
                else:
                    # Check port conflict
                    if not self.docker_manager:
                        # Create temporary docker manager for validation
                        from homeassistant.config_entries import ConfigEntry

                        temp_entry = ConfigEntry(
                            version=1,
                            domain=DOMAIN,
                            title=self.data.get("instance_name", ""),
                            data={"instance_name": self.data.get("instance_name", "")},
                            source="user",
                            options={},
                            entry_id="temp",
                        )
                        self.docker_manager = DockerManager(self.hass, temp_entry)
                        await self.docker_manager.async_validate()

                    port_in_use = await self.docker_manager.check_port_conflict(port_int)
                    if port_in_use:
                        errors["base"] = ERROR_PORT_IN_USE
                    else:
                        self.data["port"] = port_int
                        return await self.async_step_certificate()
            except ValueError:
                errors["base"] = ERROR_INVALID_PORT

        return self.async_show_form(
            step_id=STEP_PORT,
            data_schema=vol.Schema(
                {
                    vol.Required("port", default=self.data.get("port", DEFAULT_PORT)): int,
                }
            ),
            errors=errors,
        )

    async def async_step_certificate(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle certificate configuration."""
        errors = {}

        if user_input is not None:
            enable_https = user_input.get("enable_https", False)
            self.data["https_enabled"] = enable_https

            if enable_https:
                cert_path = user_input.get("certificate_path", "").strip()
                key_path = user_input.get("key_path", "").strip()

                if cert_path and key_path:
                    # Use existing certificate
                    try:
                        from pathlib import Path

                        cert_file = Path(cert_path)
                        key_file = Path(key_path)

                        instance_name = self.data.get("instance_name", "")
                        config_dir = Path(self.hass.config.config_dir)
                        certs_dir = config_dir / "squid_proxy_manager" / "certs"

                        cert_manager = CertificateManager(certs_dir, instance_name)
                        cert_file, key_file = cert_manager.use_existing_certificate(cert_file, key_file)
                        self.data["cert_file"] = str(cert_file)
                        self.data["key_file"] = str(key_file)
                    except Exception as ex:
                        errors["base"] = ERROR_CERT_GENERATION_FAILED
                        _LOGGER.error("Failed to use existing certificate: %s", ex)
                else:
                    # Generate new certificate
                    try:
                        instance_name = self.data.get("instance_name", "")
                        config_dir = Path(self.hass.config.config_dir)
                        certs_dir = config_dir / "squid_proxy_manager" / "certs"

                        cert_manager = CertificateManager(certs_dir, instance_name)
                        cert_file, key_file = await cert_manager.generate_certificate()
                        self.data["cert_file"] = str(cert_file)
                        self.data["key_file"] = str(key_file)
                    except Exception as ex:
                        errors["base"] = ERROR_CERT_GENERATION_FAILED
                        _LOGGER.error("Failed to generate certificate: %s", ex)

            if not errors:
                return await self.async_step_initial_user()

        return self.async_show_form(
            step_id=STEP_CERTIFICATE,
            data_schema=vol.Schema(
                {
                    vol.Required("enable_https", default=self.data.get("https_enabled", False)): bool,
                    vol.Optional("certificate_path"): str,
                    vol.Optional("key_path"): str,
                }
            ),
            errors=errors,
        )

    async def async_step_initial_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle initial user creation."""
        errors = {}

        if user_input is not None:
            username = user_input.get("username", "").strip()
            password = user_input.get("password", "")

            # Validate username
            is_valid, error = validate_username(username)
            if not is_valid:
                errors["base"] = ERROR_INVALID_USERNAME

            # Validate password
            if not errors:
                is_valid, error = validate_password(password)
                if not is_valid:
                    errors["base"] = ERROR_WEAK_PASSWORD

            if not errors:
                self.data["initial_username"] = username
                self.data["initial_password"] = password
                return await self.async_step_review()

        return self.async_show_form(
            step_id=STEP_INITIAL_USER,
            data_schema=vol.Schema(
                {
                    vol.Required("username"): str,
                    vol.Required("password"): str,
                }
            ),
            errors=errors,
        )

    async def async_step_review(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle review and finalize configuration."""
        if user_input is None:
            # Show review form
            return self.async_show_form(
                step_id=STEP_REVIEW,
                description_placeholders={
                    "instance_name": self.data.get("instance_name", ""),
                    "port": str(self.data.get("port", DEFAULT_PORT)),
                    "https": "Yes" if self.data.get("https_enabled", False) else "No",
                },
            )

        # Create the entry
        try:
            # Initialize Docker manager and create container
            instance_name = self.data.get("instance_name", "")
            port = self.data.get("port", DEFAULT_PORT)
            https_enabled = self.data.get("https_enabled", False)

            # Create config entry first
            entry_data = {
                "instance_name": instance_name,
                "port": port,
                "https_enabled": https_enabled,
            }
            if https_enabled:
                entry_data["cert_file"] = self.data.get("cert_file")
                entry_data["key_file"] = self.data.get("key_file")

            # Create temporary entry for Docker manager
            from homeassistant.config_entries import ConfigEntry

            temp_entry = ConfigEntry(
                version=1,
                domain=DOMAIN,
                title=instance_name,
                data=entry_data,
                source="user",
                options={},
                entry_id="temp",
            )

            docker_manager = DockerManager(self.hass, temp_entry)
            await docker_manager.async_validate()

            # Create password file and add initial user
            from pathlib import Path

            config_dir = Path(self.hass.config.config_dir)
            instance_dir = config_dir / "squid_proxy_manager" / instance_name
            instance_dir.mkdir(parents=True, exist_ok=True)
            passwd_file = instance_dir / "passwd"

            auth_manager = AuthManager(passwd_file)
            auth_manager.add_user(
                self.data["initial_username"],
                self.data["initial_password"],
            )

            # Create container
            cert_file = Path(self.data["cert_file"]) if self.data.get("cert_file") else None
            key_file = Path(self.data["key_file"]) if self.data.get("key_file") else None

            container_id = await docker_manager.create_container(
                port=port,
                https_enabled=https_enabled,
                cert_file=cert_file,
                key_file=key_file,
                passwd_file=passwd_file,
            )

            entry_data["container_id"] = container_id

            return self.async_create_entry(
                title=instance_name,
                data=entry_data,
            )

        except Exception as ex:
            _LOGGER.error("Failed to create proxy instance: %s", ex)
            return self.async_show_form(
                step_id=STEP_REVIEW,
                errors={"base": ERROR_CONTAINER_CREATION_FAILED},
                description_placeholders={"error": str(ex)},
            )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> OptionsFlow:
        """Get the options flow for this handler."""
        return SquidProxyManagerOptionsFlowHandler(config_entry)


class SquidProxyManagerOptionsFlowHandler(OptionsFlow):
    """Handle options flow for Squid Proxy Manager."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        # Options flow can be extended later for runtime configuration changes
        return self.async_create_entry(title="", data={})
