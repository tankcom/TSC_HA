"""Sensors of the TeslaSolarCharger integration."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .descriptors import (
    CAR_SENSORS,
    CONNECTOR_SENSORS,
    SERVICE_SENSORS,
    SensorSpec,
)
from .descriptions import sensor_description
from .entity import (
    CarEntity,
    ConnectorEntity,
    ServiceEntity,
    as_float,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensors of a config entry."""
    coordinator = entry.runtime_data.coordinator
    data = coordinator.data
    entities: list[SensorEntity] = [
        VersionSensor(coordinator, entry),
        IssueCountSensor(coordinator, entry),
    ]

    for spec in SERVICE_SENSORS:
        entities.append(ServiceSensorEntity(coordinator, entry, spec))

    for car_id in data.cars:
        for spec in CAR_SENSORS:
            entities.append(CarSensorEntity(coordinator, entry, car_id, spec))

    for connector_id in data.connectors:
        for spec in CONNECTOR_SENSORS:
            entities.append(
                ConnectorSensorEntity(coordinator, entry, connector_id, spec)
            )

    async_add_entities(entities)


class ServiceSensorEntity(ServiceEntity, SensorEntity):
    """A value that belongs to the TeslaSolarCharger installation."""

    def __init__(self, coordinator, entry: ConfigEntry, spec: SensorSpec) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._spec = spec
        self.entity_description = sensor_description(spec)
        self._attr_unique_id = f"{entry.entry_id}_base_{spec.key}"

    @property
    def native_value(self) -> Any:
        """Return the value of the sensor."""
        return as_float(
            self.read(
                self._spec.source,
                self._spec.field,
                time_stamped=self._spec.time_stamped,
                fallback_field=self._spec.fallback_field,
            )
        )


class CarSensorEntity(CarEntity, SensorEntity):
    """A value that belongs to one car."""

    def __init__(
        self, coordinator, entry: ConfigEntry, car_id: int, spec: SensorSpec
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, car_id)
        self._spec = spec
        self.entity_description = sensor_description(spec)
        self._attr_unique_id = f"{entry.entry_id}_car_{car_id}_{spec.key}"

    @property
    def available(self) -> bool:
        """Return True when the car data is known."""
        return super().available and self.car is not None

    @property
    def native_value(self) -> Any:
        """Return the value of the sensor."""
        return as_float(
            self.read(
                self._spec.source,
                self._spec.field,
                time_stamped=self._spec.time_stamped,
                fallback_field=self._spec.fallback_field,
            )
        )


class ConnectorSensorEntity(ConnectorEntity, SensorEntity):
    """A value that belongs to one charging connector."""

    def __init__(
        self, coordinator, entry: ConfigEntry, connector_id: int, spec: SensorSpec
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry, connector_id)
        self._spec = spec
        self.entity_description = sensor_description(spec)
        self._attr_unique_id = f"{entry.entry_id}_connector_{connector_id}_{spec.key}"

    @property
    def available(self) -> bool:
        """Return True when the connector data is known."""
        return super().available and self.connector is not None

    @property
    def native_value(self) -> Any:
        """Return the value of the sensor."""
        return as_float(
            self.read(
                self._spec.source,
                self._spec.field,
                time_stamped=self._spec.time_stamped,
                fallback_field=self._spec.fallback_field,
            )
        )


class VersionSensor(ServiceEntity, SensorEntity):
    """The installed version of TeslaSolarCharger."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:information-outline"

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_version"

    @property
    def native_value(self) -> str | None:
        """Return the version of TeslaSolarCharger."""
        data = self.coordinator.data
        return data.version if data else None


class IssueCountSensor(ServiceEntity, SensorEntity):
    """Number of issues TeslaSolarCharger reports on its start page."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:alert-circle-outline"

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_issues"

    @property
    def native_value(self) -> int | None:
        """Return the number of issues."""
        data = self.coordinator.data
        return data.issue_count if data else None
