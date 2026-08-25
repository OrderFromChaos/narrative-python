"""Convert a size with a unit suffix to a count of bytes, and back.

    4096   ->          4096   ->  4.0K
    12K    ->         12288   ->  12.0K
    800M   ->     838860800   ->  800.0M
    1.5G   ->    1610612736   ->  1.5G
    2T     -> 2199023255552   ->  2.0T

A unit is a power of 1024. A number with no suffix is a count of bytes, and a count below 1024
converts back without a suffix.
"""

from __future__ import annotations

import re

from quota_reconcile.common import ByteCount, MalformedSizeError
from quota_reconcile.logs import LOG


_UNIT_SUFFIXES = 'KMGTP'
_UNIT_STEP = 1024
_NUMBER = re.compile(r'\d+(\.\d+)?')


def parseSize(size_text: str) -> ByteCount:
    text = size_text.strip()
    if not text:
        raise _rejectSize(size_text)

    # split the unit suffix off the number
    multiplier = 1
    number_text = text
    if text[-1].upper() in _UNIT_SUFFIXES:
        multiplier = _UNIT_STEP ** (_UNIT_SUFFIXES.index(text[-1].upper()) + 1)
        number_text = text[:-1]

    if not _NUMBER.fullmatch(number_text):
        raise _rejectSize(size_text)

    return ByteCount(int(float(number_text) * multiplier))


def formatSize(size: ByteCount) -> str:
    DECIMALS = 1
    if size < _UNIT_STEP:
        return str(size)

    scaled = float(size)
    for suffix in _UNIT_SUFFIXES:
        scaled /= _UNIT_STEP
        if scaled < _UNIT_STEP:
            return f'{scaled:.{DECIMALS}f}{suffix}'

    return f'{scaled:.{DECIMALS}f}{_UNIT_SUFFIXES[-1]}'


def _rejectSize(size_text: str) -> MalformedSizeError:
    LOG.debug('size.rejected', extra={'size': size_text})
    return MalformedSizeError(f'unusable size {size_text!r}')
