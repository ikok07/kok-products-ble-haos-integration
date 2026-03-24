from homeassistant.components.bluetooth import BluetoothServiceInfoBleak, async_discovered_service_info
from homeassistant import config_entries
from homeassistant.helpers.selector import TextSelector, TextSelectorConfig, SelectSelector, SelectSelectorConfig, \
    SelectSelectorMode

from .const import DOMAIN
import voluptuous as vol

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    discovery_info: BluetoothServiceInfoBleak

    async def async_step_user(self, user_input = None):
        errors = {}

        discovered = async_discovered_service_info(self.hass, connectable=True)
        configured_addresses = [entry["address"] for entry in self._async_current_entries()]

        available_devices = [device for device in discovered if device.address not in configured_addresses]
        if not available_devices:
            return self.async_abort(reason="no_devices_found")

        user_input_schema = vol.Schema({
            vol.Required("device"): SelectSelector(
                SelectSelectorConfig(
                    options=[
                        {"value": device.address, "label": device.name} for device in available_devices
                    ],
                    mode=SelectSelectorMode.DROPDOWN
                )
            )
        })

        if user_input is not None:
            try:
                validated = user_input_schema(user_input)
                self.discovery_info = next(device for device in available_devices if device.address == validated["device"])
                return await self.async_step_device_confirm()
            except vol.Invalid as e:
                errors["device"] = str(e.msg)

        return self.async_show_form(
            step_id="user",
            data_schema=user_input_schema,
            errors=errors
        )

    async def async_step_bluetooth(self, info: BluetoothServiceInfoBleak):
        await self.async_set_unique_id(info.address)                # Set device's MAC address
        self._abort_if_unique_id_configured()

        self.discovery_info = info
        return await self.async_step_device_confirm()

    async def async_step_device_confirm(self, user_input=None):
        errors = {}
        user_input_schema = vol.Schema({
            vol.Required("device_name", default=self.discovery_info.name): TextSelector(
                TextSelectorConfig(type="text")
            )
        })

        if user_input is not None:
            try:
                validated = user_input_schema(user_input)
                return self.async_create_entry(
                    title=self.discovery_info.name,
                    data={
                        "name": validated["device_name"],
                        "address": self.discovery_info.address
                    }
                )
            except vol.Invalid as e:
                errors["device_name"] = str(e.msg)

        return self.async_show_form(
            step_id="device_confirm",
            data_schema=user_input_schema,
            description_placeholders={
                "device_name": self.discovery_info.name,
                "device_address": self.discovery_info.address
            },
            errors=errors
        )