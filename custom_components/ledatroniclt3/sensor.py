import logging
import socket
import datetime
import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import CONF_PORT, CONF_HOST, UnitOfTemperature
from homeassistant.helpers.entity import Entity
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

DEFAULT_PORT = 10001

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
    vol.Required(CONF_HOST): cv.string,
})

LEDA_SENSORS = []

STATUS_START1 = b'\x0e'
STATUS_START2 = b'\xff'
STATUS_END = int(56)


class LedatronicComm:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.current_temp = None
        self.max_temp = None
        self.grundglut = None
        self.trend = None
        self.abbrande = None
        self.heizfehler = None
        self.current_state = None
        self.current_valve_pos_target = None
        self.current_valve_pos_actual = None
        self.last_update = None
        self.puffer_unten = None
        self.puffer_oben = None
        self.vorlauf_temp = None
        self.schorn_temp = None
        self.ventilator = None

    def update(self):
        # update at most every 10 seconds
        if self.last_update is not None and (datetime.datetime.now() - self.last_update) < datetime.timedelta(
                seconds=30):
            return

        self.last_update = datetime.datetime.now()

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((self.host, self.port))

        while True:
            byte = s.recv(1)
            if byte == b'':
                raise Exception("Interrupted")

            if byte != STATUS_START1:
                continue

            byte = s.recv(1)
            if byte == b'':
                raise Exception("Interrupted")

            if byte != STATUS_START2:
                continue

            data = bytearray()
            while len(data) < STATUS_END:
                next = s.recv(STATUS_END - len(data))
                if next == b'':
                    raise Exception("Interrupted")
                data += next

            self.current_temp = data[1] + (data[55] * 255)

            self.current_valve_pos_target = data[2]
            self.current_valve_pos_actual = data[3]

            stateVal = data[4]
            if stateVal == 0:
                self.current_state = "Bereit"
            elif stateVal == 2:
                self.current_state = "Anheizen"
            elif stateVal == 3 or stateVal == 4:
                self.current_state = "Heizbetrieb"
            elif stateVal == 7 or stateVal == 8:
                self.current_state = "Grundglut"
            elif stateVal == 97:
                self.current_state = "Heizfehler"
            elif stateVal == 98:
                self.current_state = "Tuer offen"
            else:
                self.current_state = "Unbekannter Status: " + str(stateVal)

            self.max_temp = data[9] + (data[8] * 255)
            self.grundglut = data[11]
            self.trend = data[12]
            self.abbrande = data[26] + (data[25] * 255)
            self.heizfehler = data[28] + (data[27] * 255)
            self.puffer_unten = data[34]
            self.puffer_oben = data[36]
            self.vorlauf_temp = data[37]
            self.schorn_temp = data[47] + (data[46] * 255)

            self.ventilator = data[50]
            stateVent = data[50]
            if stateVent == 0:
                self.ventilator = "off"
            elif stateVent == 1:
                self.ventilator = "on"
            else:
                self.ventilator = "unknown"

            break


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the LEDATRONIC LT3 Wifi sensors."""
    host = config.get(CONF_HOST)
    port = config.get(CONF_PORT)

    comm = LedatronicComm(host, port)

    LEDA_SENSORS.append(LedatronicTemperatureSensor(comm))
    LEDA_SENSORS.append(LedatronicStateSensor(comm))
    LEDA_SENSORS.append(LedatronicValveSensor(comm))
    LEDA_SENSORS.append(LedatronicMaxTemp(comm))
    LEDA_SENSORS.append(LedatronicGrundglut(comm))
    LEDA_SENSORS.append(LedatronicTrend(comm))
    LEDA_SENSORS.append(LedatronicAbbrande(comm))
    LEDA_SENSORS.append(LedatronicHeizfehler(comm))
    LEDA_SENSORS.append(LedatronicPufferUnten(comm))
    LEDA_SENSORS.append(LedatronicPufferOben(comm))
    LEDA_SENSORS.append(LedatronicVorlaufTemp(comm))
    LEDA_SENSORS.append(LedatronicSchornTemp(comm))
    LEDA_SENSORS.append(LedatronicVentilator(comm))
    add_entities(LEDA_SENSORS)


class LedatronicTemperatureSensor(Entity):
    """Representation of the LedaTronic main temperatrure sensor."""

    def __init__(self, comm):
        """Initialize the sensor."""
        self.comm = comm

    @property
    def name(self):
        """Return the name of this sensor."""
        return "ledatronic_temp"

    @property
    def state(self):
        """Return the current state of the entity."""
        return self.comm.current_temp

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement of this entity, if any."""
        return UnitOfTemperature.CELSIUS

    def update(self):
        """Retrieve latest state."""
        try:
            self.comm.update()
        except Exception:
            _LOGGER.error("Failed to get LEDATRONIC LT3 Wifi state.")


