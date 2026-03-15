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

STATUS_START1 = b"\x0e"
STATUS_START2 = b"\xff"
STATUS_LENGTH = 56

STATE_MAP: dict[int, str] = {
    0: "bereit",
    2: "anheizen",
    3: "heizbetrieb",
    4: "heizbetrieb",
    7: "grundglut",
    8: "grundglut",
    97: "heizfehler",
    98: "tuer_offen",
}

STOVE_STATES = [
    "bereit",
    "anheizen",
    "heizbetrieb",
    "grundglut",
    "heizfehler",
    "tuer_offen",
    "unknown",
]

FAN_STATES = ["on", "off", "unknown"]


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
        value_fn=lambda data: data["current_temp"],
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
        key="valve",
        translation_key="valve",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:valve",
        value_fn=lambda data: data["valve_target"],
        attr_fn=lambda data: {"actual_position": data["valve_actual"]},
    ),
    LedatronicSensorEntityDescription(
        key="max_temperature",
        translation_key="max_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda data: data["max_temp"],
    ),
    LedatronicSensorEntityDescription(
        key="grundglut",
        translation_key="grundglut",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda data: data["grundglut"],
    ),
    LedatronicSensorEntityDescription(
        key="trend",
        translation_key="trend",
        icon="mdi:trending-up",
        value_fn=lambda data: data["trend"],
    ),
    LedatronicSensorEntityDescription(
        key="burns",
        translation_key="burns",
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:fire-circle",
        value_fn=lambda data: data["abbrande"],
    ),
    LedatronicSensorEntityDescription(
        key="heating_errors",
        translation_key="heating_errors",
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:alert-circle-outline",
        value_fn=lambda data: data["heizfehler"],
    ),
    LedatronicSensorEntityDescription(
        key="buffer_bottom",
        translation_key="buffer_bottom",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda data: data["puffer_unten"],
    ),
    LedatronicSensorEntityDescription(
        key="buffer_top",
        translation_key="buffer_top",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda data: data["puffer_oben"],
    ),
    LedatronicSensorEntityDescription(
        key="flow_temperature",
        translation_key="flow_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda data: data["vorlauf_temp"],
    ),
    LedatronicSensorEntityDescription(
        key="chimney_temperature",
        translation_key="chimney_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda data: data["schorn_temp"],
    ),
    LedatronicSensorEntityDescription(
        key="fan",
        translation_key="fan",
        device_class=SensorDeviceClass.ENUM,
        options=FAN_STATES,
        icon="mdi:fan",
        value_fn=lambda data: data["ventilator"],
    ),
)
