"""Sensor platform for knmi."""
# sensor.py

from datetime import datetime
from typing import Any, Optional

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import CONF_NAME

from .const import DOMAIN, SENSORS, WIND_DIRECTIONS_ICON_MAP
from .entity import KnmiEntity


class KnmiSensor(KnmiEntity, SensorEntity):
    """Knmi Sensor class."""

    def __init__(
        self,
        coordinator,
        config_entry,
        name: str,
        unit_of_measurement: str,
        icon: str,
        device_class: str,
        attributes: list[dict[str, Any]],
        data_key: str,
    ) -> None:
        super().__init__(coordinator, config_entry)
        self.entry_name = config_entry.data.get(CONF_NAME)
        self._name = name
        self._unit_of_measurement = unit_of_measurement
        self._icon = icon
        self._device_class = device_class
        self._attributes = attributes
        self._data_key = data_key

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return f"{self.entry_name} {self._name}"

    @property
    def native_value(self) -> Any:
        """Return the native_value of the sensor."""
        return super().get_data(self._data_key)

    @property
    def native_unit_of_measurement(self) -> Optional[str]:
        """Return the unit of measurement of this entity, if any."""
        return self._unit_of_measurement

    @property
    def icon(self) -> str:
        if self._data_key in ["windrgr", "windr"]:
            windrgr_value = super().get_data("windrgr") # use windrgr value for both windrgr and windr
            if windrgr_value is not None:
                return wind_direction_icon(int(windrgr_value)) # convert string windrgr_value to int
        elif self._data_key == "temp":
            temp_value = super().get_data("temp")
            if temp_value is not None:
                return temperature_icon(float(temp_value))
        elif self._data_key == "d0neerslag":
            neerslag_value = super().get_data("d0neerslag")
            if neerslag_value is not None:
                return neerslag_icon(int(neerslag_value))

        return self._icon

    @property
    def device_class(self) -> str:
        """Return the device class."""
        return self._device_class

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the device state attributes."""
        attributes = super().extra_state_attributes
        for attribute in self._attributes:
            value = None
            if "key" in attribute:
                value = super().get_data(attribute.get("key", None))
            if "value" in attribute:
                value = attribute.get("value", None)
            attributes[attribute.get("name", None)] = value

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


async def async_setup_entry(hass, entry, async_add_devices):
    """Setup sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    sensors = []

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

    async_add_devices(sensors)


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
    Generate the icon name based on the temperature value.

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
