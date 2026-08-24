"""Byte sizes written as text.

Units are powers of 1024: `1K` is 1024 bytes, `1M` is 1024K, and so on. A bare number is a count
of bytes. A number can carry a decimal point, so `1.5G` is legal. The unit letter is not case
sensitive, and a trailing `B` or `iB` is accepted, so `1.5G`, `1.5GB` and `1.5GiB` are the same
size.
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from .errors import SizeFormatError

UNIT_LETTERS = ("B", "K", "M", "G", "T", "P", "E")
"""Unit letters in ascending order. The index of a letter is its power of 1024."""

_POWER_OF_LETTER = {letter: power for power, letter in enumerate(UNIT_LETTERS)}

_SIZE_PATTERN = re.compile(r"(?P<number>\d+(?:\.\d+)?)\s*(?P<unit>[A-Za-z]*)")


def parse_size(text: str) -> int:
    """Return the number of bytes that `text` names.

    Raise `SizeFormatError` if `text` is not a number followed by an optional unit. A negative
    number is not a size, so it is rejected as well.
    """
    candidate = text.strip()
    match = _SIZE_PATTERN.fullmatch(candidate)
    if match is None:
        raise SizeFormatError(f"cannot read {text!r} as a size")

    power = _power_of_unit(match["unit"], text)
    try:
        number = Decimal(match["number"])
    except InvalidOperation as exc:  # pragma: no cover - the pattern already rejects these
        raise SizeFormatError(f"cannot read {text!r} as a size") from exc

    byte_count = number * (1024**power)
    return int(byte_count.to_integral_value(rounding=ROUND_HALF_UP))


def format_size(byte_count: int) -> str:
    """Return a short human-readable form of `byte_count`, such as `1.5G`."""
    if byte_count < 1024:
        return f"{byte_count}B"

    value = float(byte_count)
    for letter in UNIT_LETTERS[1:]:
        value /= 1024.0
        if value < 1024.0:
            return f"{value:.1f}{letter}"
    return f"{value:.1f}{UNIT_LETTERS[-1]}"


def _power_of_unit(unit: str, original: str) -> int:
    """Return the power of 1024 that the unit suffix `unit` selects."""
    if not unit:
        return 0

    letter = unit[0].upper()
    tail = unit[1:].upper()
    if letter not in _POWER_OF_LETTER or tail not in ("", "B", "IB"):
        raise SizeFormatError(f"unknown size unit {unit!r} in {original!r}")
    if letter == "B" and tail:
        raise SizeFormatError(f"unknown size unit {unit!r} in {original!r}")
    return _POWER_OF_LETTER[letter]
