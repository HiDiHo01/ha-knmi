# notification_helper.py

from homeassistant.components.persistent_notification import (
    async_create as async_create_notification,
    async_dismiss as async_dismiss_notification,
)
from homeassistant.core import HomeAssistant
from typing import Optional
import logging
import uuid

_LOGGER: logging.Logger = logging.getLogger(__name__)


class NotificationHelper:
    """Helper class for handling notifications."""

    def __init__(self, hass: HomeAssistant):
        self.hass = hass

    async def create_notification(self, message: str, title: str) -> Optional[str]:
        """Create a persistent notification and return its ID."""
        notification_id = str(uuid.uuid4())
        async_create_notification(self.hass, message, title, notification_id)
        return notification_id

    async def dismiss_notification(self, notification_id: str) -> None:
        """Dismiss the persistent notification with the given ID."""
        await async_dismiss_notification(self.hass, notification_id)

    def notification_exists(self, notification_id: str) -> bool:
        """Check if the persistent notification with the given ID exists."""
        notifications = self.hass.data.get("persistent_notification", {})
        existing_notification = notifications.get(notification_id)
        return existing_notification is not None
