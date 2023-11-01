"""KNMI Binary Sensor Platform."""
# binary_sensor.py

from datetime import datetime
from typing import Any, Callable

import pytz
from homeassistant.components.binary_sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.components.binary_sensor import (BinarySensorDeviceClass,
                                                    BinarySensorEntity)
from homeassistant.components.sensor import SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt

from .const import API_TIMEZONE, ATTRIBUTION, DOMAIN
from .coordinator import KnmiDataUpdateCoordinator


class KnmiBinarySensor(CoordinatorEntity[KnmiDataUpdateCoordinator], BinarySensorEntity):
    """Defines a KNMI binary sensor."""

    _attr_has_entity_name = True

    def __init__(
        self,
        conf_name: str,
        coordinator: KnmiDataUpdateCoordinator,
        entry_id: str,
        description: SensorEntityDescription,
        is_on_func: Callable[[KnmiDataUpdateCoordinator], bool],
        extra_attributes_func: Callable[[KnmiDataUpdateCoordinator], dict[str, Any] | None],
    ) -> None:
        """Initialize KNMI binary sensor."""
        super().__init__(coordinator=coordinator)

        self.entity_id = (
            f"{SENSOR_DOMAIN}.{conf_name}_{description.name}".lower()
        )
        self.entity_description = description
        self._attr_unique_id = f"{entry_id}-{conf_name} {self.name}"
        self._attr_device_info = coordinator.device_info
        self._is_on_func = is_on_func
        self._extra_attributes_func = extra_attributes_func

    @property
    def is_on(self) -> bool | None:
        """Return True if the entity is on."""
        return self._is_on_func(self.coordinator)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return entity specific state attributes."""
        return self._extra_attributes_func(self.coordinator)


def is_alarm_on(coordinator: KnmiDataUpdateCoordinator) -> bool:
    """Return True if the alarm is active."""
    value = coordinator.get_value("alarm", int)
    return value == 1

def is_sun_up(coordinator: KnmiDataUpdateCoordinator) -> bool:
    """Return True if the sun is currently up."""
    sup = coordinator.get_value("sup", str)
    sunder = coordinator.get_value("sunder", str)

    if sup is None or sunder is None:
        return None

    sunrise = _time_as_datetime(sup)
    sunset = _time_as_datetime(sunder)

    now = dt.utcnow()

    return sunrise < now < sunset


def _time_as_datetime(time: str) -> datetime:
    """Parse a time from a string like "08:13" to a datetime in UTC."""
    time_array = time.split(":")
    hour, minute = map(int, time_array)
    timezone = pytz.timezone(API_TIMEZONE)
    now = dt.now(timezone)
    time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    return dt.as_utc(time)


def get_alarm_attributes(coordinator: KnmiDataUpdateCoordinator) -> dict[str, Any]:
    """Return entity specific state attributes for the alarm sensor."""
    if is_alarm_on(coordinator):
        timestamp_int = int(coordinator.get_value("timestamp"))
        timestamp = datetime.fromtimestamp(timestamp_int).strftime("%Y-%m-%d %H:%M:%S")
        alarmtxt = coordinator.get_value("alarmtxt")

        attributes = {
            "Timestamp": timestamp,
            "Waarschuwing": alarmtxt,
            "attribution": ATTRIBUTION
        }
        
        return attributes


def get_sun_attributes(coordinator: KnmiDataUpdateCoordinator) -> dict[str, Any] | None:
    """Return entity specific state attributes for the sun sensor."""
    attributes = {}

    sup = coordinator.get_value("sup", str)
    sunder = coordinator.get_value("sunder", str)
    d0zon = coordinator.get_value("d0zon", int)
    d1zon = coordinator.get_value("d1zon", int)
    d2zon = coordinator.get_value("d2zon", int)

    if sup is not None:
        attributes["Zonsopkomst"] = _time_as_datetime(sup).isoformat()
    if sunder is not None:
        attributes["Zonsondergang"] = _time_as_datetime(sunder).isoformat()
    if d0zon is not None:
        attributes["Zonkans vandaag"] = d0zon
    if d1zon is not None:
        attributes["Zonkans morgen"] = d1zon
    if d2zon is not None:
        attributes["Zonkans overmorgen"] = d2zon

    attributes["attribution"] = ATTRIBUTION

    return attributes


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up KNMI binary sensors based on a config entry."""
    conf_name = entry.data.get(CONF_NAME, hass.config.location_name)
    coordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        [
            KnmiBinarySensor(
                conf_name=conf_name,
                coordinator=coordinator,
                entry_id=entry.entry_id,
                description=SensorEntityDescription(
                    key="alarm",
                    name="Waarschuwing",
                    icon="mdi:alert",
                    device_class=BinarySensorDeviceClass.SAFETY,
                ),
                is_on_func=is_alarm_on,
                extra_attributes_func=get_alarm_attributes,
            ),
            KnmiBinarySensor(
                conf_name=conf_name,
                coordinator=coordinator,
                entry_id=entry.entry_id,
                description=SensorEntityDescription(
                    key="sun",
                    name="Zon",
                    icon="mdi:white-balance-sunny",
                    device_class=BinarySensorDeviceClass.RUNNING,
                ),
                is_on_func=is_sun_up,
                extra_attributes_func=get_sun_attributes,
            ),
        ]
    )