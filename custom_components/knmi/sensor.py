"""Sensor platform for knmi."""
# sensor.py

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from .const import DOMAIN, SENSORS, WIND_DIRECTIONS_ICON_MAP
from .entity import KnmiEntity


class KnmiSensor(KnmiEntity, SensorEntity):
    """Knmi Sensor class."""

    def __init__(
        self,
        coordinator: object,
        config_entry: ConfigEntry,
        name: str,
        unit_of_measurement: str | None,
        icon: str,
        device_class: str | None,
        attributes: list[dict[str, Any]],
        data_key: str,
    ) -> None:
        super().__init__(coordinator, config_entry)
        self.entry_name = config_entry.data.get(CONF_NAME, "")
        self._name = name
        self._unit_of_measurement = unit_of_measurement
        self._icon = icon
        self._device_class = device_class
        self._attributes = attributes
        self._data_key = data_key

    @property
    def name(self) -> str:  # type: ignore[override]
        """Return the name of the sensor."""
        return f"{self.entry_name} {self._name}".strip()

    @property
    def native_value(self) -> StateType:  # type: ignore[override]
        """Return the native value of the sensor."""
        value = super().get_data(self._data_key)
        if value is None:
            return None
        if isinstance(value, datetime):
            return str(value.isoformat())
        if isinstance(value, (str, int, float)):
            return value  # str, int, float
        return str(value)  # fallback for unsupported types

    @property
    def native_unit_of_measurement(self) -> str | None:  # type: ignore[override]
        """Return the unit of measurement of this entity, if any."""
        return self._unit_of_measurement

    @property
    def icon(self) -> str:  # type: ignore[override]
        """Return the appropriate icon for the sensor."""
        value = super().get_data(self._data_key)

        if self._data_key in ["windrgr", "windr"] and value is not None:
            windrgr_value = safe_int(super().get_data("windrgr"))
            if windrgr_value is not None:
                return wind_direction_icon(windrgr_value)

        elif self._data_key == "temp" and value is not None:
            temp_value = safe_float(value)
            if temp_value is not None:
                return temperature_icon(temp_value)

        elif self._data_key == "d0neerslag" and value is not None:
            neerslag_value = safe_int(value)
            if neerslag_value is not None:
                return neerslag_icon(neerslag_value)

        return self._icon

    @property
    def device_class(self) -> str | None:  # type: ignore[override]
        """Return the device class."""
        return self._device_class

    @property
    def extra_state_attributes(self) -> dict[str, Any]:  # type: ignore[override]
        """Return the device state attributes."""
        attributes = dict(super().extra_state_attributes or {})
        for attribute in self._attributes:
            key = attribute.get("key")
            value = attribute.get("value")
            if key is not None:
                value = super().get_data(key)
            attributes[attribute.get("name", "")] = value
        return attributes

# not in use


def format_timestamp(timestamp: int) -> str:
    """
    Format a timestamp into a human-readable date and time string.

    Args:
        timestamp (str): The timestamp value as a string.

    Returns:
        str: The formatted date and time string or an empty string if invalid timestamp.
    """
    try:
        timestamp_int = int(timestamp)
        formatted_time = datetime.fromtimestamp(timestamp_int).strftime("%Y-%m-%d %H:%M:%S")
        return formatted_time
    except (ValueError, TypeError):
        return ""

# async def async_setup_entry(hass, entry, async_add_devices):


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Setup sensor platform with KNMI sensors from config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    sensors: list[KnmiSensor] = []

    for sensor in SENSORS:
        sensors.append(
            KnmiSensor(
                coordinator,
                entry,
                sensor.get("name", None),
                sensor.get("unit_of_measurement", None),
                sensor.get("icon", None),
                sensor.get("device_class", None),
                sensor.get("attributes", []),
                sensor.get("key", None),
            )
        )

    async_add_entities(sensors)


def wind_direction_icon(wind_direction_degrees: int) -> str:
    """
    Generate the icon name based on wind direction degrees.

    Args:
        wind_direction_degrees (int): Wind direction in degrees.

    Returns:
        str: The icon name in the format 'mdi:icon-name'.
    """
    # Calculate the wind direction value in degrees (0 to 360)
    direction = wind_direction_degrees % 360

    # Find the closest wind direction value in the dictionary
    closest_direction = min(WIND_DIRECTIONS_ICON_MAP, key=lambda angle: abs(direction - angle))

    # Handle cases where the direction does not exactly match any predefined angle
    if abs(direction - closest_direction) > 22.5:
        # Round the direction to the nearest 45-degree angle
        closest_direction = round(direction / 45) * 45

    # Get the icon name from the directions dictionary, using the closest wind direction value
    icon_direction = WIND_DIRECTIONS_ICON_MAP.get(closest_direction, 'compass-outline')
    # mdi:arrow-bottom-left

    # Return the icon name in the format 'mdi:icon-name'
    return f"mdi:{icon_direction}"


def temperature_icon(temperature: float) -> str:
    """
    Generate the icon name based on the temperature value.

    Args:
        temperature (Union[float, int, str]): Temperature value.

    Returns:
        str: The icon name in the format 'mdi:icon-name'.
    """
    try:
        temperature = float(temperature)
    except (ValueError, TypeError):
        return "mdi:thermometer-off"  # Default temperature icon for invalid temperature values

    if temperature >= 30 or temperature <= 2:
        temp_icon = "mdi:thermometer-alert"  # Verry high and freeze alert temperature icon
    elif temperature >= 25:
        temp_icon = "mdi:thermometer-high"  # High temperature icon
    elif temperature <= 10:
        temp_icon = "mdi:thermometer-low"  # Low temperature icon
    else:
        temp_icon = "mdi:thermometer"  # Default temperature icon
    return temp_icon


def neerslag_icon(neerslag: int) -> str:
    """
    Generate the icon name based on the neerslag value.

    Args:
        temperature (Union[float, int, str]): Temperature value.

    Returns:
        str: The icon name in the format 'mdi:icon-name'.
    """
    try:
        neerslag = int(neerslag)
    except (ValueError, TypeError):
        return "mdi:cloud-off-outline"  # Default temperature icon for invalid temperature values

    if neerslag >= 25:
        neer_icon = "mdi:weather-pouring"
    elif neerslag == 0:
        neer_icon = "mdi:cloud-outline"
    else:
        neer_icon = "mdi:weather-rainy"
    return neer_icon


def safe_int(value: object) -> int | None:
    """
    Safely convert a value to an integer.

    Supports:
    - int
    - float
    - str (if numeric)
    - datetime (converted to UNIX timestamp)

    Returns None if conversion fails.
    """
    try:
        if isinstance(value, datetime):
            return int(value.timestamp())
        if isinstance(value, (int, float)):
            return int(value)
        if isinstance(value, str) and value.isdigit():
            return int(value)
    except (TypeError, ValueError):
        pass
    return None


def safe_float(value: object) -> float | None:
    """
    Safely convert a value to a float.

    Supports:
    - int
    - float
    - str (if numeric)
    - datetime (converted to UNIX timestamp)

    Returns None if conversion fails.
    """
    try:
        if isinstance(value, datetime):
            return float(value.timestamp())
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            return float(value)
    except (TypeError, ValueError):
        pass
    return None
