"""Constants for knmi."""
# const.py

import logging
from datetime import timedelta
from typing import Any, Final

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.components.weather import (ATTR_CONDITION_CLEAR_NIGHT,
                                              ATTR_CONDITION_CLOUDY,
                                              ATTR_CONDITION_FOG,
                                              ATTR_CONDITION_HAIL,
                                              ATTR_CONDITION_LIGHTNING,
                                              ATTR_CONDITION_LIGHTNING_RAINY,
                                              ATTR_CONDITION_PARTLYCLOUDY,
                                              ATTR_CONDITION_POURING,
                                              ATTR_CONDITION_RAINY,
                                              ATTR_CONDITION_SNOWY,
                                              ATTR_CONDITION_SNOWY_RAINY,
                                              ATTR_CONDITION_SUNNY,
                                              ATTR_CONDITION_WINDY)
from homeassistant.const import (DEGREE, PERCENTAGE, UnitOfLength,
                                 UnitOfPressure, UnitOfSpeed,
                                 UnitOfTemperature)

# API
API_ENDPOINT: Final[str] = "https://weerlive.nl/api/json-data-10min.php?key={}&locatie={},{}"
API_TIMEOUT: Final[int] = 15
API_TIMEZONE: Final[str] = "Europe/Amsterdam"
API_CONF_URL: Final[str] = "https://weerlive.nl/api/toegang/account.php"
LIVEWEER_KEY: Final[str] = "liveweer"
WIND_BEAUFORT: Final[str] = "Bft"

# Base component constants.
NAME: Final[str] = "KNMI"
DOMAIN: Final[str] = "knmi"
VERSION: Final[str] = "1.6.1"
ATTRIBUTION: Final[str] = "Data provided by KNMI"

# Defaults
DEFAULT_NAME: Final[str] = NAME
_LOGGER: logging.Logger = logging.getLogger(__name__)
DEFAULT_AIR_PRESSURE_HPA: Final[int] = 1013

# API and Data Refresh
MAX_API_CALLS_PER_DAY: Final[int] = 300
# max 300 calls per day API limit = 288 sec * 300 = 86400 sec = 1 day
# api data is only refreshed every 600 seconds
SCAN_INTERVAL = timedelta(seconds=300)
DATA_REFRESH_INTERVAL: Final[int] = 600

# Platforms.
BINARY_SENSOR: Final[str] = "binary_sensor"
SENSOR: Final[str] = "sensor"
WEATHER: Final[str] = "weather"
PLATFORMS: Final[list[str]] = [BINARY_SENSOR, SENSOR, WEATHER]

# Icon templates (not in use)
ICON_TEMPLATE: Final[str] = "mdi:weather-{}"
WIND_DIRECTION_TEMPLATE: Final[str] = "mdi:weather-windy-{}"

# Conversion values
KMH_KNOT: Final[float] = 0.53996  # knots
MS_KNOT: Final[float] = 1.9438  # knots
KNOT_KMH: Final[float] = 1.852  # km/h
KNOT_MS: Final[float] = 0.5144  # m/s
KMH_MS: Final[float] = 0.2778  # m/s
MS_KMH: Final[float] = 3.6  # km/h
hPa_mmHg: Final[float] = 0.75006  # mmHg
mmHg_hPa: Final[float] = 1.33322  # hPa

# Binary sensors
BINARY_SENSORS: Final[list[dict[str, Any]]] = [
    {
        "name": "Waarschuwing",
        "unit": "",
        "icon": "mdi:alert",
        "key": "alarm",
        "device_class": BinarySensorDeviceClass.SAFETY,
        "attributes": [
            {
                "name": "Waarschuwing",
                "key": "alarmtxt",
            },
        ],
    },
]

