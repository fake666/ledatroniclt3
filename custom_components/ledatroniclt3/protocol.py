"""Wire protocol of the LEDATRONIC LT3 WiFi module.

The module (a Lantronix xPico serial tunnel on TCP port 10001) accepts a single
client and streams frames continuously, roughly every 4 s:

    0e ff <status payload, 16 or 18 bytes> 0d ff
    0c ff 56 <operation data, 6 bytes>     0d ff

The byte layout follows the manufacturer's Android app (Status.kt), verified
against logged burn-offs. Everything in here is plain asyncio so it can be used
and tested without Home Assistant.
"""

from __future__ import annotations

import asyncio
import contextlib
from typing import Any

FRAME_END = b"\x0d\xff"
STATUS_START = b"\x0e\xff"
COMMAND_START = b"\x0c\xff"
OPERATION_DATA = 0x56

STATUS_MIN_LENGTH = 16

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
    # Not in the manufacturer's app. Observed whenever the controller sees a
    # chamber temperature spike above ~1100 °C (loose thermocouple contact):
    # valve pinned at 100 %, burn-off not counted, persists until the door is
    # opened or the controller is power-cycled.
    99: "sensor_fault",
}

ERROR_MAP: dict[int, str] = {
    0: "none",
    1: "overheating",
    2: "motor_fault",
    3: "motor_overheating",
    16: "critical_overheating",
    18: "critical_motor_overheating",
    32: "power_fault",
}

OUTPUT_MAP: dict[int, str] = {
    0: "none",
    1: "evacuator",
    2: "shutter",
    4: "ventilation",
    8: "fuel_gas_shutter",
}


class LedatronicProtocolError(ValueError):
    """The device sent something that is not a status frame."""


def parse_status(data: bytes) -> dict[str, Any]:
    """Parse the status payload (between ``0e ff`` and ``0d ff``).

    Byte mapping:
      0-1:   chamber temperature (°C, big-endian)
      2:     air valve actual position (%)
      3:     air valve target position (%, capped at 100)
      4:     operating state
      5:     error code
      6:     switching output: bits 0-3 output id, bit 7 on/off
      7:     controller version
      8-9:   peak chamber temperature of the current burn-off (°C)
      10-11: embers threshold (°C): temperature at which the controller
             switches to "embers"; ~0.54 x peak, 0 before the burn phase
      12:    minutes without temperature rise (0-10)
      13-14: second temperature input (unused on a plain LT3)
      15:    oven type id
      16-17: firmware revision (only sent by newer modules)
    """
    if len(data) < STATUS_MIN_LENGTH:
        raise LedatronicProtocolError(f"Status packet too short: {len(data)} bytes")

    state_val = data[4]
    error_val = data[5]
    output = data[6]

    result: dict[str, Any] = {
        "chamber_temp": int.from_bytes(data[0:2], byteorder="big"),
        "motor_actual": data[2],
        "motor_target": min(data[3], 100),
        "state": STATE_MAP.get(state_val, "unknown"),
        "state_raw": state_val,
        "error": ERROR_MAP.get(error_val, "unknown"),
        "error_raw": error_val,
        "output": OUTPUT_MAP.get(output & 0x0F, "unknown"),
        "output_on": bool(output & 0x80),
        "controller_version": data[7],
        "max_chamber_temp": int.from_bytes(data[8:10], byteorder="big"),
        "embers_threshold": int.from_bytes(data[10:12], byteorder="big"),
        "minutes_without_rise": data[12],
        "temperature2": int.from_bytes(data[13:15], byteorder="big"),
        "oven_id": data[15],
    }
    if len(data) >= 18:
        result["firmware"] = f"{data[16]}.{data[17]}"
    return result


