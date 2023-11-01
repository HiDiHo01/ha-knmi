"""Weather platform for knmi."""
# weather.py

from datetime import datetime, timedelta
from typing import Any

import pytz
import requests
from homeassistant.components.sensor import SensorEntity
from homeassistant.components.weather import (
    ATTR_FORECAST_CONDITION, ATTR_FORECAST_PRECIPITATION_PROBABILITY,
    ATTR_FORECAST_TEMP, ATTR_FORECAST_TEMP_LOW, ATTR_FORECAST_TIME,
    ATTR_FORECAST_WIND_BEARING, ATTR_FORECAST_WIND_SPEED)
from homeassistant.components.weather import DOMAIN as SENSOR_DOMAIN
from homeassistant.components.weather import (Forecast, WeatherEntity,
                                              WeatherEntityDescription,
                                              WeatherEntityFeature)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (CONF_NAME, PERCENTAGE, UnitOfLength,
                                 UnitOfPressure, UnitOfSpeed,
                                 UnitOfTemperature)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt

from .api import KnmiApiClient
from .const import _LOGGER, API_TIMEZONE, ATTRIBUTION, CONDITIONS_MAP, DOMAIN
from .coordinator import KnmiDataUpdateCoordinator
from .entity import KnmiEntity
from .exceptions import KnmiApiException

# Define the WeatherEntityDescription for the weather entity
WEATHER_DESCRIPTION = [
    WeatherEntityDescription(
        key="temp",
        name="Temperature",
        unit_of_measurement=UnitOfTemperature.CELSIUS,
    ),
    WeatherEntityDescription(
        key="d0weer",
        name="Condition",
    ),
    WeatherEntityDescription(
        key="luchtd",
        name="Pressure",
        unit_of_measurement=UnitOfPressure.HPA,
    ),
    WeatherEntityDescription(
        key="lv",
        name="Humidity",
        unit_of_measurement=PERCENTAGE,
    ),
    WeatherEntityDescription(
        key="windkmh",
        name="Wind Speed",
        unit_of_measurement=UnitOfSpeed.KILOMETERS_PER_HOUR,
    ),
    WeatherEntityDescription(
        key="windr",
        name="Wind Direction",
    ),
    WeatherEntityDescription(
        key="zicht",
        name="Visibility",
        unit_of_measurement=UnitOfLength.KILOMETERS,
    ),
    WeatherEntityDescription(
        key="d0windr",
        name="Today's Wind Direction",
    ),
    WeatherEntityDescription(
        key="d0windkmh",
        name="Today's Wind Speed",
        unit_of_measurement=UnitOfSpeed.KILOMETERS_PER_HOUR,
    ),
    WeatherEntityDescription(
        key="d0tmax",
        name="Today's Max Temperature",
        unit_of_measurement=UnitOfTemperature.CELSIUS,
    ),
    WeatherEntityDescription(
        key="d0tmin",
        name="Today's Min Temperature",
        unit_of_measurement=UnitOfTemperature.CELSIUS,
    ),
    WeatherEntityDescription(
        key="d0neerslag",
        name="Today's Precipitation",
        unit_of_measurement=PERCENTAGE,
    ),
    WeatherEntityDescription(
        key="d0zon",
        name="Today's Sun Chance",
        unit_of_measurement=PERCENTAGE,
    ),
    WeatherEntityDescription(
        key="d1windr",
        name="Tomorrow's Wind Direction",
    ),
    WeatherEntityDescription(
        key="d1windkmh",
        name="Tomorrow's Wind Speed",
        unit_of_measurement=UnitOfSpeed.KILOMETERS_PER_HOUR,
    ),
    WeatherEntityDescription(
        key="d1tmax",
        name="Tomorrow's Max Temperature",
        unit_of_measurement=UnitOfTemperature.CELSIUS,
    ),
    WeatherEntityDescription(
        key="d1tmin",
        name="Tomorrow's Min Temperature",
        unit_of_measurement=UnitOfTemperature.CELSIUS,
    ),
    WeatherEntityDescription(
        key="d1neerslag",
        name="Tomorrow's Precipitation",
        unit_of_measurement=PERCENTAGE,
    ),
    WeatherEntityDescription(
        key="d1zon",
        name="Tomorrow's Sun Chance",
        unit_of_measurement=PERCENTAGE,
    ),
    WeatherEntityDescription(
        key="d2windr",
        name="Day After Tomorrow's Wind Direction",
    ),
    WeatherEntityDescription(
        key="d2windkmh",
        name="Day After Tomorrow's Wind Speed",
        unit_of_measurement=UnitOfSpeed.KILOMETERS_PER_HOUR,
    ),
    WeatherEntityDescription(
        key="d2tmax",
        name="Day After Tomorrow's Max Temperature",
        unit_of_measurement=UnitOfTemperature.CELSIUS,
    ),
    WeatherEntityDescription(
        key="d2tmin",
        name="Day After Tomorrow's Min Temperature",
        unit_of_measurement=UnitOfTemperature.CELSIUS,
    ),
    WeatherEntityDescription(
        key="d2neerslag",
        name="Day After Tomorrow's Precipitation",
        unit_of_measurement=PERCENTAGE,
    ),
    WeatherEntityDescription(
        key="d2zon",
        name="Day After Tomorrow's Sun Chance",
        unit_of_measurement=PERCENTAGE,
    ),
]


