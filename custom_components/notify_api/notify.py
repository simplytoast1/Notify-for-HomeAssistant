"""
Notify Platform for Notify API Integration

This module implements the notification service for the Notify API.
It uses the notify platform which creates services that appear in the automation UI.

WHAT IS A NOTIFY SERVICE?
A notify service is a Home Assistant service that sends notifications.
It appears in the automation UI action search (e.g., "Send a notification").
Services are created as notify.{service_name} (e.g., notify.my_phone).

HOW IT WORKS:
1. async_get_service() is called by Home Assistant during platform discovery
2. It retrieves credentials from hass.data (stored during integration setup)
3. Creates and returns a NotifyAPIService instance
4. The service becomes available for use in automations

NOTIFY API ENDPOINT:
The service communicates with the Notify API server to send notifications.

API Endpoint: POST https://notifypush.pingie.com/notify-json/{device_id}?token={token}
Content-Type: application/json

Request Body:
{
  "text": "Your notification message",
  "title": "Optional Title",
  "iconUrl": "https://example.com/icon.png",
  "groupType": "optional-group"
}

Response: 200 OK on success
"""

from __future__ import annotations

import logging
from typing import Any

import requests

from homeassistant.components.notify import ATTR_DATA, ATTR_TITLE, BaseNotificationService
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .const import (
    API_BASE_URL,
    ATTR_GROUP_TYPE,
    ATTR_ICON_URL,
    CONF_DEVICE_ID,
    CONF_TOKEN,
    DEFAULT_TIMEOUT,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


async def async_get_service(
    hass: HomeAssistant,
    config: ConfigType,
    discovery_info: DiscoveryInfoType | None = None,
) -> NotifyAPIService | None:
    """
    Get the Notify API notification service.

    This function is called by the notify platform discovery system when
    the platform is loaded. It's responsible for creating and returning
    the notification service instance.

    WHEN IS THIS CALLED?
    - During Home Assistant startup (if integration is configured)
    - When the integration is added via UI
    - When the integration is reloaded

    WHAT DOES IT DO?
    1. Validates that discovery_info was provided
    2. Retrieves the entry_id from discovery_info
    3. Fetches credentials from hass.data (stored during setup)
    4. Creates and returns the NotifyAPIService instance

    Args:
        hass: The Home Assistant instance
        config: Platform configuration (not used for config entry integrations)
        discovery_info: Discovery information containing entry_id

    Returns:
        NotifyAPIService: The notification service instance, or None if setup fails
    """
    if discovery_info is None:
        return None

    # Extract the entry_id from discovery info
    # This links the service to the specific config entry
    entry_id = discovery_info.get("entry_id")
    if entry_id is None:
        _LOGGER.error("No entry_id in discovery_info")
        return None

    # Retrieve credentials from hass.data (stored in __init__.py during setup)
    credentials = hass.data[DOMAIN].get(entry_id)
    if credentials is None:
        _LOGGER.error("No credentials found for entry_id: %s", entry_id)
        return None

    # Create and return the notification service instance
    _LOGGER.info("Setting up Notify API notification service")
    return NotifyAPIService(
        hass,
        credentials[CONF_DEVICE_ID],
        credentials[CONF_TOKEN],
    )


class NotifyAPIService(BaseNotificationService):
    """
    Implement the Notify API notification service.

    This class handles the actual sending of notifications.
    It inherits from BaseNotificationService, which is the legacy platform
    that creates services visible in the automation UI.
    """

    def __init__(self, hass: HomeAssistant, device_id: str, token: str) -> None:
        """
        Initialize the Notify API service.

        Args:
            hass: The Home Assistant instance
            device_id: The Notify API device ID
            token: The Notify API authentication token
        """
        self._hass = hass
        self._device_id = device_id
        self._token = token

        _LOGGER.info("Initialized Notify API notification service")

    def send_message(self, message: str = "", **kwargs: Any) -> None:
        """
        Send a notification message.

        This method is called when the notification service is triggered from automations.
        It's a synchronous method (not async) because BaseNotificationService expects it.

        WHEN IS THIS CALLED?
        When a user triggers the service from an automation:
        service: notify.notify_alerts
        data:
          message: "Your message"
          title: "Your title"
          data:
            icon_url: "https://example.com/icon.png"
            group_type: "security"

        Args:
            message: The notification message text
            **kwargs: Additional parameters (title, data, etc.)
        """
        # Extract title from kwargs
        title = kwargs.get(ATTR_TITLE)

        # Extract data from kwargs
        data = kwargs.get(ATTR_DATA) or {}

        # Extract optional attributes from data
        icon_url = data.get(ATTR_ICON_URL)
        group_type = data.get(ATTR_GROUP_TYPE)

        _LOGGER.debug(
            "Sending notification to %s: message=%s, title=%s, icon_url=%s, group_type=%s",
            self._device_id,
            message,
            title,
            icon_url,
            group_type,
        )

        # Send the notification
        self._send_notification(message, title, icon_url, group_type)

    def _send_notification(
        self,
        message: str,
        title: str | None,
        icon_url: str | None,
        group_type: str | None,
    ) -> None:
        """
        Send the notification via Notify API.

        This method handles the actual HTTP request to the Notify API.

        API ENDPOINT:
        POST https://notifypush.pingie.com/notify-json/{device_id}?token={token}

        PAYLOAD:
        {
          "text": "message",
          "title": "optional title",
          "iconUrl": "optional icon url",
          "groupType": "optional group type"
        }

        Args:
            message: The notification message text
            title: Optional notification title
            icon_url: Optional icon URL
            group_type: Optional group type for threading
        """
        # Build the JSON payload
        payload: dict[str, str] = {"text": message}

        # Add optional fields only if provided
        if title:
            payload["title"] = title

        if icon_url:
            payload["iconUrl"] = icon_url

        if group_type:
            payload["groupType"] = group_type

        # Construct the API URL
        url = f"{API_BASE_URL}/{self._device_id}"

        try:
            # Make the HTTP POST request
            response = requests.post(
                url,
                json=payload,
                params={"token": self._token},
                timeout=DEFAULT_TIMEOUT,
            )

            # Check response status
            if response.status_code == 200:
                _LOGGER.info("Notification sent successfully to %s", self._device_id)
            else:
                _LOGGER.error(
                    "Failed to send notification to %s. Status: %s, Response: %s",
                    self._device_id,
                    response.status_code,
                    response.text,
                )

        except requests.exceptions.Timeout:
            _LOGGER.error("Timeout sending notification to %s", self._device_id)
        except requests.exceptions.ConnectionError:
            _LOGGER.error("Connection error sending notification to %s", self._device_id)
        except requests.exceptions.RequestException as err:
            _LOGGER.error("Error sending notification to %s: %s", self._device_id, err)
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected error sending notification to %s: %s", self._device_id, err)
