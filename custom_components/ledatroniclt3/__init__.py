"""The Ledatronic LT3 integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import LedatronicCoordinator

PLATFORMS = [Platform.SENSOR]

type LedatronicConfigEntry = ConfigEntry[LedatronicCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: LedatronicConfigEntry) -> bool:
    """Set up Ledatronic LT3 from a config entry."""
    coordinator = LedatronicCoordinator(
        hass,
        host=entry.data[CONF_HOST],
        port=entry.data[CONF_PORT],
    )
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: LedatronicConfigEntry
) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
