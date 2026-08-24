"""Change a size between its text form and a count of bytes.

A size text holds a number and an optional unit suffix. Each unit step is 1024 times the step below
it. A number with no suffix is a count of bytes. The number can hold a decimal point, and the
conversion cuts the result toward zero.

    parseSizeText('4096')  ->  4096
    parseSizeText('1.5G')  ->  1610612736
    formatByteCount(1610612736)  ->  '1.5G'
    formatByteCount(4096)  ->  '4.0K'
"""

from __future__ import annotations

import logging

from quota_reconcile.vocabulary import Bytes, SizeTextError


BYTES_PER_STEP = 1024
UNIT_SUFFIXES = 'KMGTP'

LOG = logging.getLogger(__name__)


def parseSizeText(size_text: str) -> Bytes:
    """Read a size text as a count of bytes.

    Raises:
        SizeTextError: the text is empty, it does not hold a number, or the number is below zero.
    """
    stripped = size_text.strip()
    if not stripped:
        raise rejectSizeText(size_text, 'the size is empty')

    # `find` gives -1 for a text that ends with a digit, so a bare number takes 0 steps
    steps = UNIT_SUFFIXES.find(stripped[-1].upper()) + 1
    number_text = stripped[:-1] if steps > 0 else stripped
    try:
        number = float(number_text)
    except ValueError as exc:
        raise rejectSizeText(size_text, 'the size does not hold a number') from exc

    if number < 0:
        raise rejectSizeText(size_text, 'the size is below zero')
    return Bytes(int(number * BYTES_PER_STEP**steps))


def formatByteCount(count: Bytes) -> str:
    """Write a count of bytes as a size text with one decimal place.

    Returns:
        A bare number of bytes below 1024, and a number with a unit suffix above it.
    """
    scaled = float(count)
    steps = 0
    while scaled >= BYTES_PER_STEP and steps < len(UNIT_SUFFIXES):
        scaled /= BYTES_PER_STEP
        steps += 1

    if steps == 0:
        return str(count)
    return f'{scaled:.1f}{UNIT_SUFFIXES[steps - 1]}'


def rejectSizeText(size_text: str, reason: str) -> SizeTextError:
    LOG.debug('size.rejected', extra={'size_text': size_text, 'reason': reason})
    return SizeTextError(f'{size_text!r}: {reason}')
