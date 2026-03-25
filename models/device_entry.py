from enum import Enum

from pydantic import BaseModel

class DeviceType(Enum):
    SWITCH = 1

class DeviceEntryData(BaseModel):
    name: str
    address: str
    device_type: DeviceType | None
    requires_pairing: bool
