"""Tests for the device reader and the coordinator, against a fake LT3 server."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from unittest.mock import patch

import pytest

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.ledatroniclt3.coordinator import LedatronicCoordinator
from custom_components.ledatroniclt3.protocol import (
    LedatronicProtocolError,
    read_device,
)

# The fake device listens on loopback; the Home Assistant test plugin blocks
# sockets in every test unless the socket_enabled fixture is requested.
pytestmark = pytest.mark.usefixtures("socket_enabled")

STATUS = bytes.fromhex("007f02020000001e0269014b0a000013")
OPDATA = bytes.fromhex("f40a0e0b00c1")


def status_frame(temp: int = 127) -> bytes:
    """A complete status frame with the given chamber temperature."""
    payload = bytearray(STATUS)
    payload[0:2] = temp.to_bytes(2, "big")
    return b"\x0e\xff" + bytes(payload) + b"\x0d\xff"


def opdata_frame() -> bytes:
    """A complete operation-data frame."""
    return b"\x0c\xff\x56" + OPDATA + b"\x0d\xff"


@asynccontextmanager
async def fake_lt3(
    script: Callable[[asyncio.StreamWriter], AsyncIterator[bytes]] | bytes,
) -> AsyncIterator[tuple[str, int, list[int]]]:
    """Serve ``script`` (bytes or an async generator of chunks) on localhost.

    Yields (host, port, connections) where connections counts accepted clients.
    """
    connections: list[int] = []

    async def handle(
        reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        connections.append(1)
        try:
            if isinstance(script, bytes):
                writer.write(script)
                await writer.drain()
                # Keep streaming like the real module until the client leaves.
                while not reader.at_eof():
                    await asyncio.sleep(0.05)
                    if writer.is_closing():
                        break
                    writer.write(status_frame())
                    await writer.drain()
            else:
                async for chunk in script(writer):
                    writer.write(chunk)
                    await writer.drain()
        except (ConnectionError, asyncio.CancelledError):
            pass
        finally:
            writer.close()

    server = await asyncio.start_server(handle, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    try:
        yield "127.0.0.1", port, connections
    finally:
        server.close()
        await server.wait_closed()


async def test_read_status_and_opdata() -> None:
    """One status frame plus the operation data that follows it."""
    async with fake_lt3(status_frame(200) + opdata_frame()) as (host, port, _):
        data = await read_device(host, port)

    assert data["chamber_temp"] == 200
    assert data["burnoff_count"] == 3595
    assert data["fault_count"] == 193


async def test_full_cycle_with_expansion_modules() -> None:
    """A captured cycle: all four frames, and no wait for the next status."""
    cycle = bytes.fromhex(
        "0eff01ea69640400001e021700000a000008" "0dff"
        "0cff562a031524014d" "0dff"
        "0cff203c8d3f4d5f" "0dff"
        "0cff2180d000c8000001" "0dff"
    )
    async with fake_lt3(cycle) as (host, port, _):
        t0 = asyncio.get_running_loop().time()
        data = await read_device(host, port, opdata_timeout=2)
        elapsed = asyncio.get_running_loop().time() - t0

    assert data["chamber_temp"] == 490
    assert data["max_chamber_temp"] == 535
    assert data["burnoff_count"] == 5412
    assert data["fault_count"] == 333
    assert data["buffer_top"] == 63
    assert data["flow_temp"] == 77
    assert data["exhaust_temp"] == 200
    assert data["chimney_pressure"] == 20.8
    assert data["ventilation"] is True
    assert elapsed < 1


async def test_bad_reply_does_not_fail_the_poll() -> None:
    """A truncated optional frame is skipped, the status survives."""
    bad = b"\x0c\xff\x21\x80\x0d\xff"
    async with fake_lt3(status_frame(200) + bad + opdata_frame()) as (host, port, _):
        data = await read_device(host, port, opdata_timeout=0.2)

    assert data["chamber_temp"] == 200
    assert data["burnoff_count"] == 3595
    assert "chimney_pressure" not in data


async def test_opdata_buffered_before_status() -> None:
    """The module may replay last cycle's operation data first; it is used."""
    async with fake_lt3(opdata_frame() + status_frame(200)) as (host, port, _):
        t0 = asyncio.get_running_loop().time()
        data = await read_device(host, port, opdata_timeout=2)
        elapsed = asyncio.get_running_loop().time() - t0

    assert data["chamber_temp"] == 200
    assert data["burnoff_count"] == 3595
    assert elapsed < 1  # did not wait for a second operation-data frame


