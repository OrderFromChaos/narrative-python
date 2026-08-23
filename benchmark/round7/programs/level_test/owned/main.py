"""Print the reading and the retry schedule of every device.

This module knows which vendors exist. It knows nothing about any of them.

Usage:
    $ python3 main.py
"""

from __future__ import annotations

import sys

import acme
import tesla
from backoff import nextDelay


MAX_ATTEMPTS = 6
EXIT_SUCCESS = 0

VENDORS = (acme.VENDOR, tesla.VENDOR)


def main() -> int:
    """Print one line per device: its reading, then the delay before each retry."""
    for vendor in VENDORS:
        for device in vendor.devices:
            value = vendor.read_frame(device.frame)
            delays = [nextDelay(attempt, device.retry_cap_s) for attempt in range(MAX_ATTEMPTS)]
            print(f'{device.device_id} {value:7.2f}  ' + ' '.join(f'{delay:6.1f}' for delay in delays))

    return EXIT_SUCCESS


if __name__ == '__main__':
    sys.exit(main())
