"""Find the usage reports in a directory and send each one to the reader for its format.

The file name selects the reader: a name that ends in `.usage.json` is JSON, and a name that ends
in `.usage` is the tab-separated text format. Every other file, the quota file included, is left
alone. One damaged report does not stop the others: the failure becomes an outcome and the walk
carries on.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Iterable

from .errors import MalformedReportError
from .model import ReportOutcome, UsageReport
from . import usage_json, usage_text

Reader = Callable[[Path], UsageReport]

_READERS: tuple[tuple[str, Reader], ...] = (
    (usage_json.SUFFIX, usage_json.read_json_report),
    (usage_text.SUFFIX, usage_text.read_text_report),
)


def is_report(path: Path) -> bool:
    """Return whether `path` has the name of a usage report."""
    return reader_for(path) is not None


def reader_for(path: Path) -> Reader | None:
    """Return the reader that handles `path`, or `None` if the name is not a report name."""
    for suffix, reader in _READERS:
        if path.name.endswith(suffix):
            return reader
    return None


def find_reports(directory: Path) -> list[Path]:
    """Return the report files in `directory`, sorted by name, so a run is repeatable."""
    return sorted(path for path in directory.iterdir() if path.is_file() and is_report(path))


def read_report(path: Path) -> UsageReport:
    """Read one report with the reader its name selects."""
    reader = reader_for(path)
    if reader is None:
        raise MalformedReportError(str(path), "the file name matches no known report format")
    return reader(path)


def read_reports(paths: Iterable[Path]) -> tuple[list[UsageReport], list[ReportOutcome]]:
    """Read every report, and return the reports that were read next to one outcome per file."""
    reports: list[UsageReport] = []
    outcomes: list[ReportOutcome] = []

    for path in paths:
        try:
            report = read_report(path)
        except MalformedReportError as exc:
            outcomes.append(ReportOutcome.failure(path, exc.reason))
            continue

        outcomes.append(ReportOutcome.from_report(report))
        if report.entries:
            reports.append(report)

    return reports, outcomes


def read_directory(directory: Path) -> tuple[list[UsageReport], list[ReportOutcome]]:
    """Read every usage report in `directory`."""
    return read_reports(find_reports(directory))
