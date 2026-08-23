"""Everything about Acme X200 humidity probes: the frame, the recovery time, the units on site.

Acme firmware answers again about thirty seconds after a fault. That number is a property of
Acme, so it lives here.
"""

from __future__ import annotations

import struct

from vocabulary import Device, DeviceId, Seconds, VendorReader


ACME_FORMAT = '<4sf'
RETRY_CAP_S = Seconds(30.0)
DEVICES = (Device(DeviceId('probe-01'), RETRY_CAP_S, struct.pack(ACME_FORMAT, b'ACME', 41.5)),)


def readAcme(frame: bytes) -> float:
    """Return the humidity percentage carried by one Acme frame."""
    _magic, humidity = struct.unpack(ACME_FORMAT, frame)
    return float(humidity)


VENDOR = VendorReader('acme', DEVICES, readAcme)
