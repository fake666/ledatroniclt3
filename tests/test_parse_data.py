"""Tests for the binary protocol parser."""

import pytest

from custom_components.ledatroniclt3.coordinator import LedatronicCoordinator


def _make_packet(**overrides) -> bytearray:
    """Build a 16-byte status packet with optional field overrides.

    Byte layout (from decompiled Android app):
      0-1:   chamber_temp (short, big-endian)
      2:     motor_actual
      3:     motor_target
      4:     state_raw
      5:     error_raw
      6:     output
      7:     version
      8-9:   max_chamber_temp (short, big-endian)
      10-11: firebed_temp (short, big-endian)
      12:    trend
      13-14: oven (short, big-endian)
      15:    firmware2
    """
    data = bytearray(16)

    fields = {
        "chamber_temp": 0,
        "motor_actual": 0,
        "motor_target": 0,
        "state_raw": 0,
        "error_raw": 0,
        "output": 0,
        "version": 0,
        "max_chamber_temp": 0,
        "firebed_temp": 0,
        "trend": 0,
        "oven": 0,
        "firmware2": 0,
    }
    fields.update(overrides)

    data[0:2] = fields["chamber_temp"].to_bytes(2, "big")
    data[2] = fields["motor_actual"]
    data[3] = fields["motor_target"]
    data[4] = fields["state_raw"]
    data[5] = fields["error_raw"]
    data[6] = fields["output"]
    data[7] = fields["version"]
    data[8:10] = fields["max_chamber_temp"].to_bytes(2, "big")
    data[10:12] = fields["firebed_temp"].to_bytes(2, "big")
    data[12] = fields["trend"]
    data[13:15] = fields["oven"].to_bytes(2, "big")
    data[15] = fields["firmware2"]

    return data


class TestParseData:
    """Tests for LedatronicCoordinator._parse_data."""

    def test_real_device_packet(self):
        """Test parsing the actual packet captured from the device."""
        data = bytearray.fromhex("007f02020000001e0269014b0a000013")
        result = LedatronicCoordinator._parse_data(data)

        assert result["chamber_temp"] == 127
        assert result["motor_actual"] == 2
        assert result["motor_target"] == 2
        assert result["state"] == "idle"
        assert result["error"] == "none"
        assert result["controller_version"] == 30
        assert result["max_chamber_temp"] == 617
        assert result["firebed_temp"] == 331
        assert result["trend"] == 10
        assert result["firmware_revision"] == 19

    def test_typical_heating_operation(self):
        """Test parsing a packet during active heating."""
        data = _make_packet(
            chamber_temp=450,
            motor_actual=78,
            motor_target=80,
            state_raw=3,
            error_raw=0,
            max_chamber_temp=617,
            firebed_temp=380,
            trend=1,
        )

        result = LedatronicCoordinator._parse_data(data)

        assert result["chamber_temp"] == 450
        assert result["motor_actual"] == 78
        assert result["motor_target"] == 80
        assert result["state"] == "burning"
        assert result["error"] == "none"
        assert result["max_chamber_temp"] == 617
        assert result["firebed_temp"] == 380
        assert result["trend"] == 1

    def test_all_zeros(self):
        """Test parsing a packet with all zeros (cold stove)."""
        data = _make_packet()
        result = LedatronicCoordinator._parse_data(data)

        assert result["chamber_temp"] == 0
        assert result["state"] == "idle"
        assert result["error"] == "none"

    def test_motor_target_capped_at_100(self):
        """Test that motorTarget is capped at 100%."""
        data = _make_packet(motor_target=150)
        result = LedatronicCoordinator._parse_data(data)
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
            (1, "unknown"),
            (99, "unknown"),
            (255, "unknown"),
        ],
    )
    def test_state_mapping(self, state_raw, expected_state):
        """Test all known state values and unknown ones."""
        data = _make_packet(state_raw=state_raw)
        result = LedatronicCoordinator._parse_data(data)
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
        """Test all known error values and unknown ones."""
        data = _make_packet(error_raw=error_raw)
        result = LedatronicCoordinator._parse_data(data)
        assert result["error"] == expected_error
        assert result["error_raw"] == error_raw

    def test_two_byte_values(self):
        """Test that 2-byte fields correctly handle the high byte."""
        data = _make_packet(
            chamber_temp=512,
            max_chamber_temp=1000,
            firebed_temp=500,
        )
        result = LedatronicCoordinator._parse_data(data)

        assert result["chamber_temp"] == 512
        assert result["max_chamber_temp"] == 1000
        assert result["firebed_temp"] == 500

    def test_max_two_byte_values(self):
        """Test maximum 2-byte values (0xFFFF = 65535)."""
        data = _make_packet(
            chamber_temp=65535,
            max_chamber_temp=65535,
            firebed_temp=65535,
        )
        result = LedatronicCoordinator._parse_data(data)

        assert result["chamber_temp"] == 65535
        assert result["max_chamber_temp"] == 65535
        assert result["firebed_temp"] == 65535

    def test_version_fields(self):
        """Test that controller version and firmware revision are extracted."""
        data = _make_packet(version=30, firmware2=19)
        result = LedatronicCoordinator._parse_data(data)
        assert result["controller_version"] == 30
        assert result["firmware_revision"] == 19

    def test_packet_too_short_raises(self):
        """Test that a packet shorter than 16 bytes raises ValueError."""
        data = bytearray(10)
        with pytest.raises(ValueError, match="too short"):
            LedatronicCoordinator._parse_data(data)
