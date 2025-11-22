"""
Notify API Integration for Home Assistant

This integration allows Home Assistant to send push notifications using the Notify API
(https://notify.pingie.com). It creates a native notify service that works like any
other Home Assistant notification platform.

WHAT IS THIS INTEGRATION?
This is a custom integration that bridges Home Assistant with the Notify push
notification service. Once configured, you can send notifications to your iOS/Android
devices using standard Home Assistant automation syntax.

HOW IT WORKS:
1. User configures device_id and token via the UI (config flow)
2. Integration sets up a notify service (notify.{name})
3. Automations/scripts can call the service to send notifications
4. Integration handles API communication with Notify servers

EXAMPLE USAGE IN AUTOMATIONS:
automation:
  - alias: "Door Open Alert"
    trigger:
      - platform: state
        entity_id: binary_sensor.front_door
        to: "on"
    action:
      - service: notify.my_phone
        data:
          message: "Front door opened"
          title: "Security Alert"

INTEGRATION SETUP FLOW:
1. User adds integration via UI (Settings > Integrations > Add Integration)
2. Config flow prompts for device_id and token
3. Integration validates credentials with API
4. Notify platform is loaded and service becomes available
5. User can now send notifications via automations

WHY AN INTEGRATION INSTEAD OF AN ADD-ON?
- Works on ALL Home Assistant installation types (not just OS/Supervised)
- Native UI integration (no separate web interface needed)
- Cleaner automation syntax (no REST commands)
- Better user experience (standard HA patterns)
- Easier to maintain and distribute
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import discovery

from .const import CONF_DEVICE_ID, CONF_TOKEN, DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """
    Set up Notify API from a config entry.

    This function is called when Home Assistant loads the integration.
    It uses the notify platform discovery system to properly register
    the notification service with the automation UI.

    WHAT HAPPENS HERE:
    1. Store credentials in hass.data for the notify platform to access
    2. Generate a friendly service name from the integration title
    3. Load the notify platform via discovery (ensures UI fields work)
    4. Register update listener for configuration changes
    5. Return True to indicate successful setup

    WHY PLATFORM DISCOVERY?
    Platform discovery is the standard Home Assistant pattern for notify
    services. It ensures proper integration with the automation UI and
    that service fields (message, title, data) are recognized correctly.

    Args:
        hass: The Home Assistant instance
        entry: The config entry containing user configuration (device_id, token, title)

    Returns:
        bool: True if setup was successful
    """
    # Store credentials in hass.data for the notify platform to retrieve
    # The notify platform will access these when creating the service
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        CONF_DEVICE_ID: entry.data[CONF_DEVICE_ID],
        CONF_TOKEN: entry.data[CONF_TOKEN],
    }

    # Generate a friendly service name from the integration title
    # Example: "My Phone" becomes "my_phone" for service notify.my_phone
    # Remove special characters to ensure valid service name
    friendly_name = entry.title.lower().replace(" ", "_").replace("!", "").replace("(", "").replace(")", "").replace(".", "")
    service_name = friendly_name if friendly_name else f"notify_api_{entry.entry_id[:8]}"

    # Load the notify platform using discovery
    # This creates the notification service and registers it with Home Assistant
    # Discovery ensures the automation UI recognizes the service fields
    hass.async_create_task(
        discovery.async_load_platform(
            hass,
            Platform.NOTIFY,
            DOMAIN,
            {
                CONF_NAME: service_name,
                "entry_id": entry.entry_id,
            },
            {},
        )
    )

    # Register update listener to reload integration when options change
    # This allows users to reconfigure settings without removing/re-adding
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    _LOGGER.info(
        "Integration setup complete for '%s'. Service will be: notify.%s",
        entry.title,
        service_name
    )

    return True


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """
    Reload the config entry when options change.

    This is called when the user updates settings via the options flow.
    """
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """
    Unload a config entry.

    This function is called when:
    - User removes the integration via UI
    - Integration is being reloaded
    - Home Assistant is shutting down

    WHAT DOES IT DO?
    1. Unregister the notify service
    2. Clean up stored data from hass.data
    3. Return True to indicate successful unload

    WHY IS THIS IMPORTANT?
    Proper cleanup prevents:
    - Memory leaks
    - Stale data
    - Integration conflicts on reload
    - Orphaned services

    Args:
        hass: The Home Assistant instance
        entry: The config entry being unloaded

    Returns:
        bool: True if unload was successful
    """
    # Generate the service name that was registered
    service_name = f"{DOMAIN}_{entry.entry_id[:8]}"

    # Unregister the notify service
    hass.services.async_remove("notify", service_name)

    _LOGGER.info(
        "Unregistered notify service: notify.%s for '%s'",
        service_name,
        entry.title
    )

    # Remove the service instance from hass.data
    # This frees up memory and prevents stale data
    hass.data[DOMAIN].pop(entry.entry_id, None)

    # Return True to indicate successful unload
    return True
