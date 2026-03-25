import asyncio
from enum import Enum
from typing import Callable, cast

from bleak import BleakClient, BleakGATTCharacteristic, BleakError
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import _LOGGER, MAX_RECONNECT_ATTEMPTS, RECONNECT_DELAY_SECONDS, DOMAIN


class CoordinatorCallbackType(Enum):
    NOTIFICATION = "notification"

CoordinatorCallback = Callable[[CoordinatorCallbackType, BleakGATTCharacteristic, bytearray], None]

class DeviceCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, name: str, address: str):
        super().__init__(hass, _LOGGER, name=name)
        self.address = address
        self._client: BleakClient | None = None
        self._callbacks: list[CoordinatorCallback] = []

    async def connect(self, requires_pairing: bool = False) -> bool:
        self._client = BleakClient(
            self.address,
            disconnected_callback=self._on_disconnected
        )
        await self._client.connect()
        if requires_pairing:
            await self._client.pair()

        self.last_update_success = True

        _LOGGER.info("Device connected (%s:%s)", self.name, self.address)

        return True

    async def disconnect(self):
        if self._client:
            await self._client.disconnect()

    async def reconnect(self):
        _LOGGER.warning("Reconnecting device. (%s:%s)", self.name, self.address)
        for attempt in range(1, MAX_RECONNECT_ATTEMPTS + 1):
            _LOGGER.warning("Attempt: %d/%d. (%s:%s)", attempt, MAX_RECONNECT_ATTEMPTS, self.name, self.address)
            try:
                await self.connect()
                return
            except (BleakError, asyncio.TimeoutError) as e:
                _LOGGER.warning("Reconnect attempt %d failed. (%s:%s)", attempt, self.name, self.address)
                if attempt < MAX_RECONNECT_ATTEMPTS:
                    await asyncio.sleep(RECONNECT_DELAY_SECONDS * attempt)
                pass

        _LOGGER.error("Failed to reconnect to device. (%s:%s)", self.name, self.address)
        self.last_update_success = False
        self.async_update_listeners()

    async def subscribe_char(self, char: BleakGATTCharacteristic | str):
        try:
            await self._client.start_notify(char, self._on_notification)
            _LOGGER.debug("Subscribed to characteristic... Characteristic: %s. (%s:%s)", char, self.name, self.address)
        except Exception as e:
            _LOGGER.error("Failed to subscribe to %s: %s", char, e)

    async def unsubscribe_char(self, char: BleakGATTCharacteristic | str):
        try:
            await self._client.stop_notify(char)
            _LOGGER.debug("Unsubscribed to characteristic... Characteristic: %s. (%s:%s)", char, self.name, self.address)
        except Exception as e:
            _LOGGER.debug("Failed to unsubscribe from %s (may not be subscribed): %s", char, e)

    async def read_char(self, char: BleakGATTCharacteristic | str) -> bytearray:
        data = await self._client.read_gatt_char(char)
        _LOGGER.debug("Read from characteristic... Characteristic: %s, Data: %s. (%s:%s)", char, data.hex(), self.name, self.address)
        return data

    async def write_char(self, char: BleakGATTCharacteristic | str, data: bytes):
        await self._client.write_gatt_char(char, data)
        _LOGGER.debug("Wrote to characteristic... Characteristic: %s, Data: %s. (%s:%s)", char, data.hex(), self.name, self.address)

    def register_callback(self, callback: CoordinatorCallback):
        self._callbacks.append(callback)

    def unregister_callback(self, callback: CoordinatorCallback):
        self._callbacks.remove(callback)

    def fire_event(self, event_data: any):
        self.hass.bus.async_fire(f"{DOMAIN}_event", {"device_id": self.address, **event_data})

    def _on_notification(self, sender: BleakGATTCharacteristic, data: bytearray):
        for callback in self._callbacks:
            callback(CoordinatorCallbackType.NOTIFICATION, sender, data)

    def _on_disconnected(self, client: BleakClient):
        _LOGGER.info("Device disconnected (%s:%s)", self.name, self.address)
        asyncio.ensure_future(self.reconnect())