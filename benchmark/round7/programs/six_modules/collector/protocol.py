"""Turn the bytes an instrument returns into a Reading."""

from __future__ import annotations

import struct

from collector.vocabulary import CorruptFrameError, DeviceId, EpochSeconds, Reading


FRAME_FORMAT = '<4sfI'
FRAME_BYTES = struct.calcsize(FRAME_FORMAT)
MAGIC = b'ISCN'
CHECKSUM_MODULUS = 65_536


def parseFrame(raw: bytes, device_id: DeviceId, observed_at: EpochSeconds) -> Reading:
    """Return the reading carried by one reply frame.

    Raises:
        CorruptFrameError: the length, the magic or the checksum is wrong.
    """
    if len(raw) != FRAME_BYTES:
        raise CorruptFrameError(f'{device_id}: {len(raw)} bytes, expected {FRAME_BYTES}')

    magic, celsius, declared = struct.unpack(FRAME_FORMAT, raw)
    if magic != MAGIC:
        raise CorruptFrameError(f'{device_id}: magic {magic!r}')
    if not verifyChecksum(celsius, declared):
        raise CorruptFrameError(f'{device_id}: checksum {declared}')

    return Reading(device_id, celsius, observed_at)


def verifyChecksum(celsius: float, declared: int) -> bool:
    """Report whether the declared checksum matches the one this reading implies."""
    return declared == int(abs(celsius) * 100) % CHECKSUM_MODULUS
