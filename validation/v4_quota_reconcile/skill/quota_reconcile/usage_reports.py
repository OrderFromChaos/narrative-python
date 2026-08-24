"""Read every usage report in one directory, whichever format each file holds.

The name of a file selects its format. A name that ends with `.usage.json` gives the JSON format,
and a name that ends with `.usage` gives the text format. A name that matches neither is not a usage
report, and the reader passes over it without a word.

The reader gives one outcome per report file, and a file that it cannot read does not stop the files
after it.
"""

from __future__ import annotations

import logging
from pathlib import Path

from quota_reconcile.json_usage import parseJsonUsageReport
from quota_reconcile.text_usage import parseTextUsageReport
from quota_reconcile.vocabulary import FileOutcome, ReadOutcome, ReportFormat, ReportReader, UsageReportError


REPORT_GLOB = '*.usage*'
TEXT_SUFFIX = '.usage'
JSON_SUFFIX = '.usage.json'

LOG = logging.getLogger(__name__)


def readUsageReports(input_dir: Path) -> tuple[FileOutcome, ...]:
    """Read every usage report in a directory.

    Returns:
        One outcome per report file, in the sorted order of the file names.
    """
    outcomes: list[FileOutcome] = []
    for report_path in sorted(input_dir.glob(REPORT_GLOB)):
        report_format = detectReportFormat(report_path)
        if report_format is not None:
            outcomes.append(readReportFile(report_path, report_format))

    unreadable = sum(1 for outcome in outcomes if outcome.outcome is ReadOutcome.UNREADABLE)
    if unreadable:
        LOG.warning('reports.unreadable', extra={'unreadable': unreadable, 'total': len(outcomes)})
    return tuple(outcomes)


def detectReportFormat(report_path: Path) -> ReportFormat | None:
    """Give the format that the name of a file selects, and None when the name selects no format."""
    if report_path.name.endswith(JSON_SUFFIX):
        return ReportFormat.JSON
    if report_path.name.endswith(TEXT_SUFFIX):
        return ReportFormat.TEXT
    return None


def readReportFile(report_path: Path, report_format: ReportFormat) -> FileOutcome:
    """Read one report file, and turn every failure of that file into an outcome.

    Returns:
        An outcome that holds a report, unless the file is unreadable. The outcome is DEGRADED when
        the reader threw away one entry or more.
    """
    try:
        report_text = report_path.read_text(encoding='utf-8')
    except OSError:
        return rejectReportFile(report_path, report_format, 'the file does not open')
    except UnicodeDecodeError:
        return rejectReportFile(report_path, report_format, 'the file does not hold UTF-8 text')

    parse_report = selectReportReader(report_format)
    try:
        report = parse_report(report_path, report_text)
    except UsageReportError as exc:
        return rejectReportFile(report_path, report_format, str(exc))

    outcome = ReadOutcome.DEGRADED if report.rejected_lines else ReadOutcome.READ
    return FileOutcome(report_path, report_format, outcome, report, '')


def selectReportReader(report_format: ReportFormat) -> ReportReader:
    match report_format:
        case ReportFormat.TEXT:
            return parseTextUsageReport
        case ReportFormat.JSON:
            return parseJsonUsageReport


def rejectReportFile(report_path: Path, report_format: ReportFormat, reason: str) -> FileOutcome:
    LOG.debug('report.unreadable', extra={'source': str(report_path), 'reason': reason})
    return FileOutcome(report_path, report_format, ReadOutcome.UNREADABLE, None, reason)
