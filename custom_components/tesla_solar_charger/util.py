"""Helpers to read values from the TeslaSolarCharger API.

TeslaSolarCharger is a .NET (ASP.NET Core) service which serialises JSON with
Newtonsoft.Json default settings, therefore all property names are PascalCase
(``PowerBuffer``, ``MinSoc``, ``IsCharging`` ...) and .NET enums are transferred
as their integer values (``CarType.SmartCar`` is ``1000``, not an index!).
These helpers make the integration tolerant for both PascalCase and camelCase as
well as for enums sent as a string or as a number.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any


def get_item(data: Any, key: str, default: Any = None) -> Any:
    """Return a mapping value case-insensitively, ``default`` when missing."""
    if not isinstance(data, Mapping):
        return default
    if key in data:
        return data[key]
    wanted = key.lower()
    for name, value in data.items():
        if isinstance(name, str) and name.lower() == wanted:
            return value
    return default


def real_key(data: Any, key: str) -> str:
    """Return the key of ``data`` that matches ``key`` ignoring its case.

    Falls back to ``key`` itself so a value can still be written to an object
    that does not carry the property yet.
    """
    if not isinstance(data, Mapping):
        return key
    if key in data:
        return key
    wanted = key.lower()
    for name in data:
        if isinstance(name, str) and name.lower() == wanted:
            return name
    return key


def get_int(data: Any, key: str, default: int | None = None) -> int | None:
    """Return an integer value or ``default``."""
    value = get_item(data, key, default)
    if isinstance(value, bool) or value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def get_float(data: Any, key: str, default: float | None = None) -> float | None:
    """Return a float value or ``default``."""
    value = get_item(data, key, default)
    if isinstance(value, bool) or value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def get_bool(data: Any, key: str, default: bool | None = None) -> bool | None:
    """Return a boolean value or ``default`` (also accepts ``"true"``)."""
    value = get_item(data, key, None)
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in ("true", "1", "yes", "on"):
            return True
        if lowered in ("false", "0", "no", "off"):
            return False
    return default


def get_str(data: Any, key: str, default: str | None = None) -> str | None:
    """Return a string value or ``default``."""
    value = get_item(data, key, None)
    if value is None:
        return default
    if isinstance(value, str):
        return value
    return str(value)


def get_value(data: Any, default: Any = None) -> Any:
    """Return the value of a .NET ``DtoValue<T>`` wrapper (``{"Value": ...}``)."""
    return get_item(data, "Value", default)


def get_time_stamped(data: Any, key: str, default: Any = None) -> Any:
    """Return the value of a .NET ``DtoTimeStampedValue<T>`` property.

    Those look like ``{"Value": 42, "Timestamp": "2026-11-15T10:00:00+00:00"}``.
    Plain (already unwrapped) values are returned unchanged.
    """
    value = get_item(data, key)
    if isinstance(value, Mapping):
        return get_item(value, "Value", default)
    return default if value is None else value


def get_time_stamped_with_timestamp(
    data: Any, key: str
) -> tuple[Any, datetime | None]:
    """Return ``(value, timestamp)`` of a ``DtoTimeStampedValue<T>`` property."""
    wrapped = get_item(data, key)
    if isinstance(wrapped, Mapping):
        return get_item(wrapped, "Value"), parse_datetime(get_item(wrapped, "Timestamp"))
    return wrapped, None


def enum_name(
    data: Any,
    key: str,
    value_to_name: Mapping[int, str],
    allowed: Sequence[str] | None = None,
) -> str | None:
    """Return the enum member name of the property ``key``."""
    return enum_name_from_value(get_item(data, key), value_to_name, allowed)


def enum_name_from_value(
    value: Any,
    value_to_name: Mapping[int, str],
    allowed: Sequence[str] | None = None,
) -> str | None:
    """Convert an enum value (number or name) into its member name."""
    if value is None or isinstance(value, bool):
        return None
    name: str | None = None
    if isinstance(value, str):
        name = value
    elif isinstance(value, (int, float)):
        name = value_to_name.get(int(value))
    if name is None:
        return None
    if allowed is not None:
        for option in allowed:
            if option.lower() == name.lower():
                return option
        return None
    return name


def enum_value_for_name(
    option: str,
    value_to_name: Mapping[int, str],
    allowed: Sequence[str] | None = None,
) -> str:
    """Validate a selected option and return the name the API expects."""
    if allowed is not None and option not in allowed:
        for candidate in allowed:
            if candidate.lower() == option.lower():
                return candidate
        raise ValueError(f"Unsupported value '{option}', expected one of {allowed}")
    if option not in value_to_name.values():
        for number, name in value_to_name.items():
            if name.lower() == option.lower():
                return name
    return option


def parse_datetime(value: Any) -> datetime | None:
    """Parse an ISO-8601 timestamp returned by the API."""
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def build_url(host: str, port: int, use_ssl: bool) -> str:
    """Build the base URL of a TeslaSolarCharger installation from user input.

    Accepts values that already contain a scheme and/or a trailing slash; a
    scheme in ``host`` always wins over the ``use_ssl`` flag.
    """
    cleaned = host.strip()
    scheme, separator, rest = cleaned.partition("://")
    if separator:
        use_ssl = scheme.lower() in ("https", "wss")
        cleaned = rest
    cleaned = cleaned.strip("/")
    return f"{'https' if use_ssl else 'http'}://{cleaned}:{port}"