async def test_status_without_opdata() -> None:
    """Older firmware without operation data still yields a status."""
    async with fake_lt3(status_frame(200) + status_frame(201)) as (host, port, _):
        data = await read_device(host, port, opdata_timeout=0.2)

    assert data["chamber_temp"] == 200
    assert "burnoff_count" not in data


async def test_leading_junk_and_stray_marker_byte() -> None:
    """Junk and a stray 0x0e before the start marker must not eat the frame."""
    stream = b"\x00\x01\x0e" + status_frame(100) + status_frame(200)
    async with fake_lt3(stream) as (host, port, _):
        data = await read_device(host, port, opdata_timeout=0.2)

    assert data["chamber_temp"] == 100


async def test_terminator_inside_payload() -> None:
    """A payload containing 0d ff (3583 °C glitch) is read in full."""
    glitch = bytearray(STATUS)
    glitch[8:10] = (0x0DFF).to_bytes(2, "big")
    stream = b"\x0e\xff" + bytes(glitch) + b"\x0d\xff" + opdata_frame()
    async with fake_lt3(stream) as (host, port, _):
        data = await read_device(host, port)

    assert data["max_chamber_temp"] == 0x0DFF
    assert data["chamber_temp"] == 127


async def test_stream_without_frames_times_out() -> None:
    """A device that never sends a start marker ends with TimeoutError."""

    async def noise(_writer: asyncio.StreamWriter) -> AsyncIterator[bytes]:
        while True:
            yield b"\x00"
            await asyncio.sleep(0.01)

    async with fake_lt3(noise) as (host, port, _):
        with pytest.raises(TimeoutError):
            await read_device(host, port, timeout=0.3)


async def test_connection_closed_before_frame() -> None:
    """A device closing early is a connection error."""
    async with fake_lt3(lambda _w: _empty()) as (host, port, _):
        with pytest.raises(ConnectionError):
            await read_device(host, port, timeout=1)


async def _empty() -> AsyncIterator[bytes]:
    return
    yield b""  # pragma: no cover


async def test_short_status_frame_is_protocol_error() -> None:
    """A status frame that stays short is reported as protocol error."""
    short = b"\x0e\xff" + bytes(10) + b"\x0d\xff"

    async def once(_writer: asyncio.StreamWriter) -> AsyncIterator[bytes]:
        yield short
        await asyncio.sleep(0.05)

    async with fake_lt3(once) as (host, port, _):
        with pytest.raises((LedatronicProtocolError, ConnectionError)):
            await read_device(host, port, timeout=1)


async def test_fresh_connection_per_poll(hass: HomeAssistant) -> None:
    """Each poll opens and closes its own connection."""
    async with fake_lt3(status_frame() + opdata_frame()) as (host, port, connections):
        coordinator = LedatronicCoordinator(hass, None, host=host, port=port)
        await coordinator._async_update_data()
        await coordinator._async_update_data()

    assert len(connections) == 2


async def test_retry_succeeds_on_second_attempt(hass: HomeAssistant) -> None:
    """A transient error on the first attempt is retried once."""
    coordinator = LedatronicCoordinator(hass, None, host="127.0.0.1", port=1)
    calls = 0

    async def flaky(*_args, **_kwargs) -> dict:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise TimeoutError
        return {"chamber_temp": 1}

    with (
        patch("custom_components.ledatroniclt3.coordinator.read_device", flaky),
        patch("custom_components.ledatroniclt3.coordinator.asyncio.sleep"),
    ):
        result = await coordinator._async_update_data()

    assert result == {"chamber_temp": 1}
    assert calls == 2


async def test_connection_refused_raises_update_failed(hass: HomeAssistant) -> None:
    """Connection refused (e.g. the app holds the single slot) -> UpdateFailed."""
    async with fake_lt3(b"") as (host, port, _):
        pass  # server is gone now, port is free and refuses

    coordinator = LedatronicCoordinator(hass, None, host=host, port=port)
    with (
        patch("custom_components.ledatroniclt3.coordinator.asyncio.sleep"),
        pytest.raises(UpdateFailed, match="Error communicating"),
    ):
        await coordinator._async_update_data()
