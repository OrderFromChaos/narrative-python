"""Types shared by every module in this example.

A device carries its own retry cap. The vendor module that knows the firmware supplies it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import NewType


DeviceId = NewType('DeviceId', str)
Seconds = NewType('Seconds', float)


@dataclass(frozen=True, slots=True)
class Device:
    device_id: DeviceId
    retry_cap_s: Seconds
    frame: bytes
