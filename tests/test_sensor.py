"""Tests for the Ledatronic LT3 sensor platform."""

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from custom_components.ledatroniclt3.const import SENSOR_DESCRIPTIONS


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
    assert state.state == "185"


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
    assert state.state == "heizbetrieb"


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
    assert state.state == "80"
    assert state.attributes["actual_position"] == 78


async def test_fan_sensor(
    hass: HomeAssistant, mock_config_entry, mock_coordinator_fetch
) -> None:
    """Test the fan sensor."""
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entity_reg = er.async_get(hass)
    entry = entity_reg.async_get_entity_id(
        "sensor", "ledatroniclt3", "test_entry_id_fan"
    )
    state = hass.states.get(entry)
    assert state.state == "on"


async def test_unload_entry(
    hass: HomeAssistant, mock_config_entry, mock_coordinator_fetch
) -> None:
    """Test that the integration can be unloaded."""
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.async_unload(mock_config_entry.entry_id)
    assert result is True
