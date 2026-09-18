"""Weather platform for knmi."""
# weather.py

import logging
from datetime import timedelta, timezone

from homeassistant.components.weather import (
    ATTR_FORECAST_CONDITION,
    ATTR_FORECAST_NATIVE_TEMP,
    ATTR_FORECAST_NATIVE_TEMP_LOW,
    ATTR_FORECAST_NATIVE_WIND_SPEED,
    ATTR_FORECAST_PRECIPITATION_PROBABILITY,
    ATTR_FORECAST_TIME,
    ATTR_FORECAST_WIND_BEARING,
    Forecast,
    WeatherEntity,
)
from homeassistant.components.weather.const import WeatherEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_NAME,
    UnitOfLength,
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
    UnitOfVolumetricFlux,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt

from .const import ATTRIBUTION, CONDITIONS_MAP, DOMAIN
from .coordinator import KnmiDataUpdateCoordinator
from .utils import safe_float, safe_int

_LOGGER: logging.Logger = logging.getLogger(__name__)
FORECAST_DATE_FORMAT = "%Y-%m-%d"


class KnmiWeather(CoordinatorEntity[KnmiDataUpdateCoordinator], WeatherEntity):
    """Defines a KNMI weather entity."""

    _attr_attribution = ATTRIBUTION
    _attr_native_pressure_unit = UnitOfPressure.HPA
    _attr_native_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_native_visibility_unit = UnitOfLength.KILOMETERS
    _attr_native_wind_speed_unit = UnitOfSpeed.KILOMETERS_PER_HOUR
    _attr_native_precipitation_unit = UnitOfVolumetricFlux.MILLIMETERS_PER_HOUR
    _attr_supported_features = WeatherEntityFeature.FORECAST_DAILY

    def __init__(
        self,
        conf_name: str,
        coordinator: KnmiDataUpdateCoordinator,
        entry_id: str,
    ):
        super().__init__(coordinator)
        self.conf_name = conf_name.capitalize()
        self._name = conf_name.capitalize()
        self.entry_id = entry_id
        self.entry_name: str = conf_name
        self._attr_unique_id = f"{entry_id}_{conf_name}"
        self._attr_name = f"Weer {conf_name}"
        self._attr_device_info = coordinator.device_info
        self._attr_supported_features = WeatherEntityFeature.FORECAST_DAILY
        self._logger = logging.getLogger(__name__)

    def map_condition(self, key: str | None) -> str | None:
        """Map weather conditions from KNMI to HA."""
        if key is None:
            return None

        value = self.coordinator.get_value(key, str)
        if not value:
            return None

        try:
            return CONDITIONS_MAP[str(value)]
        except KeyError:
            _LOGGER.error(
                "Weather condition %s (for %s) is unknown, please raise a bug",
                value,
                key,
            )
            return None

    def get_wind_bearing(
        self, wind_dir_key: str, wind_dir_degree_key: str
    ) -> float | str | None:
        """Get the wind bearing, handle variable (VAR) direction as None."""
        wind_dir = self.coordinator.get_value(wind_dir_key)
        if wind_dir == "VAR":
            _LOGGER.debug(
                "There is light wind from variable wind directions for %s, so no value",
                wind_dir_key,
            )
            return None
        return self.coordinator.get_value(wind_dir_degree_key, int)

    @property
    def condition(self) -> str | None:  # type: ignore[override]
        """Return the current weather condition."""
        return self.map_condition("image")

    @property
    def native_temperature(self) -> float | None:  # type: ignore[override]
        """Return the temperature in native units."""
        value = self.coordinator.get_value("temp", float)
        return safe_float(value)

    @property
    def native_pressure(self) -> float | None:  # type: ignore[override]
        """Return the pressure in native units."""
        value = self.coordinator.get_value("luchtd", float)
        return safe_float(value)

    @property
    def humidity(self) -> int | None:  # type: ignore[override]
        """Return the humidity in native units."""
        value = self.coordinator.get_value("lv", int)
        if value is None:
            return None
        try:
            return safe_int(value)
        except (ValueError, TypeError):
            _LOGGER.error(
                "Failed to convert humidity value '%s' to int for %s, returning None",
                value,
                "lv",
            )
            return None

    @property
    def native_wind_speed(self) -> float | None:  # type: ignore[override]
        """Return the wind speed in native units."""
        value = self.coordinator.get_value("windkmh", float)
        return safe_float(value)

    @property
    def wind_bearing(self) -> float | str | None:  # type: ignore[override]
        """Return wind bearing."""
        return self.get_wind_bearing("windr", "windrgr")

    @property
    def native_visibility(self) -> int | None:  # type: ignore[override]
        """Return the visibility in native units."""
        value = self.coordinator.get_value("zicht", int)
        return safe_int(value)

    def _forecast(self) -> list[Forecast] | None:
        """Generate a daily weather forecast for the next three days."""
        forecast: list[Forecast] = []
        FORCAST_DAYS = 3
        rfc3339_format = "%Y-%m-%dT%H:%M:%SZ"

        today = dt.start_of_local_day(dt.now())

        for i in range(FORCAST_DAYS):
            # Calculate the utc date for the forecast
            date = today.astimezone(timezone.utc) + timedelta(days=i)
            # Format the date as RFC 3339
            date_str: str = date.strftime(rfc3339_format)
            condition: str | None = self.map_condition(f"d{i}weer")
            wind_bearing: float | str | None = self.get_wind_bearing(f"d{i}windr", f"d{i}windrgr")
            temp_min_raw = self.coordinator.get_value(f"d{i}tmin", float)
            temp_min: float | int | None = safe_float(temp_min_raw) if temp_min_raw is not None else None
            temp_max_raw = self.coordinator.get_value(f"d{i}tmax", float)
            temp_max: float | int | None = safe_float(temp_max_raw) if temp_max_raw is not None else None
            precipitation_probability_raw = self.coordinator.get_value(f"d{i}neerslag", int)
            precipitation_probability: int | None = safe_int(
                precipitation_probability_raw) if precipitation_probability_raw is not None else None
            wind_speed_raw = self.coordinator.get_value(f"d{i}windkmh", int)
            wind_speed: int | None = safe_int(wind_speed_raw) if wind_speed_raw is not None else None

            next_day: Forecast = {
                ATTR_FORECAST_TIME: date_str,
                ATTR_FORECAST_CONDITION: condition,
                ATTR_FORECAST_NATIVE_TEMP_LOW: temp_min,
                ATTR_FORECAST_NATIVE_TEMP: temp_max,
                ATTR_FORECAST_PRECIPITATION_PROBABILITY: precipitation_probability,
                ATTR_FORECAST_WIND_BEARING: wind_bearing,
                ATTR_FORECAST_NATIVE_WIND_SPEED: wind_speed,
            }
            forecast.append(next_day)

        return forecast

    @property
    def forecast(self) -> list[Forecast] | None:
        """Return the forecast array."""
        return self._forecast()

    async def async_forecast_daily(self) -> list[Forecast] | None:
        """Return the daily forecast in native units."""
        return self._forecast()


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback
) -> None:
    """Set up KNMI weather entity from a config entry."""
    coordinator: KnmiDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    conf_name: str = entry.data.get(CONF_NAME, hass.config.location_name)
    _LOGGER.debug(
        "Setting up KNMI weather entity for entry %s with name '%s'",
        entry.entry_id,
        conf_name,
    )

    # Create an instance of KnmiWeather
    knmi_weather = KnmiWeather(
        conf_name=conf_name,
        coordinator=coordinator,
        entry_id=entry.entry_id
    )

    # Add the created entity to Home Assistant
    async_add_entities([knmi_weather])
