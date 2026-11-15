"""Constants for the TeslaSolarCharger integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "tesla_solar_charger"
INTEGRATION_NAME: Final = "TeslaSolarCharger"
MANUFACTURER: Final = "TeslaSolarCharger"

PLATFORMS: Final[list[str]] = [
    "binary_sensor",
    "button",
    "number",
    "select",
    "sensor",
    "switch",
    "text",
]

# --- Configuration / options keys -------------------------------------------
CONF_USE_SSL: Final = "use_ssl"
CONF_VERIFY_SSL: Final = "verify_ssl"
CONF_API_KEY: Final = "api_key"
CONF_API_KEY_HEADER: Final = "api_key_header"
CONF_UPDATE_INTERVAL_SECONDS: Final = "update_interval_seconds"

# --- Defaults ----------------------------------------------------------------
DEFAULT_PORT: Final = 7190
DEFAULT_UPDATE_INTERVAL_SECONDS: Final = 30
MINIMUM_UPDATE_INTERVAL_SECONDS: Final = 5
DEFAULT_TIMEOUT_SECONDS: Final = 15
DEFAULT_API_KEY_HEADER: Final = "x-api-key"

# --- Services ----------------------------------------------------------------
SERVICE_SET_BASE_CONFIGURATION_VALUE: Final = "set_base_configuration_value"

# --- TeslaSolarCharger data type keys used by the LiveData / SignalR API -----
DATA_TYPE_PV_VALUES: Final = "PvValues"
DATA_TYPE_LOAD_POINT_OVERVIEW: Final = "LoadPointOverviewValues"
DATA_TYPE_CAR_OVERVIEW_STATE: Final = "CarOverviewState"
DATA_TYPE_CHARGING_CONNECTOR_OVERVIEW_STATE: Final = "ChargingConnectorOverviewState"

# --- Enums exposed by the TeslaSolarCharger API ------------------------------
# ChargeModeV2 (TeslaSolarCharger/Shared/Enums/ChargeModeV2.cs)
CHARGE_MODE_OPTIONS: Final[tuple[str, ...]] = ("Off", "Manual", "Auto", "MaxPower")
CHARGE_MODE_BY_VALUE: Final[dict[int, str]] = {
    0: "Off",
    1: "Manual",
    2: "Auto",
    3: "MaxPower",
}

# CarType (Manual=0, Tesla=1, SmartCar=1000 - not contiguous on purpose!)
CAR_TYPE_OPTIONS: Final[tuple[str, ...]] = ("Manual", "Tesla", "SmartCar")
CAR_TYPE_BY_VALUE: Final[dict[int, str]] = {0: "Manual", 1: "Tesla", 1000: "SmartCar"}

# HomeDetectionVia
HOME_DETECTION_OPTIONS: Final[tuple[str, ...]] = (
    "GpsLocation",
    "LocatedAtHome",
    "LocatedAtWork",
    "LocatedAtFavorite",
    "BlePresence",
)
HOME_DETECTION_BY_VALUE: Final[dict[int, str]] = {
    0: "GpsLocation",
    1: "LocatedAtHome",
    2: "LocatedAtWork",
    3: "LocatedAtFavorite",
    4: "BlePresence",
}

# --- Device identifier prefixes ---------------------------------------------
IDENTIFIER_SERVICE_PREFIX: Final = "service"
IDENTIFIER_CAR_PREFIX: Final = "car"
IDENTIFIER_CHARGING_STATION_PREFIX: Final = "charging_station"
IDENTIFIER_CONNECTOR_PREFIX: Final = "connector"
