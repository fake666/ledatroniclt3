"""Fixtures for Ledatronic LT3 tests."""

from unittest.mock import patch

import pytest

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ledatroniclt3.const import DOMAIN

MOCK_HOST = "192.168.1.100"
MOCK_PORT = 10001

MOCK_CONFIG = {
    "host": MOCK_HOST,
    "port": MOCK_PORT,
}

# Status frame captured from a cold stove (state idle, valve parked at 2 %),
# followed by the operation-data frame.
MOCK_STATUS_HEX = "00 7f 02 02 00 00 00 1e 02 69 01 4b 0a 00 00 13"
MOCK_OPDATA_HEX = "f4 0a 0e 0b 00 c1"

MOCK_DATA = {
    "chamber_temp": 127,
    "motor_actual": 2,
    "motor_target": 2,
    "state": "idle",
    "state_raw": 0,
    "error": "none",
    "error_raw": 0,
    "output": "none",
    "output_on": False,
    "controller_version": 30,
    "max_chamber_temp": 617,
    "embers_threshold": 331,
    "minutes_without_rise": 10,
    "temperature2": 0,
    "oven_id": 19,
    "operating_hours_raw": 62474,
    "burnoff_count": 3595,
    "fault_count": 193,
}


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations in all tests."""
    yield


@pytest.fixture
def mock_config_entry(hass) -> MockConfigEntry:
    """Create and register a mock config entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=MOCK_CONFIG,
        entry_id="test_entry_id",
        title=f"Ledatronic LT3 ({MOCK_HOST})",
    )
    entry.add_to_hass(hass)
    return entry


@pytest.fixture
def mock_coordinator_fetch():
    """Mock the device read used by the coordinator."""
    with patch(
        "custom_components.ledatroniclt3.coordinator.read_device",
        return_value=MOCK_DATA,
    ) as mock_fetch:
        yield mock_fetch
