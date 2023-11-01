"""KNMI Weather Integration."""
# config_flow.py
import logging
from typing import Any

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import (CONF_API_KEY, CONF_LATITUDE, CONF_LONGITUDE,
                                 CONF_NAME, CONF_SCAN_INTERVAL)
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .api import KnmiApiClient
from .const import DATA_REFRESH_INTERVAL, DOMAIN, PLATFORMS, SCAN_INTERVAL
from .exceptions import (KnmiApiClientApiKeyError,
                         KnmiApiClientCommunicationError,
                         KnmiApiRateLimitError)

_LOGGER: logging.Logger = logging.getLogger(__name__)


class KNMIWeatherFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for knmi."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    def __init__(self):
        """Initialize."""
        self._errors: dict[str, str] = {}

    async def async_step_user(
        self,
        user_input: dict = None,
    ) -> config_entries.FlowResult:
        """Handle a flow initialized by the user."""
        if user_input is not None:
            self._errors = {}
            try:
                valid = await self._validate_user_input(
                    user_input[CONF_API_KEY],
                    user_input[CONF_LATITUDE],
                    user_input[CONF_LONGITUDE],
                )
                if valid:
                    return self.async_create_entry(
                        title=user_input[CONF_NAME], data=user_input
                    )
                else:
                    self._errors["base"] = "api_key"
            except KnmiApiClientCommunicationError as exception:
                _LOGGER.error(exception)
                self._errors["base"] = "general"
            except KnmiApiClientApiKeyError as exception:
                _LOGGER.error(exception)
                self._errors["base"] = "api_key"
            except KnmiApiRateLimitError as exception:
                _LOGGER.error(exception)
                self._errors["base"] = "daily_limit"
            else:
                return self.async_create_entry(
                    title=user_input[CONF_NAME], data=user_input
                )

        else:
            defaults = {
                CONF_NAME: self.hass.config.location_name,
                CONF_LATITUDE: self.hass.config.latitude,
                CONF_LONGITUDE: self.hass.config.longitude,
                CONF_API_KEY: self._get_existing_api_key(),
                "refresh_interval": DATA_REFRESH_INTERVAL,  # Default to 300 seconds (5 minutes)
                CONF_SCAN_INTERVAL: SCAN_INTERVAL
            }

            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema(
                    {
                        vol.Required(CONF_NAME, default=defaults[CONF_NAME]): str,
                        vol.Required(CONF_LATITUDE, default=defaults[CONF_LATITUDE]): cv.latitude,
                        vol.Required(CONF_LONGITUDE, default=defaults[CONF_LONGITUDE]): cv.longitude,
                        vol.Required(CONF_API_KEY, default=defaults[CONF_API_KEY]): str,
                        vol.Required(
                            "refresh_interval",
                            default=defaults["refresh_interval"],
                            description="Enter the refresh interval in seconds",
                        ): int,
                    }
                ),
                errors=self._errors,
        )

    async def _validate_user_input(self, api_key: str, latitude: str, longitude: str):
        """Validate user input."""
        session = async_create_clientsession(self.hass)
        client = KnmiApiClient(api_key, latitude, longitude, session, self.hass)
        await client.async_get_data()
        return True

    @staticmethod
    @callback
    def async_get_options_flow(config_entry) -> "KnmiOptionsFlowHandler":
        return KnmiOptionsFlowHandler(config_entry)

    async def _update_options(self) -> None:
        """Update config entry options."""
        return self.async_create_entry(
            title=self.config_entry.data.get(CONF_NAME), data=self.options
        )

    async def _show_config_form(self, user_input):  # pylint: disable=unused-argument
        """Show the configuration form to edit location data."""

        # Create a description for the refresh_interval field
        help_text = (
            "The refresh interval in seconds determines how often the data is "
            "retrieved from the KNMI API. A lower value will result in more frequent "
            "updates but may consume more resources. The default value is 600 seconds "
            "(10 minutes)."
        )
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NAME, default=user_input[CONF_NAME]): str,
                    vol.Required(
                        CONF_LATITUDE, default=user_input[CONF_LATITUDE]
                    ): cv.latitude,
                    vol.Required(
                        CONF_LONGITUDE, default=user_input[CONF_LONGITUDE]
                    ): cv.longitude,
                    vol.Required(CONF_API_KEY, default=user_input[CONF_API_KEY]): str,
                    vol.Required(
                        "refresh_interval",
                        default=600,  # Default to 600 seconds (10 minutes)
                        titel=help_text,
                        description={"suggested_value": "suggested value"},
                    ): int,
                }
            ),
            description=(
                "The refresh interval in seconds determines how often the data is "
                "retrieved from the KNMI API. A lower value will result in more frequent "
                "updates but may consume more resources. The default value is 300 seconds "
                "(5 minutes)."
            ),
            description_placeholders={
                "help_text": (
                    "The refresh interval in seconds determines how often the data is "
                    "retrieved from the KNMI API. A lower value will result in more frequent "
                    "updates but may consume more resources. The default value is 300 seconds "
                    "(5 minutes)."
                )
            },
            errors=self._errors,
        )

    async def _test_user_input(self, api_key: str, latitude: str, longitude: str):
        """Return true if credentials is valid."""
        try:
            session = async_create_clientsession(self.hass)
            client = KnmiApiClient(api_key, latitude, longitude, session)
            await client.async_get_data()
            return True
        except Exception:  # pylint: disable=broad-except
            pass
        return False

    def _get_existing_api_key(self) -> str:
        """Get the existing API key from self.hass.config."""
        #return self.hass.config_entries.options.async_get(CONF_API_KEY, "")
        return self.hass.data.get(CONF_API_KEY)


