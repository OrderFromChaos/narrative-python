"""Print the reading and the retry schedule of every device.

Usage:
    $ python3 main.py
"""

from __future__ import annotations

import struct
import sys

from acme import readAcme
from backoff import nextDelay
from tesla import readTesla
from vocabulary import Device, DeviceId


MAX_ATTEMPTS = 6
EXIT_SUCCESS = 0

DEVICES = (
    Device(DeviceId('probe-01'), 'acme', struct.pack('<4sf', b'ACME', 41.5)),
    Device(DeviceId('probe-02'), 'tesla', struct.pack('<4sf', b'TSLA', 21.25)),
)

READERS = {'acme': readAcme, 'tesla': readTesla}


def main() -> int:
    """Print one line per device: its reading, then the delay before each retry."""
    for device in DEVICES:
        value = READERS[device.vendor](device.frame)
        delays = [nextDelay(device.vendor, attempt) for attempt in range(MAX_ATTEMPTS)]
        print(f'{device.device_id} {value:7.2f}  ' + ' '.join(f'{delay:6.1f}' for delay in delays))

    return EXIT_SUCCESS


if __name__ == '__main__':
    sys.exit(main())
