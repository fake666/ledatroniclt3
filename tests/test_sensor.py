"""Tests for the Ledatronic LT3 sensor platform."""

from unittest.mock import patch

from homeassistant.config_entries import SOURCE_IMPORT
from homeassistant.core import DOMAIN as HOMEASSISTANT_DOMAIN, HomeAssistant
from homeassistant.helpers import entity_registry as er, issue_registry as ir

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ledatroniclt3.const import DOMAIN, SENSOR_DESCRIPTIONS
from tests.conftest import MOCK_CONFIG, MOCK_DATA


async def test_all_sensors_created(
    hass: HomeAssistant, mock_config_entry, mock_coordinator_fetch
) -> None:
    """Test that all sensor entities are created."""
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entity_reg = er.async_get(hass)
    entities = er.async_entries_for_config_entry(
        entity_reg, mock_config_entry.entry_id
    )
    assert len(entities) == len(SENSOR_DESCRIPTIONS)


async def test_unique_ids(
    hass: HomeAssistant, mock_config_entry, mock_coordinator_fetch
) -> None:
    """Test that all sensors have correct unique IDs."""
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entity_reg = er.async_get(hass)
    entities = er.async_entries_for_config_entry(
        entity_reg, mock_config_entry.entry_id
    )
    unique_ids = {e.unique_id for e in entities}

    for desc in SENSOR_DESCRIPTIONS:
        assert f"test_entry_id_{desc.key}" in unique_ids


async def test_temperature_sensor_value(
    hass: HomeAssistant, mock_config_entry, mock_coordinator_fetch
) -> None:
    """Test the temperature sensor has the correct value."""
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entity_reg = er.async_get(hass)
    entry = entity_reg.async_get_entity_id(
        "sensor", "ledatroniclt3", "test_entry_id_temperature"
    )
    assert entry is not None

    state = hass.states.get(entry)
    assert state is not None
    assert state.state == "127"


async def test_stove_state_sensor(
    hass: HomeAssistant, mock_config_entry, mock_coordinator_fetch
) -> None:
    """Test the stove state sensor returns the correct state."""
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entity_reg = er.async_get(hass)
    entry = entity_reg.async_get_entity_id(
        "sensor", "ledatroniclt3", "test_entry_id_stove_state"
    )
    state = hass.states.get(entry)
    assert state.state == "idle"


async def test_error_sensor(
    hass: HomeAssistant, mock_config_entry, mock_coordinator_fetch
) -> None:
    """Test the error sensor."""
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entity_reg = er.async_get(hass)
    entry = entity_reg.async_get_entity_id(
        "sensor", "ledatroniclt3", "test_entry_id_error"
    )
    state = hass.states.get(entry)
    assert state.state == "none"


async def test_valve_sensor_attributes(
    hass: HomeAssistant, mock_config_entry, mock_coordinator_fetch
) -> None:
    """Test the valve sensor has extra attributes."""
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entity_reg = er.async_get(hass)
    entry = entity_reg.async_get_entity_id(
        "sensor", "ledatroniclt3", "test_entry_id_valve"
    )
    state = hass.states.get(entry)
    assert state.state == "2"
    assert state.attributes["actual_position"] == 2


async def test_firebed_temperature(
    hass: HomeAssistant, mock_config_entry, mock_coordinator_fetch
) -> None:
    """Test the firebed temperature sensor."""
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entity_reg = er.async_get(hass)
    entry = entity_reg.async_get_entity_id(
        "sensor", "ledatroniclt3", "test_entry_id_firebed_temperature"
    )
    state = hass.states.get(entry)
    assert state.state == "331"


async def test_unload_entry(
    hass: HomeAssistant, mock_config_entry, mock_coordinator_fetch
) -> None:
    """Test that the integration can be unloaded."""
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.async_unload(mock_config_entry.entry_id)
    assert result is True


async def test_import_creates_repair_issue(
    hass: HomeAssistant, mock_coordinator_fetch
) -> None:
    """Test that a YAML-imported entry creates a repair issue."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_CONFIG,
        source=SOURCE_IMPORT,
        entry_id="imported_entry",
        title="Ledatronic LT3 (192.168.1.100)",
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    issue_reg = ir.async_get(hass)
    issue = issue_reg.async_get_issue(
        HOMEASSISTANT_DOMAIN, f"deprecated_yaml_{DOMAIN}"
    )
    assert issue is not None
    assert issue.severity == ir.IssueSeverity.WARNING


async def test_normal_setup_no_repair_issue(
    hass: HomeAssistant, mock_config_entry, mock_coordinator_fetch
) -> None:
    """Test that a UI-configured entry does not create a repair issue."""
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    issue_reg = ir.async_get(hass)
    issue = issue_reg.async_get_issue(
        HOMEASSISTANT_DOMAIN, f"deprecated_yaml_{DOMAIN}"
    )
    assert issue is None
