"""Poll instruments over TCP and write readings to SQLite.

Read this file first. It is the thesis: main() names the whole workflow in the order it runs, and
each module below it holds one part.

    __main__.py   this file -- start here
    service.py    the poll loop that runs for the life of the process
    poller.py     one round, and one device inside it
    protocol.py   the bytes an instrument returns
    store.py      SQLite
    vocabulary.py every type the modules above pass between them

Usage:
    $ python3 -m collector
"""

from __future__ import annotations

import struct
import sys

from collector.protocol import FRAME_FORMAT, MAGIC
from collector.service import pollForever
from collector.store import openDatabase
from collector.vocabulary import DeviceEntry, DeviceId


DATABASE_PATH = ':memory:'
ROUNDS = 3
EXIT_SUCCESS = 0
EXIT_FAILURE = 1

DEVICES = (
    DeviceEntry(DeviceId('probe-01'), 'LAB-A'),
    DeviceEntry(DeviceId('probe-02'), 'LAB-A'),
    DeviceEntry(DeviceId('probe-03'), 'LAB-B'),
)


def framedReply(celsius: float) -> bytes:
    """Return the bytes a healthy instrument would send for this reading."""
    return struct.pack(FRAME_FORMAT, MAGIC, celsius, int(abs(celsius) * 100) % 65_536)


def main() -> int:
    """Poll every device for a few rounds and print what each round saw."""
    replies = {
        'probe-01': framedReply(21.5),
        'probe-02': framedReply(19.25),
        'probe-03': b'GARBAGE!' + bytes(4),
    }

    with openDatabase(DATABASE_PATH) as connection:
        reports = pollForever(connection, DEVICES, replies, ROUNDS)

    for number, report in enumerate(reports):
        print(f'round {number}: {report.read} read, {report.refused} refused')

    return EXIT_FAILURE if reports[-1].refused else EXIT_SUCCESS


if __name__ == '__main__':
    sys.exit(main())
