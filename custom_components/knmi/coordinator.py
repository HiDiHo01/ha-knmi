"""DataUpdateCoordinator for knmi."""
# coordinator.py

import asyncio
import random
from datetime import datetime, timedelta
from typing import Any, Callable

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import (DataUpdateCoordinator,
                                                      UpdateFailed)

from .api import KnmiApiClient
from .const import _LOGGER, DATA_REFRESH_INTERVAL, DOMAIN
from .model import WeatherData


class KnmiDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the API."""

    config_entry: ConfigEntry
    options: dict = None

    def __init__(
        self,
        hass: HomeAssistant,
        client: KnmiApiClient,
        device_info: DeviceInfo,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize."""
        self.hass = hass
        self.config_entry = config_entry
        self.api = client
        self.device_info = device_info
        self.last_update_time: datetime | None = None
        self._timestamp = None

        # Get the refresh interval from the config entry options
        self.refresh_interval = self._get_refresh_interval()

        # Set the SCAN_INTERVAL to the refresh_interval
        self.update_interval = self.refresh_interval
        SCAN_INTERVAL = timedelta(seconds=self.refresh_interval)

        super().__init__(
            hass=hass, logger=_LOGGER, name=DOMAIN, update_interval=SCAN_INTERVAL
        )

    def _get_refresh_interval(self) -> int:
        """Get the refresh interval from the config entry options."""
        _LOGGER.debug("Getting refresh_interval")
        config_entry = self.config_entry
        config_options = self.config_entry.options
        if config_entry and "refresh_interval" in config_entry.options:
            _LOGGER.debug("refresh_interval exists in options")
            _LOGGER.debug("refresh_interval: %s", config_entry.options["refresh_interval"])
            self.refresh_interval = config_entry.options["refresh_interval"]
            return self.refresh_interval
        # config_entry = self.hass.config_entries.async_get_entry(DOMAIN)
        # if config_entry and "refresh_interval" in config_entry.options:
        # refresh_interval = config_entry.options.get("refresh_interval", 300)
        if self.options and "refresh_interval" in self.options:
            _LOGGER.debug("refresh_interval exists in options")
            return self.options["refresh_interval"]
        refresh_interval = self.hass.data.get(DOMAIN, {}).get("refresh_interval", 300)
        if refresh_interval:
            _LOGGER.debug("refresh_interval exist 2: %s", refresh_interval)

        if config_entry is None:
            _LOGGER.debug("Config entry does not exist")
        if config_entry:
            _LOGGER.debug("Config entry options: %s", config_entry.options)
            if "refresh_interval" in config_entry.options:
                _LOGGER.debug("refresh_interval is %s", config_entry.options["refresh_interval"])
                return config_entry.options["refresh_interval"]
        return DATA_REFRESH_INTERVAL  # Default to 300 seconds (5 minutes)

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from API endpoint.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.
        """
        if self.last_update_time is None:
            _LOGGER.debug("last_update_time is None")
        else:
            _LOGGER.debug("last_update_time is NOT None", self.last_update_time)
        if self._is_update_interval_passed():
            _LOGGER.debug("is_update_interval_passed is True")
        else:
            _LOGGER.debug("is_update_interval_passed is False")
        # Only update data when the time now > timestamp in data plus 10 minutes
        # It makes no sense to update before data is updated, this saves unnecessary api calls
        if (
            self.last_update_time is None
            or self._is_update_interval_passed()
        ):
            try:
                _LOGGER.debug("Fetching data from API...")
                data = await self.api.async_get_data()
                # Use WeatherData to parse the data
                weather_data = WeatherData(**data)
                self.data = weather_data
                self._update_timestamp(weather_data)
                self._schedule_next_update()
                # if self.api.notification_exists():
                if self.notification_exists():
                    _LOGGER.debug("Notification exists!")
                else:
                    _LOGGER.debug("Notification does not exist!")
                return data
                # Use WeatherData to parse the data
                # weather_data_list = parse_weather_data(knmi_data)
                # return weather_data_list
            except Exception as exception:
                _LOGGER.error("Error fetching KNMI data: %s", exception, exc_info=True)
                raise UpdateFailed() from exception
        else:
            # Return existing data if the update interval has not passed
            return self.data

    def get_value(
        self, key: str, convert_to: Callable = str
    ) -> float | int | str | None:
        """Get a value from the retrieved data and convert to given type"""
        if key in self.data:
            try:
                if ("d1tmin" in key or "d1tmax" in key or "d2tmin" in key or "d2tmax" in key) and "/" in self.data.get(key, None):
                    numerator, denominator = map(int, self.data.get(key, None).split('/'))
                    return convert_to((numerator + denominator) / 2)
                return convert_to(self.data.get(key, None))
            except ValueError:
                _LOGGER.warning("Value %s with key %s can't be converted to %s", self.data.get(key, None), key, convert_to)
                return None
        _LOGGER.warning("Value %s is missing in API response", key)
        return None

    def _is_update_interval_passed(self) -> bool:
        """Check if the update interval has passed since the last update."""
        if self.last_update_time is None:
            return True
        return datetime.now() >= self.last_update_time + timedelta(seconds=600)

    def _update_timestamp(self, data: WeatherData) -> None:
        """Update the timestamp based on the fetched data."""
        if data:
            timestamp = data.timestamp
            if timestamp is not None:
                try:
                    timestamp_int = int(timestamp)
                    self._timestamp = timestamp_int
                    self.last_update_time = datetime.fromtimestamp(timestamp_int)
                    _LOGGER.debug("_update_timestamp to %s", self.last_update_time)
                except ValueError:
                    _LOGGER.warning("Invalid timestamp format: %s", timestamp)
                    self.last_update_time = datetime.now()  # Set a fallback value
                    self._timestamp = None

    def _schedule_next_update(self) -> None:
        """Schedule the next update based on last_update_time + timedelta(minutes=11)."""
        if self.last_update_time is not None:
            next_update_time = self.last_update_time + timedelta(seconds=self.refresh_interval)
            _LOGGER.debug("self.refresh_interval: %s", self.refresh_interval)
            _LOGGER.debug("next_update_time exists")
            _LOGGER.debug("next_update_time: %s", next_update_time)

            now = datetime.now()

            if next_update_time > now:
                random_time = random.randint(1, 60)
                delay = (next_update_time - now).total_seconds() + random_time

                async def refresh():
                    await asyncio.sleep(delay)
                    await self.async_request_refresh()

                asyncio.create_task(refresh())

    def notification_exists(self) -> bool:
        """Check if the notification with notification_id exists."""
        return self.api.notification_exists()
