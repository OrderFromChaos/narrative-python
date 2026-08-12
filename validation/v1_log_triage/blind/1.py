### IMPORTS ###########################################################################################################
import argparse
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


### Global scope variables ############################################################################################


# Severity ranking used for the --min-level filter. Ingest pipelines are inconsistent about the two short spellings,
# so both are accepted on input and normalised to the stdlib logging names on output.
LEVEL_SEVERITY: dict[str, int] = {
    'DEBUG': 10,
    'INFO': 20,
    'WARNING': 30,
    'ERROR': 40,
    'CRITICAL': 50,
}
LEVEL_ALIASES: dict[str, str] = {
    'WARN': 'WARNING',
    'FATAL': 'CRITICAL',
}

# CRITICAL is folded into the error grouping. It is strictly more severe than ERROR, and a report that hides the
# worst failures because they were logged one level up is worse than useless during an incident.
ERROR_GROUP_LEVELS: frozenset[str] = frozenset({'ERROR', 'CRITICAL'})

REQUIRED_FIELDS: tuple[str, ...] = ('timestamp', 'level', 'event')
DURATION_FIELD = 'duration_ms'

SLOWEST_OPERATION_COUNT = 5
ERROR_EXAMPLES_PER_EVENT = 3

# Malformed lines are echoed back to the operator, and a stray multi-megabyte line should not flood the terminal.
MALFORMED_PREVIEW_CHARS = 80
MALFORMED_LISTED_IN_TABLE = 10
EVENT_COLUMN_CHARS = 44
DETAIL_COLUMN_CHARS = 60


### Function/Class definitions ########################################################################################


@dataclass
class LogRecord:
    timestamp: datetime
    level: str
    event: str
    duration_ms: float | None
    extra: dict[str, Any]
    source_file: str
    line_number: int


@dataclass
class MalformedLine:
    source_file: str
    line_number: int
    reason: str
    preview: str


@dataclass
class ScanResult:
    records: list[LogRecord] = field(default_factory=list)
    malformed: list[MalformedLine] = field(default_factory=list)
    total_lines: int = 0
    files_read: list[str] = field(default_factory=list)


@dataclass
class ErrorGroup:
    event: str
    count: int
    examples: list[LogRecord]


@dataclass
class TriageReport:
    generated_at: datetime
    log_dir: str
    files_read: list[str]
    window_start: datetime | None
    window_end: datetime | None
    min_level: str
    total_lines: int
    malformed_count: int
    dropped_by_window: int
    dropped_by_level: int
    kept_records: int
    event_counts: dict[str, int]
    slowest: list[LogRecord]
    error_groups: list[ErrorGroup]
    malformed: list[MalformedLine]


def parseIsoTimestamp(value: str) -> datetime | None:
    # datetime.fromisoformat() only learned to parse a trailing 'Z' in 3.11 and this file targets 3.10.
    normalised = value.strip()
    if normalised.endswith(('Z', 'z')):
        normalised = f'{normalised[:-1]}+00:00'

    try:
        parsed = datetime.fromisoformat(normalised)
    except ValueError:
        return None

    # Everything downstream is compared and sorted, which throws on a mix of naive and aware values. Pipeline logs
    # without an offset are UTC by convention here.
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def normaliseLevel(value: Any) -> str | None:
    global LEVEL_ALIASES, LEVEL_SEVERITY

    if not isinstance(value, str):
        return None

    candidate = value.strip().upper()
    candidate = LEVEL_ALIASES.get(candidate, candidate)
    if candidate not in LEVEL_SEVERITY:
        return None
    return candidate


def coerceDurationMs(value: Any) -> float | None:
    # bool is a subclass of int, and True would otherwise silently become a 1 ms operation.
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)

    # Some emitters quote the number. That is worth accepting, but a non-numeric string is not.
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return None
    return None


