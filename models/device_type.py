from enum import Enum

class DeviceType(Enum):
    GENERIC_SWITCH = 0x50

DEVICE_TYPE_PLATFORMS_MAP: dict[DeviceType, list[str]] = {
    DeviceType.GENERIC_SWITCH: ["switch"]                                # Basic switch
}