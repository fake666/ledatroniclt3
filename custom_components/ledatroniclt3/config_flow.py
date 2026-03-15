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


class LedatronicLT3ConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Ledatronic LT3."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST]
            port = user_input[CONF_PORT]

            self._async_abort_entries_match({CONF_HOST: host, CONF_PORT: port})

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
