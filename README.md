# Notify Alerts Integration for Home Assistant

Send push notifications to your iOS devices using the [Notify API](https://notify.pingie.com) directly from Home Assistant.

Made with ❤️ by [Pingie.com](https://pingie.com)

## Overview

This custom integration creates a native Home Assistant notification service that works with the Notify push notification API for iOS devices. Send rich notifications with support for titles, custom icons, and grouping.

## Features

- 🔔 **Native Integration** - Works like any other Home Assistant notify service
- 📱 **iOS Native** - Designed specifically for iOS devices
- 🎨 **Rich Notifications** - Support for titles, custom icons, and group types
- ⚙️ **Config Flow** - Easy UI-based setup (no YAML editing required)
- 🔒 **Secure** - Credentials stored securely in Home Assistant
- 🚀 **Simple** - Clean automation syntax
- 🌍 **Universal** - Works on all Home Assistant installation types

## Installation

### HACS Installation (Recommended)

1. Ensure [HACS](https://hacs.xyz/) is installed in your Home Assistant
2. Add this repository as a custom repository in HACS:
   - Go to **HACS → Integrations**
   - Click the **three dots (⋮)** in the top right
   - Select **"Custom repositories"**
   - Add URL: `https://github.com/simplytoast1/Notify-for-HomeAssistant`
   - Category: **Integration**
   - Click **"Add"**
3. Find **"Notify Alerts"** in HACS and click **"Install"**
4. **Restart Home Assistant**

### Manual Installation

If you prefer not to use HACS:

1. Download the `custom_components/notify_api` folder from this repository
2. Copy it to your Home Assistant `config` directory:
   ```
   config/
   └── custom_components/
       └── notify_api/
           ├── __init__.py
           ├── config_flow.py
           ├── const.py
           ├── manifest.json
           ├── notify.py
           ├── services.yaml
           ├── strings.json
           └── translations/
               └── en.json
   ```
3. **Restart Home Assistant**

## Configuration

1. Go to **Settings → Devices & Services → Add Integration**
2. Search for "Notify Alerts"
3. Enter your credentials:
   - **Device/Group ID**: Your Notify device or group identifier
   - **Token**: Your Notify API token
   - **Name** (Optional): Friendly name for this integration (e.g., "My iPhone", "Family Group")

You can find your Device ID and Token in the Notify iOS app.

### Multiple Devices

You can add multiple instances of the integration for different devices or groups. Each instance creates a separate notify service.

**Example:**
- Instance 1: "My iPhone" → Service: `notify.my_iphone`
- Instance 2: "Family Group" → Service: `notify.family_group`

## Usage

### Service Fields

When using the notify service in automations, you have access to these fields:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `message` | string | Yes | The notification message text |
| `title` | string | No | Notification title (appears in bold) |
| `data` | object | No | Additional notification options (see below) |

### Data Object Fields

The `data` field accepts an object with these optional properties:

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `icon_url` | string | Custom icon URL (HTTPS PNG/JPG recommended) | `"https://example.com/icon.png"` |
| `group_type` | string | Group identifier for threading related notifications | `"security"`, `"alerts"`, `"climate"` |

### Examples

#### Basic Notification

```yaml
service: notify.my_iphone
data:
  message: "This is a test notification"
```

#### Notification with Title

```yaml
service: notify.my_iphone
data:
  message: "Front door was opened"
  title: "Security Alert"
```

#### Full-Featured Notification with Custom Icon and Grouping

```yaml
service: notify.my_iphone
data:
  message: "Motion detected at front door"
  title: "Security Alert"
  data:
    icon_url: "https://notifyicons.pingie.com/security.png"
    group_type: "security"
```

## Automation Examples

### Light Turned On Alert

```yaml
automation:
  - alias: "Living Room Light Alert"
    trigger:
      - platform: state
        entity_id: light.living_room
        to: "on"
    action:
      - service: notify.my_iphone
        data:
          message: "Living room light was turned on at {{ now().strftime('%I:%M %p') }}"
          title: "💡 Light Alert"
          data:
            icon_url: "https://notifyicons.pingie.com/lightbulb.png"
            group_type: "lights"
```

### Door Sensor Alert

```yaml
automation:
  - alias: "Front Door Alert"
    trigger:
      - platform: state
        entity_id: binary_sensor.front_door
        to: "on"
    action:
      - service: notify.my_iphone
        data:
          message: "Front door opened"
          title: "🚪 Security"
          data:
            icon_url: "https://notifyicons.pingie.com/door.png"
            group_type: "security"
```

### Temperature Alert with Dynamic Message

```yaml
automation:
  - alias: "High Temperature Alert"
    trigger:
      - platform: numeric_state
        entity_id: sensor.living_room_temperature
        above: 75
    action:
      - service: notify.my_iphone
        data:
          message: "Living room temperature is {{ states('sensor.living_room_temperature') }}°F"
          title: "🌡️ Temperature Alert"
          data:
            icon_url: "https://notifyicons.pingie.com/thermometer.png"
            group_type: "climate"
```

## Understanding Notification Grouping

The `group_type` field allows you to organize related notifications together:

- **Same group_type**: Notifications with the same group_type will be threaded together on your device
- **Different group_type**: Creates separate notification threads
- **No group_type**: Each notification appears independently

**Example:**
```yaml
# All these notifications will be grouped under "security"
- message: "Front door opened"
  data:
    group_type: "security"

- message: "Motion detected"
  data:
    group_type: "security"

- message: "Window sensor triggered"
  data:
    group_type: "security"
```

## Custom Icons

You can use custom icons for your notifications by providing an HTTPS URL to a PNG or JPG image.

**Recommended icon hosting:**
- Use [https://notifyicons.pingie.com/](https://notifyicons.pingie.com/) for reliable icon hosting
- Or host your own icons on a publicly accessible HTTPS server

**Icon guidelines:**
- Use HTTPS URLs only (HTTP will not work)
- Recommended size: 512x512 pixels
- Supported formats: PNG, JPG
- Keep file size under 1MB for best performance

## Troubleshooting

### Service not appearing in automations

1. Make sure you've restarted Home Assistant after installation
2. Check that the integration is configured in **Settings → Devices & Services**
3. Verify the integration shows as "Configured" (not "Not loaded")

### Notifications not being received

1. Verify your Device ID and Token are correct in the integration settings
2. Test the notification from **Developer Tools → Actions**:
   - Choose your notify service (e.g., `notify.my_iphone`)
   - Enter a test message
   - Click "Perform Action"
3. Check Home Assistant logs for errors: **Settings → System → Logs**

### Reconfiguring credentials

1. Go to **Settings → Devices & Services**
2. Find your **Notify Alerts** integration
3. Click the **Configure** button
4. Update your Device ID or Token
5. Click **Submit**

The integration will reload automatically with the new credentials.

## API Information

This integration communicates with the Notify API server at `https://notifypush.pingie.com`.

**API Endpoint:** `POST /notify-json/{device_id}?token={token}`

**Request format:**
```json
{
  "text": "Your notification message",
  "title": "Optional Title",
  "iconUrl": "https://example.com/icon.png",
  "groupType": "optional-group"
}
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For support, visit [notify.pingie.com](https://notify.pingie.com) or open an issue on GitHub.

## Changelog

### 1.0.0 (Initial Release)
- Native Home Assistant integration
- UI-based configuration with config flow
- Custom naming support for integrations
- Send notifications with title, custom icons, and grouping
- Multiple device/group support
- Based on notify platform architecture

---

Made with ❤️ by [Pingie.com](https://pingie.com)
