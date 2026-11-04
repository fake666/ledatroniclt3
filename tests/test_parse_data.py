"""Tests for the binary protocol parser."""

import pytest

from custom_components.ledatroniclt3.protocol import (
    LedatronicProtocolError,
    parse_ks04,
    parse_luc,
    parse_operation_data,
    parse_status,
)


def _make_packet(**overrides) -> bytes:
    """Build a 16-byte status packet with optional field overrides.

    Byte layout (manufacturer's app, Status.kt):
      0-1:   chamber_temp (short, big-endian)
      2:     motor_actual
      3:     motor_target
      4:     state_raw
      5:     error_raw
      6:     output (bits 0-3 id, bit 7 on)
      7:     version
      8-9:   max_chamber_temp (short, big-endian)
      10-11: embers_threshold (short, big-endian)
      12:    minutes_without_rise
      13-14: temperature2 (short, big-endian)
      15:    oven_id
    """
    fields = {
        "chamber_temp": 0,
        "motor_actual": 0,
        "motor_target": 0,
        "state_raw": 0,
        "error_raw": 0,
        "output": 0,
        "version": 0,
        "max_chamber_temp": 0,
        "embers_threshold": 0,
        "minutes_without_rise": 0,
        "temperature2": 0,
        "oven_id": 0,
    }
    fields.update(overrides)

    data = bytearray(16)
    data[0:2] = fields["chamber_temp"].to_bytes(2, "big")
    data[2] = fields["motor_actual"]
    data[3] = fields["motor_target"]
    data[4] = fields["state_raw"]
    data[5] = fields["error_raw"]
    data[6] = fields["output"]
    data[7] = fields["version"]
    data[8:10] = fields["max_chamber_temp"].to_bytes(2, "big")
    data[10:12] = fields["embers_threshold"].to_bytes(2, "big")
    data[12] = fields["minutes_without_rise"]
    data[13:15] = fields["temperature2"].to_bytes(2, "big")
    data[15] = fields["oven_id"]
    return bytes(data)


class TestParseStatus:
    """Tests for parse_status."""

    def test_cold_stove_packet(self):
        """Packet captured from a cold stove in March."""
        data = bytes.fromhex("007f02020000001e0269014b0a000013")
        result = parse_status(data)

        assert result["chamber_temp"] == 127
        assert result["motor_actual"] == 2
        assert result["motor_target"] == 2
        assert result["state"] == "idle"
        assert result["error"] == "none"
        assert result["output"] == "none"
        assert result["output_on"] is False
        assert result["controller_version"] == 30
        assert result["max_chamber_temp"] == 617
        assert result["embers_threshold"] == 331
        assert result["minutes_without_rise"] == 10
        assert result["temperature2"] == 0
        assert result["oven_id"] == 19
        assert "firmware" not in result

    def test_burning_packet_from_log(self):
        """Packet logged on 2026-11-02 right after the switch to burning."""
        data = bytes.fromhex("02336060040000 1e 0257 0144 00 0000 13".replace(" ", ""))
        result = parse_status(data)

        assert result["chamber_temp"] == 563
        assert result["motor_actual"] == 96
        assert result["motor_target"] == 96
        assert result["state"] == "burning"
        assert result["state_raw"] == 4
        assert result["max_chamber_temp"] == 599
        assert result["embers_threshold"] == 324
        assert result["minutes_without_rise"] == 0

    def test_sensor_fault_packet_from_log(self):
        """Packet logged on 2026-10-18: thermocouple glitch, controller in state 99."""
        data = bytes.fromhex("01be6464630000 1e 05ae 0000 00 0000 13".replace(" ", ""))
        result = parse_status(data)

        assert result["state"] == "sensor_fault"
        assert result["state_raw"] == 99
        assert result["max_chamber_temp"] == 1454
        assert result["motor_target"] == 100

    def test_firmware_bytes_optional(self):
        """Newer modules append two firmware bytes."""
        result = parse_status(_make_packet(version=30) + bytes([1, 7]))
        assert result["firmware"] == "1.7"

    def test_motor_target_capped_at_100(self):
        """Target is capped at 100 % like the manufacturer's app does."""
        result = parse_status(_make_packet(motor_target=150))
        assert result["motor_target"] == 100

    @pytest.mark.parametrize(
        ("state_raw", "expected_state"),
        [
            (0, "idle"),
            (2, "heating_up"),
            (3, "burning"),
            (4, "burning"),
            (6, "starting"),
            (7, "embers"),
            (8, "embers"),
            (97, "fault"),
            (98, "door_open"),
            (99, "sensor_fault"),
            (1, "unknown"),
            (100, "unknown"),
            (255, "unknown"),
        ],
    )
    def test_state_mapping(self, state_raw, expected_state):
        """All known state values and unknown ones."""
        result = parse_status(_make_packet(state_raw=state_raw))
        assert result["state"] == expected_state
        assert result["state_raw"] == state_raw

    @pytest.mark.parametrize(
        ("error_raw", "expected_error"),
        [
            (0, "none"),
            (1, "overheating"),
            (2, "motor_fault"),
            (3, "motor_overheating"),
            (16, "critical_overheating"),
            (18, "critical_motor_overheating"),
            (32, "power_fault"),
            (5, "unknown"),
            (255, "unknown"),
        ],
    )
    def test_error_mapping(self, error_raw, expected_error):
        """All known error values and unknown ones."""
        result = parse_status(_make_packet(error_raw=error_raw))
        assert result["error"] == expected_error
        assert result["error_raw"] == error_raw

    @pytest.mark.parametrize(
        ("output", "expected", "on"),
        [
            (0x00, "none", False),
            (0x01, "evacuator", False),
            (0x82, "shutter", True),
            (0x84, "ventilation", True),
            (0x08, "fuel_gas_shutter", False),
            (0x05, "unknown", False),
        ],
    )
    def test_output_mapping(self, output, expected, on):
        """Switching output id in the low nibble, on/off in bit 7."""
        result = parse_status(_make_packet(output=output))
        assert result["output"] == expected
        assert result["output_on"] is on

    def test_max_two_byte_values(self):
        """Maximum 2-byte values (0xFFFF = 65535)."""
        result = parse_status(
            _make_packet(
                chamber_temp=65535, max_chamber_temp=65535, embers_threshold=65535
            )
        )
        assert result["chamber_temp"] == 65535
        assert result["max_chamber_temp"] == 65535
        assert result["embers_threshold"] == 65535

    def test_packet_too_short_raises(self):
        """A packet shorter than 16 bytes raises."""
        with pytest.raises(LedatronicProtocolError, match="too short"):
            parse_status(bytes(10))


