"""Print the reading and the retry schedule of every device.

Usage:
    $ python3 main.py
"""

from __future__ import annotations

import struct
import sys

import acme
import tesla
from backoff import nextDelay
from vocabulary import Device, DeviceId


MAX_ATTEMPTS = 6
EXIT_SUCCESS = 0

DEVICES = (
    (Device(DeviceId('probe-01'), acme.RETRY_CAP_S, struct.pack('<4sf', b'ACME', 41.5)), acme.readAcme),
    (Device(DeviceId('probe-02'), tesla.RETRY_CAP_S, struct.pack('<4sf', b'TSLA', 21.25)), tesla.readTesla),
)


def main() -> int:
    """Print one line per device: its reading, then the delay before each retry."""
    for device, read_frame in DEVICES:
        value = read_frame(device.frame)
        delays = [nextDelay(attempt, device.retry_cap_s) for attempt in range(MAX_ATTEMPTS)]
        print(f'{device.device_id} {value:7.2f}  ' + ' '.join(f'{delay:6.1f}' for delay in delays))

    return EXIT_SUCCESS


if __name__ == '__main__':
    sys.exit(main())
