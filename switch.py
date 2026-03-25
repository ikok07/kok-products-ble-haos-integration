from typing import cast

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from const import DOMAIN
from coordinator import DeviceCoordinator
from devices.switch_device import SwitchDevice


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> bool:
    coordinator = cast(DeviceCoordinator, hass.data[DOMAIN][entry.entry_id])

    switch_device = SwitchDevice(coordinator, should_poll=False)
    async_add_entities([switch_device])

    return True