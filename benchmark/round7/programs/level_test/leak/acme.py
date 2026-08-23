"""Read a frame from an Acme X200 humidity probe."""

from __future__ import annotations

import struct


VENDOR = 'acme'
ACME_FORMAT = '<4sf'


def readAcme(frame: bytes) -> float:
    """Return the humidity percentage carried by one Acme frame."""
    _magic, humidity = struct.unpack(ACME_FORMAT, frame)
    return float(humidity)
