"""Constants for the Ledatronic LT3 integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntityDescription,
)
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfPressure,
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
    # Set for expansion-module values: the entity is only created once this
    # key has been received, and is unavailable while it is missing.
    data_key: str | None = None


@dataclass(frozen=True, kw_only=True)
class LedatronicBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describes a flag reported by an expansion module."""

    data_key: str


def _nonzero(key: str) -> Callable[[dict[str, Any]], Any]:
    """Return the value, or None while the controller reports 0 (not set)."""
    return lambda data: data[key] or None


def _temperature(key: str, data_key: str) -> LedatronicSensorEntityDescription:
    """Describe a temperature reported by an expansion module."""
    return LedatronicSensorEntityDescription(
        key=key,
        translation_key=key,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        data_key=data_key,
        value_fn=lambda data: data[data_key],
    )


def _luc_error(key: str) -> LedatronicBinarySensorEntityDescription:
    """Describe an error flag of the LUC module."""
    return LedatronicBinarySensorEntityDescription(
        key=key,
        translation_key=key,
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        data_key=key,
    )


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

# Only created when the module is present (see async_add_expansion_entities).
EXPANSION_SENSOR_DESCRIPTIONS: tuple[LedatronicSensorEntityDescription, ...] = (
    _temperature("buffer_bottom", "buffer_bottom"),
    _temperature("buffer_middle", "buffer_middle"),
    _temperature("buffer_top", "buffer_top"),
    _temperature("flow_temperature", "flow_temp"),
    LedatronicSensorEntityDescription(
        key="pump_speed",
        translation_key="pump_speed",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        data_key="pump_speed",
        value_fn=lambda data: data["pump_speed"],
    ),
    _temperature("exhaust_temperature", "exhaust_temp"),
    LedatronicSensorEntityDescription(
        key="chimney_pressure",
        translation_key="chimney_pressure",
        device_class=SensorDeviceClass.PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPressure.PA,
        suggested_display_precision=1,
        data_key="chimney_pressure",
        value_fn=lambda data: data["chimney_pressure"],
    ),
    LedatronicSensorEntityDescription(
        key="alarm_counter",
        translation_key="alarm_counter",
        entity_category=EntityCategory.DIAGNOSTIC,
        data_key="alarm_counter",
        value_fn=lambda data: data["alarm_counter"],
    ),
)

BINARY_SENSOR_DESCRIPTIONS: tuple[LedatronicBinarySensorEntityDescription, ...] = (
    LedatronicBinarySensorEntityDescription(
        key="ventilation",
        translation_key="ventilation",
        device_class=BinarySensorDeviceClass.RUNNING,
        data_key="ventilation",
    ),
    LedatronicBinarySensorEntityDescription(
        key="lock",
        translation_key="lock",
        entity_category=EntityCategory.DIAGNOSTIC,
        data_key="lock",
    ),
    _luc_error("error_offset"),
    _luc_error("error_pressure"),
    _luc_error("error_exhaust"),
    _luc_error("error_relay"),
)
