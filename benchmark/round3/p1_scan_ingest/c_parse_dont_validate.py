from __future__ import annotations

import json
import shutil
import sqlite3
import struct
import sys
from argparse import ArgumentParser
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import NewType


LOG_PATH = Path('jsonl_logs/scan_ingest.jsonl')
DEFAULT_DB_PATH = Path('scan_ingest.db')
SCAN_GLOB = '*.scan'
ARCHIVE_DIRECTORY_NAME = Path('archive')
QUARANTINE_DIRECTORY_NAME = Path('quarantine')
EXIT_SUCCESS = 0
EXIT_BATCH_HAD_FAILURES = 1
EXIT_BATCH_IMPOSSIBLE = 2


def main() -> int:
    """Run one batch and report the per-outcome counts on stdout.

    Each stage that can make the batch impossible is caught separately, so the log names the stage
    rather than a tuple of unrelated causes.

    Returns:
        0 when every file was ingested or was an already-seen duplicate, 1 when the batch finished
        with rejections or unreadable files, 2 when the config or the database stopped it starting.
    """
    parser = ArgumentParser()
    parser.add_argument('input_dir', type=Path)
    parser.add_argument('config_path', type=Path)
    parser.add_argument('--db', dest='db_path', type=Path, default=DEFAULT_DB_PATH)
    args = parser.parse_args()

    try:
        config = loadConfig(args.config_path)
    except ConfigError as exc:
        logEvent(LogLevel.ERROR, 'batch_abandoned', stage='load_config', error=str(exc))
        return EXIT_BATCH_IMPOSSIBLE

    try:
        connection = openDatabase(args.db_path)
    except DatabaseError as exc:
        logEvent(LogLevel.ERROR, 'batch_abandoned', stage='open_database', error=str(exc))
        return EXIT_BATCH_IMPOSSIBLE

    try:
        counts = ingestDirectory(connection, config, args.input_dir)
    except DatabaseError as exc:
        logEvent(LogLevel.ERROR, 'batch_abandoned', stage='ingest_directory', error=str(exc))
        return EXIT_BATCH_IMPOSSIBLE
    finally:
        connection.close()

    for outcome in sorted(counts, key=lambda item: item.value):
        print(f'{outcome.value}: {counts[outcome]}')

    return EXIT_BATCH_HAD_FAILURES if counts[Outcome.REJECTED] or counts[Outcome.ERROR] else EXIT_SUCCESS


def loadConfig(config_path: Path) -> dict[SampleRef, SampleEntry]:
    """Read the sample config into frozen entries, once, at the process boundary.

    Every way the file can be unusable is checked before use rather than caught after the fact, and
    each is a separate branch so the log says which one happened.

    Args:
        config_path: JSON file mapping a sample reference to its expected pixel_count and site_code.

    Returns:
        The parsed mapping. Nothing downstream re-checks it.

    Raises:
        ConfigError: The file is missing, unreadable, not JSON, not an object, or has an entry that
            omits pixel_count or site_code.
    """
    if not config_path.is_file():
        logEvent(LogLevel.ERROR, 'config_unusable', config_path=str(config_path), problem='missing')
        raise ConfigError(f'config file does not exist: {config_path}')

    try:
        text = config_path.read_text(encoding='utf-8')
    except OSError as exc:
        logEvent(LogLevel.ERROR, 'config_unusable', config_path=str(config_path), problem='unreadable')
        raise ConfigError(f'config file could not be read: {config_path}') from exc

    try:
        raw = json.loads(text)
    except json.JSONDecodeError as exc:
        logEvent(LogLevel.ERROR, 'config_unusable', config_path=str(config_path), problem='not_json')
        raise ConfigError(f'config file is not valid JSON: {config_path}') from exc

    if not isinstance(raw, dict):
        logEvent(LogLevel.ERROR, 'config_unusable', config_path=str(config_path), problem='not_an_object')
        raise ConfigError(f'config root must be a JSON object: {config_path}')

    config: dict[SampleRef, SampleEntry] = {}
    for reference, entry in raw.items():
        if not isinstance(entry, dict) or 'pixel_count' not in entry or 'site_code' not in entry:
            logEvent(LogLevel.ERROR, 'config_unusable', config_path=str(config_path), problem='incomplete_entry')
            raise ConfigError(f'config entry {reference} needs both pixel_count and site_code')

        config[SampleRef(str(reference))] = SampleEntry(
            expected_pixels=int(entry['pixel_count']),
            site_code=SiteCode(str(entry['site_code'])),
        )

    logEvent(LogLevel.INFO, 'config_loaded', config_path=str(config_path), sample_count=len(config))

    return config