# Sensors
SENSORS: Final[list] = [
    {
        "name": "Omschrijving",
        "icon": "mdi:text",
        "key": "samenv",
    },
    {
        "name": "Plaats",
        "icon": "mdi:map-marker",
        "key": "plaats",
    },
    {
        "name": "Korte dagverwachting",
        "icon": "mdi:text",
        "key": "verw",
    },
    {
        "name": "Dauwpunt",
        "unit_of_measurement": UnitOfTemperature.CELSIUS,
        "icon": "mdi:thermometer",
        "key": "dauwp",
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
    },
    {
        "name": "Gevoelstemperatuur",
        "unit_of_measurement": UnitOfTemperature.CELSIUS,
        "icon": "mdi:thermometer",
        "key": "gtemp",
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
    },
    {
        "name": "Temperatuur",
        "unit_of_measurement": UnitOfTemperature.CELSIUS,
        "icon": "mdi:thermometer",
        "key": "temp",
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
    },
    {
        "name": "Minimum temperatuur",
        "unit_of_measurement": UnitOfTemperature.CELSIUS,
        "icon": "mdi:thermometer-chevron-down",
        "key": "d0tmin",
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
    },
    {
        "name": "Maximum temperatuur",
        "unit_of_measurement": UnitOfTemperature.CELSIUS,
        "icon": "mdi:thermometer-chevron-up",
        "key": "d0tmax",
        "device_class": SensorDeviceClass.TEMPERATURE,
        "state_class": SensorStateClass.MEASUREMENT,
    },
    {
        "name": "Temperatuur omschrijving",
        "icon": "mdi:text",
        "key": "tempdesc",
    },
    {
        "name": "Windrichting",
        "icon": "mdi:compass-outline",
        "key": "windr",
        "state_class": SensorStateClass.MEASUREMENT
    },
    {
        "name": "Windrichting graden",
        "unit_of_measurement": DEGREE,
        "icon": "mdi:compass-outline",
        'device_class': 'direction',
        "key": "windrgr",
        "state_class": SensorStateClass.MEASUREMENT
    },
    {
        "name": "Windsnelheid m/s",
        "unit_of_measurement": UnitOfSpeed.METERS_PER_SECOND,
        "icon": "mdi:weather-windy",
        "key": "windms",
        "device_class": SensorDeviceClass.WIND_SPEED,
        "state_class": SensorStateClass.MEASUREMENT,
    },
    {
        "name": "Windsnelheid km/h",
        "unit_of_measurement": UnitOfSpeed.KILOMETERS_PER_HOUR,
        "icon": "mdi:weather-windy",
        "key": "windkmh",
        "device_class": SensorDeviceClass.WIND_SPEED,
        "state_class": SensorStateClass.MEASUREMENT,
    },
    {
        "name": "Windsnelheid knopen",
        "unit_of_measurement": UnitOfSpeed.KNOTS,
        "icon": "mdi:weather-windy",
        "key": "windk",
        "device_class": SensorDeviceClass.WIND_SPEED,
        "state_class": SensorStateClass.MEASUREMENT,
    },
    {
        "name": "Windkracht Beaufort",
        "unit_of_measurement": WIND_BEAUFORT,
        "icon": "mdi:weather-windy",
        "key": "winds",
        "state_class": SensorStateClass.MEASUREMENT,
    },
    {
        "name": "Wind omschrijving",
        "icon": "mdi:text",
        "key": "winddesc",
    },
    {
        "name": "Relatieve luchtvochtigheid",
        "unit_of_measurement": PERCENTAGE,
        "icon": "mdi:water-percent",
        "key": "lv",
        "device_class": SensorDeviceClass.HUMIDITY,
        "state_class": SensorStateClass.MEASUREMENT,
    },
    {
        "name": "Luchtvochtigheid omschrijving",
        "icon": "mdi:text",
        "key": "lvdesc",
    },
    {
        "name": "Luchtdruk",
        "unit_of_measurement": UnitOfPressure.HPA,
        "icon": "mdi:gauge",
        "key": "luchtd",
        "device_class": SensorDeviceClass.PRESSURE,
        "state_class": SensorStateClass.MEASUREMENT,
    },
    {
        "name": "Luchtdruk mmHg",
        "unit_of_measurement": UnitOfPressure.MMHG,
        "icon": "mdi:gauge",
        "key": "ldmmhg",
        "device_class": SensorDeviceClass.PRESSURE,
        "state_class": SensorStateClass.MEASUREMENT,
    },
    {
        "name": "Luchtdruk omschrijving",
        "icon": "mdi:text",
        "key": "air_pressure_desc",
    },
    {
        "name": "Barometer",
        "icon": "mdi:text",
        "key": "air_pressure_barometer",
    },
    {
        "name": "Zicht",
        "unit_of_measurement": UnitOfLength.KILOMETERS,
        "icon": "mdi:arrow-left-right",
        "key": "zicht",
        "device_class": SensorDeviceClass.DISTANCE,
        "state_class": SensorStateClass.MEASUREMENT,
    },
    {
        "name": "Zicht omschrijving",
        "icon": "mdi:text",
        "key": "zichtdesc",
    },
    {
        "name": "Zonsopkomst",
        "icon": "mdi:weather-sunset-up",
        "key": "sup",
        "state_class": SensorStateClass.MEASUREMENT,
    },
    {
        "name": "Zonsondergang",
        "icon": "mdi:weather-sunset-down",
        "key": "sunder",
        "state_class": SensorStateClass.MEASUREMENT,
    },
    {
        "name": "Kans op neerslag vandaag",
        "unit_of_measurement": PERCENTAGE,
        "icon": "mdi:weather-rainy",
        "key": "d0neerslag",
        "state_class": SensorStateClass.MEASUREMENT,
    },
    {
        "name": "Kans op zon vandaag",
        "unit_of_measurement": PERCENTAGE,
        "icon": "mdi:weather-sunny",
        "key": "d0zon",
        "state_class": SensorStateClass.MEASUREMENT,
    },
    {
        "name": "Laatste update",
        "icon": "mdi:clock",
        "device_class": None,
        "attributes": [],
        "key": "timestamp",
    },
]

