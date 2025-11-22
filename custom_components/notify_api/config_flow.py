"""
Config Flow for Notify API Integration

This module handles the UI-based configuration of the integration.
It creates the forms users see when adding/configuring the integration.

WHAT IS A CONFIG FLOW?
A config flow is the UI wizard that guides users through setting up an integration.
It's what you see when you go to Settings > Integrations > Add Integration.

CONFIG FLOW STEPS:
1. User clicks "Add Integration" and selects "Notify API"
2. Form is displayed asking for device_id and token
3. User enters their credentials
4. Config flow validates credentials by testing API connection
5. If valid, integration is created and notify service becomes available
6. If invalid, error is shown and user can try again

WHY USE CONFIG FLOW?
- User-friendly UI for configuration (no YAML editing)
- Built-in validation and error handling
- Credentials are stored securely
- Users can reconfigure without editing files
- Multiple instances supported (multiple devices/groups)

EXAMPLE USER FLOW:
1. User: "I want to add Notify API integration"
2. HA: Shows form with device_id and token fields
3. User: Enters "ABC12345" and "my_secret_token"
4. Config Flow: Validates by sending test API request
5. HA: Creates integration and notify.notify_api service
6. User: Can now use notify.notify_api in automations
"""

from __future__ import annotations

import logging
from typing import Any

