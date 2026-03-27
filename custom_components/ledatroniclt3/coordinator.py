"""DataUpdateCoordinator for the Ledatronic LT3 integration."""

from __future__ import annotations

import asyncio
import logging
import socket
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DOMAIN,
    ERROR_MAP,
    FRAME_END1,
    FRAME_END2,
    FRAME_START1,
    FRAME_START2,
    STATE_MAP,
)

_LOGGER = logging.getLogger(__name__)

UPDATE_INTERVAL = timedelta(seconds=30)
SOCKET_TIMEOUT = 10
MAX_RETRIES = 3
RETRY_DELAY = 2


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
        self._sock: socket.socket | None = None

    def _connect(self) -> socket.socket:
        """Establish a new TCP connection to the device."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(SOCKET_TIMEOUT)
        sock.connect((self.host, self.port))
        _LOGGER.debug("Connected to %s:%s", self.host, self.port)
        return sock

    def _disconnect(self) -> None:
        """Close the current connection if open."""
        if self._sock is not None:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None

    async def async_shutdown(self) -> None:
        """Close the connection on coordinator shutdown."""
        await super().async_shutdown()
        await self.hass.async_add_executor_job(self._disconnect)

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from the device with retries for transient errors."""
        last_err: Exception | None = None
        for attempt in range(MAX_RETRIES):
            try:
                return await self.hass.async_add_executor_job(self._fetch_data)
            except (OSError, TimeoutError) as err:
                last_err = err
                self._disconnect()
                if attempt < MAX_RETRIES - 1:
                    _LOGGER.debug(
                        "Attempt %d/%d failed: %s – retrying in %ds",
                        attempt + 1,
                        MAX_RETRIES,
                        err,
                        RETRY_DELAY,
                    )
                    await asyncio.sleep(RETRY_DELAY)
        raise UpdateFailed(f"Error communicating with device: {last_err}") from last_err

    def _fetch_data(self) -> dict[str, Any]:
        """Fetch data from the device, reusing an existing connection."""
        if self._sock is None:
            self._sock = self._connect()

        sock = self._sock

        # Wait for status frame start marker: 0x0E 0xFF
        while True:
            byte = sock.recv(1)
            if byte == b"":
                raise ConnectionError("Connection closed by device")
            if byte != FRAME_START1:
                continue

            byte = sock.recv(1)
            if byte == b"":
                raise ConnectionError("Connection closed by device")
            if byte != FRAME_START2:
                continue

            # Read until end marker: 0x0D 0xFF
            data = bytearray()
            prev = -1
            while True:
                chunk = sock.recv(1)
                if chunk == b"":
                    raise ConnectionError("Connection closed by device")
                cur = chunk[0]
                if prev == FRAME_END1 and cur == FRAME_END2:
                    # Remove the 0x0D that was already appended
                    data = data[:-1]
                    break
                data.append(cur)
                prev = cur

            _LOGGER.debug("Status packet (%d bytes): %s", len(data), data.hex(" "))
            return self._parse_data(data)

    @staticmethod
    def _parse_data(data: bytearray) -> dict[str, Any]:
        """Parse the binary status packet (16 bytes).

        Byte mapping:
          0-1:   chamber temperature (short, big-endian)
          2:     motor/valve actual position (%)
          3:     motor/valve target position (%, capped at 100)
          4:     operating state
          5:     error code
          6:     output flags
          7:     controller version
          8-9:   max chamber temperature (short, big-endian)
          10-11: firebed temperature (short, big-endian)
          12:    temperature trend
          13-14: oven identifier (short, big-endian)
          15:    firmware revision
        """
        if len(data) < 16:
            raise ValueError(f"Status packet too short: {len(data)} bytes")

        state_val = data[4]
        error_val = data[5]

        return {
            "chamber_temp": int.from_bytes(data[0:2], byteorder="big"),
            "motor_actual": data[2],
            "motor_target": min(data[3], 100),
            "state": STATE_MAP.get(state_val, "unknown"),
            "state_raw": state_val,
            "error": ERROR_MAP.get(error_val, "unknown"),
            "error_raw": error_val,
            "controller_version": data[7],
            "max_chamber_temp": int.from_bytes(data[8:10], byteorder="big"),
            "firebed_temp": int.from_bytes(data[10:12], byteorder="big"),
            "trend": data[12],
            "firmware_revision": data[15],
        }
