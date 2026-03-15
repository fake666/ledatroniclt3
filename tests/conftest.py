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

MOCK_DATA = {
    "current_temp": 185,
    "valve_target": 80,
    "valve_actual": 78,
    "state": "heizbetrieb",
    "state_raw": 3,
    "max_temp": 250,
    "grundglut": 60,
    "trend": 1,
    "abbrande": 42,
    "heizfehler": 0,
    "puffer_unten": 45,
    "puffer_oben": 65,
    "vorlauf_temp": 55,
    "schorn_temp": 130,
    "ventilator": "on",
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
    """Mock the coordinator's _fetch_data to return test data."""
    with patch(
        "custom_components.ledatroniclt3.coordinator.LedatronicCoordinator._fetch_data",
        return_value=MOCK_DATA,
    ) as mock_fetch:
        yield mock_fetch
