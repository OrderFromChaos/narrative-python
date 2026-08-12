from __future__ import annotations

import argparse
import json
import logging
import sys
from collections import Counter, defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import NewType


LOG_GLOB = '*.jsonl'
DEFAULT_REPORT_PATH = Path('triage_report.json')
SLOWEST_COUNT = 5
ERROR_EXAMPLES = 3
EXIT_SUCCESS = 0
EXIT_FAILURE = 1

LOG = logging.getLogger('log_triage')


def main() -> int:
    """Summarise a directory of JSONL ingest logs as a table and a JSON file.

    Returns:
        EXIT_FAILURE if the directory is unusable, the time window or level is unreadable, the
        report cannot be written, or any line was malformed. EXIT_SUCCESS otherwise. A malformed
        line never stops the scan; it is counted and reported (Q24).
    """
    parser = argparse.ArgumentParser(description='Triage the JSONL logs written by the ingest pipeline.')
    parser.add_argument('log_dir', type=Path, help='directory holding the log files')
    parser.add_argument('--since', help='ISO 8601 start of the window, inclusive')
    parser.add_argument('--until', help='ISO 8601 end of the window, inclusive')
    parser.add_argument('--min-level', default=LogLevel.INFO.value, choices=[level.value for level in LogLevel])
    parser.add_argument('--json-out', type=Path, default=DEFAULT_REPORT_PATH, help='where to write the JSON report')
    parser.add_argument('--verbose', action='store_true', help='log every rejected line')
    args = parser.parse_args()

    configureLogging(args.verbose)
    if not args.log_dir.is_dir():
        LOG.error('log_dir_unusable', extra={'directory': str(args.log_dir)})
        return EXIT_FAILURE

    try:
        selection = selectionFrom(args.since, args.until, args.min_level)
    except TriageError as exc:
        LOG.error('selection_unusable', extra={'reason': str(exc)})
        return EXIT_FAILURE

    paths = sorted(args.log_dir.glob(LOG_GLOB))
    if not paths:
        LOG.error('no_log_files', extra={'directory': str(args.log_dir), 'glob': LOG_GLOB})
        return EXIT_FAILURE

    report = buildReport(scanLogs(paths, selection))
    print(renderReport(report))

    try:
        writeReport(report, args.json_out)
    except TriageError as exc:
        LOG.error('report_not_written', extra={'target': str(args.json_out), 'reason': str(exc)})
        return EXIT_FAILURE

    return EXIT_FAILURE if report.scan.malformed else EXIT_SUCCESS


def configureLogging(verbose: bool) -> None:
    global LOG  # attaching a handler mutates the shared logger: a side effect on module state
    # Logs go to stderr as JSONL so that the report on stdout stays pipeable (Q08).
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(JsonlFormatter())
    LOG.addHandler(handler)
    LOG.setLevel(logging.DEBUG if verbose else logging.INFO)


def selectionFrom(since: str | None, until: str | None, min_level: str) -> Selection:
    # The one gate where the raw CLI strings become the frozen object every later stage consults.
    start = parseTimestamp(since) if since else None
    end = parseTimestamp(until) if until else None
    level = levelFrom(min_level)

    if level is None:
        LOG.debug('selection_rejected', extra={'reason': 'unknown level', 'value': min_level})
        raise TriageError(f'unknown minimum level: {min_level}')

    if start is not None and end is not None and start > end:
        LOG.debug('selection_rejected', extra={'reason': 'inverted window'})
        raise TriageError(f'--since {start.isoformat()} is after --until {end.isoformat()}')

    return Selection(start, end, level)


def parseTimestamp(text: str) -> datetime:
    # `datetime.fromisoformat` only learned the trailing 'Z' in 3.11, and this targets the 3.10
    # floor, so rewrite it: '2024-05-01T00:00:00Z' -> '2024-05-01T00:00:00+00:00'.
    normalised = f'{text[:-1]}+00:00' if text.endswith('Z') else text
    try:
        parsed = datetime.fromisoformat(normalised)
    except ValueError as exc:
        LOG.debug('timestamp_rejected', extra={'value': text})
        raise TriageError(f'not an ISO 8601 timestamp: {text}') from exc

    # A timestamp with no offset is read as UTC, so every comparison in `selected` is aware-to-aware.
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)


