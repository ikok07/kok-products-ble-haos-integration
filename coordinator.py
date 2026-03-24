import logging
from enum import Enum
from typing import Callable

from bleak import BleakClient, BleakGATTCharacteristic
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity

_LOGGER = logging.getLogger(__name__)

class CoordinatorCallbackType(Enum):
    NOTIFICATION = "notification"

CoordinatorCallback = Callable[[CoordinatorCallbackType, BleakGATTCharacteristic, bytearray], None]

class DeviceCoordinator:
    def __init__(self, hass: HomeAssistant, name: str, address: str):
        self.hass = hass
        self.name = name
        self.address = address
        self._client: BleakClient | None = None
        self._callbacks: list[CoordinatorCallback] = []

    async def connect(self) -> bool:
        self._client = BleakClient(
            self.address,
            disconnected_callback=self._on_disconnected
        )
        await self._client.connect()
        await self._client.pair()

        return True

    async def disconnect(self):
        if self._client:
            await self._client.disconnect()

    async def subscribe_char(self, char: BleakGATTCharacteristic | str):
        await self._client.start_notify(char, self._on_notification)

    async def read_char(self, char: BleakGATTCharacteristic | str) -> bytearray:
        return await self._client.read_gatt_char(char)

    async def write_char(self, char: BleakGATTCharacteristic | str, data: bytes):
        await self._client.write_gatt_char(char, data)

    def register_callback(self, callback: CoordinatorCallback):
        self._callbacks.append(callback)

    def unregister_callback(self, callback: CoordinatorCallback):
        self._callbacks.remove(callback)

    def _on_notification(self, sender: BleakGATTCharacteristic, data: bytearray):
        for callback in self._callbacks:
            callback(CoordinatorCallbackType.NOTIFICATION, sender, data)

    def _on_disconnected(self, client: BleakClient):
        _LOGGER.warning("Device %s disconnected", client.name)
        # TODO: Implement reconnect...