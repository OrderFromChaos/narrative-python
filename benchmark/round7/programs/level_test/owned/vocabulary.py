"""Types shared by every module in this example.

A vendor module publishes one VendorReader. Nothing else needs to know how it reads a frame or
what its firmware does after a fault.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import NewType, Protocol


DeviceId = NewType('DeviceId', str)
Seconds = NewType('Seconds', float)


class FrameReader(Protocol):
    def __call__(self, frame: bytes) -> float: ...


@dataclass(frozen=True, slots=True)
class Device:
    device_id: DeviceId
    retry_cap_s: Seconds
    frame: bytes


@dataclass(frozen=True, slots=True)
class VendorReader:
    name: str
    devices: tuple[Device, ...]
    read_frame: FrameReader
