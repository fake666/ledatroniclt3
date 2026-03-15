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
from homeassistant.const import PERCENTAGE, UnitOfTemperature

DOMAIN = "ledatroniclt3"
DEFAULT_PORT = 10001

FRAME_START1 = b"\x0e"
FRAME_START2 = b"\xff"
FRAME_END1 = 0x0D
FRAME_END2 = 0xFF

STATE_MAP: dict[int, str] = {
    0: "idle",
    2: "heating_up",
    3: "burning",
    4: "burning",
    6: "starting",
    7: "embers",
    8: "embers",
    97: "fault",
    98: "door_open",
}

STOVE_STATES = [
    "idle",
    "heating_up",
    "burning",
    "starting",
    "embers",
    "fault",
    "door_open",
    "unknown",
]

ERROR_MAP: dict[int, str] = {
    0: "none",
    1: "overheating",
    2: "motor_fault",
    3: "motor_overheating",
    16: "critical_overheating",
    18: "critical_motor_overheating",
    32: "power_fault",
}

ERROR_STATES = [
    "none",
    "overheating",
    "motor_fault",
    "motor_overheating",
    "critical_overheating",
    "critical_motor_overheating",
    "power_fault",
    "unknown",
]


@dataclass(frozen=True, kw_only=True)
class LedatronicSensorEntityDescription(SensorEntityDescription):
    """Describes a Ledatronic LT3 sensor entity."""

    value_fn: Callable[[dict[str, Any]], Any]
    attr_fn: Callable[[dict[str, Any]], dict[str, Any]] | None = None


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
        icon="mdi:fireplace",
        value_fn=lambda data: data["state"],
    ),
    LedatronicSensorEntityDescription(
        key="error",
        translation_key="error",
        device_class=SensorDeviceClass.ENUM,
        options=ERROR_STATES,
        icon="mdi:alert-circle-outline",
        value_fn=lambda data: data["error"],
    ),
    LedatronicSensorEntityDescription(
        key="valve",
        translation_key="valve",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:valve",
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
        value_fn=lambda data: data["firebed_temp"],
    ),
    LedatronicSensorEntityDescription(
        key="trend",
        translation_key="trend",
        icon="mdi:trending-up",
        value_fn=lambda data: data["trend"],
    ),
)
