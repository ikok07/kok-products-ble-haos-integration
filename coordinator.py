import asyncio
from enum import Enum
from typing import Callable, cast

from bleak import BleakClient, BleakGATTCharacteristic, BleakError, BleakScanner
from bleak_retry_connector import establish_connection, BleakClientWithServiceCache, BleakNotFoundError, \
    BleakOutOfConnectionSlotsError, BleakConnectionError
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import _LOGGER, MAX_RECONNECT_ATTEMPTS, DOMAIN, RECONNECT_ATTEMPT_DELAY_SECONDS


class CoordinatorCallbackType(Enum):
    NOTIFICATION = "notification"
    DISCONNECT = "disconnect"
    RECONNECT = "reconnect"

CoordinatorCallback = Callable[[CoordinatorCallbackType, str | None, bytearray | None], None]

class DeviceCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, name: str, address: str):
        super().__init__(hass, _LOGGER, name=name)
        self.address = address
        self._client: BleakClient | None = None
        self._callbacks: list[CoordinatorCallback] = []
        self._subscribed_chars: list[str] = []
        self._reconnect_task: asyncio.Task | None = None

    async def connect(self, requires_pairing: bool = False) -> bool:
        device = await BleakScanner.find_device_by_address(self.address)
        if not device:
            _LOGGER.error("Device not found! (%s:%s)", self.name, self.address)
            return False

        try:
            self._client = await establish_connection(
                client_class=BleakClient,
                device=device,
                name=self.name,
                max_attempts=MAX_RECONNECT_ATTEMPTS,
                disconnected_callback=self._on_disconnected
            )
        except BleakNotFoundError:
            _LOGGER.error("Device not found! (%s:%s)", self.name, self.address)
            return False
        except BleakOutOfConnectionSlotsError:
            _LOGGER.error("No connection slots available - try disconnecting other devices!")
            return False
        except BleakConnectionError:
            _LOGGER.error("Connection failed! (%s:%s)", self.name, self.address)
            return False
        except Exception:
            return False

        if requires_pairing:
            await self._client.pair()

        self.last_update_success = True

        _LOGGER.info("Device connected (%s:%s)", self.name, self.address)

        return True

    async def disconnect(self):
        if self._client:
            await self._client.disconnect()

    async def subscribe_char(self, char: BleakGATTCharacteristic | str):
        try:
            await self._client.start_notify(char, self._on_notification)
            self._subscribed_chars.append(char.uuid)
            _LOGGER.debug("Subscribed to characteristic... Characteristic: %s. (%s:%s)", char, self.name, self.address)
        except Exception as e:
            _LOGGER.error("Failed to subscribe to %s: %s", char, e)

    async def unsubscribe_char(self, char: BleakGATTCharacteristic | str):
        try:
            await self._client.stop_notify(char)
            self._subscribed_chars.remove(char.uuid)
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
            callback(CoordinatorCallbackType.NOTIFICATION, sender.uuid, data)

    def _on_disconnected(self, client: BleakClient):
        for callback in self._callbacks:
            callback(CoordinatorCallbackType.DISCONNECT, None, None)

        _LOGGER.info("Device disconnected (%s:%s)", self.name, self.address)

        if self._reconnect_task is None or self._reconnect_task.done():
            self._reconnect_task = self.hass.async_create_task(self._reconnect_loop())


    async def _resubscribe_all(self):
        for uuid in self._subscribed_chars:
            try:
                await self._client.start_notify(uuid, self._on_notification)
                self._subscribed_chars.append(uuid)
                _LOGGER.debug("Resubscribed to characteristic... Characteristic: %s. (%s:%s)", uuid, self.name, self.address)
            except Exception as e:
                _LOGGER.error("Failed to resubscribe to %s: %s", uuid, e)

    async def _reconnect_loop(self):
        while True:
            await asyncio.sleep(RECONNECT_ATTEMPT_DELAY_SECONDS)             # Delay before a reconnection attempt

            _LOGGER.debug("Scanning for device (%s:%s)...", self.name, self.address)
            device = await BleakScanner.find_device_by_address(self.address)
            if not device:
                _LOGGER.debug("Device not found in scan, retrying... (%s:%s)", self.name, self.address)
                continue

            try:
                self._client = await establish_connection(
                    client_class=BleakClient,
                    device=device,
                    name=self.name,
                    max_attempts=MAX_RECONNECT_ATTEMPTS,
                    disconnected_callback=self._on_disconnected
                )
            except Exception as e:
                _LOGGER.warning("Reconnect attempt failed (%s:%s): %s", self.name, self.address, e)
                continue

            await self._resubscribe_all()

            for callback in self._callbacks:
                callback(CoordinatorCallbackType.RECONNECT, None, None)

            return
