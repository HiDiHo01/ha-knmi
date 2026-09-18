# api.py
import asyncio
import json
import logging
import socket
from typing import Optional

import aiohttp
import requests
from aiohttp import ClientSession
from homeassistant.components.persistent_notification import (
    async_create as async_create_notification,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import storage

from .const import API_ENDPOINT, API_TIMEOUT
from .exceptions import (
    ApiError,
    InvalidApiKeyError,
    KnmiApiException,
    RequestsExceededError,
)
from .notification_helper import NotificationHelper

_LOGGER: logging.Logger = logging.getLogger(__name__)

STORAGE_KEY = "knmi_api_call_counter"
INVALID_API_KEY_MESSAGE = "Vraag eerst een API-key op"
DAILY_LIMIT_MESSAGE = "Dagelijkse limiet"
SERVER_ERROR_MESSAGE = "De server ondervindt een probleem"
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds


class KnmiApiClient:
    """KNMI API wrapper"""

    def __init__(
        self,
        api_key: str,
        latitude: float | None,
        longitude: float | None,
        session: ClientSession,
        hass: HomeAssistant,
    ) -> None:
        self.api_key: str = api_key
        self.secret_api_key = str()  # Initialize as empty string to avoid AttributeError if secrets are not found
        # Use Home Assistant's secrets manager:
        secrets_data = hass.data.get("secrets")
        if secrets_data and isinstance(secrets_data, dict):
            self.secret_api_key: str | None = secrets_data.get("knmi_api_key")
            _LOGGER.warning(
                "Secrets found in hass.data.")
        else:
            _LOGGER.warning(
                "No secrets found or invalid data structure in hass.data.")
            # _LOGGER.warning(
            #     "No secrets found or invalid data structure in hass.data. hass.data content: %s",
            #     hass.data,
            # )
        if self.secret_api_key is not None and self.secret_api_key != "":
            self.api_key = self.secret_api_key
        self.latitude: float | None = latitude
        self.longitude: float | None = longitude
        self._session: ClientSession = session
        self.hass: HomeAssistant = hass
        self.api_call_counter: int = 0
        self.notification_id: Optional[str] = None
        self.notification_helper = NotificationHelper(hass)

        _LOGGER.debug(
            "Initialized KnmiApiClient with notification_id: %s", self.notification_id)

    async def old_async_get_data(self) -> dict:
        """Get data from the KNMI API."""
        url: str = API_ENDPOINT.format(
            self.api_key, self.latitude, self.longitude)
        return await self._api_wrapper(url)

    async def async_get_data(self) -> dict:
        """Get data from the KNMI API with retry logic on temporary errors."""
        url: str = API_ENDPOINT.format(
            self.api_key, self.latitude, self.longitude)
        retries = 0
        while retries < MAX_RETRIES:
            try:
                return await self._api_wrapper(url)
            except InvalidApiKeyError:
                _LOGGER.error(
                    "Invalid API key. Please verify the configuration.")
                raise  # Stop execution if the API key is invalid
            except (asyncio.TimeoutError, aiohttp.ClientError, socket.gaierror) as e:
                retries += 1
                _LOGGER.warning(
                    "Failed to fetch data (Attempt %d/%d). Retrying in %d seconds. Error: %s",
                    retries, MAX_RETRIES, RETRY_DELAY, e,
                )
                await asyncio.sleep(RETRY_DELAY)

        # After all retries are exhausted, log a final error and raise exception
        _LOGGER.error(
            "Max retries reached. Failed to fetch data from KNMI API.")
        raise ApiError(
            "Failed to fetch data from KNMI API after multiple attempts.")

    async def old_api_wrapper(self, url: str) -> dict:
        """Private method to get information from the API."""
        # Initialize the counter variable from persistent storage
        # api_call_counter: int = await self.hass.async_add_executor_job(load_counter_from_storage, self.hass)
        api_call_counter: int = await load_counter_from_storage(self.hass)
        try:
            # async with async_timeout.timeout(API_TIMEOUT):
            async with asyncio.timeout(API_TIMEOUT):
                response: aiohttp.ClientResponse = await self._session.get(url)
                _LOGGER.debug("Response status: %s", response.status)
                _LOGGER.debug("Response headers: %s", response.headers)
                # response_json = await response.json()
                response_text: str = await response.text()
                _LOGGER.debug("Response text: %s", response_text)

                # Handle error responses
                await self._handle_error_responses(response_text)

                # Parse JSON response
                data: dict = await self._parse_json_response(response, response_text)
                _LOGGER.debug("Raw JSON response: %s", data)

                if isinstance(data, dict) and "liveweer" in data:
                    _LOGGER.debug("OK! Data is dict and liveweer exist")
                    # A list containing a single dictionary element.
                    liveweer: dict = data["liveweer"][0]
                    if liveweer:
                        _LOGGER.debug("OK! Liveweer")
                        # Increment the API call counter
                        self.api_call_counter += 1
                        # Log the API call and current count
                        _LOGGER.info(
                            "API call received. Total count: %d", api_call_counter)

                        # Save the updated counter to persistent storage
                        # await self.hass.async_add_executor_job(save_counter_to_storage, self.hass, api_call_counter)
                        await save_counter_to_storage(self.hass, api_call_counter)
                        await self._handle_notification_dismissal()
                        return liveweer
                    else:
                        raise ApiError("No 'liveweer' data in the response")
                else:
                    raise ApiError(
                        "Invalid data type or structure in JSON response")
        except asyncio.TimeoutError as exception:
            _LOGGER.error(
                "Timeout error fetching information from %s - %s",
                url,
                exception,
            )
            # raise KnmiApiException("Timeout error")
            # return
        except (aiohttp.ClientError, socket.gaierror) as exception:
            await self._handle_error_logging(exception, url)
        except RequestsExceededError as exception:
            _LOGGER.error("API Call Limit! - %s", exception)
            raise  # Re-raise the exception to stop code execution
        except KnmiApiException as exception:
            await self._handle_error_logging(exception)
            # Raise to pass on to the user.
            raise exception

    async def _api_wrapper(self, url: str) -> dict:
        """Private method to get information from the API.

        Args:
            url (str): The API endpoint URL to fetch data from.

        Returns:
            dict: The parsed JSON data from the API response or an empty dict if an error occurs.

        Raises:
            ApiError: If there's an error with the API response data.
            KnmiApiException: For general API errors or timeout issues.
        """
        self.api_call_counter = await load_counter_from_storage(self.hass)

        try:
            # async with async_timeout.timeout(API_TIMEOUT):
            async with asyncio.timeout(API_TIMEOUT):
                response: aiohttp.ClientResponse = await self._session.get(url)
                _LOGGER.debug("Response status: %s", response.status)
                _LOGGER.debug("Response headers: %s", response.headers)
                response_text: str = await response.text()
                _LOGGER.debug("Response text: %s", response_text)

                # Handle specific error responses before parsing
                await self._handle_error_responses(response_text)

                # Parse JSON response and check for 'liveweer' key
                data: dict = await self._parse_json_response(response, response_text)
                _LOGGER.debug("Parsed JSON response: %s", data)

                if "liveweer" in data:
                    # Expecting a single dict in a list
                    liveweer: dict = data["liveweer"][0]
                    if liveweer:
                        self.api_call_counter += 1
                        _LOGGER.info(
                            "API call successful. Total count: %d", self.api_call_counter)

                        # Save the updated counter to persistent storage
                        await save_counter_to_storage(self.hass, self.api_call_counter)
                        await self._handle_notification_dismissal()
                        return liveweer
                    else:
                        raise ApiError(
                            "Missing 'liveweer' data in the response")
                else:
                    raise ApiError(
                        "Unexpected JSON structure or missing data in response")

        except asyncio.TimeoutError as exception:
            _LOGGER.error(
                "Timeout error fetching information from %s - %s", url, exception)
            raise KnmiApiException("Timeout error fetching API data")

        except (aiohttp.ClientError, socket.gaierror) as exception:
            await self._handle_error_logging(exception, url)

        except RequestsExceededError as exception:
            _LOGGER.error("API request limit exceeded - %s", exception)
            raise

        except KnmiApiException as exception:
            await self._handle_error_logging(exception)
            raise exception

        # Return an empty dict if no valid data is retrieved
        return {}

    async def _handle_error_responses(self, response_text: str) -> None:
        """Handle error responses from the API."""
        if INVALID_API_KEY_MESSAGE in response_text:
            raise InvalidApiKeyError("Invalid API key")

        if DAILY_LIMIT_MESSAGE in response_text:
            message: str = "Het maximum aantal van 300 API verzoeken per dag voor KNMI is bereikt."
            title: str = "API limiet bereikt"
            if not self.notification_exists():
                # self.notification_id = str(uuid.uuid4())
                self.notification_id = "knmi_api_limit_notification"
                async_create_notification(
                    self.hass, message, title, self.notification_id)
            # raise RequestsExceededError(
            #     "The allowed number of requests has been exceeded")

        if SERVER_ERROR_MESSAGE in response_text:
            error_message: str = f"Error fetching information from the API: {
                response_text}"
            raise KnmiApiException(error_message)

    async def _parse_json_response(self, response, response_text: str) -> dict:
        """Parse the JSON response from the API."""
        if response.status != 200:
            raise ApiError(
                "Non-successful response from the API: {}".format(response.status))

        if response.headers.get("Content-Type") != "application/json":
            raise ApiError("Invalid content type in the response")

        try:
            if response.status == 200 and "Dagelijkse limiet" not in response_text:
                data: dict = json.loads(response_text)
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

    async def _handle_notification_dismissal(self) -> None:
        """Dismiss the notification if it exists."""
        if self.notification_id is not None and self.notification_helper.notification_exists(self.notification_id):
            await self.notification_helper.dismiss_notification(self.notification_id)
            self.notification_id = None

    async def _handle_error_logging(self, exception, url: str = None) -> None:
        """Handle and log errors."""
        error_msg: str = "Error fetching information" if url is None else f"Error fetching information from {
            url}"
        exception_details = f"Exception Type: {
            type(exception).__name__}, Exception Message: {str(exception)}"
        _LOGGER.error("%s - %s", error_msg, exception_details)

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