def parseLogLine(raw_line: str, source_file: str, line_number: int) -> LogRecord | MalformedLine:
    global DURATION_FIELD, MALFORMED_PREVIEW_CHARS, REQUIRED_FIELDS

    preview = raw_line.strip()[:MALFORMED_PREVIEW_CHARS]

    try:
        payload = json.loads(raw_line)
    except json.JSONDecodeError as exc:
        return MalformedLine(source_file, line_number, f'invalid JSON ({exc.msg})', preview)

    if not isinstance(payload, dict):
        return MalformedLine(source_file, line_number, f'not a JSON object (got {type(payload).__name__})', preview)

    missing = [name for name in REQUIRED_FIELDS if name not in payload]
    if missing:
        return MalformedLine(source_file, line_number, f'missing field(s): {", ".join(missing)}', preview)

    raw_timestamp = payload['timestamp']
    if not isinstance(raw_timestamp, str):
        return MalformedLine(source_file, line_number, 'timestamp is not a string', preview)
    timestamp = parseIsoTimestamp(raw_timestamp)
    if timestamp is None:
        return MalformedLine(source_file, line_number, f'unparseable timestamp: {raw_timestamp!r}', preview)

    level = normaliseLevel(payload['level'])
    if level is None:
        return MalformedLine(source_file, line_number, f'unknown level: {payload["level"]!r}', preview)

    event = payload['event']
    if not isinstance(event, str) or not event.strip():
        return MalformedLine(source_file, line_number, f'event is not a non-empty string: {event!r}', preview)

    # A bad duration does not invalidate the line. The record still counts towards its event and towards any error
    # grouping, it just cannot take part in the slowest-operation ranking.
    duration_ms = coerceDurationMs(payload.get(DURATION_FIELD))
    extra = {key: value for key, value in payload.items() if key not in REQUIRED_FIELDS and key != DURATION_FIELD}

    return LogRecord(
        timestamp=timestamp,
        level=level,
        event=event.strip(),
        duration_ms=duration_ms,
        extra=extra,
        source_file=source_file,
        line_number=line_number,
    )


def scanLogDirectory(log_dir: Path, pattern: str, recursive: bool) -> ScanResult:
    result = ScanResult()
    log_files = sorted(log_dir.rglob(pattern) if recursive else log_dir.glob(pattern))

    for log_file in log_files:
        if not log_file.is_file():
            continue
        display_name = str(log_file.relative_to(log_dir))

        # A single unreadable or partially corrupt file must not take the whole run down; 'replace' turns undecodable
        # bytes into U+FFFD, which then fails JSON parsing and lands in the malformed bucket like any other bad line.
        try:
            handle = log_file.open('r', encoding='utf-8', errors='replace')
        except OSError as exc:
            print(f'WARNING: skipping {display_name}: {exc}', file=sys.stderr)
            continue

        result.files_read.append(display_name)
        with handle:
            for line_number, raw_line in enumerate(handle, start=1):
                if not raw_line.strip():
                    continue
                result.total_lines += 1
                parsed = parseLogLine(raw_line, display_name, line_number)
                if isinstance(parsed, LogRecord):
                    result.records.append(parsed)
                else:
                    result.malformed.append(parsed)

    return result


def countEvents(records: list[LogRecord]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        counts[record.event] = counts.get(record.event, 0) + 1

    # Highest count first, then alphabetical so equal counts have a stable order across runs.
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def findSlowestOperations(records: list[LogRecord], limit: int) -> list[LogRecord]:
    timed = [record for record in records if record.duration_ms is not None]
    timed.sort(key=lambda record: (-float(record.duration_ms or 0.0), record.timestamp))
    return timed[:limit]


def groupErrors(records: list[LogRecord], examples_per_event: int) -> list[ErrorGroup]:
    global ERROR_GROUP_LEVELS

    grouped: dict[str, list[LogRecord]] = {}
    for record in records:
        if record.level in ERROR_GROUP_LEVELS:
            grouped.setdefault(record.event, []).append(record)

    groups = [
        ErrorGroup(event=event, count=len(matches), examples=matches[:examples_per_event])
        for event, matches in grouped.items()
    ]
    groups.sort(key=lambda group: (-group.count, group.event))
    return groups


def buildReport(
        scan: ScanResult,
        log_dir: Path,
        window_start: datetime | None,
        window_end: datetime | None,
        min_level: str,
    ) -> TriageReport:
    global ERROR_EXAMPLES_PER_EVENT, LEVEL_SEVERITY, SLOWEST_OPERATION_COUNT

    minimum_severity = LEVEL_SEVERITY[min_level]
    kept: list[LogRecord] = []
    dropped_by_window = 0
    dropped_by_level = 0

    # The window is applied before the level so that the "dropped" counters describe disjoint sets and add up.
    for record in scan.records:
        if window_start is not None and record.timestamp < window_start:
            dropped_by_window += 1
            continue
        if window_end is not None and record.timestamp > window_end:
            dropped_by_window += 1
            continue
        if LEVEL_SEVERITY[record.level] < minimum_severity:
            dropped_by_level += 1
            continue
        kept.append(record)

    return TriageReport(
        generated_at=datetime.now(timezone.utc),
        log_dir=str(log_dir),
        files_read=scan.files_read,
        window_start=window_start,
        window_end=window_end,
        min_level=min_level,
        total_lines=scan.total_lines,
        malformed_count=len(scan.malformed),
        dropped_by_window=dropped_by_window,
        dropped_by_level=dropped_by_level,
        kept_records=len(kept),
        event_counts=countEvents(kept),
        slowest=findSlowestOperations(kept, SLOWEST_OPERATION_COUNT),
        error_groups=groupErrors(kept, ERROR_EXAMPLES_PER_EVENT),
        malformed=scan.malformed,
    )


def truncate(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    return f'{value[:limit - 3]}...'


def formatTimestamp(value: datetime | None) -> str:
    if value is None:
        return '-'
    return value.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'


def formatExtra(extra: dict[str, Any], limit: int) -> str:
    if not extra:
        return '-'
    parts = [f'{key}={json.dumps(value, default=str)}' for key, value in extra.items()]
    return truncate(' '.join(parts), limit)


def renderTable(headers: list[str], rows: list[list[str]]) -> str:
    if not rows:
        return '  (none)'

    widths = [len(header) for header in headers]
    for row in rows:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], len(cell))

    separator = '  +' + '+'.join('-' * (width + 2) for width in widths) + '+'
    lines = [separator, '  | ' + ' | '.join(header.ljust(widths[i]) for i, header in enumerate(headers)) + ' |']
    lines.append(separator)
    for row in rows:
        lines.append('  | ' + ' | '.join(cell.ljust(widths[i]) for i, cell in enumerate(row)) + ' |')
    lines.append(separator)
    return '\n'.join(lines)


