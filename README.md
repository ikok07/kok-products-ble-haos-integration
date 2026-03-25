# KOK BLE Products — Home Assistant Integration

A custom [Home Assistant](https://www.home-assistant.io/) integration for personal embedded devices that communicate over **Bluetooth Low Energy (BLE)**. It enables discovery, pairing, and control of supported KOK devices directly from the Home Assistant UI.

---

## Features

- Automatic BLE device discovery via Home Assistant's Bluetooth stack
- Device pairing and configuration through the UI config flow (no YAML required)
- Real-time state updates via BLE GATT notifications
- Supported device types:
  - **Switch** — toggle on/off via the Bluetooth Digital Characteristic (`0x2A56`)

---

## Requirements

- Home Assistant 2024.1 or newer
- A Bluetooth adapter accessible by Home Assistant (built-in or USB)
- `bluetooth` and `bluetooth_adapters` HA integrations enabled (built-in, enabled by default)

---

## Installation

1. In your Home Assistant config directory, open (or create) the `custom_components/` folder.
2. Copy all files from this repository into:
   ```
   <config>/custom_components/kok_products_ble/
   ```
   > ⚠️ The integration's folder name **must exactly match** the `domain` field in `manifest.json`, which is `kok_products_ble`.
   The final structure should look like:
   ```
   config/
   └── custom_components/
       └── kok_products_ble/       ← must be this exact name
           ├── __init__.py
           ├── manifest.json
           ├── config_flow.py
           ├── const.py
           ├── coordinator.py
           ├── switch.py
           ├── strings.json
           ├── devices/
           │   └── switch_device.py
           ├── models/
           │   └── device_entry.py
           └── translations/
               └── en.json
   ```
3. Restart Home Assistant.
4. Go to **Settings → Devices & Services → Add Integration** and search for **KOK BLE Products**.

## Device Protocol

Devices advertise themselves over BLE. The integration identifies supported devices by:

- **Service UUID**: `88c85bc1-feec-4c35-aa49-74ae36355165`
- **Manufacturer Data** (ID `0x4862`): first byte encodes the device type:

| Byte value | Device type |
|------------|-------------|
| `0x01`     | Switch      |

---

## Adding a Device

1. Make sure your device is powered on and within Bluetooth range.
2. Go to **Settings → Devices & Services → Add Integration → KOK BLE Products**.
3. Select the discovered device from the dropdown.
4. Confirm and optionally rename the device.
5. The device will appear in the Home Assistant dashboard.---
