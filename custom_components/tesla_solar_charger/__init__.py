"""The TeslaSolarCharger integration."""

from __future__ import annotations

import logging
from typing import Any

try:  # Home Assistant 2026.11 renamed the schema library to probatio
    import probatio as vol
except ImportError:  # pragma: no cover - older Home Assistant versions
    import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_API_KEY,
    CONF_HOST,
    CONF_PORT,
    CONF_VERIFY_SSL,
)
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import aiohttp_client, config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .api import TeslaSolarChargerApiClient
from .const import (
    CONF_API_KEY_HEADER,
    CONF_USE_SSL,
    DEFAULT_API_KEY_HEADER,
    DEFAULT_PORT,
    DOMAIN,
    PLATFORMS,
    SERVICE_SET_BASE_CONFIGURATION_VALUE,
)
from .coordinator import (
    TeslaSolarChargerDataUpdateCoordinator,
    TeslaSolarChargerRuntimeData,
)
from .descriptors import BASE_CONFIGURATION_FIELDS, FieldSpec
from .util import build_url

_LOGGER = logging.getLogger(__name__)

CONF_CONFIG_ENTRY_ID = "config_entry_id"
CONF_FIELD = "field"
CONF_VALUE = "value"

SET_BASE_CONFIGURATION_VALUE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_CONFIG_ENTRY_ID): cv.string,
        vol.Required(CONF_FIELD): cv.string,
        vol.Required(CONF_VALUE): cv.match_all,
    }
)


def _coerce_service_value(spec: FieldSpec, raw_value: Any) -> Any:
    """Convert a service value into the type TeslaSolarCharger expects."""
    if spec.kind == "number":
        if raw_value is None:
            return None
        try:
            number = float(raw_value)
        except (TypeError, ValueError) as err:
            raise ServiceValidationError(
                translation_key="invalid_value",
                translation_placeholders={
                    "field": spec.field,
                    "expected": "a number",
                },
            ) from err
        if spec.minimum is not None:
            number = max(number, spec.minimum)
        if spec.maximum is not None:
            number = min(number, spec.maximum)
        return int(round(number)) if spec.integer else number
    if spec.kind == "bool":
        if isinstance(raw_value, bool):
            return raw_value
        if isinstance(raw_value, str) and raw_value.lower() in ("true", "false"):
            return raw_value.lower() == "true"
        if isinstance(raw_value, (int, float)) and raw_value in (0, 1):
            return bool(raw_value)
        raise ServiceValidationError(
            translation_key="invalid_value",
            translation_placeholders={
                "field": spec.field,
                "expected": "true or false",
            },
        )
    if raw_value is None:
        return None
    return str(raw_value)


def _find_field_spec(field: str) -> FieldSpec | None:
    """Return the descriptor of a base configuration property."""
    wanted = field.strip().lower()
    for spec in BASE_CONFIGURATION_FIELDS:
        if spec.field.lower() == wanted or spec.key.lower() == wanted:
            return spec
    return None


def _coordinator_of_entry(
    entry: ConfigEntry,
) -> TeslaSolarChargerDataUpdateCoordinator:
    """Return the coordinator of a loaded config entry."""
    runtime_data = getattr(entry, "runtime_data", None)
    if not isinstance(runtime_data, TeslaSolarChargerRuntimeData):
        raise ServiceValidationError(
            translation_key="entry_not_loaded",
            translation_placeholders={"title": entry.title},
        )
    return runtime_data.coordinator


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register the services that work on any config entry of this integration."""

    async def async_set_base_configuration_value(call: ServiceCall) -> None:
        """Change a single property of the base configuration."""
        entry_id = str(call.data[CONF_CONFIG_ENTRY_ID])
        field = str(call.data[CONF_FIELD])
        raw_value: Any = call.data[CONF_VALUE]

        entry = hass.config_entries.async_get_entry(entry_id)
        if entry is None or entry.domain != DOMAIN:
            raise ServiceValidationError(
                translation_key="config_entry_not_found",
                translation_placeholders={"config_entry_id": entry_id},
            )

        spec = _find_field_spec(field)
        if spec is None:
            known = ", ".join(sorted(item.field for item in BASE_CONFIGURATION_FIELDS))
            raise ServiceValidationError(
                translation_key="unknown_setting",
                translation_placeholders={"field": field, "known": known},
            )

        value = _coerce_service_value(spec, raw_value)
        coordinator = _coordinator_of_entry(entry)
        await coordinator.async_set_base_configuration_value(spec.field, value)

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_BASE_CONFIGURATION_VALUE,
        async_set_base_configuration_value,
        schema=SET_BASE_CONFIGURATION_VALUE_SCHEMA,
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up TeslaSolarCharger from a config entry."""
    values: dict[str, Any] = {**dict(entry.data), **dict(entry.options)}
    base_url = build_url(
        str(values[CONF_HOST]),
        int(values.get(CONF_PORT, DEFAULT_PORT)),
        bool(values.get(CONF_USE_SSL, False)),
    )
    session = aiohttp_client.async_get_clientsession(
        hass, verify_ssl=bool(values.get(CONF_VERIFY_SSL, True))
    )
    client = TeslaSolarChargerApiClient(
        session,
        base_url,
        api_key=values.get(CONF_API_KEY) or None,
        api_key_header=str(values.get(CONF_API_KEY_HEADER, DEFAULT_API_KEY_HEADER)),
    )

    coordinator = TeslaSolarChargerDataUpdateCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = TeslaSolarChargerRuntimeData(
        client=client,
        coordinator=coordinator,
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the config entry when its options changed."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
