# api.py
import asyncio
import json
import socket
import uuid

import aiohttp
from aiohttp import ClientSession
import async_timeout
from homeassistant.components.persistent_notification import \
    async_create as async_create_notification
from homeassistant.components.persistent_notification import \
    async_dismiss as async_dismiss_notification
from homeassistant.core import HomeAssistant

from .const import _LOGGER, API_ENDPOINT, API_TIMEOUT
from .exceptions import (ApiError, InvalidApiKeyError, KnmiApiException,
                         RequestsExceededError)


class KnmiApiClient:
    """KNMI API wrapper"""

    def __init__(
        self,
        api_key: str,
        latitude: float,
        longitude: float,
        session: ClientSession,
        hass: HomeAssistant,
    ) -> None:
        self.api_key = api_key
        self.latitude = latitude
        self.longitude = longitude
        self._session = session
        self.hass = hass
        self.notification_id = None

        _LOGGER.debug("Initialized KnmiApiClient with notification_id: %s", self.notification_id)

    async def async_get_data(self) -> dict:
        """Get data from the KNMI API."""
        url = API_ENDPOINT.format(self.api_key, self.latitude, self.longitude)
        return await self._api_wrapper(url)

    async def _api_wrapper(self, url: str) -> dict:
        """Private method to get information from the API."""
        try:
            async with async_timeout.timeout(API_TIMEOUT):
                response = await self._session.get(url)
                _LOGGER.debug("Response status: %s", response.status)
                _LOGGER.debug("Response headers: %s", response.headers)
                #response_json = await response.json()
                response_text = await response.text()
                _LOGGER.debug("Response text: %s", response_text)

                # Handle error responses
                await self._handle_error_responses(response_text)

                # Parse JSON response
                data = await self._parse_json_response(response, response_text)
                _LOGGER.debug("Raw JSON response: %s", data)

                if isinstance(data, dict) and "liveweer" in data:
                    _LOGGER.debug("OK! Data is dict and liveweer exist")
                    liveweer = data["liveweer"][0] # A list containing a single dictionary element.
                    if liveweer:
                        _LOGGER.debug("OK! Liveweer")
                        await self._handle_notification_dismissal()
                        return liveweer
                    else:
                        raise ApiError("No 'liveweer' data in the response")
                else:
                    raise ApiError("Invalid data type or structure in JSON response")
        except asyncio.TimeoutError as exception:
            _LOGGER.error(
                "Timeout error fetching information from %s - %s",
                url,
                exception,
            )
            #raise KnmiApiException("Timeout error")
            #return
        except (aiohttp.ClientError, socket.gaierror) as exception:
            await self._handle_error_logging(exception, url)
        except RequestsExceededError as exception:
            _LOGGER.error("API Call Limit! - %s", exception)
            raise  # Re-raise the exception to stop code execution
        except KnmiApiException as exception:
            await self._handle_error_logging(exception)
            # Raise to pass on to the user.
            raise exception

    async def _handle_error_responses(self, response_text: str) -> None:
        """Handle error responses from the API."""
        if "Vraag eerst een API-key op" in response_text:
            raise InvalidApiKeyError("Invalid API key")

        if "Dagelijkse limiet" in response_text:
            message = "Het maximum aantal van 300 API verzoeken per dag voor KNMI is bereikt."
            title = "API limiet bereikt"
            if not self.notification_exists():
                self.notification_id = str(uuid.uuid4())
                async_create_notification(self.hass, message, title, self.notification_id)
            raise RequestsExceededError("The allowed number of requests has been exceeded")

        if "De server ondervindt een probleem" in response_text:
            raise KnmiApiException("Error fetching information from the API")

    async def _parse_json_response(self, response, response_text: str) -> dict:
        """Parse the JSON response from the API."""
        if response.headers.get("Content-Type") != "application/json":
            raise ApiError("Invalid content type in the response")

        try:
            if response.status == 200 and not "Dagelijkse limiet" in response_text:
                data = json.loads(response_text)
            else:
                data = None
        except json.JSONDecodeError as exception:
            _LOGGER.error(
                "Error decoding JSON response - %s: %s",
                exception,
                response_text,
            )
            raise ApiError("Invalid JSON data in the response")

        return data

    async def old_parse_json_response(self, response, response_text: str) -> dict:
        """Parse the JSON response from the API."""
        if response.headers.get("Content-Type") != "application/json":
            raise ApiError("Invalid content type in the response")

        try:
            if response.status == 200 and not "Dagelijkse limiet" in response_text:
                data = json.loads(response_text)
            else:
                data = None
        except json.JSONDecodeError as exception:
            _LOGGER.error(
                "Error decoding JSON response - %s: %s",
                exception,
                response_text,
            )
            raise ApiError("Invalid JSON data in the response")

        # Provide default values for missing condition attributes
        if data and isinstance(data, dict) and "liveweer" in data:
            liveweer = data["liveweer"][0]
            default_condition = "Unknown"
            
            liveweer["image"] = liveweer.get("image", default_condition)
            liveweer["d0weer"] = liveweer.get("d0weer", default_condition)
            liveweer["d1weer"] = liveweer.get("d1weer", default_condition)
            liveweer["d2weer"] = liveweer.get("d2weer", default_condition)
        
        return data


    async def _handle_notification_dismissal(self) -> None:
        """Dismiss the notification if it exists."""
        if self.notification_id is not None and self.notification_exists():
            await async_dismiss_notification(self.hass, self.notification_id)
            self.notification_id = None

    async def _handle_error_logging(self, exception, url: str = None) -> None:
        """Handle and log errors."""
        if url:
            _LOGGER.error(
                "Error fetching information from %s - %s",
                url,
                exception,
            )
        else:
            _LOGGER.error("Error: %s", exception)

    def old_notification_exists(self) -> bool:
        """Check if the notification with notification_id exists."""
        notifications = self.hass.data.get("persistent_notification", [])
        if isinstance(notifications, dict):
            # Check if notifications is a dictionary
            _LOGGER.debug("notifications is a dictionary")
            exists = any(
                notification.get("notification_id") == self.notification_id
                for notification in notifications.values()
            )
            _LOGGER.debug("notification_exists: %s", exists)
            return exists
        return False
    
    def notification_exists(self) -> bool:
        """Check if the notification with notification_id exists."""
        notifications = self.hass.data.get("persistent_notification", {})
        
        if not isinstance(notifications, dict):
            _LOGGER.debug("notifications is not a dictionary")
            return False

        existing_notification = notifications.get(self.notification_id)
        
        if existing_notification is not None:
            _LOGGER.debug("Notification exists: %s", self.notification_id)
            return True
        
        _LOGGER.debug("Notification does not exist: %s", self.notification_id)
        return False

    # 502, message='Bad Gateway'    
    async def async_fetch_daily_forecast_data(self) -> list[dict]:
        """Fetch daily forecast data from the KNMI API."""
        try:
            url = API_ENDPOINT.format(self.api_key, self.latitude, self.longitude)
            async with async_timeout.timeout(API_TIMEOUT):
                response = await self._session.get(url)
                response.raise_for_status()

                #data = await self._parse_json_response(response)
                response_text = await response.text()
                data = await self._parse_json_response(response, response_text)

                if not data is None:
                    return data.get("forecast", [])

        except aiohttp.ClientError as e:
            raise KnmiApiException(f"Error fetching daily forecast data: {e}")