def renderReport(report: TriageReport) -> str:
    global DETAIL_COLUMN_CHARS, ERROR_EXAMPLES_PER_EVENT, EVENT_COLUMN_CHARS, MALFORMED_LISTED_IN_TABLE
    global SLOWEST_OPERATION_COUNT

    sections: list[str] = []

    summary_rows = [
        ['log directory', report.log_dir],
        ['files read', str(len(report.files_read))],
        ['lines seen', str(report.total_lines)],
        ['malformed lines', str(report.malformed_count)],
        ['outside window', str(report.dropped_by_window)],
        ['below min level', str(report.dropped_by_level)],
        ['records reported', str(report.kept_records)],
        ['window start', formatTimestamp(report.window_start)],
        ['window end', formatTimestamp(report.window_end)],
        ['minimum level', report.min_level],
    ]
    sections.append('LOG TRIAGE REPORT\n' + renderTable(['field', 'value'], summary_rows))

    event_rows = [[truncate(event, EVENT_COLUMN_CHARS), str(count)] for event, count in report.event_counts.items()]
    sections.append('COUNTS BY EVENT\n' + renderTable(['event', 'count'], event_rows))

    slowest_rows = [
        [
            str(rank),
            truncate(record.event, EVENT_COLUMN_CHARS),
            f'{record.duration_ms:.1f}',
            record.level,
            formatTimestamp(record.timestamp),
            f'{record.source_file}:{record.line_number}',
        ]
        for rank, record in enumerate(report.slowest, start=1)
    ]
    sections.append(
        f'SLOWEST {SLOWEST_OPERATION_COUNT} OPERATIONS BY duration_ms\n'
        + renderTable(['#', 'event', 'duration_ms', 'level', 'timestamp', 'source'], slowest_rows)
    )

    # One row per example rather than one per group, so the operator can read the offending payloads directly.
    error_rows: list[list[str]] = []
    for group in report.error_groups:
        for index, example in enumerate(group.examples):
            error_rows.append([
                truncate(group.event, EVENT_COLUMN_CHARS) if index == 0 else '',
                str(group.count) if index == 0 else '',
                example.level,
                formatTimestamp(example.timestamp),
                f'{example.source_file}:{example.line_number}',
                formatExtra(example.extra, DETAIL_COLUMN_CHARS),
            ])
    sections.append(
        f'ERRORS BY EVENT (first {ERROR_EXAMPLES_PER_EVENT} examples each)\n'
        + renderTable(['event', 'total', 'level', 'timestamp', 'source', 'detail'], error_rows)
    )

    malformed_rows = [
        [f'{bad.source_file}:{bad.line_number}', bad.reason, bad.preview]
        for bad in report.malformed[:MALFORMED_LISTED_IN_TABLE]
    ]
    malformed_title = f'MALFORMED LINES ({report.malformed_count})'
    if report.malformed_count > MALFORMED_LISTED_IN_TABLE:
        malformed_title = f'{malformed_title}, showing first {MALFORMED_LISTED_IN_TABLE}'
    sections.append(malformed_title + '\n' + renderTable(['source', 'reason', 'line preview'], malformed_rows))

    return '\n\n'.join(sections)


