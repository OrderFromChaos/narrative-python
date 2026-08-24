"""Convert a size with a unit suffix to a count of bytes, and back.

A unit is a power of 1024. `1K` is 1024 bytes and `1M` is 1024K. A number with no suffix is a count
of bytes. A size can carry a decimal point, thus `1.5G` is 1610612736 bytes.
"""

from __future__ import annotations

import re

from quota_reconcile.logs import LOG
from quota_reconcile.vocabulary import ByteCount, MalformedSizeError


_UNIT_SUFFIXES = ('B', 'K', 'M', 'G', 'T', 'P')
_BYTES_PER_UNIT = 1024
_SIZE_PATTERN = re.compile(r'(\d+(?:\.\d+)?)([' + ''.join(_UNIT_SUFFIXES) + r']?)')
_DISPLAY_DIGITS = 1


def parseByteSize(size_text: str) -> ByteCount:
    matched = _SIZE_PATTERN.fullmatch(size_text.strip().upper())
    if matched is None:
        raise _rejectSize(size_text)

    number, suffix = matched.groups()
    exponent = _UNIT_SUFFIXES.index(suffix) if suffix else 0
    # A fractional count of bytes truncates, because a file holds a whole number of bytes.
    return ByteCount(int(float(number) * _BYTES_PER_UNIT**exponent))


def formatByteSize(size: ByteCount) -> str:
    scaled = float(size)
    exponent = 0
    while scaled >= _BYTES_PER_UNIT and exponent < len(_UNIT_SUFFIXES) - 1:
        scaled /= _BYTES_PER_UNIT
        exponent += 1
    return f'{scaled:.{_DISPLAY_DIGITS}f}{_UNIT_SUFFIXES[exponent]}'


def _rejectSize(size_text: str) -> MalformedSizeError:
    LOG.debug('size.rejected', extra={'size_text': size_text})
    return MalformedSizeError(f'{size_text!r} is not a size in bytes')
