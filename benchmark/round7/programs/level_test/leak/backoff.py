"""Compute the delay before the next retry.

This module reads as generic infrastructure. It is not. VENDOR_CAPS_S names every vendor the
program supports, so a third vendor forces an edit here as well as in its own module.
"""

from __future__ import annotations

from vocabulary import Seconds


BASE_S = 1.0
VENDOR_CAPS_S = {'acme': 30.0, 'tesla': 120.0}


def nextDelay(vendor: str, attempt: int) -> Seconds:
    """Return the delay before retry `attempt`, capped at what this vendor's firmware needs."""
    return Seconds(min(BASE_S * 2**attempt, VENDOR_CAPS_S[vendor]))
