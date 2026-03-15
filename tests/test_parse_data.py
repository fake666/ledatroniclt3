"""Tests for the binary protocol parser."""

import pytest

from custom_components.ledatroniclt3.coordinator import LedatronicCoordinator


def _make_packet(**overrides) -> bytearray:
    """Build a 56-byte status packet with optional field overrides."""
    data = bytearray(56)

    fields = {
        "current_temp": 0,
        "valve_target": 0,
        "valve_actual": 0,
        "state_raw": 0,
        "max_temp": 0,
        "grundglut": 0,
        "trend": 0,
        "abbrande": 0,
        "heizfehler": 0,
        "puffer_unten": 0,
        "puffer_oben": 0,
        "vorlauf_temp": 0,
        "schorn_temp": 0,
        "fan_raw": 0,
    }
    fields.update(overrides)

    data[0:2] = fields["current_temp"].to_bytes(2, "big")
    data[2] = fields["valve_target"]
    data[3] = fields["valve_actual"]
    data[4] = fields["state_raw"]
    data[8:10] = fields["max_temp"].to_bytes(2, "big")
    data[11] = fields["grundglut"]
    data[12] = fields["trend"]
    data[25:27] = fields["abbrande"].to_bytes(2, "big")
    data[27:29] = fields["heizfehler"].to_bytes(2, "big")
    data[34] = fields["puffer_unten"]
    data[36] = fields["puffer_oben"]
    data[37] = fields["vorlauf_temp"]
    data[46:48] = fields["schorn_temp"].to_bytes(2, "big")
    data[50] = fields["fan_raw"]

    return data


class TestParseData:
    """Tests for LedatronicCoordinator._parse_data."""

    def test_typical_heating_operation(self):
        """Test parsing a typical packet during active heating."""
        data = _make_packet(
            current_temp=185,
            valve_target=80,
            valve_actual=78,
            state_raw=3,
            max_temp=250,
            grundglut=60,
            trend=1,
            abbrande=42,
            heizfehler=0,
            puffer_unten=45,
            puffer_oben=65,
            vorlauf_temp=55,
            schorn_temp=130,
            fan_raw=1,
        )

        result = LedatronicCoordinator._parse_data(data)

        assert result["current_temp"] == 185
        assert result["valve_target"] == 80
        assert result["valve_actual"] == 78
        assert result["state"] == "heizbetrieb"
        assert result["state_raw"] == 3
        assert result["max_temp"] == 250
        assert result["grundglut"] == 60
        assert result["trend"] == 1
        assert result["abbrande"] == 42
        assert result["heizfehler"] == 0
        assert result["puffer_unten"] == 45
        assert result["puffer_oben"] == 65
        assert result["vorlauf_temp"] == 55
        assert result["schorn_temp"] == 130
        assert result["ventilator"] == "on"

    def test_all_zeros(self):
        """Test parsing a packet with all zeros (idle/cold stove)."""
        data = _make_packet()
        result = LedatronicCoordinator._parse_data(data)

        assert result["current_temp"] == 0
        assert result["state"] == "bereit"
        assert result["ventilator"] == "off"

    @pytest.mark.parametrize(
        ("state_raw", "expected_state"),
        [
            (0, "bereit"),
            (2, "anheizen"),
            (3, "heizbetrieb"),
            (4, "heizbetrieb"),
            (7, "grundglut"),
            (8, "grundglut"),
            (97, "heizfehler"),
            (98, "tuer_offen"),
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
        ("fan_raw", "expected"),
        [
            (0, "off"),
            (1, "on"),
            (2, "unknown"),
            (255, "unknown"),
        ],
    )
    def test_fan_states(self, fan_raw, expected):
        """Test fan state interpretation."""
        data = _make_packet(fan_raw=fan_raw)
        result = LedatronicCoordinator._parse_data(data)
        assert result["ventilator"] == expected

    def test_two_byte_values_high_byte(self):
        """Test that 2-byte fields correctly handle the high byte."""
        data = _make_packet(
            current_temp=512,
            max_temp=1000,
            abbrande=300,
            heizfehler=256,
            schorn_temp=500,
        )
        result = LedatronicCoordinator._parse_data(data)

        assert result["current_temp"] == 512
        assert result["max_temp"] == 1000
        assert result["abbrande"] == 300
        assert result["heizfehler"] == 256
        assert result["schorn_temp"] == 500

    def test_max_two_byte_values(self):
        """Test maximum 2-byte values (0xFFFF = 65535)."""
        data = _make_packet(
            current_temp=65535,
            max_temp=65535,
            schorn_temp=65535,
        )
        result = LedatronicCoordinator._parse_data(data)

        assert result["current_temp"] == 65535
        assert result["max_temp"] == 65535
        assert result["schorn_temp"] == 65535

    def test_single_byte_max_values(self):
        """Test single-byte fields with max value 255."""
        data = _make_packet(
            valve_target=255,
            valve_actual=255,
            grundglut=255,
            trend=255,
            puffer_unten=255,
            puffer_oben=255,
            vorlauf_temp=255,
        )
        result = LedatronicCoordinator._parse_data(data)

        assert result["valve_target"] == 255
        assert result["valve_actual"] == 255
        assert result["grundglut"] == 255
        assert result["puffer_unten"] == 255
        assert result["puffer_oben"] == 255
        assert result["vorlauf_temp"] == 255
