"""Golden whitespace, as marked up by the author."""

from __future__ import annotations

import json
import logging
import sqlite3
import struct
from dataclasses import dataclass
from pathlib import Path


LOG = logging.getLogger('golden')
FRAME_FORMAT = '<4sfI'
MAGIC = b'ISCN'
CHECKSUM_MODULUS = 65_536
MAX_CELSIUS = 150.0


def runIngest(connection: sqlite3.Connection, source: Path, config: Config) -> RoundReport:
    """L1: four phases -- load, parse, store, report."""
    cutoff = config.retention_days * 86_400

    if not source.exists():
        raise SourceMissingError(f'{source} does not exist')

    raw_lines = [line for line in source.read_bytes().split(b'\n') if line]
    LOG.info('batch_loaded', extra={'source': str(source), 'lines': len(raw_lines)})

    # parse data
    readings = []
    refusals = []
    for number, payload in enumerate(raw_lines):
        try:
            readings.append(parseFrame(payload, f'probe-{number:02d}'))
        except CorruptFrameError as exc:
            refusals.append(str(exc))
            LOG.debug('frame_refused', extra={'line': number, 'error': str(exc)})

    # execute sql
    connection.executemany(
        'INSERT OR IGNORE INTO readings VALUES (?, ?)',
        [(reading.device_id, reading.celsius) for reading in readings],
    )
    connection.commit()
    deleted = connection.execute('DELETE FROM readings WHERE observed_at < ?', (cutoff,))

    LOG.warning(
        'batch_done',
        extra={'stored': len(readings), 'refused': len(refusals), 'pruned': deleted.rowcount},
    )
    report = RoundReport(len(readings), len(refusals), deleted.rowcount)
    return report


def parseFrame(raw: bytes, device_id: str) -> Reading:
    """L2: guards, decode, validate, build -- with the guards spread through."""
    if len(raw) != struct.calcsize(FRAME_FORMAT):
        raise CorruptFrameError(f'{device_id}: wrong length')
    if not raw.startswith(MAGIC):
        raise CorruptFrameError(f'{device_id}: bad magic')

    magic, celsius, checksum = struct.unpack(FRAME_FORMAT, raw)

    # validate
    expected = int(abs(celsius) * 100) % CHECKSUM_MODULUS
    if checksum != expected:
        raise CorruptFrameError(f'{device_id}: checksum {checksum} wanted {expected}')
    if abs(celsius) > MAX_CELSIUS:
        raise CorruptFrameError(f'{device_id}: {celsius} out of range')
    if device_id == '':
        raise CorruptFrameError('empty device id')

    reading = Reading(device_id, round(celsius, 2))
    return reading


def driftSlope(readings: list[Reading], window_s: float) -> float:
    """L3: one linear computation, no obvious phases."""
    if len(readings) < 2:
        return 0.0

    times = [float(index) for index in range(len(readings))]
    values = [reading.celsius for reading in readings]

    mean_time = sum(times) / len(times)
    mean_value = sum(values) / len(values)

    covariance = sum((t - mean_time) * (v - mean_value) for t, v in zip(times, values))
    variance = sum((t - mean_time) ** 2 for t in times)
    if variance == 0.0:
        return 0.0

    slope = covariance / variance
    scaled = slope * window_s
    return scaled


def summariseSites(connection: sqlite3.Connection, sites: list[str]) -> dict[str, object]:
    """L4: a loop whose body has its own phases."""
    total_readings = 0
    summary = {}
    for site in sites:
        rows = connection.execute(
            'SELECT device_id, celsius FROM readings WHERE site_code = ?',
            (site,),
        ).fetchall()

        if not rows:
            LOG.debug('site_empty', extra={'site': site})
            continue

        celsius_values = [row[1] for row in rows]
        hottest = max(celsius_values)
        coldest = min(celsius_values)
        mean = sum(celsius_values) / len(celsius_values)

        summary[site] = {'hottest': hottest, 'coldest': coldest, 'mean': round(mean, 2)}
        total_readings += len(rows)

        LOG.debug('site_summarised', extra={'site': site, 'readings': len(rows)})

    summary['total'] = total_readings

    payload = json.dumps(summary, sort_keys=True)
    LOG.info('sites_summarised', extra={'sites': len(sites), 'bytes': len(payload)})

    return summary

### vocabulary #########################################################################


class CorruptFrameError(RuntimeError):
    """A frame this program cannot read."""


class SourceMissingError(RuntimeError):
    """The batch file named on the command line is not there."""


@dataclass(frozen=True, slots=True)
class Config:
    retention_days: int


@dataclass(frozen=True, slots=True)
class Reading:
    device_id: str
    celsius: float


@dataclass(frozen=True, slots=True)
class RoundReport:
    stored: int
    refused: int
    pruned: int
