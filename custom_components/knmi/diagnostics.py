"""KNMI Diagnostics Support."""
# diagnostics.py

import asyncio

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY, CONF_LATITUDE, CONF_LONGITUDE
from homeassistant.core import HomeAssistant

from . import DOMAIN, KnmiDataUpdateCoordinator

TO_REDACT = {CONF_API_KEY, CONF_LATITUDE, CONF_LONGITUDE}


class KnmiDiagnostics:
    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize KNMI Diagnostics support."""
        self.hass = hass
        self.coordinator_cache = self.hass.data[DOMAIN]

    async def get_config_entry_diagnostics(
        self, config_entry: ConfigEntry
    ) -> dict:
        """Return diagnostics for a config entry.

        Args:
            config_entry (ConfigEntry): The config entry to get diagnostics for.

        Returns:
            dict: A dictionary containing the diagnostics information.
        """
        self._validate_config_entry(config_entry)
        coordinator = self._get_coordinator(config_entry)
        data = await self._get_coordinator_data(coordinator)

        redacted_config_entry = {
            k: v for k, v in config_entry.as_dict().items() if k not in TO_REDACT
        }

        return {
            "config_entry": redacted_config_entry,
            "data": data,
        }

    def _validate_config_entry(self, config_entry: ConfigEntry) -> None:
        """Validate if the input is a valid ConfigEntry instance.

        Args:
            config_entry (ConfigEntry): The config entry to validate.

        Raises:
            TypeError: If config_entry is not a ConfigEntry instance.
        """
        if not isinstance(config_entry, ConfigEntry):
            raise TypeError("config_entry should be a ConfigEntry instance")

    def _get_coordinator(self, config_entry: ConfigEntry) -> KnmiDataUpdateCoordinator:
        """Retrieve the coordinator for the given config entry.

        Args:
            config_entry (ConfigEntry): The config entry to get the coordinator for.

        Returns:
            KnmiDataUpdateCoordinator: The coordinator associated with the config entry.
        """
        return self.coordinator_cache.get(config_entry.entry_id)

    async def _get_coordinator_data(
        self, coordinator: KnmiDataUpdateCoordinator
    ) -> dict:
        """Retrieve data from the coordinator, or return an empty dictionary if it's None.

        Args:
            coordinator (KnmiDataUpdateCoordinator): The coordinator to get data from.

        Returns:
            dict: The data from the coordinator or an empty dictionary if None.
        """
        return coordinator.data or {}

    async def refresh_data(self, config_entry: ConfigEntry) -> None:
        """Refresh KNMI data for a specific config entry.

        Args:
            config_entry (ConfigEntry): The config entry to refresh data for.
        """
        coordinator = self._get_coordinator(config_entry)
        if coordinator:
            await coordinator.async_request_refresh()

    async def refresh_all_data(self) -> None:
        """Refresh KNMI data for all config entries."""
        await asyncio.gather(
            *[self.refresh_data(config_entry) for config_entry in self.hass.config_entries.async_entries(DOMAIN)]
        )

    async def async_on_remove(self) -> None:
        """Remove config entries when the integration is uninstalled."""
        async for config_entry in self.hass.config_entries.async_entries(DOMAIN):
            await self.hass.config_entries.async_remove(config_entry.entry_id)