def levelFrom(text: str) -> LogLevel | None:
    # LBYL (Q22): returning None beats `LogLevel(text)` raising ValueError, because both callers
    # want to report the bad value rather than catch.
    wanted = text.strip().upper()
    return next((level for level in LogLevel if level.value == wanted), None)


def scanLogs(paths: Iterable[Path], selection: Selection) -> ScanResult:
    """Read every line of every file and keep the records the selection admits.

    An unreadable file and an unparseable line are both recorded and skipped, so one bad input
    never costs the rest of the batch (Q24). Blank lines are ignored and not counted.

    Args:
        paths: The log files to read, in the order they should be scanned.
        selection: The time window and minimum level to keep.

    Returns:
        The kept records in file order, the number of non-blank lines read, and one entry per
        line or file that was rejected.
    """
    records: list[LogEntry] = []
    malformed: list[MalformedLine] = []
    scanned = 0

    for path in paths:
        try:
            lines = path.read_text(encoding='utf-8').splitlines()
        except OSError as exc:
            LOG.error('log_file_unreadable', extra={'source': str(path), 'reason': str(exc)})
            malformed.append(MalformedLine(path, 0, f'unreadable: {exc}'))
            continue
        except UnicodeDecodeError as exc:
            LOG.error('log_file_not_utf8', extra={'source': str(path), 'reason': exc.reason})
            malformed.append(MalformedLine(path, 0, f'not UTF-8: {exc.reason}'))
            continue

        for line_number, line in enumerate(lines, start=1):
            if not line.strip():
                continue

            scanned += 1
            try:
                entry = parseRecord(line, path, line_number)
            except MalformedLineError as exc:
                LOG.warning('line_skipped', extra={'source': str(path), 'line': line_number, 'reason': str(exc)})
                malformed.append(MalformedLine(path, line_number, str(exc)))
                continue

            if selected(entry, selection):
                records.append(entry)

    return ScanResult(tuple(records), scanned, tuple(malformed))


def parseRecord(line: str, source: Path, line_number: int) -> LogEntry:
    """Parse one JSONL line into a frozen record. This is the only validation gate (Q14).

    Args:
        line: One raw line of a log file, without its newline.
        source: The file it came from.
        line_number: Its 1-based position in that file.

    Returns:
        The parsed record. Fields beyond the four known ones are kept as one compact JSON string,
        e.g. `{"batch": 7, "shard": "a"}`; an empty string means there were none.

    Raises:
        MalformedLineError: The line is not a JSON object, lacks a required field, or carries a
            timestamp, level or duration that cannot be read.
    """
    REQUIRED_FIELDS = frozenset({'timestamp', 'level', 'event'})
    KNOWN_FIELDS = REQUIRED_FIELDS | {'duration_ms'}

    try:
        payload = json.loads(line)
    except json.JSONDecodeError as exc:
        raise rejectLine(f'not valid JSON: {exc.msg}') from exc

    if not isinstance(payload, dict):
        raise rejectLine(f'top-level value is {type(payload).__name__}, not an object')

    missing = sorted(REQUIRED_FIELDS - payload.keys())
    if missing:
        raise rejectLine(f'missing field(s): {", ".join(missing)}')

    unusable = sorted(field for field in REQUIRED_FIELDS if not isinstance(payload[field], str))
    if unusable:
        raise rejectLine(f'field(s) not a string: {", ".join(unusable)}')

    level = levelFrom(payload['level'])
    if level is None:
        raise rejectLine(f'unknown level: {payload["level"]}')

    duration = payload.get('duration_ms')
    if duration is not None and not isinstance(duration, (int, float)):
        raise rejectLine(f'duration_ms is {type(duration).__name__}, not a number')

    try:
        timestamp = parseTimestamp(payload['timestamp'])
    except TriageError as exc:
        raise rejectLine(str(exc)) from exc

    extra = {key: value for key, value in payload.items() if key not in KNOWN_FIELDS}
    return LogEntry(
        timestamp=timestamp,
        level=level,
        event=EventName(payload['event']),
        duration=None if duration is None else Milliseconds(float(duration)),
        detail=json.dumps(extra, sort_keys=True) if extra else '',
        source=source,
        line=line_number,
    )


def rejectLine(reason: str) -> MalformedLineError:
    # One place logs the generic fact for every raise site in `parseRecord`; the handler in
    # `scanLogs` logs what it meant there, which is that the line was dropped (Q23).
    LOG.debug('line_rejected', extra={'reason': reason})
    return MalformedLineError(reason)


