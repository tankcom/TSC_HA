"""Select entities for the enum settings of TeslaSolarCharger."""

from __future__ import annotations

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CAR_TYPE_BY_VALUE,
    CAR_TYPE_OPTIONS,
    CHARGE_MODE_BY_VALUE,
    CHARGE_MODE_OPTIONS,
    HOME_DETECTION_BY_VALUE,
    HOME_DETECTION_OPTIONS,
)
from .descriptions import select_description
from .entity import CarEntity, ConnectorEntity
from .util import enum_name, enum_name_from_value

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the select entities of a config entry."""
    coordinator = entry.runtime_data.coordinator
    entities: list[SelectEntity] = []

    for car_id in coordinator.data.cars:
        entities.append(CarChargeModeSelect(coordinator, entry, car_id))
        entities.append(CarTypeSelect(coordinator, entry, car_id))
        entities.append(HomeDetectionSelect(coordinator, entry, car_id))

    for connector_id in coordinator.data.connectors:
        entities.append(ConnectorChargeModeSelect(coordinator, entry, connector_id))

    async_add_entities(entities)


class CarChargeModeSelect(CarEntity, SelectEntity):
    """How a car is charged: off, manual, auto or max power."""

    def __init__(self, coordinator, entry: ConfigEntry, car_id: int) -> None:
        """Initialize the select."""
        super().__init__(coordinator, entry, car_id)
        self.entity_description = select_description(
            "charge_mode", CHARGE_MODE_OPTIONS, icon="mdi:car-clock"
        )
        self._attr_unique_id = f"{entry.entry_id}_car_{car_id}_charge_mode"

    @property
    def available(self) -> bool:
        """Return True when the car data is known."""
        return super().available and self.car is not None

    @property
    def current_option(self) -> str | None:
        """Return the current charge mode."""
        return enum_name(self.car.overview if self.car else {}, "ChargeMode",
                         CHARGE_MODE_BY_VALUE, CHARGE_MODE_OPTIONS)

    async def async_select_option(self, option: str) -> None:
        """Change the charge mode of the car."""
        value = enum_name_from_value(option, CHARGE_MODE_BY_VALUE, CHARGE_MODE_OPTIONS)
        if value is None:
            raise ValueError(f"Unsupported charge mode '{option}'")
        await self.coordinator.async_set_car_overview_field(self.car_id, "ChargeMode", value)


class ConnectorChargeModeSelect(ConnectorEntity, SelectEntity):
    """How a charging connector is charged."""

    def __init__(self, coordinator, entry: ConfigEntry, connector_id: int) -> None:
        """Initialize the select."""
        super().__init__(coordinator, entry, connector_id)
        self.entity_description = select_description(
            "charge_mode", CHARGE_MODE_OPTIONS, icon="mdi:car-clock"
        )
        self._attr_unique_id = f"{entry.entry_id}_connector_{connector_id}_charge_mode"

    @property
    def available(self) -> bool:
        """Return True when the connector data is known."""
        return super().available and self.connector is not None

    @property
    def current_option(self) -> str | None:
        """Return the current charge mode of the connector."""
        return enum_name(self.connector.overview if self.connector else {},
                         "ChargeMode", CHARGE_MODE_BY_VALUE, CHARGE_MODE_OPTIONS)

    async def async_select_option(self, option: str) -> None:
        """Change the charge mode of the connector."""
        value = enum_name_from_value(option, CHARGE_MODE_BY_VALUE, CHARGE_MODE_OPTIONS)
        if value is None:
            raise ValueError(f"Unsupported charge mode '{option}'")
        await self.coordinator.async_set_connector_charge_mode(self.connector_id, value)


class CarTypeSelect(CarEntity, SelectEntity):
    """Which kind of car this is (Tesla, manual or SmartCar)."""

    def __init__(self, coordinator, entry: ConfigEntry, car_id: int) -> None:
        """Initialize the select."""
        super().__init__(coordinator, entry, car_id)
        self.entity_description = select_description(
            "car_type",
            CAR_TYPE_OPTIONS,
            category=EntityCategory.CONFIG,
            enabled_default=False,
            icon="mdi:car-search",
        )
        self._attr_unique_id = f"{entry.entry_id}_car_{car_id}_car_type"

    @property
    def available(self) -> bool:
        """Return True when the car data is known."""
        return super().available and self.car is not None

    @property
    def current_option(self) -> str | None:
        """Return the configured car type."""
        return enum_name(
            self.car.basic if self.car else {},
            "CarType",
            CAR_TYPE_BY_VALUE,
            CAR_TYPE_OPTIONS,
        )

    async def async_select_option(self, option: str) -> None:
        """Change the car type."""
        value = enum_name_from_value(option, CAR_TYPE_BY_VALUE, CAR_TYPE_OPTIONS)
        if value is None:
            raise ValueError(f"Unsupported car type '{option}'")
        await self.coordinator.async_set_car_field(self.car_id, "CarType", value)


class HomeDetectionSelect(CarEntity, SelectEntity):
    """How TeslaSolarCharger detects that the car is at home."""

    def __init__(self, coordinator, entry: ConfigEntry, car_id: int) -> None:
        """Initialize the select."""
        super().__init__(coordinator, entry, car_id)
        self.entity_description = select_description(
            "home_detection",
            HOME_DETECTION_OPTIONS,
            category=EntityCategory.CONFIG,
            enabled_default=False,
            icon="mdi:map-marker-radius-outline",
        )
        self._attr_unique_id = f"{entry.entry_id}_car_{car_id}_home_detection"

    @property
    def available(self) -> bool:
        """Return True when the car data is known."""
        return super().available and self.car is not None

    @property
    def current_option(self) -> str | None:
        """Return the configured way to detect the car at home."""
        return enum_name(
            self.car.basic if self.car else {},
            "HomeDetectionVia",
            HOME_DETECTION_BY_VALUE,
            HOME_DETECTION_OPTIONS,
        )

    async def async_select_option(self, option: str) -> None:
        """Change how the car is detected at home."""
        value = enum_name_from_value(
            option, HOME_DETECTION_BY_VALUE, HOME_DETECTION_OPTIONS
        )
        if value is None:
            raise ValueError(f"Unsupported home detection '{option}'")
        await self.coordinator.async_set_car_field(
            self.car_id, "HomeDetectionVia", value
        )
