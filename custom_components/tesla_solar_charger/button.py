"""Buttons for the one-shot actions of TeslaSolarCharger."""

from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .descriptions import button_description
from .entity import CarEntity, ServiceEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the buttons of a config entry."""
    coordinator = entry.runtime_data.coordinator
    entities: list[ButtonEntity] = [
        HomeBatteryLearningResetButton(coordinator, entry),
        TelegramTestButton(coordinator, entry),
    ]

    for car_id in coordinator.data.cars:
        entities.append(CarWakeUpButton(coordinator, entry, car_id))
        entities.append(CarUsableEnergyResetButton(coordinator, entry, car_id))

    async_add_entities(entities)


class CarWakeUpButton(CarEntity, ButtonEntity):
    """Wake up a car so TeslaSolarCharger can reach it again."""

    def __init__(self, coordinator, entry: ConfigEntry, car_id: int) -> None:
        """Initialize the button."""
        super().__init__(coordinator, entry, car_id)
        self.entity_description = button_description(
            "wake_up", category=EntityCategory.CONFIG, icon="mdi:car-key"
        )
        self._attr_unique_id = f"{entry.entry_id}_car_{car_id}_wake_up"

    @property
    def available(self) -> bool:
        """Return True when the car data is known."""
        return super().available and self.car is not None

    async def async_press(self) -> None:
        """Send the wake up call."""
        await self.coordinator.async_run_car_action(self.car_id, "wake_up")


class CarUsableEnergyResetButton(CarEntity, ButtonEntity):
    """Let TeslaSolarCharger forget the learned usable energy of a car."""

    def __init__(self, coordinator, entry: ConfigEntry, car_id: int) -> None:
        """Initialize the button."""
        super().__init__(coordinator, entry, car_id)
        self.entity_description = button_description(
            "reset_usable_energy",
            category=EntityCategory.CONFIG,
            enabled_default=False,
            icon="mdi:battery-sync",
        )
        self._attr_unique_id = f"{entry.entry_id}_car_{car_id}_reset_usable_energy"

    @property
    def available(self) -> bool:
        """Return True when the car data is known."""
        return super().available and self.car is not None

    async def async_press(self) -> None:
        """Reset the learned values."""
        await self.coordinator.async_run_car_action(self.car_id, "reset_usable_energy")


class HomeBatteryLearningResetButton(ServiceEntity, ButtonEntity):
    """Let TeslaSolarCharger forget the learned usable energy of the home battery."""

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        """Initialize the button."""
        super().__init__(coordinator, entry)
        self.entity_description = button_description(
            "reset_home_battery_learning",
            category=EntityCategory.CONFIG,
            enabled_default=False,
            icon="mdi:home-battery",
        )
        self._attr_unique_id = f"{entry.entry_id}_reset_home_battery_learning"

    async def async_press(self) -> None:
        """Reset the learned values."""
        await self.coordinator.async_run_service_action("reset_home_battery_learning")


class TelegramTestButton(ServiceEntity, ButtonEntity):
    """Ask TeslaSolarCharger to send a Telegram test message."""

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        """Initialize the button."""
        super().__init__(coordinator, entry)
        self.entity_description = button_description(
            "send_test_telegram_message",
            category=EntityCategory.CONFIG,
            enabled_default=False,
            icon="mdi:send",
        )
        self._attr_unique_id = f"{entry.entry_id}_send_test_telegram_message"

    async def async_press(self) -> None:
        """Send the test message."""
        await self.coordinator.async_run_service_action("send_test_telegram_message")
