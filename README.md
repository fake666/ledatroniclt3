# Ledatronic LT3

Custom integration for [Home Assistant](https://www.home-assistant.io/) that reads
the status of LEDA stoves with a LEDATronic LT3 WiFi module over the local network.

## Sensors

| Sensor | Description |
| --- | --- |
| Temperature | Current combustion chamber temperature (°C) |
| State | Operating state (idle, heating up, burning, starting, embers, fault, door open, sensor fault); raw code, switching output and oven id as attributes |
| Error | Error code (none, overheating, motor fault, …); raw code as attribute |
| Valve position | Target position of the air valve (%), actual position as attribute |
| Peak temperature | Highest chamber temperature of the current burn-off (°C) |
| Embers threshold | Temperature at which the controller switches to *embers* (°C, about 54 % of the peak; unknown before the burning phase) |
| Minutes without rise | Minutes since the chamber temperature last rose (0–10) |
| Burn-offs | Number of burn-offs counted by the controller (diagnostic) |
| Heating faults | Number of heating faults counted by the controller (diagnostic) |

The **sensor fault** state is not part of the manufacturer's app. The controller
reports it (code 99) as soon as it sees a chamber temperature spike above roughly
1100 °C, which on a healthy stove only happens with a loose thermocouple contact.
While in this state the valve stays fully open, the burn-off is not counted and
the state persists until the stove door is opened or the controller is
power-cycled. *Peak temperature* above 1000 °C is the tell-tale.

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

### One client at a time

The WiFi module (a Lantronix xPico serial tunnel) accepts a **single TCP
connection**. While the LEDATRONIC app is connected, every poll of this
integration is refused and the entities become *unavailable*; they recover with
the next poll after the app disconnects. The integration keeps its own
connections short (one status frame every 30 s, a few seconds at most) so the
app can connect in between. The app can hang on its start screen while holding
the connection; closing it frees the module after a few minutes.

## Protocol

The module streams frames continuously, roughly every 4 seconds:

```
0e ff <status, 16 or 18 bytes> 0d ff
0c ff 56 <operation data, 6 bytes> 0d ff
```

Status payload (big-endian shorts), as implemented by the manufacturer's app:

| Bytes | Field |
| --- | --- |
| 0–1 | chamber temperature (°C) |
| 2 | air valve, actual position (%) |
| 3 | air valve, target position (%) |
| 4 | operating state: 0 idle, 2 heating up, 3/4 burning, 6 starting, 7/8 embers, 97 fault, 98 door open, 99 sensor fault (see above) |
| 5 | error: 0 none, 1 overheating, 2 motor, 3 motor overheating, 16 critical overheating, 18 critical motor overheating, 32 power supply |
| 6 | switching output: bits 0–3 id (1 evacuator, 2 shutter, 4 ventilation, 8 fuel gas shutter), bit 7 on |
| 7 | controller version |
| 8–9 | peak chamber temperature of the burn-off (°C) |
| 10–11 | embers threshold (°C) |
| 12 | minutes without temperature rise (0–10) |
| 13–14 | second temperature input (unused on a plain LT3) |
| 15 | oven type id |
| 16–17 | firmware revision (newer modules only) |

Operation data: operating hours (unit unverified), number of burn-offs, number
of heating faults. Buffer, flow and chimney temperatures of the optional
expansion modules are not streamed; they have to be requested with commands the
integration does not send.

The integration reads one status frame and the operation data that follows it,
then disconnects. Reading is fully asynchronous with a 10 s deadline per poll.

## Origin

The protocol decoding and the first Home Assistant sensor platform were written
by Thomas "fake" Högemann on 6 January 2019 and published as
[a gist](https://gist.github.com/fake666/1915ce1d9839e1c86afe006a3e30c906)
(`ledatroniclt3.py`, the `sensor: - platform: ledatroniclt3` YAML platform
this integration still imports). ManClone built
his repository on that code in October 2022; this repository was created from
his shortly afterwards, which is why GitHub lists it as a fork. The lineage is
the other way round: this is the original author's continuation.

## Translations

The integration is available in English and German. Pull requests for further
languages are welcome.

## License

Copyright (C) 2019-2026 Thomas "fake" Högemann and contributors

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU Affero General Public License as published by the Free
Software Foundation, either version 3 of the License, or (at your option) any
later version. See [LICENSE](LICENSE) for the full text.

SPDX-License-Identifier: AGPL-3.0-or-later