def parse_operation_data(data: bytes) -> dict[str, Any]:
    """Parse the payload of an OPERATION_DATA frame (after ``0c ff 56``).

    Three big-endian shorts: operating hours (unit unverified), number of
    burn-offs, number of heating faults.
    """
    if len(data) < 6:
        raise LedatronicProtocolError(
            f"Operation data packet too short: {len(data)} bytes"
        )
    return {
        "operating_hours_raw": int.from_bytes(data[0:2], byteorder="big"),
        "burnoff_count": int.from_bytes(data[2:4], byteorder="big"),
        "fault_count": int.from_bytes(data[4:6], byteorder="big"),
    }


async def _read_chunk(reader: asyncio.StreamReader) -> bytes:
    """Read up to and excluding the next ``0d ff``."""
    try:
        chunk = await reader.readuntil(FRAME_END)
    except asyncio.IncompleteReadError as err:
        raise ConnectionError("Connection closed by device") from err
    except asyncio.LimitOverrunError as err:
        raise LedatronicProtocolError("No frame terminator in stream") from err
    return chunk[: -len(FRAME_END)]


def _split_frame(body: bytes) -> tuple[int, bytes] | None:
    """Return (kind, payload) for the last frame start in ``body``, else None.

    ``kind`` is the first marker byte (0x0e status, 0x0c command reply).
    The last marker wins: a stray 0x0e directly before ``0e ff`` must not
    swallow the frame (the previous byte-wise scanner had that bug).
    """
    pos = max(body.rfind(STATUS_START), body.rfind(COMMAND_START))
    if pos < 0:
        return None
    return body[pos], bytes(body[pos + 2 :])


async def _read_frame(reader: asyncio.StreamReader) -> tuple[int, bytes] | None:
    """Read the next complete frame.

    A status payload may itself contain the byte pair ``0d ff`` (a temperature
    of 3583 °C: only ever seen as a thermocouple glitch). A status frame that
    comes up short is therefore extended with the following chunk, unless that
    chunk starts a new frame.
    """
    frame = _split_frame(await _read_chunk(reader))
    if frame is None:
        return None
    kind, payload = frame
    while kind == STATUS_START[0] and len(payload) < STATUS_MIN_LENGTH:
        more = await _read_chunk(reader)
        if (next_frame := _split_frame(more)) is not None:
            kind, payload = next_frame
            continue
        payload += FRAME_END + more
    return kind, payload


async def read_device(
    host: str,
    port: int,
    timeout: float = 10.0,  # noqa: ASYNC109 - the deadline is part of the contract
    opdata_timeout: float = 5.0,
) -> dict[str, Any]:
    """Connect, read one status frame (plus operation data if it follows), disconnect.

    A fresh connection per poll keeps the single-client module free for the
    manufacturer's app between polls and avoids stale frames in the TCP buffer.
    Raises OSError/TimeoutError on connection problems and
    LedatronicProtocolError on garbage.
    """
    async with asyncio.timeout(timeout):
        reader, writer = await asyncio.open_connection(host, port)
        try:
            status: dict[str, Any] | None = None
            opdata: dict[str, Any] | None = None
            while status is None:
                frame = await _read_frame(reader)
                if frame is None:
                    continue
                kind, payload = frame
                if kind == STATUS_START[0]:
                    status = parse_status(payload)
                elif _is_opdata(kind, payload):
                    # The module buffers the last frame sent; that may be the
                    # operation data of the previous cycle, which is as good.
                    opdata = parse_operation_data(payload[1:])

            # The OPERATION_DATA frame normally arrives right behind the
            # status frame. Older firmware may not send it: do not insist.
            if opdata is None:
                try:
                    async with asyncio.timeout(opdata_timeout):
                        frame = await _read_frame(reader)
                except (TimeoutError, OSError, LedatronicProtocolError):
                    frame = None
                if frame is not None and _is_opdata(*frame):
                    opdata = parse_operation_data(frame[1][1:])
            if opdata is not None:
                status.update(opdata)
            return status
        finally:
            writer.close()
            with contextlib.suppress(OSError):
                await writer.wait_closed()


def _is_opdata(kind: int, payload: bytes) -> bool:
    """True for a command reply carrying OPERATION_DATA."""
    return kind == COMMAND_START[0] and payload[:1] == bytes([OPERATION_DATA])