def openDatabase(db_path: Path) -> sqlite3.Connection:
    """Open the scan database and put the schema in place.

    Args:
        db_path: SQLite file to open, created if it is not there yet.

    Returns:
        The open connection.

    Raises:
        DatabaseError: SQLite could not open the file or could not apply the schema.
    """
    SCHEMA_SQL = (
        'CREATE TABLE IF NOT EXISTS scans ('
        ' row_id INTEGER PRIMARY KEY,'
        ' scan_id INTEGER NOT NULL UNIQUE,'
        ' sample_ref TEXT NOT NULL,'
        ' site_code TEXT NOT NULL,'
        ' pixel_count INTEGER NOT NULL,'
        ' repetitions INTEGER NOT NULL,'
        ' source_filename TEXT NOT NULL,'
        ' ingested_at TEXT NOT NULL'
        ')'
    )

    try:
        connection = sqlite3.connect(db_path)
        connection.execute(SCHEMA_SQL)
        connection.commit()
    except sqlite3.Error as exc:
        logEvent(LogLevel.ERROR, 'database_open_failed', db_path=str(db_path), error=str(exc))
        raise DatabaseError(f'could not open the scan database at {db_path}') from exc

    return connection


def ingestDirectory(
    connection: sqlite3.Connection,
    config: Mapping[SampleRef, SampleEntry],
    input_dir: Path,
) -> Counter[Outcome]:
    """Process every scan file in one directory, keeping going past bad ones.

    The IO shell: it reads bytes, hands them to the pure core, and acts on whichever half of the
    result union comes back. Only genuinely unexpected conditions travel as exceptions.

    Args:
        connection: Open database, already carrying the schema.
        config: Expected geometry and site code per sample reference.
        input_dir: Directory holding the scan files, and parent of archive/ and quarantine/.

    Returns:
        How many files reached each outcome.

    Raises:
        DatabaseError: An insert failed, which means no later file can be trusted either.
    """
    archive_dir = input_dir / ARCHIVE_DIRECTORY_NAME
    quarantine_dir = input_dir / QUARANTINE_DIRECTORY_NAME
    counts: Counter[Outcome] = Counter()

    for scan_path in sorted(input_dir.glob(SCAN_GLOB)):
        if not scan_path.is_file():
            counts[Outcome.ERROR] += 1
            logEvent(LogLevel.ERROR, 'scan_io_error', source=scan_path.name, error='not a regular file')
            continue

        try:
            raw = scan_path.read_bytes()
        except OSError as exc:
            # Unreadable file: leave it in place so the next run retries rather than quarantining something good.
            # A moveInto failure below is uncaught by design -- an unwritable archive/ dooms the whole batch.
            counts[Outcome.ERROR] += 1
            logEvent(LogLevel.ERROR, 'scan_io_error', source=scan_path.name, error=str(exc))
            continue

        match parseScan(raw, config):
            case ValidScan() as scan:
                outcome = Outcome.INGESTED if insertScan(connection, scan, scan_path.name) else Outcome.DUPLICATE
                fields: dict[str, object] = {'scan_id': int(scan.scan_id)}
            case RejectedScan() as rejection:
                outcome = Outcome.REJECTED
                # The pure core cannot log, so the shell records the bare fact the moment the rejection crosses
                # the boundary; the scan_processed record below says what it meant for this file.
                logEvent(LogLevel.WARNING, 'scan_rejected', reason=rejection.reason.value, detail=rejection.detail)
                fields = {
                    'reason': rejection.reason.value,
                    'detail': rejection.detail,
                    'reason_text': describeRejection(rejection.reason),
                }

        moved_to = moveInto(scan_path, quarantine_dir if outcome is Outcome.REJECTED else archive_dir)
        counts[outcome] += 1
        logEvent(
            severityFor(outcome),
            'scan_processed',
            source=scan_path.name,
            outcome=outcome.value,
            moved_to=str(moved_to),
            **fields,
        )

    summary = {outcome.value: count for outcome, count in counts.items()}
    logEvent(LogLevel.INFO, 'batch_complete', input_dir=str(input_dir), counts=summary)

    return counts