class KnmiOptionsFlowHandler(config_entries.OptionsFlow):
    """knmi config flow options handler."""

    def __init__(self, config_entry) -> None:
        """Initialize HACS options flow."""
        self.config_entry = config_entry
        self.options = dict(config_entry.options)

    #async def async_step_init(self, user_input=None):  # pylint: disable=unused-argument
    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Manage the options."""
        return await self.async_step_user()

    async def async_step_user(self, user_input=None) -> config_entries.FlowResult:
        """Handle a flow initialized by the user."""
        if user_input is not None:
            self.options.update(user_input)
            # Update the config entry options
            self.hass.config_entries.async_update_entry(self.config_entry, options=self.options)
            return await self._update_options()

        defaults = {
            CONF_NAME: self.hass.config.location_name,
            CONF_LATITUDE: self.hass.config.latitude,
            CONF_LONGITUDE: self.hass.config.longitude,
            CONF_API_KEY: self._get_existing_api_key(),
            "refresh_interval": self.options.get("refresh_interval", DATA_REFRESH_INTERVAL),
        }

        data_schema = vol.Schema(
            {
                vol.Required(x, default=self.options.get(x, True)): bool
                for x in sorted(PLATFORMS)
            },
            extra=vol.ALLOW_EXTRA,
        )

        refresh_interval_schema = vol.Schema(
            {
                vol.Required(
                    "refresh_interval",
                    default=defaults["refresh_interval"],
                    description="Enter the refresh interval in seconds",
                ): int
            }
        )

        combined_schema = data_schema.schema.copy()
        combined_schema.update(refresh_interval_schema.schema)

        return self.async_show_form(step_id="user", data_schema=vol.Schema(combined_schema, extra=vol.ALLOW_EXTRA))

    async def _update_options(self) -> None:
        """Update config entry options."""
        return self.async_create_entry(
            title=self.config_entry.data.get(CONF_NAME), data=self.options
        )

    def _get_existing_api_key(self) -> str:
        """Get the existing API key from self.config_entry.data."""
        return self.config_entry.data.get(CONF_API_KEY, "")