class KnmiWeather(WeatherEntity, SensorEntity):
    """Defines a KNMI weather entity."""

    _attr_attribution = ATTRIBUTION
    _attr_native_pressure_unit = UnitOfPressure.HPA
    _attr_native_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_native_visibility_unit = UnitOfLength.KILOMETERS
    _attr_native_wind_speed_unit = UnitOfSpeed.KILOMETERS_PER_HOUR
    _attr_supported_features = WeatherEntityFeature.FORECAST_DAILY

    def __init__(
        self,
        conf_name: str,
        coordinator: KnmiDataUpdateCoordinator,
        entry_id: str,
    ):
        self.coordinator = coordinator
        self.conf_name = conf_name.capitalize()
        self._name = conf_name.capitalize()
        self.entry_id = entry_id
        self.entry_name: str = conf_name
        self.entity_id = f"{SENSOR_DOMAIN}.{conf_name}"
        self._attr_unique_id = f"{entry_id}-{conf_name}"
        self._attr_device_info = coordinator.device_info
        self._attr_supported_features = WeatherEntityFeature.FORECAST_DAILY
        self._attr_condition = self.map_condition("image")

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return f"Weer {self.entry_name}"

    def map_condition(self, key: str | None) -> str | None:
        """Map weather conditions from KNMI to HA."""
        value = self.coordinator.get_value(key, str)
        if value == "":
            return None

        try:
            return CONDITIONS_MAP[value]
        except KeyError:
            _LOGGER.error(
                "Weather condition %s (for %s) is unknown, please raise a bug",
                value,
                key,
            )
        return None

    def get_wind_bearing(
        self, wind_dir_key: str, wind_dir_degree_key: str
    ) -> float | None:
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
    def condition(self) -> str | None:
        """Return the current condition."""
        return self.map_condition("image")

    @property
    def native_temperature(self) -> float | None:
        """Return the temperature in native units."""
        return self.coordinator.get_value("temp", float)

    @property
    def native_pressure(self) -> float | None:
        """Return the pressure in native units."""
        return self.coordinator.get_value("luchtd", float)

    @property
    def humidity(self) -> int | None:
        """Return the humidity in native units."""
        return self.coordinator.get_value("lv", int)

    @property
    def native_wind_speed(self) -> float | None:
        """Return the wind speed in native units."""
        return self.coordinator.get_value("windkmh", float)

    @property
    def wind_bearing(self) -> float | str | None:
        """Return the wind bearing."""
        return self.get_wind_bearing("windr", "windrgr")

    @property
    def native_visibility(self) -> int | None:
        """Return the visibility in native units."""
        return self.coordinator.get_value("zicht", int)

    @property
    def forecast(self) -> list[Forecast] | None:
        """Return the forecast in native units."""
        forecast = []
        timezone = pytz.timezone(API_TIMEZONE)
        today = dt.as_utc(
            dt.now(timezone).replace(hour=0, minute=0, second=0, microsecond=0)
        )

        for i in range(0, 3):
            date = today + timedelta(days=i)
            condition = self.map_condition(f"d{i}weer")
            wind_bearing = self.get_wind_bearing(f"d{i}windr", f"d{i}windrgr")
            temp_min = self.coordinator.get_value(f"d{i}tmin", int)
            temp_max = self.coordinator.get_value(f"d{i}tmax", int)
            precipitation_probability = self.coordinator.get_value(
                f"d{i}neerslag", int
            )
            wind_speed = self.coordinator.get_value(f"d{i}windkmh", float)
            sun_chance = self.coordinator.get_value(f"d{i}zon", int)
            wind_speed_bft = self.coordinator.get_value(f"d{i}windk", int)
            next_day = {
                ATTR_FORECAST_TIME: date.isoformat(),
                ATTR_FORECAST_CONDITION: condition,
                ATTR_FORECAST_TEMP_LOW: temp_min,
                ATTR_FORECAST_TEMP: temp_max,
                ATTR_FORECAST_PRECIPITATION_PROBABILITY: precipitation_probability,
                ATTR_FORECAST_WIND_BEARING: wind_bearing,
                ATTR_FORECAST_WIND_SPEED: wind_speed,
                # Not officially supported, but nice additions.
                "wind_speed_bft": wind_speed_bft,
                "sun_chance": sun_chance,
            }
            forecast.append(next_day)

        return forecast

    def update_from_api_data(self, api_data: dict):
        self._attr_temperature = float(api_data["temp"])
        self._attr_wind_speed = float(api_data["windkmh"])
        self._attr_humidity = int(api_data["lv"])
        self._attr_wind_direction = api_data["windr"]
        self._attr_condition = self.map_condition("image")
        self.temperature = float(api_data["temp"])
        self.wind_speed = float(api_data["windkmh"])
        self.humidity = int(api_data["lv"])
        self.wind_direction = api_data["windr"]
        self.condition = self.map_condition("image")


    async def async_forecast_daily(self) -> list[Forecast] | None:
        """Return the daily forecast in native units.

        Only implement this method if `WeatherEntityFeature.FORECAST_DAILY` is set.
        """
        if WeatherEntityFeature.FORECAST_DAILY not in self.supported_features:
            return None

        try:
            daily_forecast_data = await self.coordinator.api.async_fetch_daily_forecast_data()
            return self.parse_forecast_data(daily_forecast_data)
        except KnmiApiException as e:
            _LOGGER.error("Error fetching daily forecast data: %s", e)
            return None

    def parse_forecast_data(self, forecast_data: list[dict[str, Any]]) -> list[Forecast]:
        forecast = []

        for entry in forecast_data:
            date_str = entry["date"]
            condition = entry["condition"]
            temp_min = entry["temp_min"]
            temp_max = entry["temp_max"]
            precipitation_probability = entry["precipitation_probability"]
            wind_bearing = entry["wind_bearing"]
            wind_speed = entry["wind_speed"]
            sun_chance = entry["sun_chance"]
            wind_speed_bft = entry["wind_speed_bft"]

            date = datetime.strptime(date_str, "%Y-%m-%d").date()

            forecast_entry = {
                ATTR_FORECAST_TIME: date.isoformat(),
                ATTR_FORECAST_CONDITION: condition,
                ATTR_FORECAST_TEMP_LOW: temp_min,
                ATTR_FORECAST_TEMP: temp_max,
                ATTR_FORECAST_PRECIPITATION_PROBABILITY: precipitation_probability,
                ATTR_FORECAST_WIND_BEARING: wind_bearing,
                ATTR_FORECAST_WIND_SPEED: wind_speed,
                # Not officially supported, but nice additions.
                "wind_speed_bft": wind_speed_bft,
                "sun_chance": sun_chance,
            }
            forecast.append(forecast_entry)

        return forecast

