# model.py

from dataclasses import dataclass
from datetime import datetime


@dataclass
class WeatherData:
    """Class representing weather data."""

    # Properties with type hints
    plaats: str
    timestamp: int
    time: datetime
    temp: float
    gtemp: float
    samenv: str
    lv: int
    windr: str
    windrgr: int
    windms: int
    winds: int
    windk: float
    windkmh: float
    luchtd: float
    ldmmhg: int
    dauwp: int
    zicht: int
    verw: str
    sup: str
    sunder: str
    image: str
    d0weer: str
    d0tmax: int
    d0tmin: int
    d0windk: int
    d0windknp: int
    d0windms: int
    d0windkmh: int
    d0windr: str
    d0windrgr: int
    d0neerslag: int
    d0zon: int
    d1weer: str
    d1tmax: int
    d1tmin: int
    d1windk: int
    d1windknp: int
    d1windms: int
    d1windkmh: int
    d1windr: str
    d1windrgr: int
    d1neerslag: int
    d1zon: int
    d2weer: str
    d2tmax: int
    d2tmin: int
    d2windk: int
    d2windknp: int
    d2windms: int
    d2windkmh: int
    d2windr: str
    d2windrgr: int
    d2neerslag: int
    d2zon: int
    alarm: int
    alarmtxt: str
