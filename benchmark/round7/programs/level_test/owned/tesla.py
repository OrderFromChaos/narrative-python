"""Everything about Tesla T9 thermocouples: the frame, the recovery time, the units on site.

Tesla firmware reboots after a fault and needs about two minutes. That number is a property of
Tesla, so it lives here.
"""

from __future__ import annotations

import struct

from vocabulary import Device, DeviceId, Seconds, VendorReader


TESLA_FORMAT = '<4sf'
RETRY_CAP_S = Seconds(120.0)
DEVICES = (Device(DeviceId('probe-02'), RETRY_CAP_S, struct.pack(TESLA_FORMAT, b'TSLA', 21.25)),)


def readTesla(frame: bytes) -> float:
    """Return the temperature in Celsius carried by one Tesla frame."""
    _magic, celsius = struct.unpack(TESLA_FORMAT, frame)
    return float(celsius)


VENDOR = VendorReader('tesla', DEVICES, readTesla)
