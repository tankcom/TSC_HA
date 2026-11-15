"""Number entities that expose the settings of TeslaSolarCharger."""

from __future__ import annotations

import logging

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfElectricCurrent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .descriptors import (
    BASE_CONFIGURATION_FIELDS,
    CAR_BASIC_FIELDS,
    CONNECTOR_FIELDS,
    FieldSpec,
)
from .descriptions import number_description
from .entity import (
    CarEntity,
    ConnectorEntity,
    ServiceEntity,
    as_float,
)

_LOGGER = logging.getLogger(__name__)

# Settings that are not part of CarBasicConfiguration but of the car overview.
MIN_SOC_SPEC = FieldSpec(
    "MinSoc", "min_soc", "number", unit=PERCENTAGE, minimum=0, maximum=100, step=1
)
MAX_SOC_SPEC = FieldSpec(
    "MaxSoc", "max_soc", "number", unit=PERCENTAGE, minimum=0, maximum=100, step=1
)
CHARGING_CURRENT_SPEC = FieldSpec(
    "ChargingCurrent",
    "charging_current_setpoint",
    "number",
    unit=UnitOfElectricCurrent.AMPERE,
    minimum=0,
    maximum=64,
    step=1,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the number entities of a config entry."""
    coordinator = entry.runtime_data.coordinator
    data = coordinator.data
    entities: list[NumberEntity] = []

    for spec in BASE_CONFIGURATION_FIELDS:
        if spec.kind == "number":
            entities.append(BaseConfigurationNumber(coordinator, entry, spec))

    for car_id in data.cars:
        for spec in CAR_BASIC_FIELDS:
            if spec.kind == "number":
                entities.append(CarBasicNumber(coordinator, entry, car_id, spec))
        for spec in (MIN_SOC_SPEC, MAX_SOC_SPEC):
            entities.append(CarOverviewNumber(coordinator, entry, car_id, spec))
        entities.append(
            CarChargingCurrentNumber(coordinator, entry, car_id, CHARGING_CURRENT_SPEC)
        )

    for connector_id in data.connectors:
        for spec in CONNECTOR_FIELDS:
            if spec.kind == "number":
                entities.append(
                    ConnectorNumber(coordinator, entry, connector_id, spec)
                )



class BaseConfigurationNumber(ServiceEntity, NumberEntity):
    """A global setting of the TeslaSolarCharger base configuration."""

    def __init__(
        self,
        coordinator,
        entry: ConfigEntry,
        spec: FieldSpec,
    ) -> None:
        """Initialize the number."""
        super().__init__(coordinator, entry)
        self._spec = spec
        self.entity_description = number_description(spec)
        self._attr_unique_id = f"{entry.entry_id}_base_{spec.key}"

    @property
    def native_value(self) -> float | None:
        """Return the current value from TeslaSolarCharger."""
        return as_float(self.read("base", self._spec.field))

    async def async_set_native_value(self, value: float) -> None:
        """Write the value back to TeslaSolarCharger."""
        await self.coordinator.async_set_base_configuration_value(
            self._spec.field,
            int(round(value)) if self._spec.integer else value,
        )


class CarBasicNumber(CarEntity, NumberEntity):
    """A setting stored in the basic configuration of one car."""

    def __init__(
        self,
        coordinator,
        entry: ConfigEntry,
        car_id: int,
        spec: FieldSpec,
    ) -> None:
        """Initialize the number."""
        super().__init__(coordinator, entry, car_id)
        self._spec = spec
        self.entity_description = number_description(spec)
        self._attr_unique_id = f"{entry.entry_id}_car_{car_id}_{spec.key}"

    @property
    def available(self) -> bool:
        """Return True when the car data is known."""
        return super().available and self.car is not None

    @property
    def native_value(self) -> float | None:
        """Return the current value from TeslaSolarCharger."""
        return as_float(self.read("basic", self._spec.field))

    async def async_set_native_value(self, value: float) -> None:
        """Write the value back to TeslaSolarCharger."""
        await self.coordinator.async_set_car_field(
            self.car_id,
            self._spec.field,
            int(round(value)) if self._spec.integer else value,
        )


class CarOverviewNumber(CarEntity, NumberEntity):
    """The minimum or maximum SoC of one car."""

    def __init__(
        self,
        coordinator,
        entry: ConfigEntry,
        car_id: int,
        spec: FieldSpec,
    ) -> None:
        """Initialize the number."""
        super().__init__(coordinator, entry, car_id)
        self._spec = spec
        self.entity_description = number_description(spec)
        self._attr_unique_id = f"{entry.entry_id}_car_{car_id}_{spec.key}"

    @property
    def available(self) -> bool:
        """Return True when the car data is known."""
        return super().available and self.car is not None

    @property
    def native_value(self) -> float | None:
        """Return the current value from TeslaSolarCharger."""
        return as_float(self.read("overview", self._spec.field))

    async def async_set_native_value(self, value: float) -> None:
        """Write the value back to TeslaSolarCharger."""
        await self.coordinator.async_set_car_overview_field(
            self.car_id, self._spec.field, int(round(value))
        )


class CarChargingCurrentNumber(CarEntity, NumberEntity):
    """The charging current TeslaSolarCharger last set for a car."""

    def __init__(
        self,
        coordinator,
        entry: ConfigEntry,
        car_id: int,
        spec: FieldSpec,
    ) -> None:
        """Initialize the number."""
        super().__init__(coordinator, entry, car_id)
        self._spec = spec
        self.entity_description = number_description(spec)
        self._attr_unique_id = f"{entry.entry_id}_car_{car_id}_set_current"

    @property
    def available(self) -> bool:
        """Return True when the car data is known."""
        return super().available and self.car is not None

    @property
    def native_value(self) -> float | None:
        """Return the current value from TeslaSolarCharger."""
        return as_float(self.read("details", "LastSetAmp", time_stamped=True))

    async def async_set_native_value(self, value: float) -> None:
        """Ask TeslaSolarCharger to charge the car with the given current."""
        await self.coordinator.async_set_car_charging_current(
            self.car_id, int(round(value))
        )


class ConnectorNumber(ConnectorEntity, NumberEntity):
    """A setting of one OCPP charging connector."""

    def __init__(
        self,
        coordinator,
        entry: ConfigEntry,
        connector_id: int,
        spec: FieldSpec,
    ) -> None:
        """Initialize the number."""
        super().__init__(coordinator, entry, connector_id)
        self._spec = spec
        self.entity_description = number_description(spec)
        self._attr_unique_id = f"{entry.entry_id}_connector_{connector_id}_{spec.key}"

    @property
    def available(self) -> bool:
        """Return True when the connector data is known."""
        return super().available and self.connector is not None

    @property
    def native_value(self) -> float | None:
        """Return the current value from TeslaSolarCharger."""
        return as_float(self.read("connector", self._spec.field))

    async def async_set_native_value(self, value: float) -> None:
        """Write the value back to TeslaSolarCharger."""
        await self.coordinator.async_set_connector_field(
            self.connector_id,
            self._spec.field,
            int(round(value)) if self._spec.integer else value,
        )

    async_add_entities(entities)