# Map weather conditions from KNMI to HA.
CONDITIONS_MAP: Final[dict[str, str]] = {
    "bliksem": ATTR_CONDITION_LIGHTNING,
    "bliksemregen": ATTR_CONDITION_LIGHTNING_RAINY,
    "regen": ATTR_CONDITION_RAINY,
    "buien": ATTR_CONDITION_POURING,
    "hagel": ATTR_CONDITION_HAIL,
    "mist": ATTR_CONDITION_FOG,
    "sneeuw": ATTR_CONDITION_SNOWY,
    "sneeuwregen": ATTR_CONDITION_SNOWY_RAINY,
    "bewolkt": ATTR_CONDITION_CLOUDY,
    "halfbewolkt": ATTR_CONDITION_PARTLYCLOUDY,
    "lichtbewolkt": ATTR_CONDITION_PARTLYCLOUDY,
    "halfbewolkt_regen": ATTR_CONDITION_PARTLYCLOUDY,
    "nachtbewolkt": ATTR_CONDITION_CLOUDY,
    "nachtmist": ATTR_CONDITION_FOG,
    "helderenacht": ATTR_CONDITION_CLEAR_NIGHT,
    "wolkennacht": ATTR_CONDITION_CLOUDY,
    "wind": ATTR_CONDITION_WINDY,
    "zonnig": ATTR_CONDITION_SUNNY,
    "zwaarbewolkt": ATTR_CONDITION_CLOUDY,
}

# Map wind direction from KNMI string to number.
WIND_DIRECTION_MAP: Final[dict[str, float | None]] = {
    "VAR": None,
    "N": 360,
    "Noord": 360,
    "NNO": 22.5,
    "NO": 45,
    "ONO": 67.5,
    "O": 90,
    "Oost": 90,
    "OZO": 112.5,
    "ZO": 135,
    "ZZO": 157.5,
    "Z": 180,
    "Zuid": 180,
    "ZZW": 202.5,
    "ZW": 225,
    "WZW": 247.5,
    "W": 270,
    "West": 270,
    "WNW": 292.5,
    "NW": 315,
    "NNW": 337.5,
}

# Define the wind directions and their corresponding icon names
WIND_DIRECTIONS_ICON_MAP = {
    0: 'arrow-down-thick',
    45: 'arrow-bottom-left-thick',
    90: 'arrow-left-thick',
    135: 'arrow-top-left-thick',
    180: 'arrow-up-thick',
    225: 'arrow-top-right-thick',
    270: 'arrow-right-thick',
    315: 'arrow-bottom-right-thick',
}

