# TeslaSolarCharger for Home Assistant

A Home Assistant integration for [TeslaSolarCharger](https://github.com/pkuehnel/TeslaSolarCharger) (TSC).
It reads the live values of your PV setup, your cars and your charging connectors through the
TSC REST API, and it exposes most of the TSC settings as Home Assistant entities so you can
change them from a dashboard or an automation instead of opening the TSC web UI.

The integration polls the API. It does not connect to the SignalR hub that the TSC frontend
uses, which keeps it simple and makes it survive a TSC restart without reconnect gymnastics.
The price is latency: a value is at most one polling interval old (30 s by default).

## What you get

On the **TeslaSolarCharger** device:

- Solar production, grid power, home battery power and SoC, combined car charging power
- The TSC version and the number of open issues
- Settings as entities: power buffer, max combined current, minutes until charging starts /
  stops, home battery limits and power, geofence radius, prediction switches, polling
  intervals, correction factors, BLE tuning, URLs and credentials

Per **car**:

- SoC, charging power, charging current, voltage, phases, battery temperatures, distance to home
- Charging, plugged in, at home and online as binary sensors
- Charge mode (`Off` / `Manual` / `Auto` / `MaxPower`) as a select
- Min SoC and Max SoC as numbers, plus a charging current setpoint for manual charging
- Minimum / maximum amperage, phases, usable energy and charging priority as numbers,
  "managed" as a switch, car type and home detection as selects
- Buttons for "wake up" and "forget learned usable energy"

Per **OCPP charging connector**: charge mode select, charging power / current sensors, charging,
plugged in and OCPP connection as binary sensors, and the connector limits as numbers.

Settings that TSC itself marks as advanced are placed in the *Configuration* section of the
device, and a few of them (correction factors, BLE internals, MQTT/TeslaMate credentials) are
disabled by default. Enable them on the device page if you want them.

## Requirements

- TeslaSolarCharger **2.45 or newer**. The endpoints used here (`BaseConfiguration`, `Config`,
  `LiveData`, `Home`, `ChargingStations`) exist from 2.45 on; older versions use different routes.
- The TSC API must be reachable from Home Assistant, default port `7190`. TSC does not require an
  API key, so leave that field empty unless you run it behind a reverse proxy that does.
- Home Assistant 2024.12 or newer. Development happens against 2026.11, so expect the newest
  release to be the one that behaves best.

## Installation

### HACS

1. Add this repository as an HACS integration repository (HACS → Integrations → ⋮ → Custom
   → add this repo, category "Integration").
2. Install "TeslaSolarCharger" and restart Home Assistant.

### Manual

Copy `custom_components/tesla_solar_charger` into your `config/` directory and restart
Home Assistant.

## Configuration

Settings → Devices & Services → Add Integration → **TeslaSolarCharger**.

| Field | Meaning |
| --- | --- |
| Host | IP or hostname of the machine running TSC. A `http://` prefix is accepted and stripped. |
| Port | TSC API port, `7190` unless you changed it. |
| Use HTTPS | Only needed if you terminated TLS in front of TSC or enabled its own HTTPS. |
| Verify SSL | Turn off for self-signed certificates. |
| API key | Optional. Sent as the `x-api-key` header; useful behind a proxy, useless for plain TSC. |
| Update interval | Poll interval in seconds, minimum 5. |

The entry is identified by the TSC installation id, so adding the same instance twice is
refused. The three-dot menu of the entry has a **Reconfigure** item for changing host or port,
and **Configure** for the poll interval and the connection options.

## Changing settings

Every setting entity writes to TSC immediately. Writes are optimistic: the entity shows the new
value at once and the next poll confirms what TSC actually stored (TSC sometimes normalises a
value, e.g. clamps a current to the connector limits).

There is also a service for settings that have no entity, or for values that you do not want to
keep around as entities:

```yaml
service: tesla_solar_charger.set_base_configuration_value
data:
  config_entry_id: 01J...      # the entry to change
  field: PowerBuffer           # TSC property name or the entity key
  value: 200
```

`field` accepts both spellings (`PowerBuffer` and `power_buffer`), and the value is converted to
the type TSC expects, so booleans may be written as `true`, `"true"` or `1`. Passing
`value: null` clears an optional setting such as `MaxCombinedCurrent` — something a number
entity cannot express.

Run `python scripts/check_integration.py --print-keys` to get the full list of writable fields.
