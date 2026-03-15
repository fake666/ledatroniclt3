"""Tests for the Ledatronic LT3 config flow."""

from unittest.mock import patch

from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.ledatroniclt3.const import DOMAIN


async def test_form_is_shown(hass: HomeAssistant) -> None:
    """Test that the user form is shown on init."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}


async def test_successful_connection(hass: HomeAssistant) -> None:
    """Test that a successful connection creates a config entry."""
    with patch(
        "custom_components.ledatroniclt3.config_flow._test_connection",
        return_value=True,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_USER},
            data={"host": "192.168.1.100", "port": 10001},
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Ledatronic LT3 (192.168.1.100)"
    assert result["data"] == {"host": "192.168.1.100", "port": 10001}


async def test_connection_failure(hass: HomeAssistant) -> None:
    """Test that a failed connection shows an error."""
    with patch(
        "custom_components.ledatroniclt3.config_flow._test_connection",
        return_value=False,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_USER},
            data={"host": "192.168.1.100", "port": 10001},
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_duplicate_entry(hass: HomeAssistant) -> None:
    """Test that adding the same device twice aborts."""
    with patch(
        "custom_components.ledatroniclt3.config_flow._test_connection",
        return_value=True,
    ):
        await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_USER},
            data={"host": "192.168.1.100", "port": 10001},
        )

    with patch(
        "custom_components.ledatroniclt3.config_flow._test_connection",
        return_value=True,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_USER},
            data={"host": "192.168.1.100", "port": 10001},
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
