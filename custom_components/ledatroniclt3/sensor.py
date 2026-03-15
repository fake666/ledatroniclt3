"""Sensor platform for the Ledatronic LT3 integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA, SensorEntity
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import LedatronicConfigEntry
from .const import DEFAULT_PORT, DOMAIN, SENSOR_DESCRIPTIONS, LedatronicSensorEntityDescription
from .coordinator import LedatronicCoordinator

_LOGGER = logging.getLogger(__name__)

# Legacy YAML platform schema (kept for import migration)
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
    }
)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Import YAML configuration and trigger config flow."""
    _LOGGER.warning(
        "Configuration of the Ledatronic LT3 integration via YAML is deprecated "
        "and will be removed in a future version. Please remove it from your "
        "configuration.yaml and set it up via the UI"
    )
    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": "import"},
            data={
                CONF_HOST: config[CONF_HOST],
                CONF_PORT: config.get(CONF_PORT, DEFAULT_PORT),
            },
        )
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: LedatronicConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Ledatronic LT3 sensors from a config entry."""
    coordinator = entry.runtime_data
    async_add_entities(
        LedatronicSensor(coordinator, description, entry)
        for description in SENSOR_DESCRIPTIONS
    )


class LedatronicSensor(CoordinatorEntity[LedatronicCoordinator], SensorEntity):
    """Representation of a Ledatronic LT3 sensor."""

    entity_description: LedatronicSensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: LedatronicCoordinator,
        description: LedatronicSensorEntityDescription,
        entry: LedatronicConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Ledatronic LT3",
            manufacturer="LEDA Werk",
            model="LT3",
        )

    @property
    def native_value(self) -> Any:
        """Return the sensor value."""
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return additional state attributes."""
        if self.coordinator.data is None or self.entity_description.attr_fn is None:
            return None
        return self.entity_description.attr_fn(self.coordinator.data)
