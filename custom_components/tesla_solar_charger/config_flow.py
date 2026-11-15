"""Config flow for the TeslaSolarCharger integration."""

from __future__ import annotations

import logging
from typing import Any

try:  # Home Assistant 2026.11 renamed the schema library to probatio
    import probatio as vol
except ImportError:  # pragma: no cover - older Home Assistant versions
    import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import (
    CONF_API_KEY,
    CONF_HOST,
    CONF_PORT,
    CONF_VERIFY_SSL,
)
from homeassistant.core import callback
from homeassistant.helpers import aiohttp_client

from .api import (
    TeslaSolarChargerApiClient,
    TeslaSolarChargerApiError,
    TeslaSolarChargerConnectionError,
    TeslaSolarChargerNotFoundError,
)
from .const import (
    CONF_API_KEY_HEADER,
    CONF_UPDATE_INTERVAL_SECONDS,
    CONF_USE_SSL,
    DEFAULT_API_KEY_HEADER,
    DEFAULT_PORT,
    DEFAULT_UPDATE_INTERVAL_SECONDS,
    DOMAIN,
    INTEGRATION_NAME,
    MINIMUM_UPDATE_INTERVAL_SECONDS,
)
from .util import build_url

_LOGGER = logging.getLogger(__name__)


def _user_schema(suggestion: dict[str, Any] | None = None) -> vol.Schema:
    """Return the schema of the connection form."""
    current = suggestion or {}
    return vol.Schema(
        {
            vol.Required(CONF_HOST, default=current.get(CONF_HOST, "")): str,
            vol.Required(
                CONF_PORT, default=current.get(CONF_PORT, DEFAULT_PORT)
            ): vol.All(vol.Coerce(int), vol.Range(min=1, max=65535)),
            vol.Optional(
                CONF_USE_SSL, default=current.get(CONF_USE_SSL, False)
            ): bool,
            vol.Optional(
                CONF_VERIFY_SSL, default=current.get(CONF_VERIFY_SSL, True)
            ): bool,
            vol.Optional(CONF_API_KEY, default=current.get(CONF_API_KEY, "")): str,
            vol.Optional(
                CONF_UPDATE_INTERVAL_SECONDS,
                default=current.get(
                    CONF_UPDATE_INTERVAL_SECONDS, DEFAULT_UPDATE_INTERVAL_SECONDS
                ),
            ): vol.All(
                vol.Coerce(int), vol.Range(min=MINIMUM_UPDATE_INTERVAL_SECONDS)
            ),
        }
    )


def _options_schema(current: dict[str, Any]) -> vol.Schema:
    """Return the schema of the options form."""
    return vol.Schema(
        {
            vol.Optional(
                CONF_UPDATE_INTERVAL_SECONDS,
                default=current.get(CONF_UPDATE_INTERVAL_SECONDS,
                                    DEFAULT_UPDATE_INTERVAL_SECONDS),
            ): vol.All(
                vol.Coerce(int), vol.Range(min=MINIMUM_UPDATE_INTERVAL_SECONDS)
            ),
            vol.Optional(
                CONF_USE_SSL, default=current.get(CONF_USE_SSL, False)
            ): bool,
            vol.Optional(
                CONF_VERIFY_SSL, default=current.get(CONF_VERIFY_SSL, True)
            ): bool,
            vol.Optional(CONF_API_KEY, default=current.get(CONF_API_KEY, "")): str,
        }
    )


def _client_from_values(
    hass: Any, values: dict[str, Any]
) -> TeslaSolarChargerApiClient:
    """Build an API client from config flow values."""
    session = aiohttp_client.async_get_clientsession(
        hass, verify_ssl=bool(values.get(CONF_VERIFY_SSL, True))
    )
    return TeslaSolarChargerApiClient(
        session,
        build_url(
            str(values[CONF_HOST]),
            int(values.get(CONF_PORT, DEFAULT_PORT)),
            bool(values.get(CONF_USE_SSL, False)),
        ),
        api_key=values.get(CONF_API_KEY) or None,
        api_key_header=str(values.get(CONF_API_KEY_HEADER, DEFAULT_API_KEY_HEADER)),
    )


class TeslaSolarChargerConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for TeslaSolarCharger."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> TeslaSolarChargerOptionsFlow:
        """Return the options flow handler."""
        return TeslaSolarChargerOptionsFlow()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        description_placeholders: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            user_input = {**user_input, CONF_HOST: host}
            installation_id, error = await self._async_test_connection(user_input)
            if error is None:
                if installation_id:
                    await self.async_set_unique_id(installation_id)
                    self._abort_if_unique_id_configured(
                        updates={
                            CONF_HOST: user_input[CONF_HOST],
                            CONF_PORT: user_input[CONF_PORT],
                            CONF_USE_SSL: user_input.get(CONF_USE_SSL, False),
                        }
                    )
                title = f"{INTEGRATION_NAME} ({user_input[CONF_HOST]})"
                return self.async_create_entry(
                    title=title,
                    data=user_input,
                    options={
                        CONF_UPDATE_INTERVAL_SECONDS: user_input[
                            CONF_UPDATE_INTERVAL_SECONDS
                        ]
                    },
                )
            errors["base"] = error
            description_placeholders["url"] = build_url(
                user_input[CONF_HOST],
                user_input.get(CONF_PORT, DEFAULT_PORT),
                user_input.get(CONF_USE_SSL, False),
            )

        return self.async_show_form(
            step_id="user",
            data_schema=_user_schema(user_input),
            errors=errors,
            description_placeholders=description_placeholders,
        )

    async def _async_test_connection(
        self, values: dict[str, Any]
    ) -> tuple[str | None, str | None]:
        """Return the installation id or an error key for the given values."""
        client = _client_from_values(self.hass, values)
        version: str | None = None
        try:
            version = await client.async_get_product_version()
        except TeslaSolarChargerConnectionError as err:
            _LOGGER.debug("Cannot reach TeslaSolarCharger: %s", err)
            return None, "cannot_connect"
        except TeslaSolarChargerNotFoundError:
            # Unusual installations: fall back to the plain live probe.
            try:
                if not await client.async_is_alive():
                    return None, "not_tesla_solar_charger"
            except (TeslaSolarChargerApiError, TeslaSolarChargerConnectionError) as err:
                _LOGGER.debug("TeslaSolarCharger live probe failed: %s", err)
                return None, "cannot_connect"
        except TeslaSolarChargerApiError as err:
            _LOGGER.debug("TeslaSolarCharger answered unexpectedly: %s", err)
            return None, "not_tesla_solar_charger"

        installation_id: str | None = None
        try:
            installation_id = await client.async_get_installation_id()
        except (
            TeslaSolarChargerApiError,
            TeslaSolarChargerConnectionError,
            TeslaSolarChargerNotFoundError,
        ) as err:
            _LOGGER.debug("Could not read the installation id: %s", err)

        if version is None and installation_id is None:
            return None, "not_tesla_solar_charger"
        return installation_id, None


    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Allow changing the address of an existing installation."""
        entry = self._get_reconfigure_entry()
        current = {**dict(entry.data), **dict(entry.options)}

        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            merged = {**current, **user_input, CONF_HOST: host}
            _installation_id, error = await self._async_test_connection(merged)
            if error is None:
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates={
                        CONF_HOST: host,
                        CONF_PORT: merged[CONF_PORT],
                        CONF_USE_SSL: merged.get(CONF_USE_SSL, False),
                        CONF_VERIFY_SSL: merged.get(CONF_VERIFY_SSL, True),
                        CONF_API_KEY: merged.get(CONF_API_KEY, ""),
                    },
                )
            errors["base"] = error
            user_input = {**user_input, CONF_HOST: host}

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_HOST, default=current.get(CONF_HOST, "")
                    ): str,
                    vol.Required(
                        CONF_PORT, default=current.get(CONF_PORT, DEFAULT_PORT)
                    ): vol.All(vol.Coerce(int), vol.Range(min=1, max=65535)),
                    vol.Optional(
                        CONF_USE_SSL, default=current.get(CONF_USE_SSL, False)
                    ): bool,
                    vol.Optional(
                        CONF_VERIFY_SSL, default=current.get(CONF_VERIFY_SSL, True)
                    ): bool,
                    vol.Optional(
                        CONF_API_KEY, default=current.get(CONF_API_KEY, "")
                    ): str,
                }
            ),
            errors=errors,
        )


class TeslaSolarChargerOptionsFlow(OptionsFlow):
    """Handle the options of an existing config entry."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        current = {**dict(self.config_entry.data), **dict(self.config_entry.options)}
        if user_input is not None:
            return self.async_create_entry(
                title=self.config_entry.title, data=user_input
            )
        return self.async_show_form(
            step_id="init", data_schema=_options_schema(current)
        )

    )
