from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .models.device_type import DEVICE_TYPE_PLATFORMS_MAP
from .const import DOMAIN, _LOGGER
from .coordinator import DeviceCoordinator
from .models.device_entry import DeviceEntryData

# Suggested BLE adapter - UGREEN CM109

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    try:
        device_entry_data = DeviceEntryData.model_validate(dict(entry.data))
    except Exception as err:
        raise ConfigEntryNotReady(f"Invalid entry data: {err}") from err

    coordinator = DeviceCoordinator(hass, name=device_entry_data.name, address=device_entry_data.address)
    await coordinator.connect(requires_pairing=device_entry_data.requires_pairing)

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    platforms: list[str]
    if not device_entry_data.device_type:
        raise ConfigEntryNotReady(f"Missing device type. It should be placed in the advertised manufacturer data!")

    if not device_entry_data.device_type in DEVICE_TYPE_PLATFORMS_MAP:
        raise ConfigEntryNotReady(f"Unsupported device type '{device_entry_data.device_type}'!")

    _LOGGER.debug("Device coordinator created. Device name: %s", device_entry_data.name)

    await hass.config_entries.async_forward_entry_setups(entry, DEVICE_TYPE_PLATFORMS_MAP.get(device_entry_data.device_type))

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    _LOGGER.debug("Entry %s has been removed!", entry.entry_id)

    coordinator: DeviceCoordinator | None = hass.data[DOMAIN][entry.entry_id]
    if coordinator:
        try:
            await coordinator.disconnect()
            _LOGGER.debug("Coordinator disconnected successfully! (%s:%s)", coordinator.name, coordinator.address)
        except Exception as e:
            _LOGGER.warning("Failed to disconnect coordinator after removing entry! (%s:%s)", coordinator.name, coordinator.address)

        hass.data[DOMAIN].pop(entry.entry_id)