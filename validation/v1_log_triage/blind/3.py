#!/usr/bin/env python3
"""Triage JSONL logs produced by the ingest pipeline.

Reads every ``*.jsonl`` file under a directory, keeps the records that fall
inside an optional time window and at or above a minimum severity, and reports:

* how many records were seen per ``event``
* the slowest operations, ranked by the optional ``duration_ms`` field
* every ``ERROR``-or-worse record grouped by ``event``, with a few examples

The report is printed as a terminal table and written as JSON.

Lines that cannot be understood never abort the run: they are counted and
summarised (with examples) at the end of the report.

Usage::

    python base.py LOGDIR --since 2024-05-01T00:00:00Z --min-level WARNING

Python 3.10+, standard library only.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TextIO

__all__ = ["main", "triage", "LogRecord", "SkippedLine", "Report"]

#: Severity names mapped to a rank. Aliases share a rank with their canonical
#: name so that ``WARN`` and ``WARNING`` filter identically.
LEVEL_RANKS: dict[str, int] = {
    "TRACE": 5,
    "DEBUG": 10,
    "INFO": 20,
    "NOTICE": 25,
    "WARN": 30,
    "WARNING": 30,
    "ERROR": 40,
    "CRITICAL": 50,
    "FATAL": 50,
}

#: Records at or above this rank are treated as errors for the grouped section.
ERROR_RANK = LEVEL_RANKS["ERROR"]

DEFAULT_SLOWEST = 5
DEFAULT_EXAMPLES = 3
SNIPPET_LIMIT = 160


class TriageError(Exception):
    """Raised for conditions that make a run impossible (bad input paths)."""


@dataclass(frozen=True, slots=True)
class Origin:
    """Where a line came from, for blame-friendly reporting."""

    path: Path
    line_no: int

    def __str__(self) -> str:
        return f"{self.path.name}:{self.line_no}"


@dataclass(frozen=True, slots=True)
class LogRecord:
    """A single well-formed log line."""

    timestamp: datetime
    level: str
    rank: int
    event: str
    duration_ms: float | None
    fields: dict[str, Any]
    origin: Origin

    @property
    def is_error(self) -> bool:
        return self.rank >= ERROR_RANK


@dataclass(frozen=True, slots=True)
class SkippedLine:
    """A line that could not be turned into a :class:`LogRecord`."""

    origin: Origin
    reason: str
    detail: str
    snippet: str


@dataclass(frozen=True, slots=True)
class Report:
    """The result of a triage run, ready to render or serialise."""

    source: Path
    since: datetime | None
    until: datetime | None
    min_level: str | None
    files: list[Path]
    total_lines: int
    parsed: int
    selected: int
    filtered_out: int
    event_counts: list[tuple[str, int]]
    slowest: list[LogRecord]
    errors_by_event: list[tuple[str, int, list[LogRecord]]]
    skipped: list[SkippedLine]


# --------------------------------------------------------------------------- #
# Parsing
# --------------------------------------------------------------------------- #


def parse_timestamp(value: Any) -> datetime:
    """Parse an ISO-8601 string or epoch seconds into an aware UTC datetime.

    Naive timestamps are assumed to be UTC, which matches what the ingest
    pipeline writes.

    Raises:
        ValueError: if the value is not a recognisable timestamp.
    """
    if isinstance(value, bool):  # bool is an int; reject it explicitly.
        raise ValueError("boolean is not a timestamp")
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc)
    if not isinstance(value, str):
        raise ValueError(f"expected string or number, got {type(value).__name__}")

    text = value.strip()
    if text.endswith(("Z", "z")):
        text = f"{text[:-1]}+00:00"
    parsed = datetime.fromisoformat(text)  # raises ValueError on junk
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def parse_level(value: Any) -> tuple[str, int]:
    """Normalise a level name and return ``(name, rank)``.

    Raises:
        ValueError: if the level is missing from :data:`LEVEL_RANKS`.
    """
    if not isinstance(value, str):
        raise ValueError(f"expected string, got {type(value).__name__}")
    name = value.strip().upper()
    try:
        return name, LEVEL_RANKS[name]
    except KeyError:
        raise ValueError(f"unknown level {value!r}") from None


def parse_duration(value: Any) -> float | None:
    """Coerce ``duration_ms`` to a float, or ``None`` when unusable.

    A bad duration does not invalidate a line; the record simply drops out of
    the "slowest operations" ranking.
    """
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        duration = float(value)
    elif isinstance(value, str):
        try:
            duration = float(value.strip())
        except ValueError:
            return None
    else:
        return None
    return duration if duration == duration and duration >= 0 else None  # NaN-safe


def parse_line(raw: str, origin: Origin) -> LogRecord | SkippedLine:
    """Turn one raw line into a record, or explain why it was skipped."""
    snippet = raw.strip()[:SNIPPET_LIMIT]

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        return SkippedLine(origin, "invalid_json", exc.msg, snippet)

    if not isinstance(payload, dict):
        detail = f"top-level {type(payload).__name__}, expected object"
        return SkippedLine(origin, "not_an_object", detail, snippet)

    missing = [key for key in ("timestamp", "level", "event") if key not in payload]
    if missing:
        detail = "missing " + ", ".join(missing)
        return SkippedLine(origin, "missing_field", detail, snippet)

    try:
        timestamp = parse_timestamp(payload["timestamp"])
    except (ValueError, OSError, OverflowError) as exc:
        return SkippedLine(origin, "bad_timestamp", str(exc), snippet)

    try:
        level, rank = parse_level(payload["level"])
    except ValueError as exc:
        return SkippedLine(origin, "bad_level", str(exc), snippet)

    event = payload["event"]
    if not isinstance(event, str) or not event.strip():
        detail = f"event must be a non-empty string, got {payload['event']!r}"
        return SkippedLine(origin, "bad_event", detail, snippet)

    fields = {
        key: value
        for key, value in payload.items()
        if key not in ("timestamp", "level", "event")
    }
    return LogRecord(
        timestamp=timestamp,
        level=level,
        rank=rank,
        event=event.strip(),
        duration_ms=parse_duration(payload.get("duration_ms")),
        fields=fields,
        origin=origin,
    )


def discover_files(source: Path, pattern: str = "*.jsonl") -> list[Path]:
    """Return the log files to read, sorted for reproducible output.

    ``source`` may be a single file or a directory, which is searched
    recursively.

    Raises:
        TriageError: if the path does not exist.
    """
    if not source.exists():
        raise TriageError(f"no such file or directory: {source}")
    if source.is_file():
        return [source]
    return sorted(path for path in source.rglob(pattern) if path.is_file())


def read_lines(paths: Iterable[Path]) -> Iterator[tuple[str, Origin]]:
    """Yield ``(raw_line, origin)`` for every non-blank line in ``paths``.

    Unreadable files and undecodable bytes are surfaced as skipped lines rather
    than exceptions, so one bad file cannot abort the run.
    """
    for path in paths:
        try:
            with path.open("r", encoding="utf-8", errors="replace") as handle:
                for line_no, raw in enumerate(handle, start=1):
                    if raw.strip():
                        yield raw, Origin(path, line_no)
        except OSError as exc:
            yield "", Origin(path, 0)  # placeholder; reason attached below
            print(f"warning: cannot read {path}: {exc}", file=sys.stderr)


# --------------------------------------------------------------------------- #
# Analysis
# --------------------------------------------------------------------------- #


def triage(
    source: Path,
    *,
    pattern: str = "*.jsonl",
    since: datetime | None = None,
    until: datetime | None = None,
    min_rank: int = 0,
    min_level: str | None = None,
    slowest: int = DEFAULT_SLOWEST,
    examples: int = DEFAULT_EXAMPLES,
) -> Report:
    """Scan ``source`` and build a :class:`Report`.

    Args:
        source: Directory (searched recursively) or single log file.
        pattern: Glob applied when ``source`` is a directory.
        since: Inclusive lower bound on record timestamps.
        until: Exclusive upper bound on record timestamps.
        min_rank: Minimum severity rank a record must reach to be kept.
        min_level: Display name for ``min_rank``, used only in the report.
        slowest: How many operations to list in the duration ranking.
        examples: How many example records to keep per error event.
    """
    files = discover_files(source, pattern)

    total_lines = 0
    parsed = 0
    filtered_out = 0
    event_counts: Counter[str] = Counter()
    by_duration: list[LogRecord] = []
    error_examples: defaultdict[str, list[LogRecord]] = defaultdict(list)
    error_counts: Counter[str] = Counter()
    skipped: list[SkippedLine] = []

    for raw, origin in read_lines(files):
        total_lines += 1
        if not raw:
            skipped.append(SkippedLine(origin, "unreadable_file", "read failed", ""))
            continue

        outcome = parse_line(raw, origin)
        if isinstance(outcome, SkippedLine):
            skipped.append(outcome)
            continue

        parsed += 1
        if not _in_window(outcome.timestamp, since, until) or outcome.rank < min_rank:
            filtered_out += 1
            continue

        event_counts[outcome.event] += 1
        if outcome.duration_ms is not None:
            by_duration.append(outcome)
        if outcome.is_error:
            error_counts[outcome.event] += 1
            if len(error_examples[outcome.event]) < examples:
                error_examples[outcome.event].append(outcome)

    by_duration.sort(key=lambda record: (-record.duration_ms, record.timestamp))  # type: ignore[operator]
    errors_by_event = [
        (event, count, error_examples[event])
        for event, count in sorted(error_counts.items(), key=lambda kv: (-kv[1], kv[0]))
    ]

    return Report(
        source=source,
        since=since,
        until=until,
        min_level=min_level,
        files=files,
        total_lines=total_lines,
        parsed=parsed,
        selected=sum(event_counts.values()),
        filtered_out=filtered_out,
        event_counts=sorted(event_counts.items(), key=lambda kv: (-kv[1], kv[0])),
        slowest=by_duration[:slowest],
        errors_by_event=errors_by_event,
        skipped=skipped,
    )


def _in_window(
    moment: datetime, since: datetime | None, until: datetime | None
) -> bool:
    """Test ``since <= moment < until`` with either bound optional."""
    if since is not None and moment < since:
        return False
    if until is not None and moment >= until:
        return False
    return True


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #


def format_table(headers: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
    """Render a plain-text table with left-aligned, space-padded columns."""
    if not rows:
        return "  (none)"
    widths = [len(header) for header in headers]
    for row in rows:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], len(cell))

    def line(cells: Sequence[str]) -> str:
        padded = (cell.ljust(widths[i]) for i, cell in enumerate(cells))
        return "  " + "  ".join(padded).rstrip()

    divider = "  " + "  ".join("-" * width for width in widths)
    return "\n".join([line(headers), divider, *(line(row) for row in rows)])


def render(report: Report, stream: TextIO) -> None:
    """Write the human-readable report to ``stream``."""
    write = lambda text="": print(text, file=stream)  # noqa: E731

    write("=" * 72)
    write(f"LOG TRIAGE  {report.source}")
    write("=" * 72)
    write(
        f"files: {len(report.files)}   lines: {report.total_lines}   "
        f"parsed: {report.parsed}   selected: {report.selected}   "
        f"filtered out: {report.filtered_out}   skipped: {len(report.skipped)}"
    )
    write(
        f"window: {_iso(report.since) or '-'} .. {_iso(report.until) or '-'}   "
        f"min level: {report.min_level or '-'}"
    )

    write()
    write("Events")
    write(
        format_table(
            ("EVENT", "COUNT"),
            [(event, str(count)) for event, count in report.event_counts],
        )
    )

    write()
    write(f"Slowest operations (top {len(report.slowest)})")
    write(
        format_table(
            ("DURATION_MS", "EVENT", "TIMESTAMP", "SOURCE"),
            [
                (
                    f"{record.duration_ms:,.1f}",
                    record.event,
                    _iso(record.timestamp) or "",
                    str(record.origin),
                )
                for record in report.slowest
            ],
        )
    )

    write()
    total_errors = sum(count for _, count, _ in report.errors_by_event)
    write(f"Errors by event ({total_errors} total)")
    if not report.errors_by_event:
        write("  (none)")
    for event, count, examples in report.errors_by_event:
        write(f"  {event}  ({count})")
        for record in examples:
            write(f"      {_iso(record.timestamp)}  [{record.level}]  {record.origin}")
            if record.fields:
                write(f"      {_compact(record.fields)}")

    write()
    write(f"Skipped lines ({len(report.skipped)})")
    reasons = Counter(item.reason for item in report.skipped)
    write(
        format_table(
            ("REASON", "COUNT"),
            [
                (reason, str(count))
                for reason, count in sorted(reasons.items(), key=lambda kv: (-kv[1], kv[0]))
            ],
        )
    )
    for item in report.skipped[:DEFAULT_EXAMPLES]:
        write(f"      {item.origin}  {item.reason}: {item.detail}")
        if item.snippet:
            write(f"      {item.snippet}")
    if len(report.skipped) > DEFAULT_EXAMPLES:
        write(f"      ... {len(report.skipped) - DEFAULT_EXAMPLES} more")


def to_json(report: Report) -> dict[str, Any]:
    """Build the JSON-serialisable form of the report."""
    return {
        "generated_at": _iso(datetime.now(tz=timezone.utc)),
        "source": str(report.source),
        "filters": {
            "since": _iso(report.since),
            "until": _iso(report.until),
            "min_level": report.min_level,
        },
        "totals": {
            "files": len(report.files),
            "lines": report.total_lines,
            "parsed": report.parsed,
            "selected": report.selected,
            "filtered_out": report.filtered_out,
            "skipped": len(report.skipped),
        },
        "files": [str(path) for path in report.files],
        "counts_by_event": [
            {"event": event, "count": count} for event, count in report.event_counts
        ],
        "slowest": [
            {
                "duration_ms": record.duration_ms,
                "event": record.event,
                "level": record.level,
                "timestamp": _iso(record.timestamp),
                "source": str(record.origin),
                "fields": record.fields,
            }
            for record in report.slowest
        ],
        "errors_by_event": [
            {
                "event": event,
                "count": count,
                "examples": [
                    {
                        "timestamp": _iso(record.timestamp),
                        "level": record.level,
                        "source": str(record.origin),
                        "fields": record.fields,
                    }
                    for record in examples
                ],
            }
            for event, count, examples in report.errors_by_event
        ],
        "skipped": {
            "by_reason": dict(Counter(item.reason for item in report.skipped)),
            "lines": [
                {
                    "source": str(item.origin),
                    "reason": item.reason,
                    "detail": item.detail,
                    "snippet": item.snippet,
                }
                for item in report.skipped
            ],
        },
    }


def _iso(moment: datetime | None) -> str | None:
    """Format a datetime as ISO-8601 with a ``Z`` suffix."""
    if moment is None:
        return None
    return moment.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _compact(fields: dict[str, Any], limit: int = 120) -> str:
    """Render extra fields as a short single-line summary."""
    text = json.dumps(fields, default=str, sort_keys=True)
    return text if len(text) <= limit else text[: limit - 3] + "..."


# --------------------------------------------------------------------------- #
# Command line
# --------------------------------------------------------------------------- #


def _timestamp_arg(value: str) -> datetime:
    try:
        return parse_timestamp(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid timestamp {value!r}: {exc}") from None


def _level_arg(value: str) -> str:
    try:
        name, _ = parse_level(value)
    except ValueError:
        choices = ", ".join(sorted(LEVEL_RANKS, key=LEVEL_RANKS.get))  # type: ignore[arg-type]
        raise argparse.ArgumentTypeError(
            f"invalid level {value!r}; choose from: {choices}"
        ) from None
    return name


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="log-triage",
        description=__doc__.split("\n\n", 1)[0] if __doc__ else None,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("source", type=Path, help="log directory or single .jsonl file")
    parser.add_argument(
        "--pattern", default="*.jsonl", help="glob used when source is a directory"
    )
    parser.add_argument(
        "--since", type=_timestamp_arg, help="keep records at or after this time (ISO-8601)"
    )
    parser.add_argument(
        "--until", type=_timestamp_arg, help="keep records strictly before this time"
    )
    parser.add_argument(
        "--min-level", type=_level_arg, help="keep records at or above this severity"
    )
    parser.add_argument(
        "--top",
        type=int,
        default=DEFAULT_SLOWEST,
        metavar="N",
        help="how many slow operations to list",
    )
    parser.add_argument(
        "--examples",
        type=int,
        default=DEFAULT_EXAMPLES,
        metavar="N",
        help="how many example errors to keep per event",
    )
    parser.add_argument(
        "--json",
        dest="json_path",
        type=Path,
        default=Path("log_report.json"),
        help="path for the JSON report ('-' for stdout)",
    )
    parser.add_argument(
        "--quiet", action="store_true", help="suppress the terminal table"
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point. Returns a process exit code."""
    args = build_parser().parse_args(argv)

    if args.top < 0 or args.examples < 0:
        print("error: --top and --examples must not be negative", file=sys.stderr)
        return 2
    if args.since and args.until and args.since >= args.until:
        print("error: --since must be earlier than --until", file=sys.stderr)
        return 2

    try:
        report = triage(
            args.source,
            pattern=args.pattern,
            since=args.since,
            until=args.until,
            min_rank=LEVEL_RANKS[args.min_level] if args.min_level else 0,
            min_level=args.min_level,
            slowest=args.top,
            examples=args.examples,
        )
    except TriageError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if not args.quiet:
        render(report, sys.stdout)

    payload = to_json(report)
    if str(args.json_path) == "-":
        json.dump(payload, sys.stdout, indent=2, default=str)
        sys.stdout.write("\n")
    else:
        try:
            args.json_path.parent.mkdir(parents=True, exist_ok=True)
            with args.json_path.open("w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2, default=str)
                handle.write("\n")
        except OSError as exc:
            print(f"error: cannot write {args.json_path}: {exc}", file=sys.stderr)
            return 1
        if not args.quiet:
            print(f"\nJSON report written to {args.json_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
