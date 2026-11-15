"""API client for the TeslaSolarCharger integration."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import aiohttp

from .const import DEFAULT_TIMEOUT_SECONDS
from .util import get_item

_LOGGER = logging.getLogger(__name__)

# TeslaSolarCharger exposes its controllers below /api/<Controller>/<Action>.
PATH_IS_ALIVE: str = "/api/Hello/IsAlive"
PATH_PRODUCT_VERSION: str = "/api/Hello/ProductVersion"
PATH_INSTALLATION_ID: str = "/api/Hello/GetInstallationId"
PATH_IS_STARTUP_COMPLETED: str = "/api/Hello/IsStartupCompleted"
PATH_SEND_TEST_TELEGRAM_MESSAGE: str = "/api/Hello/SendTestTelegramMessage"
PATH_ERROR_COUNT: str = "/api/Issue/ErrorCount"
PATH_GET_BASE_CONFIGURATION: str = "/api/BaseConfiguration/GetBaseConfiguration"
PATH_UPDATE_BASE_CONFIGURATION: str = "/api/BaseConfiguration/UpdateBaseConfiguration"
PATH_GET_CAR_BASIC_CONFIGURATIONS: str = "/api/Config/GetCarBasicConfigurations"
PATH_UPDATE_CAR_BASIC_CONFIGURATION: str = "/api/Config/UpdateCarBasicConfiguration"
PATH_GET_CAR_OVERVIEW: str = "/api/Home/GetCarOverview"
PATH_GET_CHARGING_CONNECTOR_OVERVIEW: str = "/api/Home/GetChargingConnectorOverview"
PATH_UPDATE_CAR_CHARGE_MODE: str = "/api/Home/UpdateCarChargeMode"
PATH_UPDATE_CAR_MIN_SOC: str = "/api/Home/UpdateCarMinSoc"
PATH_UPDATE_CAR_MAX_SOC: str = "/api/Home/UpdateCarMaxSoc"
PATH_SET_CAR_CHARGING_CURRENT: str = "/api/Home/SetCarChargingCurrent"
PATH_UPDATE_CONNECTOR_CHARGE_MODE: str = "/api/Home/UpdateChargingConnectorChargeMode"
PATH_GET_ALL_LATEST_STATES: str = "/api/LiveData/GetAllLatestStates"
PATH_GET_LATEST_STATE_FOR_KEY: str = "/api/LiveData/GetLatestStateForKey"
PATH_GET_CHARGING_STATIONS: str = "/api/ChargingStations/GetChargingStations"
PATH_GET_CHARGING_STATION_CONNECTORS: str = (
    "/api/ChargingStations/GetChargingStationConnectors"
)
PATH_UPDATE_CHARGING_STATION_CONNECTOR: str = (
    "/api/ChargingStations/UpdateChargingStationConnector"
)
PATH_GET_DTO_CAR: str = "/api/Debug/GetDtoCar"
PATH_WAKE_UP_CAR: str = "/api/Debug/WakeUpCar"
PATH_RESET_CAR: str = "/api/UsableEnergy/ResetCar"
PATH_RESET_HOME_BATTERY: str = "/api/UsableEnergy/ResetHomeBattery"


class TeslaSolarChargerError(Exception):
    """Base error for the TeslaSolarCharger API client."""


class TeslaSolarChargerConnectionError(TeslaSolarChargerError):
    """Raised when TeslaSolarCharger cannot be reached at all."""


class TeslaSolarChargerNotReadyError(TeslaSolarChargerError):
    """Raised when TeslaSolarCharger answers with its startup page."""


class TeslaSolarChargerNotFoundError(TeslaSolarChargerError):
    """Raised when an endpoint does not exist (other TeslaSolarCharger version)."""


class TeslaSolarChargerApiError(TeslaSolarChargerError):
    """Raised when TeslaSolarCharger answers with an error status code."""


def _summarise(text: str, limit: int = 400) -> str:
    """Return a single line summary of a response body for logging."""
    collapsed = " ".join(text.split())
    if len(collapsed) > limit:
        return f"{collapsed[:limit]}..."
    return collapsed


class TeslaSolarChargerApiClient:
    """Talk to a TeslaSolarCharger installation over its REST API."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        base_url: str,
        *,
        api_key: str | None = None,
        api_key_header: str = "x-api-key",
        timeout: int = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        """Initialize the client with an aiohttp session and the base URL."""
        self._session = session
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key or None
        self._api_key_header = api_key_header or "x-api-key"
        self._timeout = timeout

    @property
    def base_url(self) -> str:
        """Return the base URL of the TeslaSolarCharger installation."""
        return self._base_url

    async def _async_request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: Any = None,
    ) -> Any:
        """Perform a request and return the parsed JSON body.

        ``None`` is returned for empty bodies, as many update endpoints answer
        without content.
        """
        url = f"{self._base_url}{path}"
        clean_params = {
            key: ("true" if value else "false") if isinstance(value, bool) else value
            for key, value in (params or {}).items()
            if value is not None
        }
        headers: dict[str, str] = {}
        if self._api_key:
            headers[self._api_key_header] = self._api_key
        try:
            async with self._session.request(
                method,
                url,
                params=clean_params or None,
                headers=headers or None,
                json=json_body,
                timeout=aiohttp.ClientTimeout(total=self._timeout),
            ) as response:
                text = await response.text()
                if response.status == 404:
                    raise TeslaSolarChargerNotFoundError(
                        f"TeslaSolarCharger has no endpoint '{path}' (HTTP 404)"
                    )
                if response.status == 503:
                    raise TeslaSolarChargerNotReadyError(
                        f"TeslaSolarCharger is not ready yet (HTTP 503 for '{path}')"
                    )
                if response.status >= 400:
                    raise TeslaSolarChargerApiError(
                        f"'{path}' returned HTTP {response.status}: {_summarise(text)}"
                    )
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise TeslaSolarChargerConnectionError(
                f"Could not reach TeslaSolarCharger at {url}: {err}"
            ) from err

        if not text.strip():
            return None
        try:
            return json.loads(text)
        except ValueError as err:
            # While TeslaSolarCharger starts up it answers almost every request
            # with an HTML page showing its startup log instead of JSON.
            lowered = text.lower()
            if text.lstrip().startswith(("<!doctype", "<html")) or "starting up" in lowered:
                raise TeslaSolarChargerNotReadyError(
                    "TeslaSolarCharger answered with an HTML page instead of JSON. "
                    "The service is probably still starting up, or the configured "
                    "address points to something else."
                ) from err
            raise TeslaSolarChargerApiError(
                f"'{path}' returned invalid JSON: {_summarise(text)}"
            ) from err

    @staticmethod
    def _unwrap(data: Any, default: Any = None) -> Any:
        """Unwrap a ``DtoValue<T>`` answer (``{"Value": ...}``)."""
        return get_item(data, "Value", default)


    async def async_get_product_version(self) -> str | None:
        """Return the version of the TeslaSolarCharger installation."""
        data = await self._async_request("GET", PATH_PRODUCT_VERSION)
        version = self._unwrap(data)
        return version if isinstance(version, str) else None

    async def async_get_installation_id(self) -> str | None:
        """Return the stable installation id of TeslaSolarCharger."""
        data = await self._async_request("GET", PATH_INSTALLATION_ID)
        value = self._unwrap(data)
        return value if isinstance(value, str) else None

    async def async_is_startup_completed(self) -> bool | None:
        """Return whether TeslaSolarCharger finished its startup."""
        data = await self._async_request("GET", PATH_IS_STARTUP_COMPLETED)
        value = self._unwrap(data)
        return value if isinstance(value, bool) else None

    async def async_get_error_count(self) -> int | None:
        """Return the number of issues TeslaSolarCharger reports."""
        data = await self._async_request("GET", PATH_ERROR_COUNT)
        value = self._unwrap(data)
        if isinstance(value, bool) or value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    async def async_get_base_configuration(self) -> dict[str, Any]:
        """Return the full TeslaSolarCharger base configuration."""
        data = await self._async_request("GET", PATH_GET_BASE_CONFIGURATION)
        if not isinstance(data, dict):
            raise TeslaSolarChargerApiError(
                f"'{PATH_GET_BASE_CONFIGURATION}' returned an unexpected payload"
            )
        return data

    async def async_update_base_configuration(self, config: dict[str, Any]) -> None:
        """Send the full base configuration back to TeslaSolarCharger."""
        await self._async_request(
            "POST", PATH_UPDATE_BASE_CONFIGURATION, json_body=config
        )

    async def async_get_car_basic_configurations(self) -> list[dict[str, Any]]:
        """Return the basic configuration of every car known to TeslaSolarCharger."""
        data = await self._async_request("GET", PATH_GET_CAR_BASIC_CONFIGURATIONS)
        if data is None:
            return []
        if not isinstance(data, list):
            raise TeslaSolarChargerApiError(
                f"'{PATH_GET_CAR_BASIC_CONFIGURATIONS}' returned an unexpected payload"
            )
        return [item for item in data if isinstance(item, dict)]

    async def async_update_car_basic_configuration(
        self, car_id: int, configuration: dict[str, Any]
    ) -> None:
        """Update the basic configuration of a single car."""
        await self._async_request(
            "POST",
            PATH_UPDATE_CAR_BASIC_CONFIGURATION,
            params={"carId": car_id},
            json_body=configuration,
        )

    async def async_get_car_overview(self, car_id: int) -> dict[str, Any]:
        """Return charge mode and SoC limits of a single car."""
        data = await self._async_request(
            "GET", PATH_GET_CAR_OVERVIEW, params={"carId": car_id}
        )
        return data if isinstance(data, dict) else {}

    async def async_get_car_details(self, car_id: int) -> dict[str, Any]:
        """Return the detailed live data of a single car.

        TeslaSolarCharger wraps the car into a ``DtoValue<string>`` that holds a
        JSON string, therefore the value is decoded a second time.
        """
        data = await self._async_request(
            "GET", PATH_GET_DTO_CAR, params={"carId": car_id}
        )
        raw = self._unwrap(data)
        if isinstance(raw, str):
            try:
                parsed = json.loads(raw)
            except ValueError as err:
                raise TeslaSolarChargerApiError(
                    f"'{PATH_GET_DTO_CAR}' returned invalid JSON: {_summarise(raw)}"
                ) from err
            return parsed if isinstance(parsed, dict) else {}
        return raw if isinstance(raw, dict) else {}


    async def async_get_all_latest_states(self) -> dict[str, Any]:
        """Return every state TeslaSolarCharger publishes to its web UI."""
        data = await self._async_request("GET", PATH_GET_ALL_LATEST_STATES)
        if data is None:
            return {}
        if not isinstance(data, dict):
            raise TeslaSolarChargerApiError(
                f"'{PATH_GET_ALL_LATEST_STATES}' returned an unexpected payload"
            )
        return data

    async def async_get_latest_state(
        self, data_type: str, entity_id: str = ""
    ) -> Any:
        """Return a single published state of TeslaSolarCharger."""
        return await self._async_request(
            "GET",
            PATH_GET_LATEST_STATE_FOR_KEY,
            params={"dataType": data_type, "entityId": entity_id},
        )

    async def async_get_charging_stations(self) -> list[dict[str, Any]]:
        """Return all configured OCPP charging stations."""
        data = await self._async_request("GET", PATH_GET_CHARGING_STATIONS)
        if data is None:
            return []
        if not isinstance(data, list):
            raise TeslaSolarChargerApiError(
                f"'{PATH_GET_CHARGING_STATIONS}' returned an unexpected payload"
            )
        return [item for item in data if isinstance(item, dict)]

    async def async_get_charging_station_connectors(
        self, charging_station_id: int
    ) -> list[dict[str, Any]]:
        """Return the connectors of one charging station."""
        data = await self._async_request(
            "GET",
            PATH_GET_CHARGING_STATION_CONNECTORS,
            params={"chargingStationId": charging_station_id},
        )
        if data is None:
            return []
        if not isinstance(data, list):
            raise TeslaSolarChargerApiError(
                f"'{PATH_GET_CHARGING_STATION_CONNECTORS}' returned unexpected payload"
            )
        return [item for item in data if isinstance(item, dict)]

    async def async_update_charging_station_connector(
        self, connector: dict[str, Any]
    ) -> None:
        """Send the changed configuration of one connector back."""
        await self._async_request(
            "POST",
            PATH_UPDATE_CHARGING_STATION_CONNECTOR,
            json_body=connector,
        )

    async def async_get_charging_connector_overview(
        self, charging_connector_id: int
    ) -> dict[str, Any]:
        """Return the charge mode of a charging connector."""
        data = await self._async_request(
            "GET",
            PATH_GET_CHARGING_CONNECTOR_OVERVIEW,
            params={"chargingConnectorId": charging_connector_id},
        )
        return data if isinstance(data, dict) else {}


    async def async_set_car_charge_mode(self, car_id: int, charge_mode: str) -> None:
        """Change the charge mode of a car."""
        await self._async_request(
            "POST",
            PATH_UPDATE_CAR_CHARGE_MODE,
            params={"carId": car_id, "chargeMode": charge_mode},
        )

    async def async_set_car_min_soc(self, car_id: int, min_soc: int) -> None:
        """Change the minimum SoC of a car."""
        await self._async_request(
            "POST", PATH_UPDATE_CAR_MIN_SOC, params={"carId": car_id, "minSoc": min_soc}
        )

    async def async_set_car_max_soc(self, car_id: int, max_soc: int) -> None:
        """Change the maximum SoC of a car."""
        await self._async_request(
            "POST", PATH_UPDATE_CAR_MAX_SOC, params={"carId": car_id, "soc": max_soc}
        )

    async def async_set_car_charging_current(self, car_id: int, current: int) -> None:
        """Set the charging current of a car (manual charging)."""
        await self._async_request(
            "POST",
            PATH_SET_CAR_CHARGING_CURRENT,
            params={"carId": car_id, "currentToSet": current},
        )

    async def async_set_connector_charge_mode(
        self, charging_connector_id: int, charge_mode: str
    ) -> None:
        """Change the charge mode of an OCPP charging connector."""
        await self._async_request(
            "POST",
            PATH_UPDATE_CONNECTOR_CHARGE_MODE,
            params={
                "chargingConnectorId": charging_connector_id,
                "chargeMode": charge_mode,
            },
        )

    async def async_wake_up_car(self, car_id: int) -> None:
        """Send a wake up call to a Tesla."""
        await self._async_request("POST", PATH_WAKE_UP_CAR, params={"carId": car_id})

    async def async_reset_car_usable_energy_learning(self, car_id: int) -> None:
        """Forget the learned usable energy of a car."""
        await self._async_request("POST", PATH_RESET_CAR, params={"carId": car_id})

    async def async_reset_home_battery_usable_energy_learning(self) -> None:
        """Forget the learned usable energy of the home battery."""
        await self._async_request("POST", PATH_RESET_HOME_BATTERY)

    async def async_send_test_telegram_message(self) -> Any:
        """Ask TeslaSolarCharger to send a test message via Telegram."""
        return await self._async_request("GET", PATH_SEND_TEST_TELEGRAM_MESSAGE)

    async def async_is_alive(self) -> bool:
        """Return True when the TeslaSolarCharger API answers."""
        data = await self._async_request("GET", PATH_IS_ALIVE)
        return data is True or bool(self._unwrap(data, True))