def selected(entry: LogEntry, selection: Selection) -> bool:
    # Both bounds are inclusive. A record with no `duration_ms` is unaffected by either.
    if severityFor(entry.level) < severityFor(selection.min_level):
        return False
    if selection.since is not None and entry.timestamp < selection.since:
        return False
    return selection.until is None or entry.timestamp <= selection.until


def severityFor(level: LogLevel) -> int:
    match level:
        case LogLevel.DEBUG:
            return logging.DEBUG
        case LogLevel.INFO:
            return logging.INFO
        case LogLevel.WARNING:
            return logging.WARNING
        case LogLevel.ERROR:
            return logging.ERROR
        case LogLevel.CRITICAL:
            return logging.CRITICAL
        # No `case _`: a new member then fails mypy with "Missing return statement" (Q18).


def buildReport(scan: ScanResult) -> Report:
    """Reduce the kept records to the three tables the report is made of.

    Every ordering is deterministic — counts and error groups by descending count then event name,
    slowest by descending duration — so two runs over the same logs diff cleanly.

    Args:
        scan: Everything the pass over the log files produced.

    Returns:
        The finished report, ready to render or serialise.
    """
    counts = Counter(entry.event for entry in scan.records)
    event_counts = tuple(
        EventCount(event, count) for event, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    )

    # Pairing the duration with its record keeps the sort key a plain float; sorting the records
    # themselves would need a key that mypy cannot prove is never None.
    timed = [(entry.duration, entry) for entry in scan.records if entry.duration is not None]
    slowest = tuple(entry for _, entry in sorted(timed, key=lambda pair: pair[0], reverse=True)[:SLOWEST_COUNT])

    by_event: defaultdict[EventName, list[LogEntry]] = defaultdict(list)
    for entry in scan.records:
        if entry.level is LogLevel.ERROR:
            by_event[entry.event].append(entry)

    error_groups = tuple(
        ErrorGroup(event, len(entries), tuple(entries[:ERROR_EXAMPLES]))
        for event, entries in sorted(by_event.items(), key=lambda item: (-len(item[1]), item[0]))
    )

    return Report(scan, event_counts, slowest, error_groups)


def renderReport(report: Report) -> str:
    """Lay the report out as three plain-text tables and a one-line summary.

    Args:
        report: The report to render.

    Returns:
        The whole terminal report as one string, with no trailing newline.
    """
    DETAIL_WIDTH = 56
    SLOW_HEADINGS = ('duration_ms', 'event', 'timestamp', 'source')
    ERROR_HEADINGS = ('event', 'errors', 'timestamp', 'detail')

    event_rows = [(item.event, str(item.count)) for item in report.event_counts]
    slow_rows = [
        (f'{entry.duration:.1f}', entry.event, entry.timestamp.isoformat(), f'{entry.source.name}:{entry.line}')
        for entry in report.slowest
    ]

    # The event and its total are printed once, against the first of its examples.
    error_rows: list[tuple[str, ...]] = []
    for group in report.error_groups:
        for position, example in enumerate(group.examples):
            heading = (group.event, str(group.count)) if position == 0 else ('', '')
            error_rows.append((*heading, example.timestamp.isoformat(), example.detail[:DETAIL_WIDTH]))

    kept = len(report.scan.records)
    malformed = len(report.scan.malformed)
    summary = f'{report.scan.scanned} lines scanned, {kept} kept, {malformed} malformed'
    tables = [
        renderTable('counts by event', ('event', 'count'), event_rows),
        renderTable(f'slowest {SLOWEST_COUNT} operations', SLOW_HEADINGS, slow_rows),
        renderTable(f'ERROR lines by event (first {ERROR_EXAMPLES})', ERROR_HEADINGS, error_rows),
        summary,
    ]

    return '\n\n'.join(tables)


def renderTable(title: str, headings: Sequence[str], rows: Sequence[tuple[str, ...]]) -> str:
    # Every column is as wide as its widest cell and nothing wraps, because a wrapped row cannot
    # be grepped out of a terminal scrollback.
    if not rows:
        return f'{title}\n  (none)'

    widths = [len(heading) for heading in headings]
    for row in rows:
        widths = [max(width, len(cell)) for width, cell in zip(widths, row, strict=True)]

    body = [title, '  '.join(heading.ljust(width) for heading, width in zip(headings, widths, strict=True)).rstrip()]
    body.append('  '.join('-' * width for width in widths))
    for row in rows:
        body.append('  '.join(cell.ljust(width) for cell, width in zip(row, widths, strict=True)).rstrip())
    return '\n'.join(body)


