from pydantic import BaseModel

from .device_type import DeviceType

class DeviceEntryData(BaseModel):
    name: str
    address: str
    device_type: DeviceType | None
    requires_pairing: bool
