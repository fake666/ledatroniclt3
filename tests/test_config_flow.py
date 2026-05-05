"""Tests for the Ledatronic LT3 config flow."""

from unittest.mock import patch

from homeassistant.config_entries import SOURCE_IMPORT, SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from pytest_homeassistant_custom_component.common import MockConfigEntry

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


async def test_import_from_yaml(hass: HomeAssistant) -> None:
    """Test that YAML config is imported as a config entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_IMPORT},
        data={"host": "192.168.1.100", "port": 10001},
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Ledatronic LT3 (192.168.1.100)"
    assert result["data"] == {"host": "192.168.1.100", "port": 10001}


async def test_import_duplicate_aborts(hass: HomeAssistant) -> None:
    """Test that importing the same device twice aborts."""
    await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_IMPORT},
        data={"host": "192.168.1.100", "port": 10001},
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_IMPORT},
        data={"host": "192.168.1.100", "port": 10001},
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_unique_id_is_set_on_create(hass: HomeAssistant) -> None:
    """Test that successful setup stores host:port as unique_id."""
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
    assert result["result"].unique_id == "192.168.1.100:10001"


async def test_reconfigure_updates_host(hass: HomeAssistant) -> None:
    """Test that reconfigure updates host and unique_id."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"host": "192.168.1.100", "port": 10001},
        unique_id="192.168.1.100:10001",
        title="Ledatronic LT3 (192.168.1.100)",
    )
    entry.add_to_hass(hass)

    result = await entry.start_reconfigure_flow(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure"

    with patch(
        "custom_components.ledatroniclt3.config_flow._test_connection",
        return_value=True,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"host": "192.168.1.200", "port": 10001},
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.data == {"host": "192.168.1.200", "port": 10001}
    assert entry.unique_id == "192.168.1.200:10001"


async def test_reconfigure_cannot_connect(hass: HomeAssistant) -> None:
    """Test that reconfigure shows an error when the new host is unreachable."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"host": "192.168.1.100", "port": 10001},
        unique_id="192.168.1.100:10001",
    )
    entry.add_to_hass(hass)

    result = await entry.start_reconfigure_flow(hass)

    with patch(
        "custom_components.ledatroniclt3.config_flow._test_connection",
        return_value=False,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"host": "192.168.1.200", "port": 10001},
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}
    assert entry.data == {"host": "192.168.1.100", "port": 10001}


async def test_reconfigure_wrong_device_aborts(hass: HomeAssistant) -> None:
    """Test that reconfiguring to a host already configured by another entry aborts."""
    other = MockConfigEntry(
        domain=DOMAIN,
        data={"host": "192.168.1.200", "port": 10001},
        unique_id="192.168.1.200:10001",
    )
    other.add_to_hass(hass)

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"host": "192.168.1.100", "port": 10001},
        unique_id="192.168.1.100:10001",
    )
    entry.add_to_hass(hass)

    result = await entry.start_reconfigure_flow(hass)

    with patch(
        "custom_components.ledatroniclt3.config_flow._test_connection",
        return_value=True,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"host": "192.168.1.200", "port": 10001},
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "wrong_device"
