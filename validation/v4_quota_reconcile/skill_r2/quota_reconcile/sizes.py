"""Convert a size with a unit suffix to a count of bytes, and back.

    4096   ->          4096            4096 -> 4.0K
    12K    ->         12288           12288 -> 12.0K
    1.5G   ->    1610612736      1610612736 -> 1.5G
    2T     -> 2199023255552   2199023255552 -> 2.0T

A unit is a power of 1024 and its letter is one of K, M, G, T. A number with no suffix is a count
of bytes, and a fractional count of bytes truncates.
"""

from __future__ import annotations

import logging
import re
from typing import NewType


BYTES_PER_UNIT = 1024
UNIT_LETTERS = ('K', 'M', 'G', 'T')
BYTE_LETTER = 'B'

LOG = logging.getLogger(__name__)


def parseSizeBytes(size_text: str) -> ByteCount:
    SIZE_PATTERN = r'(\d+(?:\.\d+)?)([KMGT]?)'

    match = re.fullmatch(SIZE_PATTERN, size_text.strip())
    if match is None:
        raise rejectSize(size_text)

    number, unit = match.groups()
    scale = BYTES_PER_UNIT ** (UNIT_LETTERS.index(unit) + 1) if unit else 1
    return ByteCount(int(float(number) * scale))


def formatSizeText(size_bytes: ByteCount) -> str:
    DECIMALS = 1

    scale = 1
    letter = BYTE_LETTER
    for candidate in UNIT_LETTERS:
        if size_bytes < scale * BYTES_PER_UNIT:
            break
        scale *= BYTES_PER_UNIT
        letter = candidate

    if letter == BYTE_LETTER:
        return f'{size_bytes}{BYTE_LETTER}'
    return f'{size_bytes / scale:.{DECIMALS}f}{letter}'


def rejectSize(size_text: str) -> MalformedSizeError:
    LOG.debug('size.malformed', extra={'size_text': size_text})
    return MalformedSizeError(f'not a size: {size_text!r}')


### vocabulary #########################################################################

ByteCount = NewType('ByteCount', int)


class MalformedSizeError(RuntimeError):
    """A size field does not read as a number with an optional unit letter."""