class LedatronicStateSensor(Entity):
    """Representation of the LedaTronic state sensor."""

    def __init__(self, comm):
        """Initialize the sensor."""
        self.comm = comm

    @property
    def name(self):
        """Return the name of this sensor."""
        return "ledatronic_state"

    @property
    def state(self):
        """Return the current state of the entity."""
        return self.comm.current_state

    def update(self):
        """Retrieve latest state."""
        try:
            self.comm.update()
        except Exception:
            _LOGGER.error("Failed to get LEDATRONIC LT3 Wifi state.")


class LedatronicValveSensor(Entity):
    """Representation of the LedaTronic valve sensor."""

    def __init__(self, comm):
        """Initialize the sensor."""
        self.comm = comm

    @property
    def name(self):
        """Return the name of this sensor."""
        return "ledatronic_valve"

    @property
    def state(self):
        """Return the current state of the entity."""
        return self.comm.current_valve_pos_target

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement of this entity, if any."""
        return '%'

    def update(self):
        """Retrieve latest state."""
        try:
            self.comm.update()
        except Exception:
            _LOGGER.error("Failed to get LEDATRONIC LT3 Wifi state.")

    @property
    def device_state_attributes(self):
        """Show Device Attributes."""
        return {"Actual Position": self.comm.current_valve_pos_actual}


class LedatronicMaxTemp(Entity):
    """Representation of the LedaTronic max temperatrure."""

    def __init__(self, comm):
        """Initialize the sensor."""
        self.comm = comm

    @property
    def name(self):
        """Return the name of this sensor."""
        return "ledatronic_maxtemp"

    @property
    def state(self):
        """Return the current state of the entity."""
        return self.comm.max_temp

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement of this entity, if any."""
        return UnitOfTemperature.CELSIUS

    def update(self):
        """Retrieve latest state."""
        try:
            self.comm.update()
        except Exception:
            _LOGGER.error("Failed to get LEDATRONIC LT3 Wifi state.")


