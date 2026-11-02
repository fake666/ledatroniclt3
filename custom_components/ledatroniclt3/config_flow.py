"""Config flow for the Ledatronic LT3 integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PORT

from .const import DEFAULT_PORT, DOMAIN
from .protocol import LedatronicProtocolError, read_device

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): vol.All(
            int, vol.Range(min=1, max=65535)
        ),
    }
)


async def _async_try_device(host: str, port: int) -> dict[str, Any] | None:
    """Read one status frame; None if the device does not answer like an LT3."""
    try:
        return await read_device(host, port)
    except (OSError, TimeoutError, LedatronicProtocolError) as err:
        _LOGGER.debug("Cannot read %s:%s: %s", host, port, err)
        return None


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

            if await _async_try_device(host, port) is not None:
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

            if await _async_try_device(host, port) is not None:
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
