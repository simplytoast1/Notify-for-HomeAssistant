"""Constants for the Notify API integration."""

DOMAIN = "notify_api"

# Configuration keys
CONF_DEVICE_ID = "device_id"
CONF_TOKEN = "token"

# Optional configuration keys (customizable via options flow)
CONF_DEFAULT_TITLE = "default_title"
CONF_DEFAULT_ICON_URL = "default_icon_url"
CONF_DEFAULT_GROUP_TYPE = "default_group_type"

# API endpoint
API_BASE_URL = "https://notifypush.pingie.com/notify-json"

# Notification attributes
ATTR_TITLE = "title"
ATTR_ICON_URL = "icon_url"
ATTR_GROUP_TYPE = "group_type"

# Default values
DEFAULT_NAME = "Notify Alerts"
DEFAULT_TIMEOUT = 10