class TestParseOperationData:
    """Tests for parse_operation_data."""

    def test_logged_frame(self):
        """Operation data logged on 2026-10-19."""
        result = parse_operation_data(bytes.fromhex("f40a0e0b00c1"))
        assert result["operating_hours_raw"] == 62474
        assert result["burnoff_count"] == 3595
        assert result["fault_count"] == 193

    def test_too_short_raises(self):
        """Fewer than three shorts is garbage."""
        with pytest.raises(LedatronicProtocolError, match="too short"):
            parse_operation_data(bytes(5))


class TestParseExpansionModules:
    """Tests for the KS04 and LUC frames, from a capture of a burning stove."""

    def test_ks04_capture(self):
        """Frame captured on 2026-11-04, values confirmed in the app."""
        result = parse_ks04(bytes.fromhex("3c8d3f4d5f"))
        assert result == {
            "buffer_bottom": 60,
            "buffer_middle": 141,
            "buffer_top": 63,
            "flow_temp": 77,
            "pump_speed": 95,
        }

    def test_luc_capture(self):
        """Frame captured on 2026-11-04, ventilation on in the app."""
        result = parse_luc(bytes.fromhex("80d000c8000001"))
        assert result["chimney_pressure"] == 20.8
        assert result["exhaust_temp"] == 200
        assert result["ventilation"] is True
        assert result["lock"] is False
        assert result["alarm_counter"] == 0
        assert result["error_relay"] is False

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("80d0", 20.8),
            ("00d0", -20.8),
            ("8100", 25.6),
            ("87ff", 204.7),
            ("8000", 0.0),
            ("0000", 0.0),
        ],
    )
    def test_luc_pressure(self, raw, expected):
        """Bit 15 is the sign, bits 0-10 the magnitude in 0.1 Pa."""
        result = parse_luc(bytes.fromhex(raw + "00c8000000"))
        assert result["chimney_pressure"] == expected
        assert str(result["chimney_pressure"]) != "-0.0"

    def test_luc_flags(self):
        """Lock in bit 15, alarm counter in bits 7-14, errors in bits 0-3."""
        result = parse_luc(bytes.fromhex("000000008185" + "00"))
        assert result["lock"] is True
        assert result["alarm_counter"] == 3
        assert result["error_offset"] is True
        assert result["error_pressure"] is False
        assert result["error_exhaust"] is True
        assert result["error_relay"] is False
        assert result["ventilation"] is False

    @pytest.mark.parametrize(("parser", "length"), [(parse_ks04, 4), (parse_luc, 6)])
    def test_too_short_raises(self, parser, length):
        """Truncated frames are garbage."""
        with pytest.raises(LedatronicProtocolError, match="too short"):
            parser(bytes(length))
