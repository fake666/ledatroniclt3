"""Tests for the Ledatronic LT3 coordinator."""

from unittest.mock import MagicMock, patch

import pytest

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.ledatroniclt3.coordinator import LedatronicCoordinator
from tests.conftest import MOCK_DATA, MOCK_HOST, MOCK_PORT


def _make_coordinator(hass: HomeAssistant) -> LedatronicCoordinator:
    return LedatronicCoordinator(hass, host=MOCK_HOST, port=MOCK_PORT)


async def test_persistent_connection_reused(hass: HomeAssistant) -> None:
    """Test that the socket is created once and reused across polls."""
    coordinator = _make_coordinator(hass)

    with patch.object(coordinator, "_connect") as mock_connect:
        mock_sock = MagicMock()
        mock_connect.return_value = mock_sock

        with patch.object(coordinator, "_parse_data", return_value=MOCK_DATA):
            # Simulate a valid frame on each recv call
            frame = _build_frame()
            mock_sock.recv.side_effect = _recv_side_effect(frame)

            await coordinator._async_update_data()

            mock_sock.recv.side_effect = _recv_side_effect(frame)
            await coordinator._async_update_data()

    assert mock_connect.call_count == 1


async def test_reconnect_after_error(hass: HomeAssistant) -> None:
    """Test that a broken connection is closed and rebuilt on next poll."""
    coordinator = _make_coordinator(hass)

    mock_sock1 = MagicMock()
    mock_sock2 = MagicMock()

    with patch.object(
        coordinator, "_connect", side_effect=[mock_sock1, mock_sock2, mock_sock2]
    ) as mock_connect, patch.object(
        coordinator, "_parse_data", return_value=MOCK_DATA
    ):
        # First call: socket dies immediately
        mock_sock1.recv.side_effect = ConnectionError("Connection closed by device")

        # Second call (retry): works
        frame = _build_frame()
        mock_sock2.recv.side_effect = _recv_side_effect(frame)

        result = await coordinator._async_update_data()

    assert result == MOCK_DATA
    # First socket was closed after error
    mock_sock1.close.assert_called_once()
    # Needed 2 connects: original + reconnect
    assert mock_connect.call_count == 2


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


async def test_disconnect_on_each_retry(hass: HomeAssistant) -> None:
    """Test that the socket is disconnected between retry attempts."""
    coordinator = _make_coordinator(hass)
    coordinator._sock = MagicMock()

    with patch.object(
        coordinator, "_fetch_data", side_effect=OSError("fail")
    ), patch(
        "custom_components.ledatroniclt3.coordinator.asyncio.sleep"
    ), patch.object(
        coordinator, "_disconnect"
    ) as mock_disconnect, pytest.raises(
        UpdateFailed
    ):
        await coordinator._async_update_data()

    assert mock_disconnect.call_count == 3


async def test_shutdown_closes_socket(hass: HomeAssistant) -> None:
    """Test that async_shutdown closes the socket."""
    coordinator = _make_coordinator(hass)
    mock_sock = MagicMock()
    coordinator._sock = mock_sock

    await coordinator.async_shutdown()

    mock_sock.close.assert_called_once()
    assert coordinator._sock is None


async def test_disconnect_ignores_close_error(hass: HomeAssistant) -> None:
    """Test that _disconnect swallows OSError from close."""
    coordinator = _make_coordinator(hass)
    mock_sock = MagicMock()
    mock_sock.close.side_effect = OSError("already closed")
    coordinator._sock = mock_sock

    coordinator._disconnect()

    assert coordinator._sock is None


async def test_disconnect_noop_without_socket(hass: HomeAssistant) -> None:
    """Test that _disconnect is a no-op when no socket exists."""
    coordinator = _make_coordinator(hass)
    assert coordinator._sock is None
    coordinator._disconnect()
    assert coordinator._sock is None


def _build_frame() -> bytes:
    """Build a minimal valid 16-byte status frame with start/end markers."""
    payload = bytes(16)
    return bytes([0x0E, 0xFF]) + payload + bytes([0x0D, 0xFF])


def _recv_side_effect(frame: bytes):
    """Create a side_effect list that yields the frame byte by byte."""
    return [bytes([b]) for b in frame]
