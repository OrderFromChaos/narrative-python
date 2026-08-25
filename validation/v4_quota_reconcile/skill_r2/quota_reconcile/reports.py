"""Read every usage report in a directory, whichever format each is.

    ReportOutcome(report_path=PosixPath('fixture/node-a.usage'), status=<ReportStatus.READ: 'read'>,
                  entries=(UsageEntry(...), ...), detail='')
    ReportOutcome(report_path=PosixPath('fixture/node-c.usage'), status=<ReportStatus.MALFORMED: 'malformed'>,
                  entries=(), detail='line 3: expected 2 tab-separated fields')

A `*.usage.json` name goes to the JSON reader and any other `*.usage` name to the text reader; any
other name in the directory is not a report. Outcomes sort by report_path. `detail` carries the
rejection message and is empty on a report that was read. A rejected report yields no entries and
does not stop the rest of the directory.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from quota_reconcile.entries import MalformedReportError, UsageEntry
from quota_reconcile.usage_json import readJsonReport
from quota_reconcile.usage_text import readTextReport


TEXT_REPORT_SUFFIX = '.usage'
JSON_REPORT_SUFFIX = '.usage.json'

LOG = logging.getLogger(__name__)


def readReportDirectory(reports_dir: Path) -> list[ReportOutcome]:
    report_paths = sorted(
        path
        for path in reports_dir.iterdir()
        if path.is_file() and path.name.endswith((TEXT_REPORT_SUFFIX, JSON_REPORT_SUFFIX))
    )
    outcomes = [readReport(report_path) for report_path in report_paths]

    rejected = [outcome for outcome in outcomes if rejectedReport(outcome.status)]
    if rejected:
        LOG.warning('reports.rejected', extra={'rejected': len(rejected), 'total': len(outcomes)})
    return outcomes


def readReport(report_path: Path) -> ReportOutcome:
    try:
        if report_path.name.endswith(JSON_REPORT_SUFFIX):
            entries = readJsonReport(report_path)
        else:
            entries = readTextReport(report_path)
    except MalformedReportError as exc:
        return ReportOutcome(report_path, ReportStatus.MALFORMED, (), str(exc))
    except OSError as exc:
        return ReportOutcome(report_path, ReportStatus.UNREADABLE, (), str(exc))
    return ReportOutcome(report_path, ReportStatus.READ, tuple(entries), '')


def rejectedReport(status: ReportStatus) -> bool:
    match status:
        case ReportStatus.READ:
            return False
        case ReportStatus.MALFORMED | ReportStatus.UNREADABLE:
            return True


### vocabulary #########################################################################


class ReportStatus(Enum):
    READ = 'read'
    MALFORMED = 'malformed'
    UNREADABLE = 'unreadable'


@dataclass(frozen=True)
class ReportOutcome:
    report_path: Path
    status: ReportStatus
    entries: tuple[UsageEntry, ...]
    detail: str
