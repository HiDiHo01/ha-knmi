"""
Custom integration to integrate knmi with Home Assistant.

For more details about this integration, please refer to
https://github.com/HiDiHo01/ha-knmi/
"""
# __init__.py
# import asyncio
# import json
# from datetime import datetime, timedelta
from typing import Any, Callable

# import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (CONF_API_KEY, CONF_LATITUDE, CONF_LONGITUDE,
                                 Platform)
from homeassistant.core import Config, HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import (DataUpdateCoordinator,
                                                      UpdateFailed)

from .api import KnmiApiClient
from .const import (_LOGGER, API_CONF_URL, DOMAIN, NAME, PLATFORMS,
                    SCAN_INTERVAL, VERSION)
from .coordinator import KnmiDataUpdateCoordinator

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.SENSOR,
    Platform.WEATHER,
]


async def async_setup(hass: HomeAssistant, config: Config) -> bool:
    """Set up this integration using YAML is not supported."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up this integration using UI."""
    if hass.data.get(DOMAIN) is None:
        hass.data.setdefault(DOMAIN, {})

    api_key = entry.data.get(CONF_API_KEY)
    latitude = entry.data.get(CONF_LATITUDE)
    longitude = entry.data.get(CONF_LONGITUDE)
    #refresh_interval = entry.data.get("refresh_interval")
    #refresh_interval = entry.options.get("refresh_interval")

    # Check if the config entry exists and print its options
    if entry.options:
        _LOGGER.debug("Config entry options: %s", entry.options)
    else:
        _LOGGER.debug("Config entry options are empty")

    session = async_get_clientsession(hass)
    client = KnmiApiClient(api_key, latitude, longitude, session, hass)

    device_info = DeviceInfo(
        entry_type=DeviceEntryType.SERVICE,
        identifiers={(DOMAIN, entry.entry_id)},
        manufacturer=NAME,
        name=entry.title,
        model="Weer informatie",
        configuration_url=API_CONF_URL,
        sw_version=VERSION,
    )

    hass.data[DOMAIN][entry.entry_id] = coordinator = KnmiDataUpdateCoordinator(
        hass=hass, client=client, device_info=device_info, config_entry=entry,
    )
    # Fetch the config entry options directly from the entry
    refresh_interval = entry.options.get("refresh_interval", 300)

    if refresh_interval:
        _LOGGER.debug("refresh_interval exists 0: %s",refresh_interval)
        coordinator.refresh_interval = refresh_interval

    _LOGGER.debug("coordinator attributes: %s", dir(coordinator))
    _LOGGER.debug("coordinator attribute refresh_interval: %s", coordinator.refresh_interval)
    _LOGGER.debug("coordinator attribute options: %s", coordinator.options)
    await coordinator.async_config_entry_first_refresh()

    if not coordinator.last_update_success:
        raise ConfigEntryNotReady

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Handle removal of an entry."""
    if unloaded := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unloaded

async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)