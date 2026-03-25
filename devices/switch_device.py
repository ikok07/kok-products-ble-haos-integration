from bleak import BleakGATTCharacteristic, normalize_uuid_16
from homeassistant.components.switch import SwitchEntity, SwitchDeviceClass
from homeassistant.helpers.device_registry import DeviceInfo

from const import DOMAIN
from coordinator import CoordinatorCallbackType, DeviceCoordinator

class SwitchDevice(SwitchEntity):
    _SWITCH_CHARACTERISTIC = normalize_uuid_16(0x2A56)                             # Bluetooth Digital Characteristic (from Automation Service [0x1815] )
    _attr_device_class = SwitchDeviceClass.SWITCH
    _notification_cb: callable

    def __init__(self, coordinator: DeviceCoordinator, should_poll: bool = True):
        self.coordinator = coordinator
        self.should_poll = should_poll
        self._attr_unique_id = f"{coordinator.address}_switch"
        self._attr_device_info = DeviceInfo(name=coordinator.name, identifiers={{DOMAIN, coordinator.address}})
        self._attr_icon = "mdi:toggle-switch-outline"

    async def turn_on(self, **kwargs):
        await self.coordinator.write_char(self._SWITCH_CHARACTERISTIC, bytes([0x01]))

    async def turn_off(self, **kwargs):
        await self.coordinator.write_char(self._SWITCH_CHARACTERISTIC, bytes([0x00]))

    async def async_added_to_hass(self):
        self._notification_cb = self._on_ble_notification
        self.coordinator.register_callback(self._notification_cb)

        await self.coordinator.subscribe_char(self._SWITCH_CHARACTERISTIC)

        data = await self.coordinator.read_char(self._SWITCH_CHARACTERISTIC)
        self._attr_is_on = bool(data[0])

    async def async_will_remove_from_hass(self):
        self.coordinator.unregister_callback(self._notification_cb)

    def _on_ble_notification(self, cb_type: CoordinatorCallbackType, char: BleakGATTCharacteristic, data: bytearray):
        if cb_type == CoordinatorCallbackType.NOTIFICATION and char.uuid == self._SWITCH_CHARACTERISTIC:
            self._attr_is_on = bool(data[0])
            self.async_schedule_update_ha_state()