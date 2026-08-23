"""Compute the delay before the next retry.

This module names no vendor. The cap arrives as a value, because how long a fault lasts is a
property of the manufacturer's networking stack and not of the backoff policy.
"""

from __future__ import annotations

from vocabulary import Seconds


BASE_S = 1.0


def nextDelay(attempt: int, cap: Seconds) -> Seconds:
    """Return the delay before retry `attempt`, capped at `cap`."""
    return Seconds(min(BASE_S * 2**attempt, cap))
