"""Hold readings in SQLite, and forget the ones that are too old."""

from __future__ import annotations

import sqlite3

from collector.vocabulary import DeviceId, EpochSeconds, Reading


SCHEMA = (
    'CREATE TABLE IF NOT EXISTS readings ('
    '  device_id TEXT NOT NULL,'
    '  celsius REAL NOT NULL,'
    '  observed_at REAL NOT NULL,'
    '  UNIQUE (device_id, observed_at))'
)


def openDatabase(path: str) -> sqlite3.Connection:
    """Return a connection with the readings table present."""
    connection = sqlite3.connect(path)
    connection.execute(SCHEMA)
    return connection


def insertReading(connection: sqlite3.Connection, reading: Reading) -> None:
    """Write one reading, ignoring a repeat of one already held."""
    connection.execute(
        'INSERT OR IGNORE INTO readings VALUES (?, ?, ?)',
        (reading.device_id, reading.celsius, reading.observed_at),
    )


def readingSeen(connection: sqlite3.Connection, device_id: DeviceId, observed_at: EpochSeconds) -> bool:
    """Report whether this device already has a reading at this instant."""
    row = connection.execute(
        'SELECT 1 FROM readings WHERE device_id = ? AND observed_at = ?',
        (device_id, observed_at),
    )

    return row.fetchone() is not None


def pruneOldReadings(connection: sqlite3.Connection, cutoff: EpochSeconds) -> int:
    """Delete every reading taken before the cutoff, and return how many went."""
    deleted = connection.execute('DELETE FROM readings WHERE observed_at < ?', (cutoff,))
    return deleted.rowcount