TEMPERATURE_MAP: Final[dict[str, dict[str, any]]] = {
    "-30": {
        "range": (-30, -20),
        "short_description": "Extreem koud",
        "description": "Onmiddellijke bevriezing mogelijk aan blootgestelde huid."
    },
    "-20": {
        "range": (-20, -10),
        "short_description": "Zeer koud",
        "description": "Bijtende kou, gevoelloosheid zelfs onder geïsoleerde kleding."
    },
    "-10": {
        "range": (-10, 0),
        "short_description": "Erg koud",
        "description": "Voelt ijzig aan, ongemakkelijk, vooral bij wind."
    },
    "0": {
        "range": (0, 10),
        "short_description": "Koud",
        "description": "Fris, maar comfortabel met de juiste kleding."
    },
    "5": {
        "range": (5, 10),
        "short_description": "Koel tot milde kou",
        "description": "Nog steeds fris, maar minder ongemakkelijk."
    },
    "10": {
        "range": (10, 15),
        "short_description": "Fris",
        "description": "Aangenaam, vooral in lente of herfst."
    },
    "15": {
        "range": (15, 20),
        "short_description": "Aangenaam",
        "description": "Comfortabele temperatuur, lichte jas of trui is voldoende."
    },
    "20": {
        "range": (20, 25),
        "short_description": "Warm",
        "description": "Lekker warm, ideaal voor buitenactiviteiten."
    },
    "25": {
        "range": (25, 30),
        "short_description": "Warm tot heet",
        "description": "Aangenaam zomergevoel."
    },
    "30": {
        "range": (30, 35),
        "short_description": "Heet",
        "description": "Ongemakkelijk, vooral bij hoge luchtvochtigheid."
    },
    "35": {
        "range": (35, 40),
        "short_description": "Erg heet",
        "description": "Gezondheidsrisico's bij langdurige blootstelling."
    },
    "40": {
        "range": (40, 50),
        "short_description": "Zeer heet",
        "description": "Potentieel gevaarlijk, risico op oververhitting."
    },
    "50": {
        "range": (50, 100),
        "short_description": "Extreem heet",
        "description": "Levensbedreigende omstandigheden voor de meeste mensen."
    },
}

TEMPERATURE_ALERT_MAP: Final[dict[str, dict[str, Any]]] = {
    "geel_koud": {"range": (-5, 0), "description": "Code geel", "alert": "Code Geel: Vorstwaarschuwing voor lichte vorst"},
    "oranje_koud": {"range": (-10, -6), "description": "Code oranje", "alert": "Code Oranje: Vorstwaarschuwing voor matige vorst"},
    "rood_koud": {"range": (-50, -11), "description": "Code rood", "alert": "Code Rood: Vorstwaarschuwing voor strenge vorst"},
    "geel_warm": {"range": (25, 30), "description": "Code geel", "alert": "Code Geel: Waarschuwing voor aanhoudend warm weer"},
    "oranje_warm": {"range": (30, 35), "description": "Code oranje", "alert": "Code Oranje: Waarschuwing voor hitte"},
    "rood_warm": {"range": (35, 40), "description": "Code rood", "alert": "Code Rood: Waarschuwing voor extreme hitte"},
}

AIR_PRESSURE_MAP: Final[dict[str, dict[str, Any]]] = {
    "extreem_laag": {"range": (900, 940), "short_description": "Extreem laag", "barometer": "Orkaan"},
    "zeer_laag": {"range": (940, 970), "short_description": "Zeer laag", "barometer": "Stormachtig"},
    "laag": {"range": (970, 990), "short_description": "Laag", "barometer": "Regenachtig"},
    "matig_laag": {"range": (990, 1010), "short_description": "Matig laag", "barometer": "Veranderlijk"},
    "stabiel": {"range": (1010, 1030), "short_description": "Stabiel", "barometer": "Mooi weer"},
    "hoog": {"range": (1030, 1050), "short_description": "Hoog", "barometer": "Droog"},
    "zeer_hoog": {"range": (1050, 1100), "short_description": "Zeer hoog", "barometer": "Zeer droog"},
    "extreem_hoog": {"range": (1100, 1200), "short_description": "Extreem hoog", "barometer": "Uitzonderlijk droog"},
}

