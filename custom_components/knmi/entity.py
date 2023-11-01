"""KnmiEntity class"""
# entity.py

import json
from datetime import datetime

from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (_LOGGER, AIR_PRESSURE_MAP, API_CONF_URL, ATTRIBUTION,
                    DOMAIN, HUMIDITY_MAP, NAME, TEMPERATURE_MAP, VERSION,
                    VISIBILITY_MAP, WIND_FORCE_MAP)


class KnmiEntity(CoordinatorEntity):
    """KNMI CoordinatorEntity"""

    def __init__(self, coordinator, config_entry):
        super().__init__(coordinator)
        self.coordinator = coordinator
        self.config_entry = config_entry
        self._timestamp: datetime | None = None

    def get_data(self, key: str) -> str | int | float | datetime | None:
        """Return the data key from the coordinator."""
        data = self.coordinator.data
        # this method is called for every sensor
        #_LOGGER.debug("Data received: %s", data)
        if data is None:
            return None

        # Check if data is a string and convert it to a dictionary
        if isinstance(data, str):
            _LOGGER.debug("Data is a string: %s", data)
            try:
                data = json.loads(data)
            except json.JSONDecodeError as e:
                _LOGGER.error("Failed to parse JSON data: %s", data)
                raise ValueError(f"Failed to parse JSON data: {data}") from e

        timestamp = data.get("timestamp")
        if timestamp is not None:
            self.update_timestamp(int(timestamp))

        if key == 'winddesc':
            winds_bft = data.get('winds')
            if winds_bft is not None:
                wind_speed_data = self.get_windforce_description(int(winds_bft))
                if wind_speed_data:
                    return wind_speed_data.get("benaming")

        if key == 'tempdesc':
            temperature = data.get('temp')
            if temperature is not None:
                return self.get_temperature_description(float(temperature))

        if key == 'air_pressure_desc':
            air_pressure = data.get('luchtd')
            if air_pressure is not None:
                return self.get_air_pressure_description(float(air_pressure))

        if key == 'lvdesc':
            humidity = data.get('lv')
            if humidity is not None:
                return self.get_humidity_description(int(humidity))

        if key == 'air_pressure_barometer':
            air_pressure = data.get('luchtd')
            if air_pressure is not None:
                return self.get_air_pressure_barometer(float(air_pressure))

        if key == 'zichtdesc':
            visibility = data.get('zicht')
            if visibility is not None:
                return self.get_visibility_description(int(visibility))

        if key == "timestamp":
            timestamp = data.get('timestamp')
            if timestamp is not None:
                return datetime.fromtimestamp(int(timestamp)).strftime("%d-%m-%Y %H:%M:%S")

        return data.get(key)

    @property
    def unique_id(self) -> str:
        """Return a unique ID to use for this entity."""
        return f"{self.config_entry.entry_id}-{self.name.lower().replace(' ', '_')}"

    @property
    def device_info(self) -> dict:
        return {
            "identifiers": {(DOMAIN, self.config_entry.entry_id)},
            "name": NAME,
            "model": "Weer informatie",
            "manufacturer": NAME,
            "entry_type": DeviceEntryType.SERVICE,
            "suggested_area": self.config_entry.title,
            "configuration_url": API_CONF_URL,
        }

    @property
    def extra_state_attributes(self) -> dict:
        """Return the state attributes."""
        return {
            "timestamp": self._timestamp,
            "attribution": ATTRIBUTION,
        }

    def update_timestamp(self, timestamp: int) -> None:
        """Update the timestamp."""
        self._timestamp = datetime.fromtimestamp(timestamp)

    def update(self) -> None:
        """Update the entity."""
        super().update()
        data = self.coordinator.data
        if data and "timestamp" in data:
            self.update_timestamp(int(data["timestamp"]))

    def get_temperature_description(self, temperature: float) -> str | None:
        """
        Get the description of the temperature based on the given temperature value.

        Args:
            temperature (float): The temperature value in Celsius.

        Returns:
            Optional[str]: The temperature description if found, None otherwise.
        """
        for temperature_range in TEMPERATURE_MAP.values():
            if temperature_range["range"][0] <= int(temperature) <= temperature_range["range"][1]:
                return temperature_range["short_description"]

    def get_windforce_description(self, windforce: int) -> dict | None:
        """
        Get the description of the wind force (Beaufort scale) based on the given wind force value.

        Args:
            windforce (int): The wind force value in Beaufort scale.

        Returns:
            Optional[dict[str, Any]]: The wind force description as a dictionary if found, None otherwise.
        """
        return WIND_FORCE_MAP.get(windforce, None)

    def get_air_pressure_description(self, air_pressure: float) -> str | None:
        """
        Get the description of the air pressure based on the given air pressure value.

        Args:
            air_pressure (float): The air pressure value in hPa.

        Returns:
            Optional[str]: The air pressure description if found, None otherwise.
        """
        for pressure_range in AIR_PRESSURE_MAP.values():
            if pressure_range["range"][0] <= int(air_pressure) <= pressure_range["range"][1]:
                return pressure_range["short_description"]

    def get_air_pressure_barometer(self, air_pressure: float) -> str | None:
        """
        Get the barometer of the air pressure based on the given air pressure value.

        Args:
            air_pressure (float): The air pressure value in hPa.

        Returns:
            Optional[str]: The air pressure barometer if found, None otherwise.
        """
        for pressure_range in AIR_PRESSURE_MAP.values():
            if pressure_range["range"][0] <= int(air_pressure) <= pressure_range["range"][1]:
                return pressure_range["barometer"]

    def get_humidity_description(self, humidity: int) -> str | None:
        """Get the short humidity description based on the humidity value."""
        for humidity_level, humidity_info in HUMIDITY_MAP.items():
            if humidity_info["range"][0] <= humidity < humidity_info["range"][1]:
                return humidity_info["short_description"]

    def get_visibility_description(self, visibility: int) -> str | None:
        """Get the short visibility description based on the visibility value."""
        for visibility_level, visibility_info in VISIBILITY_MAP.items():
            if visibility_info["range"][0] <= visibility < visibility_info["range"][1]:
                return visibility_info["short_description"]

