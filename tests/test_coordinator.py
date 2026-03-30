"""Tests for the Ledatronic LT3 coordinator."""

from unittest.mock import MagicMock, patch

import pytest

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.ledatroniclt3.coordinator import LedatronicCoordinator
from tests.conftest import MOCK_DATA, MOCK_HOST, MOCK_PORT


def _make_coordinator(hass: HomeAssistant) -> LedatronicCoordinator:
    return LedatronicCoordinator(hass, host=MOCK_HOST, port=MOCK_PORT)


def _build_frame() -> bytes:
    """Build a minimal valid 16-byte status frame with start/end markers."""
    payload = bytes(16)
    return bytes([0x0E, 0xFF]) + payload + bytes([0x0D, 0xFF])


def _recv_side_effect(frame: bytes):
    """Create a side_effect list that yields the frame byte by byte."""
    return [bytes([b]) for b in frame]


async def test_fresh_connection_per_poll(hass: HomeAssistant) -> None:
    """Test that each poll opens and closes its own connection."""
    coordinator = _make_coordinator(hass)

    frame = _build_frame()
    mock_sock = MagicMock()

    with patch("custom_components.ledatroniclt3.coordinator.socket.socket") as mock_cls, \
         patch.object(coordinator, "_parse_data", return_value=MOCK_DATA):
        mock_cls.return_value = mock_sock

        # First poll
        mock_sock.recv.side_effect = _recv_side_effect(frame)
        await coordinator._async_update_data()
        assert mock_cls.call_count == 1
        assert mock_sock.close.call_count == 1

        # Second poll – new socket
        mock_sock.recv.side_effect = _recv_side_effect(frame)
        await coordinator._async_update_data()
        assert mock_cls.call_count == 2
        assert mock_sock.close.call_count == 2


async def test_socket_closed_on_error(hass: HomeAssistant) -> None:
    """Test that the socket is closed even when recv raises."""
    coordinator = _make_coordinator(hass)
    mock_sock = MagicMock()
    mock_sock.recv.side_effect = ConnectionError("gone")

    with patch("custom_components.ledatroniclt3.coordinator.socket.socket") as mock_cls, \
         patch("custom_components.ledatroniclt3.coordinator.asyncio.sleep"), \
         pytest.raises(UpdateFailed):
        mock_cls.return_value = mock_sock
        await coordinator._async_update_data()

    # Socket closed once per attempt (3 retries)
    assert mock_sock.close.call_count == 3


async def test_retry_succeeds_on_second_attempt(hass: HomeAssistant) -> None:
    """Test that a transient error on first attempt is retried successfully."""
    coordinator = _make_coordinator(hass)

    call_count = 0

    def _fetch_with_transient_error() -> dict:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise TimeoutError("socket timed out")
        return MOCK_DATA

    with patch.object(
        coordinator, "_fetch_data", side_effect=_fetch_with_transient_error
    ), patch("custom_components.ledatroniclt3.coordinator.asyncio.sleep"):
        result = await coordinator._async_update_data()

    assert result == MOCK_DATA
    assert call_count == 2


async def test_all_retries_exhausted_raises_update_failed(
    hass: HomeAssistant,
) -> None:
    """Test that UpdateFailed is raised after all retries fail."""
    coordinator = _make_coordinator(hass)

    with patch.object(
        coordinator, "_fetch_data", side_effect=OSError("connection refused")
    ), patch(
        "custom_components.ledatroniclt3.coordinator.asyncio.sleep"
    ), pytest.raises(
        UpdateFailed, match="connection refused"
    ):
        await coordinator._async_update_data()


async def test_connection_closed_by_device(hass: HomeAssistant) -> None:
    """Test that empty recv (device closed connection) raises ConnectionError."""
    coordinator = _make_coordinator(hass)
    mock_sock = MagicMock()
    mock_sock.recv.return_value = b""

    with patch("custom_components.ledatroniclt3.coordinator.socket.socket") as mock_cls, \
         patch("custom_components.ledatroniclt3.coordinator.asyncio.sleep"), \
         pytest.raises(UpdateFailed):
        mock_cls.return_value = mock_sock
        await coordinator._async_update_data()
