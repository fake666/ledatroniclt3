"""Wire protocol of the LEDATRONIC LT3 WiFi module.

The module (a Lantronix xPico serial tunnel on TCP port 10001) accepts a single
client and streams frames continuously, every 1-4 s depending on the module:

    0e ff <status payload, 16 or 18 bytes> 0d ff
    0c ff 56 <operation data, 6 bytes>     0d ff
    0c ff 20 <KS04 data, 5 bytes>          0d ff  (only with a KS04 station)
    0c ff 21 <LUC data, 7 bytes>           0d ff  (only with a LUC module)

The byte layout follows the manufacturer's Android app (Status.kt), verified
against logged burn-offs. Everything in here is plain asyncio so it can be used
and tested without Home Assistant.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import Callable
from typing import Any

_LOGGER = logging.getLogger(__name__)

FRAME_END = b"\x0d\xff"
STATUS_START = b"\x0e\xff"
COMMAND_START = b"\x0c\xff"
OPERATION_DATA = 0x56
KS04 = 0x20
LUC = 0x21

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


def parse_ks04(data: bytes) -> dict[str, Any]:
    """Parse the payload of a KS04 frame (after ``0c ff 20``).

    One byte each: buffer bottom, middle and top (°C), flow temperature (°C),
    pump speed (%). A value is passed on as sent: the manufacturer's app does
    not filter it either, so a broken probe shows up as a constant reading.
    """
    if len(data) < 5:
        raise LedatronicProtocolError(f"KS04 packet too short: {len(data)} bytes")
    return {
        "buffer_bottom": data[0],
        "buffer_middle": data[1],
        "buffer_top": data[2],
        "flow_temp": data[3],
        "pump_speed": data[4],
    }


def parse_luc(data: bytes) -> dict[str, Any]:
    """Parse the payload of a LUC frame (after ``0c ff 21``).

    Byte mapping:
      0-1: chimney pressure: bits 0-10 in 0.1 Pa, bit 15 set = positive
      2-3: exhaust temperature (°C, signed)
      4-5: flags: bit 0 offset, bit 1 pressure, bit 2 exhaust and bit 3 relay
           error, bits 7-14 alarm counter, bit 15 lock
      6:   ventilation (> 0 = on)
    """
    if len(data) < 7:
        raise LedatronicProtocolError(f"LUC packet too short: {len(data)} bytes")
    raw_pressure = int.from_bytes(data[0:2], byteorder="big")
    pressure = (raw_pressure & 0x07FF) / 10
    if pressure and not raw_pressure & 0x8000:
        pressure = -pressure
    flags = int.from_bytes(data[4:6], byteorder="big")
    return {
        "chimney_pressure": pressure,
        "exhaust_temp": int.from_bytes(data[2:4], byteorder="big", signed=True),
        "ventilation": data[6] > 0,
        "lock": bool(flags & 0x8000),
        "alarm_counter": (flags & 0x7F80) >> 7,
        "error_offset": bool(flags & 0x01),
        "error_pressure": bool(flags & 0x02),
        "error_exhaust": bool(flags & 0x04),
        "error_relay": bool(flags & 0x08),
    }


REPLY_PARSERS: dict[int, Callable[[bytes], dict[str, Any]]] = {
    OPERATION_DATA: parse_operation_data,
    KS04: parse_ks04,
    LUC: parse_luc,
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
    """Connect, read one status frame plus the rest of its cycle, disconnect.

    The cycle ends when every known reply has been seen or the next status
    frame arrives, so a stove without expansion modules is not held up.

    A fresh connection per poll keeps the single-client module free for the
    manufacturer's app between polls and avoids stale frames in the TCP buffer.
    Raises OSError/TimeoutError on connection problems and
    LedatronicProtocolError on a bad status frame. Replies are optional: a bad
    one is skipped.
    """
    async with asyncio.timeout(timeout):
        reader, writer = await asyncio.open_connection(host, port)
        try:
            status: dict[str, Any] | None = None
            replies: dict[int, dict[str, Any]] = {}
            while status is None:
                frame = await _read_frame(reader)
                if frame is None:
                    continue
                kind, payload = frame
                if kind == STATUS_START[0]:
                    status = parse_status(payload)
                else:
                    # The module buffers the last frame sent; that may be a
                    # reply of the previous cycle, which is as good.
                    _collect_reply(payload, replies)

            # The replies normally arrive right behind the status frame. Older
            # firmware may not send them: do not insist.
            with contextlib.suppress(TimeoutError, OSError, LedatronicProtocolError):
                async with asyncio.timeout(opdata_timeout):
                    while len(replies) < len(REPLY_PARSERS):
                        frame = await _read_frame(reader)
                        if frame is None:
                            continue
                        if frame[0] == STATUS_START[0]:
                            break
                        _collect_reply(frame[1], replies)
            for reply in replies.values():
                status.update(reply)
            return status
        finally:
            writer.close()
            with contextlib.suppress(OSError):
                await writer.wait_closed()


def _collect_reply(payload: bytes, replies: dict[int, dict[str, Any]]) -> None:
    """Parse a command reply into ``replies``; skip unknown and bad ones."""
    parser = REPLY_PARSERS.get(payload[0]) if payload else None
    if parser is None:
        return
    try:
        replies[payload[0]] = parser(payload[1:])
    except LedatronicProtocolError as err:
        _LOGGER.debug("Skipping reply 0x%02x: %s", payload[0], err)
