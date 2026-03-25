from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DOMAIN, _LOGGER
from .coordinator import DeviceCoordinator
from .models.device_entry import DeviceEntry, DeviceType

platforms_map: dict[DeviceType, list[str]] = {
    DeviceType.SWITCH: ["switch"]
}

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    try:
        device_entry = DeviceEntry.model_validate(dict(entry.data))
    except Exception as err:
        raise ConfigEntryNotReady(f"Invalid entry data: {err}") from err

    coordinator = DeviceCoordinator(hass, name=device_entry.name, address=device_entry.address)
    await coordinator.connect()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    platforms: list[str]
    if not device_entry.device_type:
        raise ConfigEntryNotReady(f"Missing device type. It should be placed in the advertised manufacturer data!")

    if not device_entry.device_type in platforms_map:
        raise ConfigEntryNotReady(f"Unsupported device type '{device_entry.device_type}'!")

    _LOGGER.debug("Device coordinator created. Device name: %s", device_entry.name)

    await hass.config_entries.async_forward_entry_setups(entry, platforms_map.get(device_entry.device_type))

    return True