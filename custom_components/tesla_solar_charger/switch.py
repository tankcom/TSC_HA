"""Switch entities for the boolean settings of TeslaSolarCharger."""

from __future__ import annotations

import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .descriptors import (
    BASE_CONFIGURATION_FIELDS,
    CAR_BASIC_FIELDS,
    CONNECTOR_FIELDS,
    FieldSpec,
)
from .descriptions import switch_description
from .entity import CarEntity, ConnectorEntity, ServiceEntity, as_bool

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the switch entities of a config entry."""
    coordinator = entry.runtime_data.coordinator
    data = coordinator.data
    entities: list[SwitchEntity] = []

    for spec in BASE_CONFIGURATION_FIELDS:
        if spec.kind == "bool":
            entities.append(BaseConfigurationSwitch(coordinator, entry, spec))

    for car_id in data.cars:
        for spec in CAR_BASIC_FIELDS:
            if spec.kind == "bool":
                entities.append(CarBasicSwitch(coordinator, entry, car_id, spec))

    for connector_id in data.connectors:
        for spec in CONNECTOR_FIELDS:
            if spec.kind == "bool":
                entities.append(ConnectorSwitch(coordinator, entry, connector_id, spec))

    async_add_entities(entities)


class BaseConfigurationSwitch(ServiceEntity, SwitchEntity):
    """A boolean setting of the TeslaSolarCharger base configuration."""

    def __init__(self, coordinator, entry: ConfigEntry, spec: FieldSpec) -> None:
        """Initialize the switch."""
        super().__init__(coordinator, entry)
        self._spec = spec
        self.entity_description = switch_description(spec)
        self._attr_unique_id = f"{entry.entry_id}_base_{spec.key}"

    @property
    def is_on(self) -> bool | None:
        """Return the current value."""
        return as_bool(self.read("base", self._spec.field))

    async def async_turn_on(self, **kwargs: object) -> None:
        """Enable the setting."""
        await self.coordinator.async_set_base_configuration_value(self._spec.field, True)

    async def async_turn_off(self, **kwargs: object) -> None:
        """Disable the setting."""
        await self.coordinator.async_set_base_configuration_value(
            self._spec.field, False
        )


class CarBasicSwitch(CarEntity, SwitchEntity):
    """A boolean setting in the basic configuration of one car."""

    def __init__(
        self, coordinator, entry: ConfigEntry, car_id: int, spec: FieldSpec
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator, entry, car_id)
        self._spec = spec
        self.entity_description = switch_description(spec)
        self._attr_unique_id = f"{entry.entry_id}_car_{car_id}_{spec.key}"

    @property
    def available(self) -> bool:
        """Return True when the car data is known."""
        return super().available and self.car is not None

    @property
    def is_on(self) -> bool | None:
        """Return the current value."""
        return as_bool(self.read("basic", self._spec.field))

    async def async_turn_on(self, **kwargs: object) -> None:
        """Let TeslaSolarCharger manage this car."""
        await self.coordinator.async_set_car_field(self.car_id, self._spec.field, True)

    async def async_turn_off(self, **kwargs: object) -> None:
        """Stop TeslaSolarCharger from managing this car."""
        await self.coordinator.async_set_car_field(self.car_id, self._spec.field, False)


class ConnectorSwitch(ConnectorEntity, SwitchEntity):
    """A boolean setting of one charging connector."""

    def __init__(
        self, coordinator, entry: ConfigEntry, connector_id: int, spec: FieldSpec
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator, entry, connector_id)
        self._spec = spec
        self.entity_description = switch_description(spec)
        self._attr_unique_id = f"{entry.entry_id}_connector_{connector_id}_{spec.key}"

    @property
    def available(self) -> bool:
        """Return True when the connector data is known."""
        return super().available and self.connector is not None

    @property
    def is_on(self) -> bool | None:
        """Return the current value."""
        return as_bool(self.read("connector", self._spec.field))

    async def async_turn_on(self, **kwargs: object) -> None:
        """Enable the setting for this connector."""
        await self.coordinator.async_set_connector_field(
            self.connector_id, self._spec.field, True
        )

    async def async_turn_off(self, **kwargs: object) -> None:
        """Disable the setting for this connector."""
        await self.coordinator.async_set_connector_field(
            self.connector_id, self._spec.field, False
        )