def recordToJsonable(record: LogRecord) -> dict[str, Any]:
    return {
        'timestamp': formatTimestamp(record.timestamp),
        'level': record.level,
        'event': record.event,
        'duration_ms': record.duration_ms,
        'extra': record.extra,
        'source_file': record.source_file,
        'line_number': record.line_number,
    }


def reportToJsonable(report: TriageReport) -> dict[str, Any]:
    return {
        'generated_at': formatTimestamp(report.generated_at),
        'log_dir': report.log_dir,
        'files_read': report.files_read,
        'filters': {
            'window_start': formatTimestamp(report.window_start) if report.window_start else None,
            'window_end': formatTimestamp(report.window_end) if report.window_end else None,
            'min_level': report.min_level,
        },
        'totals': {
            'lines_seen': report.total_lines,
            'malformed': report.malformed_count,
            'dropped_by_window': report.dropped_by_window,
            'dropped_by_level': report.dropped_by_level,
            'records_reported': report.kept_records,
        },
        'event_counts': report.event_counts,
        'slowest_operations': [recordToJsonable(record) for record in report.slowest],
        'errors_by_event': [
            {
                'event': group.event,
                'count': group.count,
                'examples': [recordToJsonable(example) for example in group.examples],
            }
            for group in report.error_groups
        ],
        'malformed_lines': [
            {
                'source_file': bad.source_file,
                'line_number': bad.line_number,
                'reason': bad.reason,
                'preview': bad.preview,
            }
            for bad in report.malformed
        ],
    }


def parseArguments(argv: list[str] | None = None) -> argparse.Namespace:
    global LEVEL_SEVERITY

    parser = argparse.ArgumentParser(description='Triage JSONL ingest pipeline logs into a table and a JSON report.')
    parser.add_argument('log_dir', type=Path, help='Directory containing the JSONL log files')
    parser.add_argument('--pattern', default='*.jsonl', help='Glob for log files inside log_dir (default: *.jsonl)')
    parser.add_argument('--recursive', action='store_true', help='Search log_dir subdirectories as well')
    parser.add_argument('--start', default=None, help='Window start, ISO 8601, inclusive (naive values are UTC)')
    parser.add_argument('--end', default=None, help='Window end, ISO 8601, inclusive (naive values are UTC)')
    parser.add_argument(
        '--min-level',
        default='DEBUG',
        help=f'Minimum level to report, one of {", ".join(LEVEL_SEVERITY)} (default: DEBUG)',
    )
    parser.add_argument(
        '--json-out',
        type=Path,
        default=Path('log_triage_report.json'),
        help='Path of the JSON report (default: ./log_triage_report.json)',
    )
    parser.add_argument('--quiet', action='store_true', help='Write the JSON report only, no terminal table')
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parseArguments(argv)

    if not args.log_dir.is_dir():
        print(f'ERROR: not a directory: {args.log_dir}', file=sys.stderr)
        return 2

    min_level = normaliseLevel(args.min_level)
    if min_level is None:
        print(f'ERROR: unknown --min-level: {args.min_level!r}', file=sys.stderr)
        return 2

    window_start = parseIsoTimestamp(args.start) if args.start else None
    if args.start and window_start is None:
        print(f'ERROR: unparseable --start: {args.start!r}', file=sys.stderr)
        return 2
    window_end = parseIsoTimestamp(args.end) if args.end else None
    if args.end and window_end is None:
        print(f'ERROR: unparseable --end: {args.end!r}', file=sys.stderr)
        return 2
    if window_start is not None and window_end is not None and window_start > window_end:
        print('ERROR: --start is after --end', file=sys.stderr)
        return 2

    scan = scanLogDirectory(args.log_dir, args.pattern, args.recursive)
    if not scan.files_read:
        print(f'ERROR: no files matching {args.pattern!r} in {args.log_dir}', file=sys.stderr)
        return 1

    report = buildReport(scan, args.log_dir, window_start, window_end, min_level)

    try:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(reportToJsonable(report), indent=2, default=str) + '\n', encoding='utf-8')
    except OSError as exc:
        print(f'ERROR: could not write {args.json_out}: {exc}', file=sys.stderr)
        return 3

    if not args.quiet:
        print(renderReport(report))
        print(f'\nJSON report written to {args.json_out}')

    return 0


### if __name__ == '__main__' block ###################################################################################


if __name__ == '__main__':
    sys.exit(main())
