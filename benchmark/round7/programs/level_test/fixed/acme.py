"""Read a frame from an Acme X200 humidity probe.

The retry cap lives here because the reason for it lives here: Acme firmware answers again
about thirty seconds after a fault.
"""

from __future__ import annotations

import struct

from vocabulary import Seconds


ACME_FORMAT = '<4sf'
RETRY_CAP_S = Seconds(30.0)


def readAcme(frame: bytes) -> float:
    """Return the humidity percentage carried by one Acme frame."""
    _magic, humidity = struct.unpack(ACME_FORMAT, frame)
    return float(humidity)
