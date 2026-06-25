from __future__ import annotations

import platform
from dataclasses import dataclass


@dataclass(frozen=True)
class DeviceInfo:
    system: str
    machine: str
    release: str


def get_device_info() -> DeviceInfo:
    return DeviceInfo(
        system=platform.system(),
        machine=platform.machine(),
        release=platform.release(),
    )