async def fetch_daily_forecast_data(coordinator):
    try:
        response = await coordinator.api.async_fetch_daily_forecast_data()
        data = response.json()

        # Assuming the structure of the API response is similar to what you've used in other parts of your code
        forecast_data = []
        for entry in data.get("forecast", []):
            date_str = entry.get("date")
            condition = entry.get("condition")
            temp_min = entry.get("temp_min")
            temp_max = entry.get("temp_max")
            precipitation_probability = entry.get("precipitation_probability")
            wind_bearing = entry.get("wind_bearing")
            wind_speed = entry.get("wind_speed")

            forecast_entry = {
                "date": date_str,
                "condition": condition,
                "temp_min": temp_min,
                "temp_max": temp_max,
                "precipitation_probability": precipitation_probability,
                "wind_bearing": wind_bearing,
                "wind_speed": wind_speed,
            }
            forecast_data.append(forecast_entry)

        return forecast_data

    except requests.exceptions.RequestException as e:
        raise KnmiApiException(f"Error fetching daily forecast data: {e}")


async def load_counter_from_storage(hass):
    """Load the counter value from persistent storage."""
    store = storage.Store(hass, 1, STORAGE_KEY)
    loaded_data = await store.async_load()

    if loaded_data is not None:
        counter_value = loaded_data.get(STORAGE_KEY, 0)
    else:
        counter_value = 0

    _LOGGER.debug("API counter_value: %s", counter_value)
    return counter_value


async def save_counter_to_storage(hass, counter_value):
    """Save the counter value to persistent storage."""
    store = storage.Store(hass, 1, STORAGE_KEY)
    await store.async_save({STORAGE_KEY: counter_value})
