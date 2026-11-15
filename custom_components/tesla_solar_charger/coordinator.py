"""DataUpdateCoordinator for TeslaSolarCharger."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    TeslaSolarChargerApiClient,
    TeslaSolarChargerApiError,
    TeslaSolarChargerConnectionError,
    TeslaSolarChargerError,
    TeslaSolarChargerNotReadyError,
    TeslaSolarChargerNotFoundError,
)
from .const import (
    CONF_UPDATE_INTERVAL_SECONDS,
    DATA_TYPE_CAR_OVERVIEW_STATE,
    DATA_TYPE_CHARGING_CONNECTOR_OVERVIEW_STATE,
    DATA_TYPE_LOAD_POINT_OVERVIEW,
    DATA_TYPE_PV_VALUES,
    DEFAULT_UPDATE_INTERVAL_SECONDS,
    DOMAIN,
)
from .util import get_bool, get_int, get_item, real_key

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class CarData:
    """Everything the integration knows about one car."""

    car_id: int
    basic: dict[str, Any] = field(default_factory=dict)
    overview: dict[str, Any] = field(default_factory=dict)
    details: dict[str, Any] = field(default_factory=dict)
    state: dict[str, Any] = field(default_factory=dict)
    load_point: dict[str, Any] = field(default_factory=dict)

    @property
    def name(self) -> str:
        """Return the name of the car."""
        return get_str_name(self.basic, self.overview, fallback=f"Car {self.car_id}")

    @property
    def vin(self) -> str | None:
        """Return the VIN of the car."""
        return get_item(self.basic, "Vin") or get_item(self.details, "Vin")


@dataclass(slots=True)
class ConnectorData:
    """Everything the integration knows about one charging connector."""

    connector_id: int
    station_id: int
    chargepoint_id: str | None = None
    station_connected: bool | None = None
    config: dict[str, Any] = field(default_factory=dict)
    overview: dict[str, Any] = field(default_factory=dict)
    state: dict[str, Any] = field(default_factory=dict)
    load_point: dict[str, Any] = field(default_factory=dict)

    @property
    def name(self) -> str:
        """Return the name of the connector."""
        return get_str_name(
            self.config, self.overview, fallback=f"Connector {self.connector_id}"
        )


def get_str_name(*containers: dict[str, Any], fallback: str) -> str:
    """Return the first non empty ``Name`` property of the given API objects."""
    for container in containers:
        name = get_item(container, "Name")
        if isinstance(name, str) and name.strip():
            return name.strip()
    return fallback


@dataclass(slots=True)
class TscData:
    """The state of a whole TeslaSolarCharger installation."""

    version: str | None = None
    installation_id: str | None = None
    startup_completed: bool | None = None
    issue_count: int | None = None
    base_configuration: dict[str, Any] = field(default_factory=dict)
    pv_values: dict[str, Any] = field(default_factory=dict)
    cars: dict[int, CarData] = field(default_factory=dict)
    connectors: dict[int, ConnectorData] = field(default_factory=dict)


@dataclass(slots=True)
class TeslaSolarChargerRuntimeData:
    """Everything stored on the config entry while it is loaded."""

    client: TeslaSolarChargerApiClient
    coordinator: TeslaSolarChargerDataUpdateCoordinator


def _parse_keyed_states(
    states: dict[str, Any], data_type: str
) -> dict[str, dict[str, Any]]:
    """Split ``{"CarOverviewState:12": {...}}`` into ``{"12": {...}}``."""
    result: dict[str, dict[str, Any]] = {}
    prefix = f"{data_type}:"
    for key, value in states.items():
        if key.startswith(prefix) and isinstance(value, dict):
            result[key[len(prefix) :]] = value
    return result


class TeslaSolarChargerDataUpdateCoordinator(DataUpdateCoordinator[TscData]):
    """Poll all TeslaSolarCharger values that Home Assistant shows."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: TeslaSolarChargerApiClient,
    ) -> None:
        """Initialize the coordinator."""
        interval = entry.options.get(
            CONF_UPDATE_INTERVAL_SECONDS,
            entry.data.get(CONF_UPDATE_INTERVAL_SECONDS, DEFAULT_UPDATE_INTERVAL_SECONDS),
        )
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=max(int(interval), 5)),
        )
        self.client = client
        self._warned_endpoints: set[str] = set()
        self.data = TscData()

    # ------------------------------------------------------------------
    # Polling
    # ------------------------------------------------------------------
    def _warn_once(self, endpoint: str, message: str) -> None:
        """Log a degradation message only once per endpoint."""
        if endpoint in self._warned_endpoints:
            return
        self._warned_endpoints.add(endpoint)
        _LOGGER.warning("%s", message)

    async def _async_update_data(self) -> TscData:
        """Fetch all data from TeslaSolarCharger."""
        client = self.client
        try:
            base_configuration = await client.async_get_base_configuration()
            car_configurations = await client.async_get_car_basic_configurations()
            latest_states = await client.async_get_all_latest_states()
        except (
            TeslaSolarChargerConnectionError,
            TeslaSolarChargerNotReadyError,
        ) as err:
            raise UpdateFailed(str(err)) from err
        except TeslaSolarChargerNotFoundError as err:
            raise UpdateFailed(
                "This TeslaSolarCharger version does not provide the expected API: "
                f"{err}"
            ) from err
        except TeslaSolarChargerApiError as err:
            raise UpdateFailed(str(err)) from err

        pv_values = latest_states.get(DATA_TYPE_PV_VALUES)
        load_points = _parse_keyed_states(latest_states, DATA_TYPE_LOAD_POINT_OVERVIEW)
        car_states = _parse_keyed_states(latest_states, DATA_TYPE_CAR_OVERVIEW_STATE)
        connector_states = _parse_keyed_states(
            latest_states, DATA_TYPE_CHARGING_CONNECTOR_OVERVIEW_STATE
        )

        cars: dict[int, CarData] = {}
        for car in car_configurations:
            car_id = get_int(car, "Id")
            if car_id is None:
                continue
            cars[car_id] = CarData(car_id=car_id, basic=car)

        for key, value in load_points.items():
            car_id = _int_or_none(key.split("_", 1)[0])
            if car_id in cars:
                cars[car_id].load_point = value
        for key, value in car_states.items():
            car_id = _int_or_none(key)
            if car_id in cars:
                cars[car_id].state = value

        connectors: dict[int, ConnectorData] = {}
        stations = await self._async_optional(
            client.async_get_charging_stations(),
            "charging stations",
            default=[],
        )
        for station in stations or []:
            station_id = get_int(station, "Id")
            if station_id is None:
                continue
            connectors_of_station = await self._async_optional(
                client.async_get_charging_station_connectors(station_id),
                "charging station connectors",
                default=[],
            )
            for connector in connectors_of_station or []:
                connector_id = get_int(connector, "Id")
                if connector_id is None:
                    continue
                connectors[connector_id] = ConnectorData(
                    connector_id=connector_id,
                    station_id=station_id,
                    chargepoint_id=get_item(station, "ChargepointId")
                    or get_item(station, "ChargePointId"),
                    station_connected=get_bool(station, "IsConnected"),
                    config=connector,
                )
        for key, value in load_points.items():
            car_part, _, connector_part = key.partition("_")
            connector_id = _int_or_none(connector_part)
            if connector_id is not None and connector_id in connectors:
                connectors[connector_id].load_point = value
        for key, value in connector_states.items():
            connector_id = _int_or_none(key)
            if connector_id in connectors:
                connectors[connector_id].state = value


        car_overviews, car_details_list = await asyncio.gather(
            self._async_gather_optional(
                [(car_id, client.async_get_car_overview(car_id)) for car_id in cars],
                "car overview",
            ),
            self._async_gather_optional(
                [(car_id, client.async_get_car_details(car_id)) for car_id in cars],
                "car details",
            ),
        )
        for car_id, overview in car_overviews.items():
            if car_id in cars and isinstance(overview, dict):
                cars[car_id].overview = overview
        for car_id, details in car_details_list.items():
            if car_id in cars and isinstance(details, dict):
                cars[car_id].details = details

        connector_overviews = await self._async_gather_optional(
            [
                (connector_id, client.async_get_charging_connector_overview(connector_id))
                for connector_id in connectors
            ],
            "charging connector overview",
        )
        for connector_id, overview in connector_overviews.items():
            if connector_id in connectors and isinstance(overview, dict):
                connectors[connector_id].overview = overview

        version, installation_id, startup_completed, issue_count = await asyncio.gather(
            self._async_optional(client.async_get_product_version(), "version", default=None),
            self._async_optional(
                client.async_get_installation_id(), "installation id", default=None
            ),
            self._async_optional(
                client.async_is_startup_completed(), "startup state", default=None
            ),
            self._async_optional(client.async_get_error_count(), "issue count", default=None),
        )

        data = TscData(
            version=version,
            installation_id=installation_id,
            startup_completed=startup_completed,
            issue_count=issue_count,
            base_configuration=base_configuration,
            pv_values=pv_values if isinstance(pv_values, dict) else {},
            cars=cars,
            connectors=connectors,
        )
        return data

    async def _async_optional(
        self, awaitable: Any, description: str, *, default: Any
    ) -> Any:
        """Await a single request, returning ``default`` when it is unavailable."""
        try:
            return await awaitable
        except TeslaSolarChargerNotFoundError as err:
            self._warn_once(description, f"TeslaSolarCharger has no {description}: {err}")
        except (
            TeslaSolarChargerApiError,
            TeslaSolarChargerConnectionError,
            TeslaSolarChargerNotReadyError,
        ) as err:
            _LOGGER.debug("Could not fetch %s: %s", description, err)
        return default

    async def _async_gather_optional(
        self, calls: list[tuple[int, Any]], description: str
    ) -> dict[int, Any]:
        """Await several requests in parallel and keep the failed ones out."""
        if not calls:
            return {}
        results = await asyncio.gather(
            *[self._async_optional(awaitable, description, default=None)
              for _, awaitable in calls],
            return_exceptions=True,
        )
        collected: dict[int, Any] = {}
        for (identifier, _), result in zip(calls, results):
            if isinstance(result, BaseException) and not isinstance(result, Exception):
                raise result
            if isinstance(result, TeslaSolarChargerError):
                continue
            collected[identifier] = result
        return collected
    # ------------------------------------------------------------------
    # Writing settings - every method pushes the change back to TSC
    # ------------------------------------------------------------------
    async def _async_write(
        self, call: Any, after: Callable[[], None] | None = None
    ) -> None:
        """Run a write request, translate errors and update the cached data."""
        try:
            await call
        except TeslaSolarChargerError as err:
            raise HomeAssistantError(str(err)) from err
        if after is not None:
            after()
        self.async_set_updated_data(self.data)

    async def async_set_base_configuration_value(
        self, field_name: str, value: Any
    ) -> None:
        """Change a single property of the TeslaSolarCharger base configuration."""
        config = self.data.base_configuration
        if not isinstance(config, dict):
            raise HomeAssistantError(
                "The TeslaSolarCharger base configuration could not be read"
            )
        key = real_key(config, field_name)
        updated = dict(config)
        updated[key] = value
        await self._async_write(
            self.client.async_update_base_configuration(updated),
            after=lambda: setattr(self.data, "base_configuration", updated),
        )

    async def async_set_car_field(
        self, car_id: int, field_name: str, value: Any
    ) -> None:
        """Change a single property of a car's basic configuration."""
        car = self.data.cars.get(car_id)
        if car is None:
            raise HomeAssistantError(f"Car {car_id} is not known to TeslaSolarCharger")
        key = real_key(car.basic, field_name)
        updated = dict(car.basic)
        updated[key] = value
        await self._async_write(
            self.client.async_update_car_basic_configuration(car_id, updated),
            after=lambda: setattr(car, "basic", updated),
        )

    async def async_set_connector_field(
        self, connector_id: int, field_name: str, value: Any
    ) -> None:
        """Change a single property of a charging connector configuration."""
        connector = self.data.connectors.get(connector_id)
        if connector is None:
            raise HomeAssistantError(
                f"Charging connector {connector_id} is not known to TeslaSolarCharger"
            )
        key = real_key(connector.config, field_name)
        updated = dict(connector.config)
        updated[key] = value
        await self._async_write(
            self.client.async_update_charging_station_connector(updated),
            after=lambda: setattr(connector, "config", updated),
        )

    async def async_set_car_overview_field(
        self, car_id: int, field_name: str, value: Any
    ) -> None:
        """Change charge mode or SoC limits of a car."""
        car = self.data.cars.get(car_id)
        if car is None:
            raise HomeAssistantError(f"Car {car_id} is not known to TeslaSolarCharger")
        if field_name == "ChargeMode":
            call = self.client.async_set_car_charge_mode(car_id, str(value))
        elif field_name == "MinSoc":
            call = self.client.async_set_car_min_soc(car_id, int(value))
        elif field_name == "MaxSoc":
            call = self.client.async_set_car_max_soc(car_id, int(value))
        else:  # pragma: no cover - guarded by the descriptor table
            raise HomeAssistantError(f"Unsupported car setting '{field_name}'")
        await self._async_write(
            call, after=lambda: car.overview.__setitem__(field_name, value)
        )

    async def async_set_connector_charge_mode(
        self, connector_id: int, charge_mode: str
    ) -> None:
        """Change the charge mode of a charging connector."""
        connector = self.data.connectors.get(connector_id)
        if connector is None:
            raise HomeAssistantError(
                f"Charging connector {connector_id} is not known to TeslaSolarCharger"
            )
        await self._async_write(
            self.client.async_set_connector_charge_mode(connector_id, charge_mode),
            after=lambda: connector.overview.__setitem__("ChargeMode", charge_mode),
        )

    async def async_set_car_charging_current(
        self, car_id: int, current: int
    ) -> None:
        """Set the charging current of a car directly."""
        car = self.data.cars.get(car_id)
        if car is None:
            raise HomeAssistantError(f"Car {car_id} is not known to TeslaSolarCharger")
        await self._async_write(
            self.client.async_set_car_charging_current(car_id, current),
            after=lambda: car.details.__setitem__(
                "LastSetAmp", {"Value": current, "Timestamp": None}
            ),
        )

    async def async_run_car_action(self, car_id: int, action: str) -> None:
        """Run a one-shot action for a car (wake up, reset learning)."""
        if action == "wake_up":
            call = self.client.async_wake_up_car(car_id)
        elif action == "reset_usable_energy":
            call = self.client.async_reset_car_usable_energy_learning(car_id)
        else:  # pragma: no cover - guarded by the descriptor table
            raise HomeAssistantError(f"Unsupported car action '{action}'")
        await self._async_write(call)

    async def async_run_service_action(self, action: str) -> None:
        """Run a one-shot action for the TeslaSolarCharger installation."""
        if action == "reset_home_battery_learning":
            call = self.client.async_reset_home_battery_usable_energy_learning()
        elif action == "send_test_telegram_message":
            call = self.client.async_send_test_telegram_message()
        else:  # pragma: no cover - guarded by the descriptor table
            raise HomeAssistantError(f"Unsupported action '{action}'")
        await self._async_write(call)



def _int_or_none(value: Any) -> int | None:
    """Return ``value`` as an int, ``None`` for the ``"null"`` placeholder."""
    if value is None or value in ("", "null"):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
