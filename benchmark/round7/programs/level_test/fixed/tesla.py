"""Read a frame from a Tesla T9 thermocouple.

The retry cap lives here because the reason for it lives here: Tesla firmware reboots after a
fault and needs about two minutes.
"""

from __future__ import annotations

import struct

from vocabulary import Seconds


TESLA_FORMAT = '<4sf'
RETRY_CAP_S = Seconds(120.0)


def readTesla(frame: bytes) -> float:
    """Return the temperature in Celsius carried by one Tesla frame."""
    _magic, celsius = struct.unpack(TESLA_FORMAT, frame)
    return float(celsius)