def parseScan(raw: bytes, config: Mapping[SampleRef, SampleEntry]) -> ScanResult:
    """Turn the bytes of one scan file into a ValidScan or a RejectedScan.

    Pure and total: every failure the format allows is a value, so no caller needs a try. The
    length guard is what makes the unpack below safe.

    Args:
        raw: The whole file -- fixed header followed by the payload.
        config: Expected geometry and site code per sample reference.

    Returns:
        A ValidScan carrying exactly the fields the database row needs, or a RejectedScan naming the
        rule that failed and the observed value.
    """
    HEADER_FORMAT = '<4sHI12sIHI'
    HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
    MAGIC = b'ISCN'
    SUPPORTED_VERSIONS = frozenset({1, 2})
    SAMPLE_REF_PADDING = b'\x00'
    CHECKSUM_MASK = 0xFFFFFFFF

    if len(raw) < HEADER_SIZE:
        return RejectedScan(RejectionReason.TRUNCATED_HEADER, f'{len(raw)} bytes, need {HEADER_SIZE}')

    magic, version, scan_id, sample_bytes, pixel_count, repetitions, checksum = struct.unpack(
        HEADER_FORMAT,
        raw[:HEADER_SIZE],
    )

    if magic != MAGIC:
        return RejectedScan(RejectionReason.BAD_MAGIC, repr(magic))
    if version not in SUPPORTED_VERSIONS:
        return RejectedScan(RejectionReason.UNSUPPORTED_VERSION, str(version))

    trimmed = sample_bytes.rstrip(SAMPLE_REF_PADDING)
    # Checked rather than decoded-and-caught: the caller of a total function should not have to know
    # that UnicodeDecodeError was ever a possibility.
    if not trimmed.isascii():
        return RejectedScan(RejectionReason.BAD_SAMPLE_REF, repr(sample_bytes))

    sample_ref = SampleRef(trimmed.decode('ascii'))
    entry = config.get(sample_ref)
    if entry is None:
        return RejectedScan(RejectionReason.UNKNOWN_SAMPLE, sample_ref)
    if pixel_count != entry.expected_pixels:
        return RejectedScan(
            RejectionReason.PIXEL_COUNT_MISMATCH,
            f'header {pixel_count}, config {entry.expected_pixels}',
        )

    computed = sum(raw[HEADER_SIZE:]) & CHECKSUM_MASK
    if computed != checksum:
        return RejectedScan(RejectionReason.CHECKSUM_MISMATCH, f'header {checksum}, payload {computed}')

    return ValidScan(
        scan_id=ScanId(scan_id),
        sample_ref=sample_ref,
        site_code=entry.site_code,
        pixel_count=pixel_count,
        repetitions=repetitions,
    )


def insertScan(connection: sqlite3.Connection, scan: ValidScan, source_filename: str) -> bool:
    """Write one row, returning whether it was new.

    Args:
        connection: Open database, already carrying the schema.
        scan: The parsed scan, which by its type already satisfies every rule.
        source_filename: Name of the file the row came from, stored for provenance.

    Returns:
        True when the row was inserted, False when scan_id was already present.

    Raises:
        DatabaseError: SQLite refused the insert or the commit.
    """
    INSERT_SQL = (
        'INSERT INTO scans'
        ' (scan_id, sample_ref, site_code, pixel_count, repetitions, source_filename, ingested_at)'
        ' VALUES (?, ?, ?, ?, ?, ?, ?)'
        ' ON CONFLICT (scan_id) DO NOTHING'
    )

    row = (
        int(scan.scan_id),
        str(scan.sample_ref),
        str(scan.site_code),
        scan.pixel_count,
        scan.repetitions,
        source_filename,
        datetime.now(timezone.utc).isoformat(),
    )

    try:
        cursor = connection.execute(INSERT_SQL, row)
        # Commit per file: the row and the move to archive/ have to agree even if the next file kills the process.
        connection.commit()
    except sqlite3.Error as exc:
        logEvent(LogLevel.ERROR, 'scan_insert_failed', source=source_filename, error=str(exc))
        raise DatabaseError(f'could not insert the row for {source_filename}') from exc

    return cursor.rowcount == 1


