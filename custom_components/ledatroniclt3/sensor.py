"""Sensor platform for the Ledatronic LT3 integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import LedatronicConfigEntry
from .const import DOMAIN, SENSOR_DESCRIPTIONS, LedatronicSensorEntityDescription
from .coordinator import LedatronicCoordinator


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