# Wind force mapping using Beaufort scale
WIND_FORCE_MAP: Final[dict[int, dict[str, Any]]] = {
    0: {
        "windsnelheid_kmh": 0,
        "windsnelheid_ms": 0,
        "benaming": "Stil",
        "uitwerking": "Rook stijgt recht of bijna recht omhoog"
    },
    1: {
        "windsnelheid_kmh": 1,
        "windsnelheid_ms": 0.3,
        "benaming": "Zwak",
        "uitwerking": "Windrichting goed af te leiden uit rookpluimen"
    },
    2: {
        "windsnelheid_kmh": 6,
        "windsnelheid_ms": 1.6,
        "benaming": "Zwak",
        "uitwerking": "Wind merkbaar in gezicht"
    },
    3: {
        "windsnelheid_kmh": 12,
        "windsnelheid_ms": 3.4,
        "benaming": "Matig",
        "uitwerking": "Stof waait op"
    },
    4: {
        "windsnelheid_kmh": 20,
        "windsnelheid_ms": 5.5,
        "benaming": "Matig",
        "uitwerking": "Haar in de war, kleding flappert"
    },
    5: {
        "windsnelheid_kmh": 29,
        "windsnelheid_ms": 8.0,
        "benaming": "Vrij krachtig",
        "uitwerking": "Opwaaiend stof hinderlijk voor de ogen, gekuifde golven op meren en kanalen, vuilcontainers waaien om"
    },
    6: {
        "windsnelheid_kmh": 39,
        "windsnelheid_ms": 10.8,
        "benaming": "Krachtig",
        "uitwerking": "Paraplu's met moeite vast te houden"
    },
    7: {
        "windsnelheid_kmh": 50,
        "windsnelheid_ms": 13.9,
        "benaming": "Hard",
        "uitwerking": "Lastig tegen de wind in te lopen of fietsen"
    },
    8: {
        "windsnelheid_kmh": 62,
        "windsnelheid_ms": 17.2,
        "benaming": "Stormachtig",
        "uitwerking": "Voortbewegen zeer moeilijk"
    },
    9: {
        "windsnelheid_kmh": 75,
        "windsnelheid_ms": 20.8,
        "benaming": "Storm",
        "uitwerking": "Schoorsteenkappen en dakpannen waaien weg, kinderen waaien om"
    },
    10: {
        "windsnelheid_kmh": 89,
        "windsnelheid_ms": 24.5,
        "benaming": "Zware storm",
        "uitwerking": "Grote schade aan gebouwen, volwassenen waaien om"
    },
    11: {
        "windsnelheid_kmh": 103,
        "windsnelheid_ms": 28.5,
        "benaming": "Zeer zware storm",
        "uitwerking": "Enorme schade aan bossen"
    },
    12: {
        "windsnelheid_kmh": 117,
        "windsnelheid_ms": 32.6,
        "benaming": "Orkaan",
        "uitwerking": "Verwoestingen"
    }
}

HUMIDITY_MAP: Final[dict[str, dict[str, Any]]] = {
    "ultra_low": {
        "range": (0, 10),
        "description": "Zeer lage luchtvochtigheid. Zeer droge lucht, kan ademhalingsongemakken veroorzaken.",
        "short_description": "Zeer laag"
    },
    "very_low": {
        "range": (10, 30),
        "description": "Zeer lage luchtvochtigheid. Droge lucht, kan keel- en ademhalingsproblemen veroorzaken.",
        "short_description": "Erg laag"
    },
    "low": {
        "range": (30, 40),
        "description": "Lage luchtvochtigheid. Droge lucht, over het algemeen comfortabel voor de meeste mensen.",
        "short_description": "Laag"
    },
    "comfortable": {
        "range": (40, 60),
        "description": "Comfortabele luchtvochtigheid. Optimaal bereik voor menselijk comfort en welzijn.",
        "short_description": "Comfortabel"
    },
    "high": {
        "range": (60, 70),
        "description": "Hoge luchtvochtigheid. Vochtige lucht, kan een plakkerig gevoel veroorzaken.",
        "short_description": "Hoog"
    },
    "very_high": {
        "range": (70, 90),
        "description": "Zeer hoge luchtvochtigheid. Zeer vochtige lucht, kan schimmelgroei veroorzaken.",
        "short_description": "Erg hoog"
    },
    "ultra_high": {
        "range": (90, 100),
        "description": "Extreem hoge luchtvochtigheid. Uiterst vochtige lucht, kan gezondheidsrisico's veroorzaken.",
        "short_description": "Zeer hoog"
    }
}

VISIBILITY_MAP: Final[dict[str, dict[str, Any]]] = {
    "very_poor": {
        "range": (0, 1),
        "description": "Zeer slecht zicht. Bijna geen zichtbaarheid, gevaarlijk voor weggebruikers.",
        "short_description": "Zeer slecht"
    },
    "poor": {
        "range": (1, 3),
        "description": "Slecht zicht. Beperkt zicht, extra voorzichtigheid vereist tijdens het rijden.",
        "short_description": "Slecht"
    },
    "moderate": {
        "range": (3, 5),
        "description": "Matig zicht. Redelijk zicht, maar nog steeds enigszins beperkt.",
        "short_description": "Matig"
    },
    "good": {
        "range": (5, 10),
        "description": "Goed zicht. Voldoende zichtbaarheid, normale omstandigheden.",
        "short_description": "Goed"
    },
    "very_good": {
        "range": (10, 50),
        "description": "Zeer goed zicht. Uitstekende zichtbaarheid, zeer heldere omstandigheden.",
        "short_description": "Zeer goed"
    }
}