"""DataUpdateCoordinator for the Ledatronic LT3 integration."""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN
from .protocol import LedatronicProtocolError, parse_status, read_device

_LOGGER = logging.getLogger(__name__)

UPDATE_INTERVAL = timedelta(seconds=30)
SOCKET_TIMEOUT = 10
# Two attempts fit into one update interval (2 x 10 s + 2 s < 30 s).
MAX_ATTEMPTS = 2
RETRY_DELAY = 2


class LedatronicCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator to fetch data from a Ledatronic LT3 device."""

    # Kept for callers that parse captured frames by hand.
    _parse_data = staticmethod(parse_status)

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry | None,
        host: str,
        port: int,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )
        self.host = host
        self.port = port

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch one status frame, retrying once on transient errors.

        The module accepts a single TCP client: while the manufacturer's app
        is connected every attempt is refused and the entities go unavailable
        until the app disconnects.
        """
        last_err: Exception | None = None
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                data = await read_device(self.host, self.port, timeout=SOCKET_TIMEOUT)
            except (OSError, TimeoutError, LedatronicProtocolError) as err:
                last_err = err
                if attempt < MAX_ATTEMPTS:
                    _LOGGER.debug(
                        "Attempt %d/%d failed: %s - retrying in %ds",
                        attempt,
                        MAX_ATTEMPTS,
                        err,
                        RETRY_DELAY,
                    )
                    await asyncio.sleep(RETRY_DELAY)
            else:
                _LOGGER.debug("Status: %s", data)
                return data
        raise UpdateFailed(f"Error communicating with device: {last_err}") from last_err
