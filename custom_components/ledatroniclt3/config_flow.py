"""Config flow for the Ledatronic LT3 integration."""

from __future__ import annotations

import socket
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PORT

from .const import DEFAULT_PORT, DOMAIN

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
    }
)


def _test_connection(host: str, port: int) -> bool:
    """Test if we can connect to the device."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(5)
            sock.connect((host, port))
            return True
    except (OSError, TimeoutError):
        return False


def _unique_id(host: str, port: int) -> str:
    """Build the unique ID for a host/port pair."""
    return f"{host}:{port}"


class LedatronicLT3ConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Ledatronic LT3."""

    VERSION = 1

    async def async_step_import(
        self, import_data: dict[str, Any]
    ) -> ConfigFlowResult:
        """Handle import from YAML configuration."""
        await self.async_set_unique_id(
            _unique_id(import_data[CONF_HOST], import_data[CONF_PORT])
        )
        self._abort_if_unique_id_configured()
        return self.async_create_entry(
            title=f"Ledatronic LT3 ({import_data[CONF_HOST]})",
            data=import_data,
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST]
            port = user_input[CONF_PORT]

            await self.async_set_unique_id(_unique_id(host, port))
            self._abort_if_unique_id_configured()

            can_connect = await self.hass.async_add_executor_job(
                _test_connection, host, port
            )

            if can_connect:
                return self.async_create_entry(
                    title=f"Ledatronic LT3 ({host})",
                    data=user_input,
                )
            errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reconfiguration of an existing entry (e.g. IP change)."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST]
            port = user_input[CONF_PORT]
            new_unique_id = _unique_id(host, port)

            for other in self._async_current_entries(include_ignore=False):
                if (
                    other.entry_id != entry.entry_id
                    and other.unique_id == new_unique_id
                ):
                    return self.async_abort(reason="wrong_device")

            can_connect = await self.hass.async_add_executor_job(
                _test_connection, host, port
            )

            if can_connect:
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates=user_input,
                    unique_id=new_unique_id,
                )
            errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(
                STEP_USER_DATA_SCHEMA, entry.data
            ),
            errors=errors,
        )
