"""Read a frame from a Tesla T9 thermocouple."""

from __future__ import annotations

import struct


VENDOR = 'tesla'
TESLA_FORMAT = '<4sf'


def readTesla(frame: bytes) -> float:
    """Return the temperature in Celsius carried by one Tesla frame."""
    _magic, celsius = struct.unpack(TESLA_FORMAT, frame)
    return float(celsius)
