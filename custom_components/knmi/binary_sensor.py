"""KNMI Binary Sensor Platform."""

from collections.abc import Callable, Mapping
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from homeassistant.components.binary_sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt

from .const import API_TIMEZONE, ATTRIBUTION, DOMAIN
from .coordinator import KnmiDataUpdateCoordinator


class KnmiBinarySensor(
    CoordinatorEntity[KnmiDataUpdateCoordinator],
    BinarySensorEntity,
):
    """Defines a KNMI binary sensor."""

    _attr_has_entity_name = True

    def __init__(
        self,
        conf_name: str,
        coordinator: KnmiDataUpdateCoordinator,
        entry_id: str,
        description: BinarySensorEntityDescription,
        is_on_func: Callable[[KnmiDataUpdateCoordinator], bool],
        extra_attributes_func: Callable[[KnmiDataUpdateCoordinator], Mapping[str, object]],
    ) -> None:
        """Initialize KNMI binary sensor."""
        super().__init__(coordinator=coordinator)

        self.entity_id = f"{SENSOR_DOMAIN}.{conf_name}_{description.name}".lower()
        self.entity_description = description
        self._attr_unique_id = f"{entry_id}-{conf_name}-{description.name}"
        self._attr_device_info = coordinator.device_info
        self._is_on_func = is_on_func
        self._extra_attributes_func = extra_attributes_func

    @property
    def is_on(self) -> bool | None:  # type: ignore[override]
        """Return True if the entity is on."""
        if self.coordinator.data is None:
            return None
        try:
            return self._is_on_func(self.coordinator)
        except Exception:
            return None

    @property
    def extra_state_attributes(self) -> dict[str, object] | None:  # type: ignore[override]
        """Return entity-specific state attributes for Home Assistant."""
        if self.coordinator.data is None:
            return None
        try:
            # Convert internal object mapping to HA-compliant Any mapping
            return {k: v for k, v in self._extra_attributes_func(self.coordinator).items()}
        except Exception:
            return None


# ---------------- Internal helpers (use object) ---------------- #

def _time_as_datetime(time_val: float | int | str) -> datetime:
    """Parse a time from float/int/str like '08:13', 813, or 8.13 to a timezone-aware UTC datetime."""
    # Ensure string format "HH:MM"
    time_str = str(time_val)
    if ":" not in time_str:
        # Convert numeric hour/minute like 813 -> "08:13"
        time_str = f"{int(time_str):04}"
        time_str = f"{time_str[:2]}:{time_str[2:]}"

    hour, minute = map(int, time_str.split(":"))
    local_tz = ZoneInfo(API_TIMEZONE)
    now = dt.now(local_tz)
    local_dt = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    return dt.as_utc(local_dt)


def _get_sunrise_sunset(
    coordinator: KnmiDataUpdateCoordinator,
) -> tuple[datetime, datetime] | None:
    """Retrieve sunrise and sunset times from the coordinator, handling float/int/str."""
    sup = coordinator.get_value("sup")
    sunder = coordinator.get_value("sunder")

    if sup is None or sunder is None:
        return None

    try:
        sunrise = _time_as_datetime(str(sup))
        sunset = _time_as_datetime(str(sunder))
    except (ValueError, TypeError):
        return None

    return sunrise, sunset


def sun_up_duration(coordinator: KnmiDataUpdateCoordinator) -> timedelta | None:
    """Return duration of sun being above the horizon."""
    times = _get_sunrise_sunset(coordinator)
    if times is None:
        return None
    sunrise, sunset = times
    return sunset - sunrise


def is_sun_up(coordinator: KnmiDataUpdateCoordinator) -> bool:
    """Return True if sun is currently above the horizon."""
    times = _get_sunrise_sunset(coordinator)
    if times is None:
        return False
    sunrise, sunset = times
    now_utc = dt.utcnow().replace(tzinfo=timezone.utc)
    return sunrise < now_utc < sunset