class LedatronicGrundglut(Entity):
    """Representation of the LedaTronic grundglut temperatrure."""

    def __init__(self, comm):
        """Initialize the sensor."""
        self.comm = comm

    @property
    def name(self):
        """Return the name of this sensor."""
        return "ledatronic_grundglut"

    @property
    def state(self):
        """Return the current state of the entity."""
        return self.comm.grundglut

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement of this entity, if any."""
        return UnitOfTemperature.CELSIUS

    def update(self):
        """Retrieve latest state."""
        try:
            self.comm.update()
        except Exception:
            _LOGGER.error("Failed to get LEDATRONIC LT3 Wifi state.")


class LedatronicTrend(Entity):
    """Representation of the LedaTronic trend."""

    def __init__(self, comm):
        """Initialize the sensor."""
        self.comm = comm

    @property
    def name(self):
        """Return the name of this sensor."""
        return "ledatronic_trend"

    @property
    def state(self):
        """Return the current state of the entity."""
        return self.comm.trend

    def update(self):
        """Retrieve latest state."""
        try:
            self.comm.update()
        except Exception:
            _LOGGER.error("Failed to get LEDATRONIC LT3 Wifi state.")


class LedatronicAbbrande(Entity):
    """Representation of the LedaTronic Abbrände."""

    def __init__(self, comm):
        """Initialize the sensor."""
        self.comm = comm

    @property
    def name(self):
        """Return the name of this sensor."""
        return "ledatronic_abbrande"

    @property
    def state(self):
        """Return the current state of the entity."""
        return self.comm.abbrande

    def update(self):
        """Retrieve latest state."""
        try:
            self.comm.update()
        except Exception:
            _LOGGER.error("Failed to get LEDATRONIC LT3 Wifi state.")


class LedatronicHeizfehler(Entity):
    """Representation of the LedaTronic Heizfehler."""

    def __init__(self, comm):
        """Initialize the sensor."""
        self.comm = comm

    @property
    def name(self):
        """Return the name of this sensor."""
        return "ledatronic_heizfehler"

    @property
    def state(self):
        """Return the current state of the entity."""
        return self.comm.heizfehler

    def update(self):
        """Retrieve latest state."""
        try:
            self.comm.update()
        except Exception:
            _LOGGER.error("Failed to get LEDATRONIC LT3 Wifi state.")


class LedatronicPufferUnten(Entity):
    """Representation of the LedaTronic valve sensor."""

    def __init__(self, comm):
        """Initialize the sensor."""
        self.comm = comm

    @property
    def name(self):
        """Return the name of this sensor."""
        return "ledatronic_puffer_unten"

    @property
    def state(self):
        """Return the current state of the entity."""
        return self.comm.puffer_unten

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement of this entity, if any."""
        return UnitOfTemperature.CELSIUS

    def update(self):
        """Retrieve latest state."""
        try:
            self.comm.update()
        except Exception:
            _LOGGER.error("Failed to get LEDATRONIC LT3 Wifi state.")


class LedatronicPufferOben(Entity):
    """Representation of the LedaTronic valve sensor."""

    def __init__(self, comm):
        """Initialize the sensor."""
        self.comm = comm

    @property
    def name(self):
        """Return the name of this sensor."""
        return "ledatronic_puffer_oben"

    @property
    def state(self):
        """Return the current state of the entity."""
        return self.comm.puffer_oben

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement of this entity, if any."""
        return UnitOfTemperature.CELSIUS

    def update(self):
        """Retrieve latest state."""
        try:
            self.comm.update()
        except Exception:
            _LOGGER.error("Failed to get LEDATRONIC LT3 Wifi state.")


class LedatronicVorlaufTemp(Entity):
    """Representation of the LedaTronic valve sensor."""

    def __init__(self, comm):
        """Initialize the sensor."""
        self.comm = comm

    @property
    def name(self):
        """Return the name of this sensor."""
        return "ledatronic_vorlauf_temp"

    @property
    def state(self):
        """Return the current state of the entity."""
        return self.comm.vorlauf_temp

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement of this entity, if any."""
        return UnitOfTemperature.CELSIUS

    def update(self):
        """Retrieve latest state."""
        try:
            self.comm.update()
        except Exception:
            _LOGGER.error("Failed to get LEDATRONIC LT3 Wifi state.")


class LedatronicSchornTemp(Entity):
    """Representation of the LedaTronic valve sensor."""

    def __init__(self, comm):
        """Initialize the sensor."""
        self.comm = comm

    @property
    def name(self):
        """Return the name of this sensor."""
        return "ledatronic_schorn_temp"

    @property
    def state(self):
        """Return the current state of the entity."""
        return self.comm.schorn_temp

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement of this entity, if any."""
        return UnitOfTemperature.CELSIUS

    def update(self):
        """Retrieve latest state."""
        try:
            self.comm.update()
        except Exception:
            _LOGGER.error("Failed to get LEDATRONIC LT3 Wifi state.")


class LedatronicVentilator(Entity):
    """Representation of the LedaTronic valve sensor."""

    def __init__(self, comm):
        """Initialize the sensor."""
        self.comm = comm

    @property
    def name(self):
        """Return the name of this sensor."""
        return "ledatronic_ventilator"

    @property
    def state(self):
        """Return the current state of the entity."""
        return self.comm.ventilator

    def update(self):
        """Retrieve latest state."""
        try:
            self.comm.update()
        except Exception:
            _LOGGER.error("Failed to get LEDATRONIC LT3 Wifi state.")
