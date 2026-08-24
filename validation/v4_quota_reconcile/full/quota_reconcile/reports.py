"""Read every usage report in a directory, in whichever of the two formats each report holds.

The name of the file states the format. A name that ends in `.usage.json` holds the JSON format, and
a name that ends in `.usage` holds the text format. The reader passes over every other file, thus
the quota file can sit in the same directory.

A malformed report does not stop the other reports. The reader gives an outcome for every file that
it opened.
"""

from __future__ import annotations

from collections.abc import Iterable
from enum import Enum, auto
from itertools import chain
from pathlib import Path

from quota_reconcile import usage_json, usage_text
from quota_reconcile.logs import LOG
from quota_reconcile.vocabulary import FileOutcome, MalformedReportError, ReadStatus, ReportBatch, UsageReport


_TEXT_SUFFIX = '.usage'
_JSON_SUFFIX = '.usage.json'


def readReports(usage_dir: Path) -> ReportBatch:
    reports: list[UsageReport] = []
    outcomes: list[FileOutcome] = []

    for report_path in _reportPaths(usage_dir):
        try:
            report = _parseReport(report_path)
        except MalformedReportError as exc:
            outcomes.append(_rejectedOutcome(report_path, str(exc)))
            continue
        reports.append(report)
        outcomes.append(_readOutcome(report))

    batch = ReportBatch(reports=tuple(reports), outcomes=tuple(outcomes))
    _logRejections(batch.outcomes)
    return batch


def _rejectedOutcome(report_path: Path, detail: str) -> FileOutcome:
    return FileOutcome(
        source=report_path,
        status=ReadStatus.REJECTED,
        entry_count=0,
        rejected_lines=0,
        detail=detail,
    )


def _readOutcome(report: UsageReport) -> FileOutcome:
    return FileOutcome(
        source=report.source,
        status=ReadStatus.READ,
        entry_count=len(report.entries),
        rejected_lines=report.rejected_lines,
        detail='',
    )


def _logRejections(outcomes: Iterable[FileOutcome]) -> None:
    # The tally is what an operator acts on. Each rejected file and entry has its own DEBUG record.
    counted = tuple(outcomes)
    rejected_files = sum(1 for outcome in counted if outcome.status is ReadStatus.REJECTED)
    rejected_entries = sum(outcome.rejected_lines for outcome in counted)
    if not rejected_files and not rejected_entries:
        return
    LOG.warning(
        'reports.rejected',
        extra={'files': rejected_files, 'entries': rejected_entries, 'total_files': len(counted)},
    )


def _reportPaths(usage_dir: Path) -> list[Path]:
    return sorted(chain(usage_dir.glob('*' + _TEXT_SUFFIX), usage_dir.glob('*' + _JSON_SUFFIX)))


def _parseReport(report_path: Path) -> UsageReport:
    report_text = _readReportText(report_path)
    match _detectFormat(report_path):
        case _ReportFormat.TEXT:
            return usage_text.parseTextReport(report_text, report_path)
        case _ReportFormat.JSON:
            return usage_json.parseJsonReport(report_text, report_path)


def _readReportText(report_path: Path) -> str:
    try:
        return report_path.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError) as exc:
        raise _rejectUnreadableReport(report_path, str(exc)) from exc


def _detectFormat(report_path: Path) -> _ReportFormat:
    if report_path.name.endswith(_JSON_SUFFIX):
        return _ReportFormat.JSON
    return _ReportFormat.TEXT


def _rejectUnreadableReport(report_path: Path, reason: str) -> MalformedReportError:
    LOG.debug('report.unreadable', extra={'source': str(report_path), 'reason': reason})
    return MalformedReportError(f'{report_path}: {reason}')


### vocabulary #########################################################################


class _ReportFormat(Enum):
    TEXT = auto()
    JSON = auto()