testdata: dict[str, list[dict]] = {
    "liveweer": [
        {
            "plaats": "Schagen",
            "timestamp": "1689469384",
            "time": "16-07-2023 03:03",
            "temp": "18.1",
            "gtemp": "15.5",
            "samenv": "Zwaar bewolkt",
            "lv": "69",
            "windr": "ZW",
            "windrgr": "225",
            "windms": "13",
            "winds": "6",
            "windk": "25.3",
            "windkmh": "46.8",
            "luchtd": "1004.7",
            "ldmmhg": "754",
            "dauwp": "12",
            "zicht": "20",
            "verw": "Vandaag onstuimig, maandag enkele buien",
            "sup": "05:33",
            "sunder": "22:00",
            "image": "nachtbewolkt",
            "d0weer": "halfbewolkt",
            "d0tmax": "19",
            "d0tmin": "17",
            "d0windk": "6",
            "d0windknp": "25",
            "d0windms": "13",
            "d0windkmh": "46",
            "d0windr": "ZW",
            "d0windrgr": "225",
            "d0neerslag": "33",
            "d0zon": "57",
            "d1weer": "halfbewolkt",
            "d1tmax": "23",
            "d1tmin": "14",
            "d1windk": "3",
            "d1windknp": "8",
            "d1windms": "4",
            "d1windkmh": "15",
            "d1windr": "ZW",
            "d1windrgr": "225",
            "d1neerslag": "40",
            "d1zon": "40",
            "d2weer": "halfbewolkt",
            "d2tmax": "22",
            "d2tmin": "14",
            "d2windk": "3",
            "d2windknp": "8",
            "d2windms": "4",
            "d2windkmh": "15",
            "d2windr": "ZW",
            "d2windrgr": "225",
            "d2neerslag": "30",
            "d2zon": "40",
            "alarm": "1",
            "alarmtxt": "Aanvankelijk zijn er geen waarschuwingen van kracht.  In de nacht naar zondag en zondagochtend is er aan zee en in het Waddengebied kans op zware windstoten van 75-90 km/u, met mogelijk hinder voor verkeer en buitenactiviteiten.  De wind waait uit het zuidwesten en neemt in de tweede helft van zondagochtend weer iets af.",
        }
    ]
}