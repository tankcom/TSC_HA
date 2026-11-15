"""Builders that turn the descriptor specs into Home Assistant descriptions."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntityDescription
from homeassistant.components.button import ButtonEntityDescription
from homeassistant.components.number import NumberEntityDescription, NumberMode
from homeassistant.components.select import SelectEntityDescription
from homeassistant.components.sensor import SensorEntityDescription
from homeassistant.components.switch import SwitchEntityDescription
from homeassistant.components.text import TextEntityDescription, TextMode

from .descriptors import BinarySensorSpec, FieldSpec, SensorSpec


def number_description(spec: FieldSpec) -> NumberEntityDescription:
    """Return the number description of a setting."""
    minimum = spec.minimum if spec.minimum is not None else 0
    maximum = spec.maximum if spec.maximum is not None else 100
    return NumberEntityDescription(
        key=spec.key,
        translation_key=spec.key,
        native_unit_of_measurement=spec.unit,
        native_min_value=spec.minimum,
        native_max_value=spec.maximum,
        native_step=spec.step,
        mode=(
            NumberMode.BOX if maximum - minimum > 20 else NumberMode.AUTO
        ),
        entity_category=spec.category,
        icon=spec.icon,
        entity_registry_enabled_default=spec.enabled_default,
    )


def switch_description(spec: FieldSpec) -> SwitchEntityDescription:
    """Return the switch description of a boolean setting."""
    return SwitchEntityDescription(
        key=spec.key,
        translation_key=spec.key,
        entity_category=spec.category,
        icon=spec.icon,
        entity_registry_enabled_default=spec.enabled_default,
    )


def text_description(spec: FieldSpec) -> TextEntityDescription:
    """Return the text description of a string setting."""
    return TextEntityDescription(
        key=spec.key,
        translation_key=spec.key,
        mode=TextMode.PASSWORD if spec.kind == "secret" else TextMode.TEXT,
        native_max=spec.max_length,
        entity_category=spec.category,
        icon=spec.icon,
        entity_registry_enabled_default=spec.enabled_default,
    )


def select_description(
    key: str,
    options: tuple[str, ...],
    *,
    category=None,
    enabled_default: bool = True,
    icon: str | None = None,
) -> SelectEntityDescription:
    """Return the select description of an enum setting."""
    return SelectEntityDescription(
        key=key,
        translation_key=key,
        options=list(options),
        entity_category=category,
        icon=icon,
        entity_registry_enabled_default=enabled_default,
    )


def sensor_description(spec: SensorSpec) -> SensorEntityDescription:
    """Return the sensor description of a value."""
    return SensorEntityDescription(
        key=spec.key,
        translation_key=spec.key,
        native_unit_of_measurement=spec.unit,
        device_class=spec.device_class,
        state_class=spec.state_class,
        suggested_display_precision=spec.precision,
        icon=spec.icon,
        entity_category=spec.category,
        entity_registry_enabled_default=spec.enabled_default,
    )


def binary_sensor_description(
    spec: BinarySensorSpec,
) -> BinarySensorEntityDescription:
    """Return the binary sensor description of a boolean value."""
    return BinarySensorEntityDescription(
        key=spec.key,
        translation_key=spec.key,
        device_class=spec.device_class,
        icon=spec.icon,
        entity_registry_enabled_default=spec.enabled_default,
    )


def button_description(
    key: str,
    *,
    category=None,
    enabled_default: bool = True,
    icon: str | None = None,
) -> ButtonEntityDescription:
    """Return the button description of a one-shot action."""
    return ButtonEntityDescription(
        key=key,
        translation_key=key,
        entity_category=category,
        icon=icon,
        entity_registry_enabled_default=enabled_default,
    )
