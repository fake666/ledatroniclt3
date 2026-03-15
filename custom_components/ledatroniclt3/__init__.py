"""The Ledatronic LT3 integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import DOMAIN as HOMEASSISTANT_DOMAIN, HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.typing import ConfigType

from .const import DEFAULT_PORT, DOMAIN
from .coordinator import LedatronicCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR]

type LedatronicConfigEntry = ConfigEntry[LedatronicCoordinator]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Ledatronic LT3 integration from YAML (import only)."""
    if DOMAIN not in config:
        return True

    for platform_config in config[DOMAIN]:
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": "import"},
                data={
                    CONF_HOST: platform_config[CONF_HOST],
                    CONF_PORT: platform_config.get(CONF_PORT, DEFAULT_PORT),
                },
            )
        )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: LedatronicConfigEntry) -> bool:
    """Set up Ledatronic LT3 from a config entry."""
    if entry.source == "import":
        ir.async_create_issue(
            hass,
            HOMEASSISTANT_DOMAIN,
            f"deprecated_yaml_{DOMAIN}",
            is_fixable=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key="deprecated_yaml",
            translation_placeholders={
                "domain": DOMAIN,
                "integration_title": "Ledatronic LT3",
            },
        )

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
