from bleak import normalize_uuid_str
from homeassistant.components.switch import SwitchEntity, SwitchDeviceClass
from homeassistant.helpers.device_registry import DeviceInfo

from ..const import DOMAIN, _LOGGER
from ..coordinator import CoordinatorCallbackType, DeviceCoordinator

class SwitchDevice(SwitchEntity):
    _SWITCH_CHARACTERISTIC = normalize_uuid_str("2A56")                             # Bluetooth Digital Characteristic (from Automation Service [0x1815] )
    _attr_device_class = SwitchDeviceClass.SWITCH
    _event_cb: callable

    def __init__(self, coordinator: DeviceCoordinator, should_poll: bool = True):
        self.coordinator = coordinator
        self.should_poll = should_poll
        self._attr_unique_id = f"{coordinator.address}_switch"
        self._attr_device_info = DeviceInfo(name=coordinator.name, identifiers={(DOMAIN, coordinator.address)})
        self._attr_icon = "mdi:toggle-switch-outline"

    async def async_turn_on(self, **kwargs):
        _LOGGER.debug("Switch device turned on. (%s:%s)", self.coordinator.name, self.coordinator.address)
        await self.coordinator.write_char(self._SWITCH_CHARACTERISTIC, bytes([0x01]))

    async def async_turn_off(self, **kwargs):
        _LOGGER.debug("Switch device turned off. (%s:%s)", self.coordinator.name, self.coordinator.address)
        await self.coordinator.write_char(self._SWITCH_CHARACTERISTIC, bytes([0x00]))

    async def async_added_to_hass(self):
        self._event_cb = self._on_event
        self.coordinator.register_callback(self._event_cb)

        # Remove active subscriptions to prevent overloading
        try:
            await self.coordinator.unsubscribe_char(self._SWITCH_CHARACTERISTIC)
        except:
            pass

        await self.coordinator.subscribe_char(self._SWITCH_CHARACTERISTIC)

        await self._pull_latest_state()

        _LOGGER.debug("Switch device added to hass. (%s:%s)", self.coordinator.name, self.coordinator.address)

    async def async_will_remove_from_hass(self):
        try:
            await self.coordinator.unsubscribe_char(self._SWITCH_CHARACTERISTIC)
        except:
            pass

        self.coordinator.unregister_callback(self._event_cb)
        _LOGGER.debug("Switch device removed from hass. (%s:%s)", self.coordinator.name, self.coordinator.address)

    def _on_event(self, cb_type: CoordinatorCallbackType, attr: str, data: bytearray):
        _LOGGER.debug("Switch device received an event. Type: %s, Attribute: %s, Data: %s. (%s:%s)", cb_type, attr, data.hex(), self.coordinator.name, self.coordinator.address)
        match cb_type:
            case CoordinatorCallbackType.NOTIFICATION:
                if attr == self._SWITCH_CHARACTERISTIC:
                    self._attr_is_on = bool(data[0])
                    self._attr_available = True
                    self.coordinator.fire_event({"state": self._attr_is_on})
                    self.async_write_ha_state()
                return
            case CoordinatorCallbackType.RECONNECT:
                self._attr_available = True
                self.hass.async_create_task(self._pull_latest_state())
                self.async_write_ha_state()
                return
            case CoordinatorCallbackType.DISCONNECT:
                self._attr_available = False
                self.async_write_ha_state()
                return

    async def _pull_latest_state(self) -> bool:
        try:
            data = await self.coordinator.read_char(self._SWITCH_CHARACTERISTIC)
            self._attr_is_on = bool(data[0])
            self.async_write_ha_state()
            return True
        except Exception as e:
            _LOGGER.warning("Failed to pull latest device state: %s", e)
            return False