def is_alarm_on(coordinator: KnmiDataUpdateCoordinator) -> bool:
    """Return True if the alarm is active."""
    value = coordinator.get_value("alarm", int)
    return value == 1


def get_alarm_attributes(coordinator: KnmiDataUpdateCoordinator) -> Mapping[str, object]:
    """Return internal attributes for the alarm sensor."""
    if not is_alarm_on(coordinator):
        return {}

    timestamp_val = coordinator.get_value("timestamp")
    timestamp: datetime | None = None

    if isinstance(timestamp_val, (int, float)):
        timestamp = datetime.fromtimestamp(int(timestamp_val), tz=timezone.utc)
    elif isinstance(timestamp_val, str) and timestamp_val.isdigit():
        timestamp = datetime.fromtimestamp(int(timestamp_val), tz=timezone.utc)

    alarmtxt = coordinator.get_value("alarmtxt")

    return {
        "Timestamp": timestamp if timestamp else "",
        "Waarschuwing": alarmtxt or "",
        "attribution": ATTRIBUTION,
    }


def get_sun_attributes(
    coordinator: KnmiDataUpdateCoordinator,
) -> dict[str, object]:
    """Return entity-specific state attributes for the sun sensor, handling float/int/str."""
    attributes: dict[str, object] = {}

    sup = coordinator.get_value("sup")
    sunder = coordinator.get_value("sunder")
    supdur = sun_up_duration(coordinator)
    d0zon = coordinator.get_value("d0zon", int)
    d1zon = coordinator.get_value("d1zon", int)
    d2zon = coordinator.get_value("d2zon", int)

    if sup is not None:
        try:
            attributes["Zonsopkomst"] = _time_as_datetime(str(sup)).isoformat()
        except (ValueError, TypeError):
            pass
    if sunder is not None:
        try:
            attributes["Zonsondergang"] = _time_as_datetime(str(sunder)).isoformat()
        except (ValueError, TypeError):
            pass
    if supdur is not None:
        hours, remainder = divmod(supdur.seconds, 3600)
        minutes = remainder // 60
        formatted_duration = f"{hours:02}:{minutes:02}"
        attributes["Duur van zonlicht"] = formatted_duration
    if d0zon is not None:
        attributes["Zonkans vandaag"] = str(d0zon)
    if d1zon is not None:
        attributes["Zonkans morgen"] = str(d1zon)
    if d2zon is not None:
        attributes["Zonkans overmorgen"] = str(d2zon)

    attributes["attribution"] = ATTRIBUTION
    return attributes

# ---------------- Setup ---------------- #


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up KNMI binary sensors from config entry."""
    conf_name = entry.data.get(CONF_NAME, hass.config.location_name)
    coordinator = hass.data[DOMAIN][entry.entry_id]

    BINARY_SENSOR_TYPES: tuple[
        tuple[
            BinarySensorEntityDescription,
            Callable[[KnmiDataUpdateCoordinator], bool],
            Callable[[KnmiDataUpdateCoordinator], Mapping[str, object]],
        ],
        ...
    ] = (
        (
            BinarySensorEntityDescription(
                key="alarm",
                name="Waarschuwing",
                translation_key="alert",
                icon="mdi:alert",
                device_class=BinarySensorDeviceClass.SAFETY,
            ),
            is_alarm_on,
            get_alarm_attributes,
        ),
        (
            BinarySensorEntityDescription(
                key="sun",
                name="Zon",
                translation_key="sun",
            ),
            is_sun_up,
            get_sun_attributes,
        ),
    )

    entities = [
        KnmiBinarySensor(
            conf_name=conf_name,
            coordinator=coordinator,
            entry_id=entry.entry_id,
            description=description,
            is_on_func=is_on_func,
            extra_attributes_func=extra_attributes_func,
        )
        for description, is_on_func, extra_attributes_func in BINARY_SENSOR_TYPES
    ]

    async_add_entities(entities)
