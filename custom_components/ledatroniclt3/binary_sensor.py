"""Binary sensor platform of the Ledatronic LT3 integration (LUC module)."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import LedatronicConfigEntry
from .const import BINARY_SENSOR_DESCRIPTIONS, LedatronicBinarySensorEntityDescription
from .entity import LedatronicEntity, async_add_expansion_entities

# Entities only read coordinator data; no per-entity I/O to serialise.
PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: LedatronicConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the binary sensors of the expansion modules."""
    async_add_expansion_entities(
        entry, BINARY_SENSOR_DESCRIPTIONS, LedatronicBinarySensor, async_add_entities
    )


class LedatronicBinarySensor(LedatronicEntity, BinarySensorEntity):
    """A flag reported by the LUC module."""

    entity_description: LedatronicBinarySensorEntityDescription

    @property
    def is_on(self) -> bool | None:
        """Return the flag, or None while its frame is missing."""
        return self.coordinator.data.get(self.entity_description.data_key)
