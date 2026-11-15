"""Binary sensors of the TeslaSolarCharger integration."""

from __future__ import annotations

import logging

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .descriptors import (
    CAR_BINARY_SENSORS,
    CONNECTOR_BINARY_SENSORS,
    BinarySensorSpec,
)
from .descriptions import binary_sensor_description
from .entity import CarEntity, ConnectorEntity, as_bool

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the binary sensors of a config entry."""
    coordinator = entry.runtime_data.coordinator
    data = coordinator.data
    entities: list[BinarySensorEntity] = []

    for car_id in data.cars:
        for spec in CAR_BINARY_SENSORS:
            entities.append(CarBinarySensor(coordinator, entry, car_id, spec))

    for connector_id in data.connectors:
        for spec in CONNECTOR_BINARY_SENSORS:
            entities.append(
                ConnectorBinarySensor(coordinator, entry, connector_id, spec)
            )

    async_add_entities(entities)


class CarBinarySensor(CarEntity, BinarySensorEntity):
    """A boolean value of one car."""

    def __init__(
        self, coordinator, entry: ConfigEntry, car_id: int, spec: BinarySensorSpec
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, entry, car_id)
        self._spec = spec
        self.entity_description = binary_sensor_description(spec)
        self._attr_unique_id = f"{entry.entry_id}_car_{car_id}_{spec.key}"

    @property
    def available(self) -> bool:
        """Return True when the car data is known."""
        return super().available and self.car is not None

    @property
    def is_on(self) -> bool | None:
        """Return the current value."""
        return as_bool(
            self.read(
                self._spec.source,
                self._spec.field,
                time_stamped=self._spec.time_stamped,
                fallback_field=self._spec.fallback_field,
            )
        )


class ConnectorBinarySensor(ConnectorEntity, BinarySensorEntity):
    """A boolean value of one charging connector."""

    def __init__(
        self, coordinator, entry: ConfigEntry, connector_id: int, spec: BinarySensorSpec
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, entry, connector_id)
        self._spec = spec
        self.entity_description = binary_sensor_description(spec)
        self._attr_unique_id = f"{entry.entry_id}_connector_{connector_id}_{spec.key}"

    @property
    def available(self) -> bool:
        """Return True when the connector data is known."""
        return super().available and self.connector is not None

    @property
    def is_on(self) -> bool | None:
        """Return the current value."""
        return as_bool(
            self.read(
                self._spec.source,
                self._spec.field,
                time_stamped=self._spec.time_stamped,
                fallback_field=self._spec.fallback_field,
            )
        )