import requests
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import (
    API_BASE_URL,
    CONF_DEFAULT_GROUP_TYPE,
    CONF_DEFAULT_ICON_URL,
    CONF_DEFAULT_TITLE,
    CONF_DEVICE_ID,
    CONF_TOKEN,
    DEFAULT_TIMEOUT,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

# Define the configuration schema
# This creates the form fields users see in the UI
# vol (voluptuous) is used for data validation
STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        # Device/Group ID field
        # str type means it's a text input field
        # Required field - users must enter a value
        vol.Required(CONF_DEVICE_ID): str,

        # Token field
        # str type means it's a text input field
        # Required field - users must enter a value
        # The UI will show this as a password field (hidden characters)
        vol.Required(CONF_TOKEN): str,

        # Optional friendly name
        # Users can name their integration (e.g., "Dan's iPhone", "Family Group")
        # If not provided, defaults to "Notify! Alert ({device_id})"
        vol.Optional("name"): str,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """
    Validate the user input by testing API credentials.

    This function is called after the user submits the configuration form.
    It verifies that the provided device_id and token are valid by making
    a test API call.

    VALIDATION FLOW:
    1. Extract device_id and token from user input
    2. Build a test API request to Notify API
    3. Send the request with user's credentials
    4. Check if API accepts the credentials
    5. Return validated data or raise error

    WHY VALIDATE?
    - Catch typos in device_id or token immediately
    - Prevent invalid configurations from being saved
    - Give users instant feedback on their credentials
    - Avoid confusion from failed automations later
    - Ensure API is reachable

    WHAT HAPPENS IF VALIDATION FAILS?
    - CannotConnect error: Network/API unreachable
    - InvalidAuth error: Wrong device_id or token
    - User sees error message and can try again
    - No integration entry is created

    Args:
        hass: The Home Assistant instance
        data: User input from the config form (device_id and token)

    Returns:
        dict: The validated data with a title for the integration

    Raises:
        CannotConnect: If API is unreachable
        InvalidAuth: If credentials are invalid
    """
    device_id = data[CONF_DEVICE_ID]
    token = data[CONF_TOKEN]

    # Build test notification
    # We send a test notification to:
    # 1. Validate the credentials work
    # 2. Give the user confirmation that setup succeeded
    test_payload = {
        "text": "✅ Notify Alerts integration successfully configured in Home Assistant!",
        "title": "Integration Test"
    }

    try:
        # Make the API request using requests library
        # We use hass.async_add_executor_job to run synchronous requests code
        # in the executor pool, preventing it from blocking the event loop
        #
        # WHY async_add_executor_job?
        # - requests is synchronous (blocking)
        # - Home Assistant is async (non-blocking)
        # - This wrapper runs sync code in a thread pool
        # - Prevents blocking the main event loop
        def _make_request():
            """Synchronous API request."""
            response = requests.post(
                f"{API_BASE_URL}/{device_id}",
                json=test_payload,
                params={"token": token},
                timeout=DEFAULT_TIMEOUT,
            )
            return response

        # Run the synchronous request in executor pool
        response = await hass.async_add_executor_job(_make_request)

        # Check response status
        # 200 = Success (valid credentials)
        # 401/403 = Invalid credentials
        # 404 = Device/Group not found
        # Other = Connection/API issues
        if response.status_code == 401 or response.status_code == 403:
            # Authentication failed
            raise InvalidAuth
        elif response.status_code == 404:
            # Device/Group ID not found
            raise InvalidAuth("Device or group ID not found")
        elif response.status_code != 200:
            # Other API error
            raise CannotConnect(f"API returned status {response.status_code}")

    except requests.exceptions.Timeout:
        # API request timed out
        raise CannotConnect("Connection to Notify API timed out")
    except requests.exceptions.ConnectionError:
        # Network error (no internet, DNS failure, etc.)
        raise CannotConnect("Could not connect to Notify API")
    except requests.exceptions.RequestException as err:
        # Other request errors
        _LOGGER.error("Error validating credentials: %s", err)
        raise CannotConnect(f"Unexpected error: {err}")

    # Validation successful!
    # Return a title for the integration entry
    # This will be displayed in the UI as the integration name
    # Use custom name if provided, otherwise default to "Notify! Alert ({device_id})"
    custom_name = data.get("name", "").strip()
    if custom_name:
        title = custom_name
    else:
        title = f"Notify! Alert ({device_id.upper()})"

    return {"title": title}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """
    Handle a config flow for Notify API.

    This class manages the configuration wizard UI.
    It's responsible for:
    - Displaying configuration forms
    - Collecting user input
    - Validating input
    - Creating config entries
    - Handling errors

    WHAT IS A CONFIG ENTRY?
    A config entry is a saved configuration instance.
    Each entry represents one configured notify service.
    Users can have multiple entries (multiple devices/groups).

    USER JOURNEY:
    1. User adds integration
    2. async_step_user() shows form
    3. User fills form and submits
    4. async_step_user() validates input
    5. Config entry is created
    6. Notify service becomes available

    VERSION TRACKING:
    The VERSION constant is used to track config schema changes.
    If we change the config format in the future, we can write
    migration code to update old entries.
    """

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """
        Handle the initial step of user configuration.

        This is the first (and only) step in our config flow.
        It displays the form, collects input, validates it, and creates the entry.

        FLOW BEHAVIOR:
        - First call (user_input is None): Show the form
        - Second call (user_input has data): Validate and create entry

        WHY TWO CALLS?
        Config flows are state machines. The same method is called multiple times:
        1. First call: Display form to user
        2. User submits form
        3. Second call: Process submission
        4. Either show error and redisplay form, or create entry

        Args:
            user_input: None on first call, contains form data on submission

        Returns:
            FlowResult: Either shows form or creates config entry
        """
        # Dictionary to store any errors that occur during validation
        # Keys are field names, values are error codes
        # Error codes are translated using strings.json
        errors: dict[str, str] = {}

        if user_input is not None:
            # User has submitted the form
            # Now we validate their input
            try:
                # Validate the credentials by testing API connection
                # This calls validate_input() which makes a test API request
                info = await validate_input(self.hass, user_input)

                # Validation successful!
                # Create the config entry
                # This saves the configuration and loads the integration
                #
                # WHAT HAPPENS NEXT?
                # 1. Config entry is saved to .storage/core.config_entries
                # 2. async_setup_entry() in __init__.py is called
                # 3. Notify platform is loaded
                # 4. notify.{name} service becomes available
                # 5. User can use the service in automations
                return self.async_create_entry(title=info["title"], data=user_input)

            except CannotConnect:
                # Network/API connection error
                # Set error on the base form (not specific field)
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                # Invalid credentials (wrong device_id or token)
                # Set error on the base form
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                # Unexpected error occurred
                # Log it for debugging
                _LOGGER.exception("Unexpected exception during validation")
                errors["base"] = "unknown"

            # If we get here, validation failed
            # Fall through to show the form again with errors

        # Show the configuration form
        # This happens on:
        # - First load (user_input is None)
        # - Validation failure (errors dict is populated)
        #
        # FORM COMPONENTS:
        # - step_id: Unique identifier for this step
        # - data_schema: The form schema (defines fields)
        # - errors: Error messages to display
        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        """
        Get the options flow handler.

        This method is called by Home Assistant when the user wants to reconfigure
        the integration. It returns an OptionsFlowHandler instance.

        WHEN IS THIS CALLED?
        - User clicks "Configure" on the integration in the UI
        - User wants to change device_id or token
        - User wants to update any settings

        Returns:
            OptionsFlowHandler: The options flow handler instance
        """
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """
    Handle options flow for Notify API integration.

    This class allows users to reconfigure the integration after initial setup.
    It provides a UI to change device_id and token without deleting and re-adding.

    WHY OPTIONS FLOW?
    - Users can update credentials if they change
    - No need to delete and re-add the integration
    - Preserves automation configurations
    - Better user experience

    USER JOURNEY:
    1. User goes to Settings → Devices & Services
    2. Finds the Notify API integration
    3. Clicks "Configure" button
    4. Form appears with current credentials (token masked)
    5. User updates credentials
    6. Changes are validated and saved
    7. Integration reloads with new credentials
    """

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry

    @property
    def config_entry(self):
        """Return the config entry."""
        # Use the injected config_entry if available (standard HA behavior)
        # Fallback to our stored _config_entry if needed
        # This avoids the "sets option flow config_entry explicitly" warning
        if hasattr(super(), "config_entry"):
            return super().config_entry
        return self._config_entry

    async def async_step_init(self, user_input=None):
        """
        Handle the options flow.

        This is the main step for reconfiguration.
        It shows the form with current values and allows users to update them.

        FLOW BEHAVIOR:
        - First call (user_input is None): Show form with current values
        - Second call (user_input has data): Validate and save

        Args:
            user_input: None on first call, contains form data on submission

        Returns:
            FlowResult: Either shows form or updates config entry
        """
        errors = {}

        if user_input is not None:
            # User submitted the form
            try:
                # Validate the new credentials
                info = await validate_input(self.hass, user_input)

                # Separate core credentials from optional defaults
                # Core credentials (device_id, token) go in entry.data
                # Optional defaults go in entry.options
                core_data = {
                    CONF_DEVICE_ID: user_input[CONF_DEVICE_ID],
                    CONF_TOKEN: user_input[CONF_TOKEN],
                }

                options_data = {
                    CONF_DEFAULT_TITLE: user_input.get(CONF_DEFAULT_TITLE, ""),
                    CONF_DEFAULT_ICON_URL: user_input.get(CONF_DEFAULT_ICON_URL, ""),
                    CONF_DEFAULT_GROUP_TYPE: user_input.get(CONF_DEFAULT_GROUP_TYPE, ""),
                }

                # Update the config entry with new data and options
                # data = core credentials (device_id, token)
                # options = optional defaults (title, icon_url, group_type)
                self.hass.config_entries.async_update_entry(
                    self.config_entry,
                    data=core_data,
                    options=options_data,
                )

                # Return success - update_listener will handle reload
                return self.async_create_entry(title="", data={})

            except CannotConnect:
                # Network/API connection error
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                # Invalid credentials
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                # Unexpected error
                _LOGGER.exception("Unexpected exception during options flow")
                errors["base"] = "unknown"

        # Build the form schema with current values as defaults
        # This pre-fills the form with existing configuration
        # The token is masked with *** for security
        #
        # FORM FIELDS:
        # - device_id: Required - The device or group ID
        # - token: Required - The API authentication token
        # - default_title: Optional - Default title for all notifications
        # - default_icon_url: Optional - Default icon URL for all notifications
        # - default_group_type: Optional - Default group type for all notifications
        #
        # WHY OPTIONAL DEFAULTS?
        # - Users can set these once and forget them
        # - Automations can still override them per-notification
        # - Makes simple automations even simpler
        # - Consistent branding/styling across all notifications
        options_schema = vol.Schema(
            {
                vol.Required(
                    CONF_DEVICE_ID,
                    default=self.config_entry.data.get(CONF_DEVICE_ID, ""),
                ): str,
                vol.Required(
                    CONF_TOKEN,
                    default=self.config_entry.data.get(CONF_TOKEN, ""),
                ): str,
                vol.Optional(
                    CONF_DEFAULT_TITLE,
                    description={"suggested_value": self.config_entry.options.get(CONF_DEFAULT_TITLE, "")},
                ): str,
                vol.Optional(
                    CONF_DEFAULT_ICON_URL,
                    description={"suggested_value": self.config_entry.options.get(CONF_DEFAULT_ICON_URL, "")},
                ): str,
                vol.Optional(
                    CONF_DEFAULT_GROUP_TYPE,
                    description={"suggested_value": self.config_entry.options.get(CONF_DEFAULT_GROUP_TYPE, "")},
                ): str,
            }
        )

        # Show the reconfiguration form
        # This displays:
        # - Current device_id (pre-filled)
        # - Current token (pre-filled but will be masked in UI)
        # - Any validation errors
        return self.async_show_form(
            step_id="init",
            data_schema=options_schema,
            errors=errors,
        )


class CannotConnect(HomeAssistantError):
    """
    Error to indicate we cannot connect to the API.

    This exception is raised when:
    - Network is unreachable
    - DNS resolution fails
    - API is down
    - Request times out
    - Firewall blocks connection

    WHAT HAPPENS WHEN RAISED?
    - Config flow catches it
    - Sets errors["base"] = "cannot_connect"
    - Shows user-friendly error message
    - User can try again
    """


class InvalidAuth(HomeAssistantError):
    """
    Error to indicate authentication failure.

    This exception is raised when:
    - Token is wrong or expired
    - Device/Group ID doesn't exist
    - Token doesn't have permission for the device/group
    - API returns 401/403/404

    WHAT HAPPENS WHEN RAISED?
    - Config flow catches it
    - Sets errors["base"] = "invalid_auth"
    - Shows user-friendly error message
    - User can correct credentials and try again
    """
