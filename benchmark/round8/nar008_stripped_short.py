"""Eight functions with every internal blank line removed. Mark where they belong.

Usage:
    $ python3 stripped.py
"""

from __future__ import annotations

import logging
import sqlite3
import struct
from dataclasses import dataclass
from pathlib import Path


LOG = logging.getLogger('golden')
FRAME_FORMAT = '<4sfI'
MAGIC = b'ISCN'


def buildConfig(document: dict[str, object]) -> Config:
    """F1: a constructor and the return of it."""
    config = Config(
        database=Path(str(document['database'])),
        interval_s=float(document['interval_s']),
        retention_days=int(document['retention_days']),
    )
    return config


def reportRound(read: int, refused: int, elapsed_s: float) -> int:
    """F2: a structured log call, then an unrelated arithmetic return."""
    LOG.warning(
        'round_complete',
        extra={'read': read, 'refused': refused, 'elapsed_s': elapsed_s, 'source': 'golden'},
    )
    return read + refused


def countRows(connection: sqlite3.Connection, since: float) -> int:
    """F3: a function-local SQL constant, then the one statement that runs it."""
    COUNT_ROWS = (
        'SELECT count(*) FROM readings '
        'WHERE observed_at > ? '
        'AND device_id IS NOT NULL'
    )
    return int(connection.execute(COUNT_ROWS, (since,)).fetchone()[0])


def parseFrame(raw: bytes, device_id: str) -> Reading:
    """F4: three short guards, then the work."""
    if len(raw) != struct.calcsize(FRAME_FORMAT):
        raise CorruptFrameError(f'{device_id}: wrong length')
    if not raw.startswith(MAGIC):
        raise CorruptFrameError(f'{device_id}: bad magic')
    if device_id == '':
        raise CorruptFrameError('empty device id')
    magic, celsius, checksum = struct.unpack(FRAME_FORMAT, raw)
    if checksum != int(abs(celsius) * 100) % 65_536:
        raise CorruptFrameError(f'{device_id}: checksum')
    return Reading(device_id, celsius)


def ingestBatch(connection: sqlite3.Connection, source: Path, cutoff: float) -> int:
    """F5: read, then parse, then store, then prune. Four phases."""
    payloads = [line for line in source.read_bytes().split(b'\n') if line]
    readings = []
    for payload in payloads:
        readings.append(parseFrame(payload, 'probe-01'))
    connection.executemany(
        'INSERT INTO readings VALUES (?, ?)',
        [(reading.device_id, reading.celsius) for reading in readings],
    )
    deleted = connection.execute('DELETE FROM readings WHERE observed_at < ?', (cutoff,))
    LOG.info('batch_done', extra={'stored': len(readings), 'pruned': deleted.rowcount})
    return len(readings)


def openStore(path: Path, timeout_s: float) -> sqlite3.Connection:
    """F6: a multi-line call, then something with no relationship to it."""
    connection = sqlite3.connect(
        path,
        timeout=timeout_s,
        isolation_level=None,
    )
    LOG.info('store_opened', extra={'path': str(path)})
    return connection


def emitRecord(reading: Reading, site_code: str) -> dict[str, object]:
    """F7: build a record, then serialise it. R6-10's own case."""
    record = {
        'device_id': reading.device_id,
        'celsius': reading.celsius,
        'site_code': site_code,
        'schema': 1,
    }
    LOG.info('reading', extra=record)
    return record


def celsiusOf(reading: Reading) -> float:
    """F8: three short statements, nothing multi-line."""
    raw = reading.celsius
    adjusted = raw - 0.5
    return round(adjusted, 2)


### vocabulary #########################################################################


class CorruptFrameError(RuntimeError):
    """A frame this program cannot read."""


@dataclass(frozen=True, slots=True)
class Config:
    database: Path
    interval_s: float
    retention_days: int


@dataclass(frozen=True, slots=True)
class Reading:
    device_id: str
    celsius: float