def logEvent(level: LogLevel, event: str, **fields: object) -> None:
    record: dict[str, object] = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'level': level.value,
        'event': event,
    }

    record.update(fields)
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Reopened per record: a batch killed mid-run still leaves a complete, parseable log behind.
    with LOG_PATH.open('a', encoding='utf-8') as handle:
        handle.write(json.dumps(record) + '\n')


def describeRejection(reason: RejectionReason) -> str:
    # What the operator should do about it, which the reason code alone does not say.
    match reason:
        case RejectionReason.TRUNCATED_HEADER:
            return 'file is shorter than the fixed header'
        case RejectionReason.BAD_MAGIC:
            return 'not a scanner file'
        case RejectionReason.UNSUPPORTED_VERSION:
            return 'header version this build cannot read'
        case RejectionReason.BAD_SAMPLE_REF:
            return 'sample reference is not ASCII'
        case RejectionReason.UNKNOWN_SAMPLE:
            return 'sample reference is missing from the config'
        case RejectionReason.PIXEL_COUNT_MISMATCH:
            return 'geometry disagrees with the config, likely the wrong protocol on the console'
        case RejectionReason.CHECKSUM_MISMATCH:
            return 'payload corrupt or truncated in transfer'


def moveInto(source: Path, dest_dir: Path) -> Path:
    """Move one file into a directory and return where it landed.

    moveInto(Path('incoming/scan001.scan'), Path('incoming/archive')) creates incoming/archive/ if it
    is not there, moves the file to incoming/archive/scan001.scan and returns that path;
    incoming/scan001.scan is gone afterwards. When incoming/archive/scan001.scan already exists it is
    left untouched and a counter goes in before the suffix instead, giving
    incoming/archive/scan001.1.scan, then incoming/archive/scan001.2.scan, and so on.
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    target = dest_dir / source.name

    # The scanner reuses filenames between runs, so never clobber an already archived copy.
    attempt = 1
    while target.exists():
        target = dest_dir / f'{source.stem}.{attempt}{source.suffix}'
        attempt += 1

    shutil.move(source, target)

    return target


def severityFor(outcome: Outcome) -> LogLevel:
    # A rejection is a data problem someone has to look at; a duplicate is the idempotent path.
    match outcome:
        case Outcome.INGESTED | Outcome.DUPLICATE:
            return LogLevel.INFO
        case Outcome.REJECTED:
            return LogLevel.WARNING
        case Outcome.ERROR:
            return LogLevel.ERROR


### vocabulary #########################################################################################################

SampleRef = NewType('SampleRef', str)
ScanId = NewType('ScanId', int)
SiteCode = NewType('SiteCode', str)


class LogLevel(Enum):
    INFO = 'info'
    WARNING = 'warning'
    ERROR = 'error'


class Outcome(Enum):
    INGESTED = 'ingested'
    DUPLICATE = 'duplicate'
    REJECTED = 'rejected'
    ERROR = 'error'


class RejectionReason(Enum):
    TRUNCATED_HEADER = 'truncated_header'
    BAD_MAGIC = 'bad_magic'
    UNSUPPORTED_VERSION = 'unsupported_version'
    BAD_SAMPLE_REF = 'bad_sample_ref'
    UNKNOWN_SAMPLE = 'unknown_sample'
    PIXEL_COUNT_MISMATCH = 'pixel_count_mismatch'
    CHECKSUM_MISMATCH = 'checksum_mismatch'


class ConfigError(RuntimeError):
    """The sample config could not be turned into a usable mapping."""


class DatabaseError(RuntimeError):
    """SQLite refused an operation the batch cannot continue without."""


@dataclass(frozen=True)
class SampleEntry:
    expected_pixels: int
    site_code: SiteCode


@dataclass(frozen=True)
class ValidScan:
    scan_id: ScanId
    sample_ref: SampleRef
    site_code: SiteCode
    pixel_count: int
    repetitions: int


@dataclass(frozen=True)
class RejectedScan:
    reason: RejectionReason
    detail: str


# Everything downstream of parseScan takes one of these two and nothing else; there is no third state where a scan
# is half-checked, and no ValidScan can exist that failed a rule.
ScanResult = ValidScan | RejectedScan


if __name__ == '__main__':
    sys.exit(main())
