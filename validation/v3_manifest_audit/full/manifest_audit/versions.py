"""Order two version strings against each other.

Only the leading number of each dotted part is compared, so `1.4.0` and `1.4.0rc1` are equal here.
A part that starts with no digit counts as 0. This is sufficient for a minimum-version floor and it
is not a full PEP 440 implementation.

    belowMinimum('2.28.1', '2.31.0')   -> True
    belowMinimum('2.31.0', '2.31.0')   -> False
    belowMinimum('2.31',   '2.31.0')   -> False
"""

from __future__ import annotations

import re

from manifest_audit.vocabulary import VersionText


def belowMinimum(version: VersionText, minimum: VersionText) -> bool:
    return _versionOrder(version) < _versionOrder(minimum)


def _versionOrder(version: VersionText) -> tuple[int, ...]:
    # A fixed width makes a short version comparable with a long one: without it `2.31` sorts below
    # `2.31.0`, because a shorter tuple loses on the first missing element.
    COMPARED_PARTS = 4
    LEADING_NUMBER = r'\d+'

    numbers = []
    for part in version.split('.')[:COMPARED_PARTS]:
        found = re.match(LEADING_NUMBER, part)
        numbers.append(int(found.group()) if found else 0)

    return tuple(numbers) + (0,) * (COMPARED_PARTS - len(numbers))
