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

The repository is not in the HACS default repositories yet, so add it as a custom one:

1. HACS → Integrations → ⋮ → Custom repositories → add `https://github.com/tankcom/TSC_HA`,
   category "Integration".
2. Install "TeslaSolarCharger" from the list and restart Home Assistant.

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
and **Configure** for the poll interval and the connection options. Reconfigure probes the
address before it saves: if the TSC answering there reports a different installation id, the flow
stops instead of moving your entities onto another instance.

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

## Notes and rough edges

- **Polling, not push.** Set the interval to what your automations need; 30 s is a compromise
  between responsiveness and load on the TSC container.
- **Nullable settings.** Numbers such as `MaxCombinedCurrent` cannot be cleared from the UI once
  they hold a value, because an empty number entity is not the same as TSC's `null`. Use the
  service above.
- **Secrets are off by default.** The Telegram bot key, the MQTT password and the TeslaMate
  database password are disabled entities. If you enable one, be aware that Home Assistant's
  recorder keeps the value in its history.
- **Base configuration writes are whole-object.** TSC has no PATCH for it, so every change sends
  the complete config back. If someone edits the TSC web UI at the same moment, whoever writes
  last wins.
- **Missing endpoints are tolerated.** If your TSC version does not have a route (for example an
  older build without `Home`), the entities that depend on it go unavailable and the reason is
  logged once instead of failing the whole refresh.
- **No charging start/stop.** OCPP connectors are controlled through their charge mode; there is
  no "start session" action, because TSC does not offer one.
- **Not battle-tested.** The code has not been run against a live TSC instance yet. Expect to fix
  a couple of field names, and open an issue with the TSC version you ran it against.

## Repository layout

```
custom_components/tesla_solar_charger/
  api.py           thin async REST client, aiohttp
  coordinator.py   DataUpdateCoordinator, polling, write helpers
  const.py         constants, platform list, option keys
  descriptors.py   tables of TSC config fields (what becomes which entity)
  descriptions.py  EntityDescription builders and icons
  entity.py        base entities and device registry helpers
  util.py          case-insensitive JSON access, DtoValue unwrapping, enum conversion
  config_flow.py   user / reconfigure / options flow
  sensor.py select.py number.py switch.py binary_sensor.py text.py button.py
  __init__.py      setup, services
scripts/check_integration.py   syntax, JSON and translation-key consistency check
```

Everything that repeats (name, icon, unit, device class, translation key) is generated from the
descriptor tables, so adding a setting is usually one line in `descriptors.py` plus the matching
strings.

## Development

```bash
python -m pyflakes custom_components/tesla_solar_charger   # undefined names, unused imports
python scripts/check_integration.py                        # json files + translation keys
python scripts/check_integration.py --print-keys           # the key list, per platform
```

The check script needs nothing but Python: it parses the package with `ast` instead of importing
it, so it runs without a Home Assistant installation. It complains when a translation key is used
in code but missing from `strings.json`, about keys that are defined but never used, and about any
string containing a `[%key:…%]` reference. That last one matters: core integrations use those
references for common text, but they are expanded by core's translation build, which never runs
here - the frontend would show `[%key:common::config_flow::data::host%]` inside the form instead
of "Host". Write the text out.

`strings.json` holds the English text and `translations/en.json` is a copy of it, because Home
Assistant reads that file at runtime for a custom integration. After changing the strings:

```bash
cp custom_components/tesla_solar_charger/strings.json custom_components/tesla_solar_charger/translations/en.json
```

There is no test suite in this repository yet; running the integration against a real TSC
instance and pasting the resulting `entity_registry` + device list is the fastest way to find
the places where the API differs from the docs.

## Before publishing

- a `LICENSE` file: without one no usage rights are granted, and HACS submissions get asked for it
- the `version` in `manifest.json` is a guess - HACS takes the version from the release tag, so
  tag what you publish and keep the two in step
- `codeowners` in `manifest.json` points at `@tankcom`; add whoever should be pinged
- the manifest's `documentation` URL is this repository; a page that explains each setting would
  beat the table above