async def fetch_and_process_daily_forecast(api_client: KnmiApiClient):
    try:
        daily_forecast_data = await api_client.async_fetch_daily_forecast_data()
        # Process the daily_forecast_data here
        for forecast_entry in daily_forecast_data:
            date = forecast_entry["date"]
            condition = forecast_entry["condition"]
            temp_min = forecast_entry["temp_min"]
            temp_max = forecast_entry["temp_max"]
            precipitation_probability = forecast_entry["precipitation_probability"]
            wind_bearing = forecast_entry["wind_bearing"]
            wind_speed = forecast_entry["wind_speed"]
            #print(f"Date: {date}, Condition: {condition}, Temp Min: {temp_min}, Temp Max: {temp_max}, Precipitation Probability: {precipitation_probability}, Wind Bearing: {wind_bearing}, Wind Speed: {wind_speed}")
    except KnmiApiException as e:
        #print(f"Error fetching daily forecast data: {e}")
        raise Exception(f"Error fetching daily forecast data: {e}")

async def fetch_daily_forecast_data(self) -> list[dict[str, Any]]:
    try:
        response = await self.coordinator.api.async_fetch_daily_forecast_data()
        data = response.json()

        daily_forecast_data = []
        for entry in data["forecast"]:
            date_str = entry["date"]
            condition = entry["condition"]
            temp_min = entry["temp_min"]
            temp_max = entry["temp_max"]
            precipitation_probability = entry["precipitation_probability"]
            wind_bearing = entry["wind_bearing"]
            wind_speed = entry["wind_speed"]

            date = datetime.strptime(date_str, "%Y-%m-%d").date()

            forecast_entry = {
                "date": date,
                "condition": condition,
                "temp_min": temp_min,
                "temp_max": temp_max,
                "precipitation_probability": precipitation_probability,
                "wind_bearing": wind_bearing,
                "wind_speed": wind_speed,
            }
            daily_forecast_data.append(forecast_entry)

        return daily_forecast_data

    except requests.exceptions.RequestException as e:
        raise Exception(f"Error fetching daily forecast data: {e}")

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up KNMI weather based on a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    conf_name = entry.data.get(CONF_NAME, hass.config.location_name)
    # async_add_entities([KnmiWeather(conf_name, coordinator, entry.entry_id)])
    async_add_entities(
        [KnmiWeather(conf_name=entry.data.get(CONF_NAME, hass.config.location_name), coordinator=hass.data[DOMAIN][entry.entry_id], entry_id=entry.entry_id)]
    )