"""Text entities for the string settings of TeslaSolarCharger."""

from __future__ import annotations

import logging

from homeassistant.components.text import TextEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .descriptors import BASE_CONFIGURATION_FIELDS, FieldSpec
from .descriptions import text_description
from .entity import ServiceEntity, as_str

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the text entities of a config entry."""
    coordinator = entry.runtime_data.coordinator
    entities: list[TextEntity] = [
        BaseConfigurationText(coordinator, entry, spec)
        for spec in BASE_CONFIGURATION_FIELDS
        if spec.kind in ("text", "secret")
    ]
    async_add_entities(entities)


class BaseConfigurationText(ServiceEntity, TextEntity):
    """A string setting of the TeslaSolarCharger base configuration."""

    def __init__(self, coordinator, entry: ConfigEntry, spec: FieldSpec) -> None:
        """Initialize the text entity."""
        super().__init__(coordinator, entry)
        self._spec = spec
        self.entity_description = text_description(spec)
        self._attr_unique_id = f"{entry.entry_id}_base_{spec.key}"

    @property
    def native_value(self) -> str | None:
        """Return the current value stored in TeslaSolarCharger."""
        value = self.read("base", self._spec.field)
        return as_str(value) if value is not None else ""

    async def async_set_value(self, value: str) -> None:
        """Write the value back to TeslaSolarCharger."""
        if self._spec.max_length and len(value) > self._spec.max_length:
            raise ServiceValidationError(
                translation_key="text_too_long",
                translation_placeholders={
                    "field": self._spec.field,
                    "max": str(self._spec.max_length),
                },
            )
        await self.coordinator.async_set_base_configuration_value(self._spec.field, value)
