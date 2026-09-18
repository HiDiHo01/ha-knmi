"""KNMI Weather Integration."""
# config_flow.py
import logging
from typing import Any

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry, ConfigFlowResult
from homeassistant.const import (
    CONF_API_KEY,
    CONF_LATITUDE,
    CONF_LOCATION,
    CONF_LONGITUDE,
    CONF_NAME,
    CONF_SCAN_INTERVAL,
)
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .api import KnmiApiClient
from .const import DATA_REFRESH_INTERVAL, DOMAIN, PLATFORMS, SCAN_INTERVAL
from .exceptions import (
    KnmiApiClientApiKeyError,
    KnmiApiClientCommunicationError,
    KnmiApiRateLimitError,
)

_LOGGER: logging.Logger = logging.getLogger(__name__)


@config_entries.HANDLERS.register(DOMAIN)
class KNMIWeatherFlowHandler(config_entries.ConfigFlow):
    """Config flow for KNMI."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL
    form_errors: dict[str, str] = {}

    def __init__(self):
        """Initialize."""
        self._errors = {}
        self._form_errors = {}

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Handle a flow initialized by the user."""
        if user_input is not None:
            self._errors = {}
            latitude_value = user_input.get(CONF_LATITUDE)

            if not isinstance(latitude_value, (int, float)):
                raise ValueError(
                    "Latitude must be a numeric value. "
                    f"Got {latitude_value!r}"
                )

            latitude: float = float(latitude_value)
            longitude_value = user_input.get(CONF_LONGITUDE)

            if not isinstance(longitude_value, (int, float)):
                raise ValueError(
                    "Longitude must be a numeric value. "
                    f"Got {longitude_value!r}"
                )

            longitude: float = float(longitude_value)
            location: str = ""
            location_value = user_input.get(CONF_NAME)

            if not isinstance(location_value, str) or not location_value.strip():
                self._form_errors[CONF_NAME] = "invalid_location"
            else:
                location: str = location_value.strip()
            try:
                if not self._errors:
                    valid = await self._validate_user_input(
                        user_input[CONF_API_KEY],
                        latitude=latitude,
                        longitude=longitude,
                        location=location,
                    )
                    if valid:
                        return self.async_create_entry(
                            title=location, data=user_input
                        )
                    else:
                        self._errors["base"] = "api_key"
            except (
                KnmiApiClientCommunicationError,
                KnmiApiClientApiKeyError,
                KnmiApiRateLimitError,
            ) as exception:
                _LOGGER.error(exception)
                self._errors["base"] = "general"
            else:
                return self.async_create_entry(
                    title=location, data=user_input
                )
        return await self._show_config_form()

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:  # type: ignore[override]
        """Handle the reconfiguration step for KNMI integration."""
        errors: dict[str, str] = {}

        # Build a proper schema with HA helpers
        data_schema = vol.Schema({
            vol.Required(CONF_NAME, default=self.hass.config.location_name): cv.string,
            vol.Required(CONF_LATITUDE, default=self.hass.config.latitude): cv.latitude,
            vol.Required(CONF_LONGITUDE, default=self.hass.config.longitude): cv.longitude,
            vol.Required(CONF_API_KEY, default=""): cv.string,
            vol.Required(
                "refresh_interval",
                default=DATA_REFRESH_INTERVAL,
                description="Refresh interval in seconds"
            ): vol.All(cv.positive_int, vol.Range(min=1)),
            vol.Required(
                CONF_SCAN_INTERVAL,
                default=SCAN_INTERVAL.total_seconds(),
                description="Scan interval in seconds"
            ): vol.All(cv.positive_int, vol.Range(min=1)),
        })

        if user_input:
            # Coerce & validate inputs
            name_value = user_input.get(CONF_NAME)
            latitude_value = user_input.get(CONF_LATITUDE)
            longitude_value = user_input.get(CONF_LONGITUDE)
            api_key_value = user_input.get(CONF_API_KEY)

            # Check types
            if not isinstance(name_value, str) or not name_value.strip():
                errors[CONF_NAME] = "invalid_location"
            if not isinstance(latitude_value, (int, float)):
                errors[CONF_LATITUDE] = "invalid_latitude"
            if not isinstance(longitude_value, (int, float)):
                errors[CONF_LONGITUDE] = "invalid_longitude"
            if not isinstance(api_key_value, str) or not api_key_value.strip():
                errors[CONF_API_KEY] = "invalid_api_key"

            # Only proceed if no errors
            if not errors:
                latitude: float = float(latitude_value)
                longitude: float = float(longitude_value)
                location: str = name_value.strip()
                api_key: str = api_key_value.strip()

                try:
                    valid = await self._validate_user_input(api_key, latitude, longitude, location)
                    if valid:
                        # Find the current entry
                        entries = self._async_current_entries()
                        current_entry = next(
                            (entry for entry in entries if entry.data.get(CONF_NAME) == location),
                            None,
                        )
                        if current_entry:
                            self.hass.config_entries.async_update_entry(
                                current_entry, data=user_input
                            )
                            _LOGGER.info("Reconfiguration successful for: %s", location)
                            await self.async_set_unique_id(location)
                            return self.async_create_entry(
                                title=location,
                                data=user_input,
                            )  # type: ignore[return-value]

                        errors["base"] = "entry_not_found"
                    else:
                        errors["base"] = "invalid_auth"
                except Exception as exc:
                    _LOGGER.error("Error validating KNMI input: %s", exc)
                    errors["base"] = "general"

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=data_schema,
            errors=errors,
        )  # type: ignore[return-value]

    async def _validate_user_input(
        self,
        api_key: str,
        latitude: float,
        longitude: float,
        location: str
    ) -> bool:
        """Validate user input."""
        if (latitude is not None and longitude is not None) or location is not None:
            session = async_create_clientsession(self.hass)
            client = KnmiApiClient(
                api_key, latitude, longitude, session, self.hass)
            await client.async_get_data()
            return True
        return False

    async def _show_config_form(self) -> config_entries.FlowResult:  # type: ignore[return-value]
        """Show the configuration form to edit location and integration settings."""

        # Default values
        defaults: dict[str, object] = {
            CONF_NAME: self.hass.config.location_name,
            CONF_LATITUDE: self.hass.config.latitude,
            CONF_LONGITUDE: self.hass.config.longitude,
            CONF_API_KEY: self._get_existing_api_key(),
            "refresh_interval": DATA_REFRESH_INTERVAL,
            CONF_SCAN_INTERVAL: SCAN_INTERVAL.total_seconds(),
        }

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
                    vol.Required(schema=CONF_NAME,
                                 msg="bericht",
                                 default=defaults[CONF_NAME],
                                 description="omschrijving"): str,
                    vol.Exclusive(
                        CONF_LATITUDE, "coordinates_lat"): cv.latitude,
                    vol.Exclusive(
                        CONF_LONGITUDE, "coordinates_lon"): cv.longitude,
                    vol.Optional(CONF_LOCATION, default=""): str,
                    vol.Required(CONF_API_KEY, default=defaults[CONF_API_KEY]): str,
                    vol.Required(
                        "refresh_interval",
                        default=600,
                        description={"suggested_value": "suggested value"},
                    ): int,
                }
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

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry
    ) -> "KnmiOptionsFlowHandler":
        return KnmiOptionsFlowHandler(config_entry)

    async def _update_options(self) -> ConfigFlowResult:
        """Finalize the options flow."""

        title = user_input.get(CONF_NAME) or self.hass.config.location_name

        if not isinstance(title, str) or not title.strip():
            raise ValueError(
                "Config entry title is missing or invalid. "
                f"Got {title!r}"
            )

        return self.async_create_entry(  # type: ignore[return-value]
            title=title,
            data=self.options,
        )

    def _get_existing_api_key(self) -> str:
        """Get the existing API key from self.hass.config."""
        if self.hass.data.get(CONF_API_KEY):
            return self.hass.data.get(CONF_API_KEY)
        return ""


class KnmiOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle KNMI integration options flow."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize the options flow handler.

        :param config_entry: The config entry this options flow belongs to.
        """
        if not isinstance(config_entry, ConfigEntry):
            raise TypeError(
                "config_entry must be an instance of ConfigEntry, "
                f"got {type(config_entry).__name__}"
            )

        # self.config_entry: ConfigEntry = config_entry
        self.options: dict[str, object] = dict(config_entry.options)

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Handle the initial step of the options flow.

        :param user_input: Optional user-provided input (unused in this step).
        :return: FlowResult directing to the user step.
        """
        return await self.async_step_user()

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Handle the user step of the options flow.

        :param user_input: User provided configuration options.
        :return: FlowResult for the next step or form display.
        """
        if user_input is not None:
            if not isinstance(user_input, dict):
                raise TypeError(
                    "user_input must be a dict[str, Any] or None, "
                    f"got {type(user_input).__name__}"
                )

            self.options.update(user_input)

            # Update the config entry options
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                options=self.options
            )

            return await self._update_options()

        # Defaults for form
        refresh_interval_default = self.options.get(
            "refresh_interval",
            DATA_REFRESH_INTERVAL,
        )

        defaults: dict[str, object] = {
            CONF_NAME: self.hass.config.location_name,
            CONF_LATITUDE: self.hass.config.latitude,
            CONF_LONGITUDE: self.hass.config.longitude,
            CONF_API_KEY: self._get_existing_api_key(),
            "refresh_interval": self.options.get("refresh_interval", refresh_interval_default),
        }

        platform_schema = {
            vol.Required(
                platform,
                default=self.options.get(platform, True),
            ): bool
            for platform in sorted(PLATFORMS)
        }

        refresh_interval_schema = vol.Schema(
            {
                vol.Required(
                    "refresh_interval",
                    default=defaults["refresh_interval"],
                    description="Enter the refresh interval in seconds",
                ): vol.All(int, vol.Range(min=1))
            }
        )

        combined_schema = {
            **platform_schema,
            **refresh_interval_schema,
        }

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(combined_schema, extra=vol.ALLOW_EXTRA),
        )

    async def _update_options(self) -> FlowResult:
        """Finalize the options flow and create the updated entry.

        :return: FlowResult containing the updated options entry.
        """
        title = self.options.get(CONF_NAME) or self.hass.config.location_name

        if not isinstance(title, str) or not title.strip():
            raise ValueError(
                "Config entry title is missing or invalid. "
                f"Expected non-empty string, got {title!r}"
            )

        return self.async_create_entry(
            title=title,
            data=self.options,
        )

    def _get_existing_api_key(self) -> str:
        """Get the existing API key from self.config_entry.data."""
        return self.config_entry.data.get(CONF_API_KEY, "")
