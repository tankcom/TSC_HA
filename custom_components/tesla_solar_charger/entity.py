"""Base classes and device information for TeslaSolarCharger entities."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CAR_TYPE_BY_VALUE,
    DOMAIN,
    IDENTIFIER_CAR_PREFIX,
    IDENTIFIER_CONNECTOR_PREFIX,
    IDENTIFIER_SERVICE_PREFIX,
    INTEGRATION_NAME,
    MANUFACTURER,
)
from .coordinator import (
    CarData,
    ConnectorData,
    TeslaSolarChargerDataUpdateCoordinator,
)
from .descriptors import ValueSource
from .util import (
    enum_name,
    get_bool,
    get_item,
    get_str,
    get_time_stamped,
)


class TeslaSolarChargerEntity(CoordinatorEntity[TeslaSolarChargerDataUpdateCoordinator]):
    """Base class for every entity of this integration."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: TeslaSolarChargerDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._entry = entry

    @property
    def available(self) -> bool:
        """Return whether the coordinator has data."""
        return self.coordinator.last_update_success and self.coordinator.data is not None


class ServiceEntity(TeslaSolarChargerEntity):
    """Entity that belongs to the TeslaSolarCharger installation itself."""

    def __init__(
        self,
        coordinator: TeslaSolarChargerDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the entity and its device information."""
        super().__init__(coordinator, entry)
        self._attr_device_info = service_device_info(entry, coordinator)

    def read(self, source: ValueSource, field: str, **kwargs: Any) -> Any:
        """Read one value of the installation (base configuration or PV values)."""
        return read_value(self.coordinator, source, field, **kwargs)


def service_device_info(
    entry: ConfigEntry,
    coordinator: TeslaSolarChargerDataUpdateCoordinator,
) -> DeviceInfo:
    """Return the device information of the TeslaSolarCharger service."""
    data = coordinator.data
    return DeviceInfo(
        identifiers={(DOMAIN, f"{entry.entry_id}_{IDENTIFIER_SERVICE_PREFIX}")},
        name=INTEGRATION_NAME,
        manufacturer=MANUFACTURER,
        model=INTEGRATION_NAME,
        configuration_url=coordinator.client.base_url,
        sw_version=getattr(data, "version", None),
        entry_type=DeviceEntryType.SERVICE,
    )


class CarEntity(TeslaSolarChargerEntity):
    """Entity that belongs to one car managed by TeslaSolarCharger."""

    def __init__(
        self,
        coordinator: TeslaSolarChargerDataUpdateCoordinator,
        entry: ConfigEntry,
        car_id: int,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator, entry)
        self._car_id = car_id
        self._attr_device_info = car_device_info(entry, coordinator, car_id)

    @property
    def car(self) -> CarData | None:
        """Return the car data of this entity, if available."""
        data = self.coordinator.data
        if data is None:
            return None
        return data.cars.get(self._car_id)

    @property
    def car_id(self) -> int:
        """Return the TeslaSolarCharger car id."""
        return self._car_id

    def read(self, source: ValueSource, field: str, **kwargs: Any) -> Any:
        """Read one value that belongs to this car."""
        return read_value(self.coordinator, source, field, car=self.car, **kwargs)


def car_device_info(
    entry: ConfigEntry,
    coordinator: TeslaSolarChargerDataUpdateCoordinator,
    car_id: int,
) -> DeviceInfo:
    """Return the device information of one car."""
    car = coordinator.data.cars.get(car_id) if coordinator.data else None
    info = DeviceInfo(
        identifiers={(DOMAIN, f"{entry.entry_id}_{IDENTIFIER_CAR_PREFIX}_{car_id}")},
        name=car.name if car else f"Car {car_id}",
    )
    if car is not None:
        car_type = enum_name(car.basic, "CarType", CAR_TYPE_BY_VALUE)
        if car_type == "Tesla":
            info["manufacturer"] = "Tesla"
        if car_type:
            info["model"] = car_type
        vin = car.vin
        if vin:
            info["serial_number"] = vin
    return info


class ConnectorEntity(TeslaSolarChargerEntity):
    """Entity that belongs to one OCPP charging connector."""

    def __init__(
        self,
        coordinator: TeslaSolarChargerDataUpdateCoordinator,
        entry: ConfigEntry,
        connector_id: int,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator, entry)
        self._connector_id = connector_id
        self._attr_device_info = connector_device_info(entry, coordinator, connector_id)

    @property
    def connector(self) -> ConnectorData | None:
        """Return the connector data of this entity, if available."""
        data = self.coordinator.data
        if data is None:
            return None
        return data.connectors.get(self._connector_id)

    @property
    def connector_id(self) -> int:
        """Return the TeslaSolarCharger charging connector id."""
        return self._connector_id

    def read(self, source: ValueSource, field: str, **kwargs: Any) -> Any:
        """Read one value that belongs to this charging connector."""
        return read_value(
            self.coordinator, source, field, connector=self.connector, **kwargs
        )


def connector_device_info(
    entry: ConfigEntry,
    coordinator: TeslaSolarChargerDataUpdateCoordinator,
    connector_id: int,
) -> DeviceInfo:
    """Return the device information of one charging connector."""
    connector = (
        coordinator.data.connectors.get(connector_id) if coordinator.data else None
    )
    info = DeviceInfo(
        identifiers={
            (DOMAIN, f"{entry.entry_id}_{IDENTIFIER_CONNECTOR_PREFIX}_{connector_id}")
        },
        name=connector.name if connector else f"Charging connector {connector_id}",
    )
    if connector is not None and connector.chargepoint_id:
        info["model"] = f"OCPP ({connector.chargepoint_id})"
    return info


def read_value(
    coordinator: TeslaSolarChargerDataUpdateCoordinator,
    source: ValueSource,
    field: str,
    *,
    car: CarData | None = None,
    connector: ConnectorData | None = None,
    time_stamped: bool = False,
    fallback_field: str | None = None,
) -> Any:
    """Read one property out of the cached TeslaSolarCharger data.

    ``source`` selects the API object the value is taken from; ``car_live``
    prefers the detailed car object and falls back to the state object the web
    interface of TeslaSolarCharger uses.
    """
    data = coordinator.data
    if data is None:
        return None

    if source == "pv":
        container: dict[str, Any] | None = data.pv_values
    elif source == "base":
        container = data.base_configuration
    elif source == "car_live":
        if car is None:
            return None
        names = [field, fallback_field] if fallback_field else [field]
        for candidate in (car.details, car.state):
            if not candidate:
                continue
            for name in names:
                value = (
                    get_time_stamped(candidate, name)
                    if time_stamped
                    else get_item(candidate, name)
                )
                if value is not None:
                    return value
        return None
    elif car is not None and source in ("basic", "overview", "details", "state"):
        container = getattr(car, source)
    elif connector is not None and source in (
        "connector",
        "connector_overview",
        "connector_state",
        "load_point",
    ):
        container = connector.load_point if source == "load_point" else None
        if source == "connector":
            container = connector.config
        elif source == "connector_overview":
            container = connector.overview
        elif source == "connector_state":
            container = connector.state
    elif car is not None and source == "load_point":
        container = car.load_point
    elif source == "station":
        container = {"IsConnected": connector.station_connected} if connector else None
    else:
        container = None

    if container is None:
        return None
    if time_stamped:
        return get_time_stamped(container, field)
    return get_item(container, field)


def as_bool(value: Any) -> bool | None:
    """Convert an API value into a boolean."""
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    return get_bool({"value": value}, "value")


def as_float(value: Any) -> float | None:
    """Convert an API value into a float."""
    if isinstance(value, bool) or value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def as_int(value: Any) -> int | None:
    """Convert an API value into an integer."""
    number = as_float(value)
    if number is None:
        return None
    return int(round(number))


def as_str(value: Any) -> str | None:
    """Convert an API value into a string, ``None`` stays ``None``."""
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return get_str({"value": value}, "value")
