"""Constants for the Ledatronic LT3 integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfTemperature,
    UnitOfTime,
)

from .protocol import ERROR_MAP, STATE_MAP

DOMAIN = "ledatroniclt3"
DEFAULT_PORT = 10001

STOVE_STATES = [*dict.fromkeys(STATE_MAP.values()), "unknown"]
ERROR_STATES = [*ERROR_MAP.values(), "unknown"]


@dataclass(frozen=True, kw_only=True)
class LedatronicSensorEntityDescription(SensorEntityDescription):
    """Describes a Ledatronic LT3 sensor entity."""

    value_fn: Callable[[dict[str, Any]], Any]
    attr_fn: Callable[[dict[str, Any]], dict[str, Any]] | None = None


def _nonzero(key: str) -> Callable[[dict[str, Any]], Any]:
    """Return the value, or None while the controller reports 0 (not set)."""
    return lambda data: data[key] or None


# Entity keys are part of the unique_id: never rename, only relabel.
SENSOR_DESCRIPTIONS: tuple[LedatronicSensorEntityDescription, ...] = (
    LedatronicSensorEntityDescription(
        key="temperature",
        translation_key="temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda data: data["chamber_temp"],
    ),
    LedatronicSensorEntityDescription(
        key="stove_state",
        translation_key="stove_state",
        device_class=SensorDeviceClass.ENUM,
        options=STOVE_STATES,
        value_fn=lambda data: data["state"],
        attr_fn=lambda data: {
            "state_code": data["state_raw"],
            "output": data["output"],
            "output_on": data["output_on"],
            "oven_id": data["oven_id"],
        },
    ),
    LedatronicSensorEntityDescription(
        key="error",
        translation_key="error",
        device_class=SensorDeviceClass.ENUM,
        options=ERROR_STATES,
        value_fn=lambda data: data["error"],
        attr_fn=lambda data: {"error_code": data["error_raw"]},
    ),
    LedatronicSensorEntityDescription(
        key="valve",
        translation_key="valve",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data["motor_target"],
        attr_fn=lambda data: {"actual_position": data["motor_actual"]},
    ),
    LedatronicSensorEntityDescription(
        key="max_temperature",
        translation_key="max_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda data: data["max_chamber_temp"],
    ),
    LedatronicSensorEntityDescription(
        key="firebed_temperature",
        translation_key="firebed_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=_nonzero("embers_threshold"),
    ),
    LedatronicSensorEntityDescription(
        key="trend",
        translation_key="trend",
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        value_fn=lambda data: data["minutes_without_rise"],
    ),
    LedatronicSensorEntityDescription(
        key="burnoff_count",
        translation_key="burnoff_count",
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get("burnoff_count"),
    ),
    LedatronicSensorEntityDescription(
        key="fault_count",
        translation_key="fault_count",
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get("fault_count"),
    ),
)
