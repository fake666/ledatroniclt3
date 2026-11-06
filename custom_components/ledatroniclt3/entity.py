"""Shared entity base of the Ledatronic LT3 integration."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import TYPE_CHECKING, Any

from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import LedatronicCoordinator

if TYPE_CHECKING:
    from . import LedatronicConfigEntry


class LedatronicEntity(CoordinatorEntity[LedatronicCoordinator]):
    """An entity of the stove device, fed by the coordinator."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: LedatronicCoordinator,
        description: Any,
        entry: LedatronicConfigEntry,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Ledatronic LT3",
            manufacturer="LEDA Werk",
            model="LT3",
            hw_version=str(coordinator.data["controller_version"]),
            # Only newer modules send the firmware bytes.
            sw_version=coordinator.data.get("firmware"),
        )

    @property
    def available(self) -> bool:
        """Unavailable when the poll failed or this module's frame was missing."""
        if not super().available:
            return False
        data_key = self.entity_description.data_key
        return data_key is None or data_key in self.coordinator.data


@callback
def async_add_expansion_entities(
    entry: LedatronicConfigEntry,
    descriptions: Iterable[Any],
    factory: Callable[[LedatronicCoordinator, Any, LedatronicConfigEntry], Entity],
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add expansion-module entities once their module has been heard from.

    A stove without KS04 or LUC never sends those frames and gets no dead
    entities. A module whose frame was missed during setup is picked up by a
    later poll.
    """
    coordinator = entry.runtime_data
    pending = list(descriptions)

    @callback
    def add_new() -> None:
        data = coordinator.data or {}
        new = [desc for desc in pending if desc.data_key in data]
        if not new:
            return
        for desc in new:
            pending.remove(desc)
        async_add_entities(factory(coordinator, desc, entry) for desc in new)

    add_new()
    entry.async_on_unload(coordinator.async_add_listener(add_new))
