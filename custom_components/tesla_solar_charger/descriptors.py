"""Declarative description of everything the TeslaSolarCharger API exposes.

TeslaSolarCharger keeps its settings in plain objects (``DtoBaseConfiguration``,
``CarBasicConfiguration``, ``DtoChargingStationConnector``) that are read and
written as a whole.  The specs below map those properties onto Home Assistant
entities, so adding another setting is a one-liner here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import (
    CURRENCY_EURO,
    PERCENTAGE,
    EntityCategory,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfLength,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfTime,
)

FieldKind = Literal["number", "bool", "text", "secret", "select"]
ValueSource = Literal[
    "base",  # DtoBaseConfiguration
    "basic",  # CarBasicConfiguration
    "overview",  # DtoCarOverviewSettings
    "details",  # DtoCar (live car data)
    "state",  # CarOverviewState (live car data of the web UI)
    "car_live",  # DtoCar with CarOverviewState as fallback
    "load_point",  # DtoLoadPointWithCurrentChargingValues
    "connector",  # DtoChargingStationConnector
    "connector_overview",  # DtoChargingConnectorOverviewSettings
    "connector_state",  # DtoChargingConnectorOverviewState
    "station",  # DtoChargingStation
    "pv",  # DtoPvValues
]


@dataclass(frozen=True, slots=True)
class FieldSpec:
    """One writable setting of TeslaSolarCharger."""

    field: str
    key: str
    kind: FieldKind
    unit: str | None = None
    minimum: float | None = None
    maximum: float | None = None
    step: float | None = None
    integer: bool = True
    category: EntityCategory | None = None
    enabled_default: bool = True
    max_length: int = 255
    icon: str | None = None
    options: tuple[str, ...] | None = None


@dataclass(frozen=True, slots=True)
class SensorSpec:
    """One readable value of TeslaSolarCharger."""

    key: str
    source: ValueSource
    field: str
    unit: str | None = None
    device_class: SensorDeviceClass | None = None
    state_class: SensorStateClass | None = None
    precision: int | None = None
    icon: str | None = None
    category: EntityCategory | None = None
    enabled_default: bool = True
    time_stamped: bool = False
    enum_map: bool = False
    fallback_field: str | None = None


@dataclass(frozen=True, slots=True)
class BinarySensorSpec:
    """One boolean value of TeslaSolarCharger."""

    key: str
    source: ValueSource
    field: str
    device_class: BinarySensorDeviceClass | None = None
    icon: str | None = None
    category: EntityCategory | None = None
    enabled_default: bool = True
    time_stamped: bool = False
    fallback_field: str | None = None


# ---------------------------------------------------------------------------
# DtoBaseConfiguration - the global settings of one TeslaSolarCharger instance
# ---------------------------------------------------------------------------
BASE_CONFIGURATION_CHARGING_FIELDS: tuple[FieldSpec, ...] = (
    FieldSpec("PowerBuffer", "power_buffer", "number", unit=UnitOfPower.WATT,
              minimum=-10000, maximum=100000, step=1),
    FieldSpec("MaxCombinedCurrent", "max_combined_current", "number",
              unit=UnitOfElectricCurrent.AMPERE, minimum=1, maximum=128, step=1),
    FieldSpec("MaxInverterAcPower", "max_inverter_ac_power", "number",
              unit=UnitOfPower.WATT, minimum=0, maximum=1000000, step=1,
              category=EntityCategory.CONFIG, enabled_default=False),
    FieldSpec("MinutesUntilSwitchOn", "minutes_until_switch_on", "number",
              unit=UnitOfTime.MINUTES, minimum=0, maximum=120, step=1),
    FieldSpec("MinutesUntilSwitchOff", "minutes_until_switch_off", "number",
              unit=UnitOfTime.MINUTES, minimum=0, maximum=120, step=1),
    FieldSpec("CarChargeLoss", "charge_loss", "number", unit=PERCENTAGE,
              minimum=0, maximum=100, step=1),
    FieldSpec("AllowPowerBufferChangeOnHome", "show_power_buffer_on_home", "bool"),
    FieldSpec("PredictSolarPowerGeneration", "predict_solar_power", "bool"),
    FieldSpec("UsePredictedSolarPowerGenerationForChargingSchedules",
              "use_predicted_solar_for_schedules", "bool",
              category=EntityCategory.CONFIG, enabled_default=False),
    FieldSpec("ShowEnergyDataOnHome", "show_energy_data", "bool",
              category=EntityCategory.CONFIG, enabled_default=False),
    # Home battery settings
    FieldSpec("HomeBatteryMinSoc", "home_battery_min_soc", "number",
              unit=PERCENTAGE, minimum=0, maximum=100, step=1),
    FieldSpec("HomeBatteryMaxChargeSoc", "home_battery_max_charge_soc", "number",
              unit=PERCENTAGE, minimum=0, maximum=100, step=1),
    FieldSpec("HomeBatteryChargingPower", "home_battery_charging_power", "number",
              unit=UnitOfPower.WATT, minimum=0, maximum=1000000, step=1),
    FieldSpec("HomeBatteryDischargingPower", "home_battery_discharging_power",
              "number", unit=UnitOfPower.WATT, minimum=0, maximum=1000000, step=1),
    FieldSpec("HomeBatteryUsableEnergy", "home_battery_usable_energy", "number",
              unit=UnitOfEnergy.KILO_WATT_HOUR, minimum=0, maximum=10000,
              step=0.1, integer=False),
    FieldSpec("DynamicHomeBatteryMinSoc", "dynamic_home_battery_min_soc", "bool",
              enabled_default=False),
    FieldSpec("HomeBatteryMinDynamicMinSoc", "min_dynamic_home_battery_min_soc",
              "number", unit=PERCENTAGE, minimum=0, maximum=100, step=1,
              category=EntityCategory.CONFIG, enabled_default=False),
    FieldSpec("HomeBatteryMaxDynamicMinSoc", "max_dynamic_home_battery_min_soc",
              "number", unit=PERCENTAGE, minimum=0, maximum=100, step=1,
              category=EntityCategory.CONFIG, enabled_default=False),
    FieldSpec("DynamicMinSocCalculationBuffer", "dynamic_min_soc_buffer", "number",
              unit=UnitOfPower.WATT, minimum=0, maximum=100000, step=1,
              category=EntityCategory.CONFIG, enabled_default=False),
    FieldSpec("HoldHomeBatteryChargeSocBuffer", "hold_home_battery_soc_buffer",
              "number", unit=PERCENTAGE, minimum=0, maximum=100, step=1,
              category=EntityCategory.CONFIG, enabled_default=False),
    FieldSpec("ChargeHomeBatterySocBuffer", "charge_home_battery_soc_buffer",
              "number", unit=PERCENTAGE, minimum=0, maximum=100, step=1,
              category=EntityCategory.CONFIG, enabled_default=False),
    FieldSpec("ForceFullHomeBatteryBySunset", "full_home_battery_by_sunset", "bool"),
    FieldSpec("DischargeHomeBatteryToMinSocDuringDay",
              "discharge_home_battery_during_day", "bool"),
    FieldSpec("GridPriceBasedHomeBatteryControl", "grid_price_home_battery_control",
              "bool", enabled_default=False),
    FieldSpec("HomeBatteryUsageCostsPerKwh", "home_battery_costs_per_kwh", "number",
              unit=CURRENCY_EURO, minimum=0, maximum=10, step=0.001, integer=False,
              category=EntityCategory.CONFIG, enabled_default=False),
    FieldSpec("ChargingSwitchCosts", "switching_costs", "number",
              unit=CURRENCY_EURO, minimum=0, maximum=10, step=0.001, integer=False,
              category=EntityCategory.CONFIG, enabled_default=False),
    FieldSpec("UseLearnedUsableEnergy", "use_learned_usable_energy", "bool",
              category=EntityCategory.CONFIG, enabled_default=False),
)


BASE_CONFIGURATION_ADVANCED_FIELDS: tuple[FieldSpec, ...] = (
    # Timing
    FieldSpec("UpdateIntervalSeconds", "power_change_interval", "number",
              unit=UnitOfTime.SECONDS, minimum=1, maximum=3600, step=1,
              category=EntityCategory.CONFIG, enabled_default=False),
    FieldSpec("SkipPowerChangesOnLastAdjustmentNewerThanSeconds",
              "skip_power_changes_interval", "number", unit=UnitOfTime.SECONDS,
              minimum=0, maximum=3600, step=1, category=EntityCategory.CONFIG,
              enabled_default=False),
    FieldSpec("PvValueUpdateIntervalSeconds", "value_update_interval", "number",
              unit=UnitOfTime.SECONDS, minimum=1, maximum=3600, step=1,
              category=EntityCategory.CONFIG, enabled_default=False),
    FieldSpec("MaxModbusErrorBackoffDuration", "modbus_error_backoff", "number",
              unit=UnitOfTime.SECONDS, minimum=1, maximum=86400, step=1,
              category=EntityCategory.CONFIG, enabled_default=False),
    # Geofence
    FieldSpec("HomeGeofenceLatitude", "home_latitude", "number",
              minimum=-90, maximum=90, step=0.000001, integer=False,
              category=EntityCategory.CONFIG, enabled_default=False),
    FieldSpec("HomeGeofenceLongitude", "home_longitude", "number",
              minimum=-180, maximum=180, step=0.000001, integer=False,
              category=EntityCategory.CONFIG, enabled_default=False),
    FieldSpec("HomeGeofenceRadius", "home_geofence_radius", "number",
              unit=UnitOfLength.METERS, minimum=1, maximum=10000, step=1,
              category=EntityCategory.CONFIG),
    FieldSpec("GeoFence", "teslamate_geofence_name", "text",
              category=EntityCategory.CONFIG, enabled_default=False),
    # BLE
    FieldSpec("GetVehicleDataViaBle", "use_ble_vehicle_data", "bool",
              category=EntityCategory.CONFIG, enabled_default=False),
    FieldSpec("UseBleDebug", "ble_debug", "bool", category=EntityCategory.CONFIG,
              enabled_default=False),
    FieldSpec("BleDataRefreshIntervalSeconds", "ble_data_refresh_interval", "number",
              unit=UnitOfTime.SECONDS, minimum=1, maximum=3600, step=1,
              category=EntityCategory.CONFIG, enabled_default=False),
    FieldSpec("BleSleepWindowMinutes", "ble_sleep_window", "number",
              unit=UnitOfTime.MINUTES, minimum=0, maximum=1440, step=1,
              category=EntityCategory.CONFIG, enabled_default=False),
    FieldSpec("BleSleepStabilityMinutes", "ble_sleep_stability", "number",
              unit=UnitOfTime.MINUTES, minimum=0, maximum=1440, step=1,
              category=EntityCategory.CONFIG, enabled_default=False),
    FieldSpec("BlePresenceMaxAgeSeconds", "ble_presence_max_age", "number",
              unit=UnitOfTime.SECONDS, minimum=1, maximum=86400, step=1,
              category=EntityCategory.CONFIG, enabled_default=False),
    FieldSpec("BleMissesBeforePresenceUncertain", "ble_misses_before_uncertain",
              "number", minimum=1, maximum=100, step=1,
              category=EntityCategory.CONFIG, enabled_default=False),
    FieldSpec("BleBeaconScanWindowSeconds", "ble_beacon_scan_window", "number",
              unit=UnitOfTime.SECONDS, minimum=1, maximum=3600, step=1,
              category=EntityCategory.CONFIG, enabled_default=False),
    FieldSpec("BleApiBaseUrl", "ble_api_base_url", "text",
              category=EntityCategory.CONFIG, enabled_default=False),
    # Correction factors
    FieldSpec("CurrentPowerToGridCorrectionFactor", "grid_power_correction_factor",
              "number", minimum=-100, maximum=100, step=0.01, integer=False,
              category=EntityCategory.CONFIG, enabled_default=False),
    FieldSpec("CurrentInverterPowerCorrectionFactor", "solar_power_correction_factor",
              "number", minimum=-100, maximum=100, step=0.01, integer=False,
              category=EntityCategory.CONFIG, enabled_default=False),
    FieldSpec("HomeBatterySocCorrectionFactor", "home_battery_soc_correction_factor",
              "number", minimum=-100, maximum=100, step=0.01, integer=False,
              category=EntityCategory.CONFIG, enabled_default=False),
    FieldSpec("HomeBatteryPowerCorrectionFactor", "home_battery_power_correction_factor",
              "number", minimum=-100, maximum=100, step=0.01, integer=False,
              category=EntityCategory.CONFIG, enabled_default=False),
)


BASE_CONFIGURATION_TEXT_FIELDS: tuple[FieldSpec, ...] = (
    FieldSpec("MqttClientIdPrefix", "mqtt_client_id_prefix", "text", max_length=20,
              category=EntityCategory.CONFIG, enabled_default=False),
    FieldSpec("CurrentPowerToGridUrl", "grid_power_url", "text",
              category=EntityCategory.CONFIG, enabled_default=False),
    FieldSpec("CurrentInverterPowerUrl", "solar_power_url", "text",
              category=EntityCategory.CONFIG, enabled_default=False),
    FieldSpec("HomeBatterySocUrl", "home_battery_soc_url", "text",
              category=EntityCategory.CONFIG, enabled_default=False),
    FieldSpec("HomeBatteryPowerUrl", "home_battery_power_url", "text",
              category=EntityCategory.CONFIG, enabled_default=False),
    FieldSpec("HomeBatteryPowerInversionUrl", "home_battery_inversion_url", "text",
              category=EntityCategory.CONFIG, enabled_default=False),
    FieldSpec("CurrentPowerToGridJsonPattern", "grid_power_json_pattern", "text",
              category=EntityCategory.CONFIG, enabled_default=False),
    FieldSpec("CurrentInverterPowerJsonPattern", "solar_power_json_pattern", "text",
              category=EntityCategory.CONFIG, enabled_default=False),
    FieldSpec("HomeBatterySocJsonPattern", "home_battery_soc_json_pattern", "text",
              category=EntityCategory.CONFIG, enabled_default=False),
    FieldSpec("HomeBatteryPowerJsonPattern", "home_battery_power_json_pattern", "text",
              category=EntityCategory.CONFIG, enabled_default=False),
    FieldSpec("HttpsAdditionalHostNames", "https_additional_host_names", "text",
              category=EntityCategory.CONFIG, enabled_default=False),
    FieldSpec("SolarMqttServer", "mqtt_server", "text",
              category=EntityCategory.CONFIG, enabled_default=False),
    FieldSpec("SolarMqttUserName", "mqtt_username", "text",
              category=EntityCategory.CONFIG, enabled_default=False),
    FieldSpec("SolarMqttPassword", "mqtt_password", "secret",
              category=EntityCategory.CONFIG, enabled_default=False),
    FieldSpec("TelegramBotKey", "telegram_bot_key", "secret",
              category=EntityCategory.CONFIG, enabled_default=False),
    FieldSpec("TelegramChannelId", "telegram_channel_id", "text",
              category=EntityCategory.CONFIG, enabled_default=False),
    FieldSpec("SendStackTraceToTelegram", "telegram_send_stack_trace", "bool",
              category=EntityCategory.CONFIG, enabled_default=False),
    FieldSpec("UseTeslaMateIntegration", "teslamate_integration", "bool",
              category=EntityCategory.CONFIG, enabled_default=False),
    FieldSpec("UseTeslaMateAsDataSource", "teslamate_as_data_source", "bool",
              category=EntityCategory.CONFIG, enabled_default=False),
    FieldSpec("TeslaMateDbServer", "teslamate_db_server", "text",
              category=EntityCategory.CONFIG, enabled_default=False),
    FieldSpec("TeslaMateDbPort", "teslamate_db_port", "number",
              minimum=1, maximum=65535, step=1, category=EntityCategory.CONFIG,
              enabled_default=False),
    FieldSpec("TeslaMateDbDatabaseName", "teslamate_db_name", "text",
              category=EntityCategory.CONFIG, enabled_default=False),
    FieldSpec("TeslaMateDbUser", "teslamate_db_user", "text",
              category=EntityCategory.CONFIG, enabled_default=False),
    FieldSpec("TeslaMateDbPassword", "teslamate_db_password", "secret",
              category=EntityCategory.CONFIG, enabled_default=False),
    FieldSpec("MosquitoServer", "mosquitto_server", "text",
              category=EntityCategory.CONFIG, enabled_default=False),
)

BASE_CONFIGURATION_FIELDS: tuple[FieldSpec, ...] = (
    BASE_CONFIGURATION_CHARGING_FIELDS
    + BASE_CONFIGURATION_ADVANCED_FIELDS
    + BASE_CONFIGURATION_TEXT_FIELDS
)

# ---------------------------------------------------------------------------
# CarBasicConfiguration - settings that belong to one car
# ---------------------------------------------------------------------------
CAR_BASIC_FIELDS: tuple[FieldSpec, ...] = (
    FieldSpec("ShouldBeManaged", "managed", "bool"),
    FieldSpec("MinimumAmpere", "minimum_current", "number",
              unit=UnitOfElectricCurrent.AMPERE, minimum=0, maximum=64, step=1,
              category=EntityCategory.CONFIG),
    FieldSpec("MaximumAmpere", "maximum_current", "number",
              unit=UnitOfElectricCurrent.AMPERE, minimum=1, maximum=64, step=1,
              category=EntityCategory.CONFIG),
    FieldSpec("MaximumPhases", "maximum_phases", "number", minimum=1, maximum=3,
              step=1, category=EntityCategory.CONFIG),
    FieldSpec("UsableEnergy", "usable_energy", "number",
              unit=UnitOfEnergy.KILO_WATT_HOUR, minimum=6, maximum=500, step=1,
              category=EntityCategory.CONFIG),
    FieldSpec("ChargingPriority", "charging_priority", "number", minimum=1,
              maximum=100, step=1, category=EntityCategory.CONFIG),
    FieldSpec("SwitchOnAtCurrent", "switch_on_current", "number",
              unit=UnitOfElectricCurrent.AMPERE, minimum=0, maximum=64, step=1,
              category=EntityCategory.CONFIG, enabled_default=False),
    FieldSpec("SwitchOffAtCurrent", "switch_off_current", "number",
              unit=UnitOfElectricCurrent.AMPERE, minimum=0, maximum=64, step=1,
              category=EntityCategory.CONFIG, enabled_default=False),
    FieldSpec("UseBle", "use_ble", "bool", category=EntityCategory.CONFIG,
              enabled_default=False),
    FieldSpec("UseFleetTelemetry", "use_fleet_telemetry", "bool",
              category=EntityCategory.CONFIG, enabled_default=False),
    FieldSpec("IncludeTrackingRelevantFields", "include_tracking_fields", "bool",
              category=EntityCategory.CONFIG, enabled_default=False),
)

# ---------------------------------------------------------------------------
# DtoChargingStationConnector - settings of one OCPP charging connector
# ---------------------------------------------------------------------------
CONNECTOR_FIELDS: tuple[FieldSpec, ...] = (
    FieldSpec("ShouldBeManaged", "managed", "bool"),
    FieldSpec("MinCurrent", "minimum_current", "number",
              unit=UnitOfElectricCurrent.AMPERE, minimum=0, maximum=128, step=1,
              category=EntityCategory.CONFIG),
    FieldSpec("MaxCurrent", "maximum_current", "number",
              unit=UnitOfElectricCurrent.AMPERE, minimum=1, maximum=128, step=1,
              category=EntityCategory.CONFIG),
    FieldSpec("ChargingPriority", "charging_priority", "number", minimum=1,
              maximum=100, step=1, category=EntityCategory.CONFIG),
    FieldSpec("ConnectedPhasesCount", "connected_phases", "number", minimum=1,
              maximum=3, step=1, category=EntityCategory.CONFIG),
    FieldSpec("SwitchOnAtCurrent", "switch_on_current", "number",
              unit=UnitOfElectricCurrent.AMPERE, minimum=0, maximum=128, step=1,
              category=EntityCategory.CONFIG, enabled_default=False),
    FieldSpec("SwitchOffAtCurrent", "switch_off_current", "number",
              unit=UnitOfElectricCurrent.AMPERE, minimum=0, maximum=128, step=1,
              category=EntityCategory.CONFIG, enabled_default=False),
    FieldSpec("PhaseSwitchCoolDownTimeSeconds", "phase_switch_cooldown", "number",
              unit=UnitOfTime.SECONDS, minimum=0, maximum=3600, step=1,
              category=EntityCategory.CONFIG, enabled_default=False),
    FieldSpec("AutoSwitchBetween1And3PhasesEnabled", "auto_phase_switch", "bool",
              category=EntityCategory.CONFIG, enabled_default=False),
    FieldSpec("AllowGuestCars", "allow_guest_cars", "bool",
              category=EntityCategory.CONFIG, enabled_default=False),
)

# ---------------------------------------------------------------------------
# Read only values
# ---------------------------------------------------------------------------
SERVICE_SENSORS: tuple[SensorSpec, ...] = (
    SensorSpec("grid_power", "pv", "GridPower", unit=UnitOfPower.WATT,
               device_class=SensorDeviceClass.POWER,
               state_class=SensorStateClass.MEASUREMENT),
    SensorSpec("solar_power", "pv", "InverterPower", unit=UnitOfPower.WATT,
               device_class=SensorDeviceClass.POWER,
               state_class=SensorStateClass.MEASUREMENT),
    SensorSpec("home_battery_power", "pv", "HomeBatteryPower", unit=UnitOfPower.WATT,
               device_class=SensorDeviceClass.POWER,
               state_class=SensorStateClass.MEASUREMENT),
    SensorSpec("home_battery_soc", "pv", "HomeBatterySoc", unit=PERCENTAGE,
               device_class=SensorDeviceClass.BATTERY),
    SensorSpec("cars_charging_power", "pv", "CarCombinedChargingPowerAtHome",
               unit=UnitOfPower.WATT, device_class=SensorDeviceClass.POWER,
               state_class=SensorStateClass.MEASUREMENT),
)

CAR_SENSORS: tuple[SensorSpec, ...] = (
    SensorSpec("soc", "car_live", "SoC", unit=PERCENTAGE,
               device_class=SensorDeviceClass.BATTERY, time_stamped=True),
    SensorSpec("soc_limit", "details", "SocLimit", unit=PERCENTAGE,
               icon="mdi:battery-charging", time_stamped=True,
               enabled_default=False),
    SensorSpec("charging_power", "load_point", "ChargingPower", unit=UnitOfPower.WATT,
               device_class=SensorDeviceClass.POWER,
               state_class=SensorStateClass.MEASUREMENT),
    SensorSpec("charging_current", "load_point", "ChargingCurrent",
               unit=UnitOfElectricCurrent.AMPERE,
               device_class=SensorDeviceClass.CURRENT,
               state_class=SensorStateClass.MEASUREMENT),
    SensorSpec("charging_voltage", "load_point", "ChargingVoltage",
               unit=UnitOfElectricPotential.VOLT,
               device_class=SensorDeviceClass.VOLTAGE,
               state_class=SensorStateClass.MEASUREMENT),
    SensorSpec("charging_phases", "load_point", "ChargingPhases",
               icon="mdi:lightning-bolt"),
    SensorSpec("set_current", "details", "LastSetAmp",
               unit=UnitOfElectricCurrent.AMPERE,
               device_class=SensorDeviceClass.CURRENT, time_stamped=True,
               category=EntityCategory.CONFIG),
    SensorSpec("requested_current", "details", "ChargerRequestedCurrent",
               unit=UnitOfElectricCurrent.AMPERE,
               device_class=SensorDeviceClass.CURRENT, time_stamped=True,
               enabled_default=False),
    SensorSpec("min_battery_temperature", "details", "MinBatteryTemperature",
               unit=UnitOfTemperature.CELSIUS, device_class=SensorDeviceClass.TEMPERATURE,
               state_class=SensorStateClass.MEASUREMENT, precision=1,
               enabled_default=False),
    SensorSpec("max_battery_temperature", "details", "MaxBatteryTemperature",
               unit=UnitOfTemperature.CELSIUS, device_class=SensorDeviceClass.TEMPERATURE,
               state_class=SensorStateClass.MEASUREMENT, precision=1,
               enabled_default=False),
    SensorSpec("distance_to_home", "details", "DistanceToHomeGeofence",
               unit=UnitOfLength.METERS, device_class=SensorDeviceClass.DISTANCE,
               enabled_default=False),
)

CAR_BINARY_SENSORS: tuple[BinarySensorSpec, ...] = (
    BinarySensorSpec("charging", "car_live", "IsCharging",
                     device_class=BinarySensorDeviceClass.BATTERY_CHARGING,
                     time_stamped=True),
    BinarySensorSpec("plugged_in", "car_live", "PluggedIn",
                     fallback_field="IsPluggedIn",
                     device_class=BinarySensorDeviceClass.PLUG, time_stamped=True),
    BinarySensorSpec("home", "car_live", "IsHomeGeofence",
                     fallback_field="IsHome",
                     device_class=BinarySensorDeviceClass.PRESENCE,
                     time_stamped=True),
    BinarySensorSpec("online", "car_live", "IsOnline",
                     device_class=BinarySensorDeviceClass.CONNECTIVITY,
                     time_stamped=True),
    BinarySensorSpec("should_start_charging", "details", "ShouldStartCharging",
                     icon="mdi:battery-arrow-up", time_stamped=True,
                     enabled_default=False),
)

CONNECTOR_SENSORS: tuple[SensorSpec, ...] = (
    SensorSpec("charging_power", "load_point", "ChargingPower", unit=UnitOfPower.WATT,
               device_class=SensorDeviceClass.POWER,
               state_class=SensorStateClass.MEASUREMENT),
    SensorSpec("charging_current", "load_point", "ChargingCurrent",
               unit=UnitOfElectricCurrent.AMPERE,
               device_class=SensorDeviceClass.CURRENT,
               state_class=SensorStateClass.MEASUREMENT),
    SensorSpec("charging_phases", "load_point", "ChargingPhases",
               icon="mdi:lightning-bolt", enabled_default=False),
)

CONNECTOR_BINARY_SENSORS: tuple[BinarySensorSpec, ...] = (
    BinarySensorSpec("charging", "connector_state", "IsCharging",
                     device_class=BinarySensorDeviceClass.BATTERY_CHARGING),
    BinarySensorSpec("plugged_in", "connector_state", "IsPluggedIn",
                     device_class=BinarySensorDeviceClass.PLUG),
    BinarySensorSpec("connected", "connector_state", "IsOcppConnected",
                     device_class=BinarySensorDeviceClass.CONNECTIVITY),
)

