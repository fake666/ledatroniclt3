"""DataUpdateCoordinator for the Ledatronic LT3 integration."""

from __future__ import annotations

import logging
import socket
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, STATE_MAP, STATUS_LENGTH, STATUS_START1, STATUS_START2

_LOGGER = logging.getLogger(__name__)

UPDATE_INTERVAL = timedelta(seconds=30)
SOCKET_TIMEOUT = 10


class LedatronicCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator to fetch data from a Ledatronic LT3 device."""

    def __init__(self, hass: HomeAssistant, host: str, port: int) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )
        self.host = host
        self.port = port

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from the device."""
        try:
            return await self.hass.async_add_executor_job(self._fetch_data)
        except (OSError, TimeoutError) as err:
            raise UpdateFailed(f"Error communicating with device: {err}") from err

    def _fetch_data(self) -> dict[str, Any]:
        """Fetch data from the device (blocking)."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(SOCKET_TIMEOUT)
            sock.connect((self.host, self.port))

            while True:
                byte = sock.recv(1)
                if byte == b"":
                    raise ConnectionError("Connection closed by device")

                if byte != STATUS_START1:
                    continue

                byte = sock.recv(1)
                if byte == b"":
                    raise ConnectionError("Connection closed by device")

                if byte != STATUS_START2:
                    continue

                data = bytearray()
                while len(data) < STATUS_LENGTH:
                    chunk = sock.recv(STATUS_LENGTH - len(data))
                    if chunk == b"":
                        raise ConnectionError("Connection closed by device")
                    data += chunk

                return self._parse_data(data)

    @staticmethod
    def _parse_data(data: bytearray) -> dict[str, Any]:
        """Parse the binary status packet."""
        state_val = data[4]
        state = STATE_MAP.get(state_val, "unknown")

        fan_val = data[50]
        if fan_val == 0:
            ventilator = "off"
        elif fan_val == 1:
            ventilator = "on"
        else:
            ventilator = "unknown"

        return {
            "current_temp": int.from_bytes(data[0:2], byteorder="big"),
            "valve_target": data[2],
            "valve_actual": data[3],
            "state": state,
            "state_raw": state_val,
            "max_temp": int.from_bytes(data[8:10], byteorder="big"),
            "grundglut": data[11],
            "trend": data[12],
            "abbrande": int.from_bytes(data[25:27], byteorder="big"),
            "heizfehler": int.from_bytes(data[27:29], byteorder="big"),
            "puffer_unten": data[34],
            "puffer_oben": data[36],
            "vorlauf_temp": data[37],
            "schorn_temp": int.from_bytes(data[46:48], byteorder="big"),
            "ventilator": ventilator,
        }
