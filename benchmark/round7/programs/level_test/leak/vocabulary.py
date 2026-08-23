"""Types shared by every module in this example.

A device carries the name of its vendor. What that vendor implies is held elsewhere.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import NewType


DeviceId = NewType('DeviceId', str)
Seconds = NewType('Seconds', float)


@dataclass(frozen=True, slots=True)
class Device:
    device_id: DeviceId
    vendor: str
    frame: bytes
