"""Tests for the Ledatronic LT3 sensor platform."""

from homeassistant.config_entries import SOURCE_IMPORT
from homeassistant.core import DOMAIN as HOMEASSISTANT_DOMAIN, HomeAssistant
from homeassistant.helpers import (
    device_registry as dr,
    entity_registry as er,
    issue_registry as ir,
)

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ledatroniclt3.const import (
    BINARY_SENSOR_DESCRIPTIONS,
    DOMAIN,
    EXPANSION_SENSOR_DESCRIPTIONS,
    SENSOR_DESCRIPTIONS,
)
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
    assert state.attributes["state_code"] == 0
    assert state.attributes["output"] == "none"
    assert state.attributes["oven_id"] == 19


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
    assert state.attributes["error_code"] == 0


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


async def test_embers_threshold(
    hass: HomeAssistant, mock_config_entry, mock_coordinator_fetch
) -> None:
    """Test the embers threshold sensor (entity key kept as firebed_temperature)."""
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entity_reg = er.async_get(hass)
    entry = entity_reg.async_get_entity_id(
        "sensor", "ledatroniclt3", "test_entry_id_firebed_temperature"
    )
    state = hass.states.get(entry)
    assert state.state == "331"


async def test_counters_and_minutes(
    hass: HomeAssistant, mock_config_entry, mock_coordinator_fetch
) -> None:
    """Test the operation-data counters and the minutes-without-rise sensor."""
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entity_reg = er.async_get(hass)
    for key, expected in (
        ("burnoff_count", "3595"),
        ("fault_count", "193"),
        ("trend", "10"),
        ("max_temperature", "617"),
    ):
        entry = entity_reg.async_get_entity_id(
            "sensor", "ledatroniclt3", f"test_entry_id_{key}"
        )
        assert hass.states.get(entry).state == expected, key


async def test_device_info_without_firmware(
    hass: HomeAssistant, mock_config_entry, mock_coordinator_fetch
) -> None:
    """A 16-byte frame has no firmware; the oven id must not be shown as one."""
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    device_reg = dr.async_get(hass)
    devices = dr.async_entries_for_config_entry(device_reg, "test_entry_id")
    assert len(devices) == 1
    assert devices[0].identifiers == {(DOMAIN, "test_entry_id")}
    assert devices[0].hw_version == "30"
    assert devices[0].sw_version is None


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


async def test_unique_id_backfilled_on_setup(
    hass: HomeAssistant, mock_coordinator_fetch
) -> None:
    """Test that legacy entries (no unique_id) get one backfilled on setup."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_CONFIG,
        entry_id="legacy_entry",
        unique_id=None,
        title=f"Ledatronic LT3 ({MOCK_CONFIG['host']})",
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.unique_id == f"{MOCK_CONFIG['host']}:{MOCK_CONFIG['port']}"


async def test_coordinator_bound_to_entry(
    hass: HomeAssistant, mock_config_entry, mock_coordinator_fetch
) -> None:
    """Test that the coordinator is bound to its config entry."""
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.runtime_data.config_entry is mock_config_entry


EXPANSION_DATA = {
    **MOCK_DATA,
    "buffer_bottom": 60,
    "buffer_middle": 141,
    "buffer_top": 63,
    "flow_temp": 77,
    "pump_speed": 95,
    "chimney_pressure": 20.8,
    "exhaust_temp": 200,
    "ventilation": True,
    "lock": False,
    "alarm_counter": 0,
    "error_offset": False,
    "error_pressure": False,
    "error_exhaust": False,
    "error_relay": False,
}


def _expansion_entity_id(hass: HomeAssistant, platform: str, entry, key: str) -> str | None:
    return er.async_get(hass).async_get_entity_id(
        platform, DOMAIN, f"{entry.entry_id}_{key}"
    )


async def test_no_expansion_entities_without_modules(
    hass: HomeAssistant, mock_config_entry, mock_coordinator_fetch
) -> None:
    """A plain LT3 gets no dead entities."""
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    for desc in EXPANSION_SENSOR_DESCRIPTIONS:
        assert _expansion_entity_id(hass, "sensor", mock_config_entry, desc.key) is None
    for desc in BINARY_SENSOR_DESCRIPTIONS:
        assert (
            _expansion_entity_id(hass, "binary_sensor", mock_config_entry, desc.key)
            is None
        )


async def test_expansion_entities_and_values(
    hass: HomeAssistant, mock_config_entry, mock_coordinator_fetch
) -> None:
    """With KS04 and LUC frames all their entities appear with their values."""
    mock_coordinator_fetch.return_value = EXPANSION_DATA
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    expected = {
        "buffer_bottom": "60",
        "buffer_middle": "141",
        "buffer_top": "63",
        "flow_temperature": "77",
        "pump_speed": "95",
        "exhaust_temperature": "200",
        "chimney_pressure": "20.8",
        "alarm_counter": "0",
    }
    for key, value in expected.items():
        entity_id = _expansion_entity_id(hass, "sensor", mock_config_entry, key)
        assert hass.states.get(entity_id).state == value, key

    entity_id = _expansion_entity_id(
        hass, "binary_sensor", mock_config_entry, "ventilation"
    )
    assert hass.states.get(entity_id).state == "on"
    entity_id = _expansion_entity_id(
        hass, "binary_sensor", mock_config_entry, "error_relay"
    )
    assert hass.states.get(entity_id).state == "off"


async def test_module_heard_late_and_lost(
    hass: HomeAssistant, mock_config_entry, mock_coordinator_fetch
) -> None:
    """Entities follow the frames: added on first sight, unavailable when missing."""
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    coordinator = mock_config_entry.runtime_data
    assert _expansion_entity_id(hass, "sensor", mock_config_entry, "buffer_top") is None

    mock_coordinator_fetch.return_value = EXPANSION_DATA
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    entity_id = _expansion_entity_id(hass, "sensor", mock_config_entry, "buffer_top")
    assert hass.states.get(entity_id).state == "63"

    mock_coordinator_fetch.return_value = MOCK_DATA
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == "unavailable"
