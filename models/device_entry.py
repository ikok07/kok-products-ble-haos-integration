from enum import Enum

from pydantic import BaseModel

class DeviceType(Enum):
    SWITCH = 1

class DeviceEntry(BaseModel):
    name: str
    address: str
    device_type: DeviceType | None