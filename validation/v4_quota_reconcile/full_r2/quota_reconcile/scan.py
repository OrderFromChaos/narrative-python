"""Read every usage report in a directory, whichever of the two formats each one is.

    FileOutcome(source=PosixPath('fixture/store-01.usage'), entry_count=4, error=None)
    FileOutcome(source=PosixPath('fixture/store-04.usage'), entry_count=0,
                error="store-04.usage:3: unusable size '12X'")

A report that fails to parse becomes an outcome carrying the rejection message, and the remaining
reports are still read. Outcomes sort by source path and hold one entry per report file, parsed or
rejected; `reports` holds only the files that parsed.
"""

from __future__ import annotations

from pathlib import Path

from quota_reconcile import usage_json, usage_text
from quota_reconcile.common import FileOutcome, MalformedReportError, ReportFormat, ScanResult, UsageReport
from quota_reconcile.logs import LOG


_JSON_SUFFIX = f'.{ReportFormat.JSON.value}'


def readReports(input_dir: Path) -> ScanResult:
    reports: list[UsageReport] = []
    outcomes: list[FileOutcome] = []
    for usage_path in _listReportPaths(input_dir):
        try:
            report = _readReport(usage_path, _detectFormat(usage_path))
        except (MalformedReportError, OSError) as exc:
            LOG.debug('file.rejected', extra={'source': str(usage_path), 'reason': str(exc)})
            outcomes.append(FileOutcome(source=usage_path, entry_count=0, error=str(exc)))
            continue

        reports.append(report)
        outcomes.append(FileOutcome(source=usage_path, entry_count=len(report.entries), error=None))

    rejected = sum(1 for outcome in outcomes if outcome.error is not None)
    if rejected:
        LOG.warning('scan.rejected', extra={'rejected': rejected, 'total': len(outcomes)})

    scan_result = ScanResult(reports=tuple(reports), outcomes=tuple(outcomes))
    return scan_result


def _listReportPaths(input_dir: Path) -> list[Path]:
    paths: set[Path] = set()
    for report_format in ReportFormat:
        paths.update(input_dir.glob(f'*.{report_format.value}'))

    return sorted(paths)


def _detectFormat(usage_path: Path) -> ReportFormat:
    if usage_path.name.endswith(_JSON_SUFFIX):
        return ReportFormat.JSON

    return ReportFormat.TEXT


def _readReport(usage_path: Path, report_format: ReportFormat) -> UsageReport:
    match report_format:
        case ReportFormat.TEXT:
            return usage_text.readTextReport(usage_path)
        case ReportFormat.JSON:
            return usage_json.readJsonReport(usage_path)