def writeReport(report: Report, path: Path) -> None:
    # The JSON file is the machine-readable twin of the tables: the same numbers, none of the layout.
    payload = reportAsJson(report)
    try:
        path.write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')
    except OSError as exc:
        LOG.error('report_write_failed', extra={'target': str(path), 'reason': str(exc)})
        raise TriageError(f'cannot write {path}: {exc}') from exc

    LOG.info('report_written', extra={'target': str(path)})


def reportAsJson(report: Report) -> dict[str, object]:
    """Convert the report to JSON-serialisable primitives.

    Returns:
        A mapping ready for `json.dumps`: scan totals, the malformed lines, the counts by event,
        the slowest operations and the ERROR groups with their examples.
    """
    return {
        'scanned': report.scan.scanned,
        'kept': len(report.scan.records),
        'malformed': [
            {'source': str(item.source), 'line': item.line, 'reason': item.reason} for item in report.scan.malformed
        ],
        'counts_by_event': [{'event': str(item.event), 'count': item.count} for item in report.event_counts],
        'slowest': [entryAsJson(entry) for entry in report.slowest],
        'errors_by_event': [
            {
                'event': str(group.event),
                'count': group.count,
                'examples': [entryAsJson(entry) for entry in group.examples],
            }
            for group in report.error_groups
        ],
    }


def entryAsJson(entry: LogEntry) -> dict[str, object]:
    # `.value` is where the LogLevel enum leaves the program (R2-08).
    return {
        'timestamp': entry.timestamp.isoformat(),
        'level': entry.level.value,
        'event': str(entry.event),
        'duration_ms': entry.duration,
        'detail': entry.detail,
        'source': str(entry.source),
        'line': entry.line,
    }


### vocabulary #########################################################################

EventName = NewType('EventName', str)
Milliseconds = NewType('Milliseconds', float)


class LogLevel(Enum):
    DEBUG = 'DEBUG'
    INFO = 'INFO'
    WARNING = 'WARNING'
    ERROR = 'ERROR'
    CRITICAL = 'CRITICAL'


class TriageError(RuntimeError):
    """A log file, a line or a command-line argument could not be used."""


class MalformedLineError(TriageError):
    """One line failed to parse. The scan records it and moves on."""


@dataclass(frozen=True)
class Selection:
    since: datetime | None
    until: datetime | None
    min_level: LogLevel


@dataclass(frozen=True)
class LogEntry:
    timestamp: datetime
    level: LogLevel
    event: EventName
    duration: Milliseconds | None
    detail: str
    source: Path
    line: int


@dataclass(frozen=True)
class MalformedLine:
    source: Path
    line: int
    reason: str


@dataclass(frozen=True)
class ScanResult:
    records: tuple[LogEntry, ...]
    scanned: int
    malformed: tuple[MalformedLine, ...]


@dataclass(frozen=True)
class EventCount:
    event: EventName
    count: int


@dataclass(frozen=True)
class ErrorGroup:
    event: EventName
    count: int
    examples: tuple[LogEntry, ...]


@dataclass(frozen=True)
class Report:
    scan: ScanResult
    event_counts: tuple[EventCount, ...]
    slowest: tuple[LogEntry, ...]
    error_groups: tuple[ErrorGroup, ...]


class JsonlFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        # Anything on the record that is not one of these came from an `extra={...}` at a log call.
        # fmt: off
        STANDARD_FIELDS = frozenset({
            'args', 'asctime', 'created', 'exc_info', 'exc_text', 'filename', 'funcName',
            'levelname', 'levelno', 'lineno', 'message', 'module', 'msecs', 'msg', 'name',
            'pathname', 'process', 'processName', 'relativeCreated', 'stack_info', 'taskName',
            'thread', 'threadName',
        })
        # fmt: on

        payload: dict[str, object] = {
            'time': datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            'level': record.levelname,
            'event': record.getMessage(),
        }

        payload.update({key: value for key, value in record.__dict__.items() if key not in STANDARD_FIELDS})
        return json.dumps(payload)


if __name__ == '__main__':
    sys.exit(main())
