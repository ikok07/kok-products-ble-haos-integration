from bleak import BleakGATTCharacteristic, normalize_uuid_16
from homeassistant.components.switch import SwitchEntity, SwitchDeviceClass
from homeassistant.helpers.device_registry import DeviceInfo

from ..const import DOMAIN, _LOGGER
from ..coordinator import CoordinatorCallbackType, DeviceCoordinator

class SwitchDevice(SwitchEntity):
    _SWITCH_CHARACTERISTIC = normalize_uuid_16(0x2A56)                             # Bluetooth Digital Characteristic (from Automation Service [0x1815] )
    _attr_device_class = SwitchDeviceClass.SWITCH
    _notification_cb: callable

    def __init__(self, coordinator: DeviceCoordinator, should_poll: bool = True):
        self.coordinator = coordinator
        self.should_poll = should_poll
        self._attr_unique_id = f"{coordinator.address}_switch"
        self._attr_device_info = DeviceInfo(name=coordinator.name, identifiers={(DOMAIN, coordinator.address)})
        self._attr_icon = "mdi:toggle-switch-outline"

    async def turn_on(self, **kwargs):
        _LOGGER.debug("Switch device turned on. (%s:%s)", self.coordinator.name, self.coordinator.address)
        await self.coordinator.write_char(self._SWITCH_CHARACTERISTIC, bytes([0x01]))

    async def turn_off(self, **kwargs):
        _LOGGER.debug("Switch device turned off. (%s:%s)", self.coordinator.name, self.coordinator.address)
        await self.coordinator.write_char(self._SWITCH_CHARACTERISTIC, bytes([0x00]))

    async def async_added_to_hass(self):
        self._notification_cb = self._on_ble_notification
        self.coordinator.register_callback(self._notification_cb)

        await self.coordinator.subscribe_char(self._SWITCH_CHARACTERISTIC)

        data = await self.coordinator.read_char(self._SWITCH_CHARACTERISTIC)
        self._attr_is_on = bool(data[0])
        _LOGGER.debug("Switch device added to hass. (%s:%s)", self.coordinator.name, self.coordinator.address)

    async def async_will_remove_from_hass(self):
        self.coordinator.unregister_callback(self._notification_cb)
        _LOGGER.debug("Switch device removed from hass. (%s:%s)", self.coordinator.name, self.coordinator.address)

    def _on_ble_notification(self, cb_type: CoordinatorCallbackType, char: BleakGATTCharacteristic, data: bytearray):
        _LOGGER.debug("Switch device received BLE notification. Characteristic: %s, Data: %s. (%s:%s)", char, data.hex(), self.coordinator.name, self.coordinator.address)
        if cb_type == CoordinatorCallbackType.NOTIFICATION and char.uuid == self._SWITCH_CHARACTERISTIC:
            self._attr_is_on = bool(data[0])
            self.async_schedule_update_ha_state()