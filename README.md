# Ledatronic LT3

Custom integration for [Home Assistant](https://www.home-assistant.io/) that reads
the status of LEDA stoves with a LEDATronic LT3 WiFi module over the local network.

## Sensors

| Sensor | Description |
| --- | --- |
| Temperature | Current combustion chamber temperature (°C) |
| State | Operating state (idle, heating up, burning, starting, embers, fault, door open) |
| Error | Error code (none, overheating, motor fault, …) |
| Valve position | Target position of the air valve (%), actual position as attribute |
| Max temperature | Maximum chamber temperature (°C) |
| Firebed temperature | Firebed temperature (°C) |
| Trend | Temperature trend |

## Installation

### HACS

1. Add `https://github.com/fake666/ledatroniclt3` as a custom repository
   (category *Integration*) in HACS.
2. Install **Ledatronic LT3** and restart Home Assistant.

### Manual

Copy `custom_components/ledatroniclt3` into the `custom_components` folder of
your Home Assistant configuration directory and restart Home Assistant.

## Configuration

Go to **Settings → Devices & services → Add integration**, search for
**Ledatronic LT3** and enter the host (IP address or hostname) and port
(default `10001`) of the LT3 WiFi module.

If the IP address of the module changes, use **Reconfigure** on the integration
entry to update it.

YAML configuration (`sensor: - platform: ledatroniclt3`) is deprecated; existing
YAML entries are imported automatically and can be removed from
`configuration.yaml` afterwards.

## Translations

The integration is available in English and German. Pull requests for further
languages are welcome.
