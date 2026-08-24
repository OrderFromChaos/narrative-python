"""Read the JSON usage report format, which the suffix `.usage.json` selects.

The file holds one object. That object names the host, and it holds one entry per path. Each entry
names a path, a plain count of bytes, and the team that owns the path.

    {"host": "store-01", "entries": [{"path": "/srv/index", "bytes": 4096, "team": "search"}]}

A file that does not hold this shape is unreadable, and the reader raises. A single bad entry inside
a readable file is not: the reader throws that entry away, counts it, and reads the entries after it.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from quota_reconcile.vocabulary import Bytes, HostName, TeamName, UsageEntry, UsageReport, UsageReportError


LOG = logging.getLogger(__name__)


def parseJsonUsageReport(report_path: Path, report_text: str) -> UsageReport:
    """Read the text of one `*.usage.json` file as a usage report.

    Args:
        report_path: Where the text came from. The reader puts it on the report and in the log.

    Raises:
        UsageReportError: the text does not hold JSON, or the object misses `host` or `entries`.
    """
    try:
        document = json.loads(report_text)
    except json.JSONDecodeError as exc:
        raise rejectJsonReport(report_path, 'the file does not hold JSON') from exc

    # the report header, which the entries below depend on
    if not isinstance(document, dict):
        raise rejectJsonReport(report_path, 'the top level of the file is not an object')
    host = document.get('host')
    if not isinstance(host, str):
        raise rejectJsonReport(report_path, 'the host field is absent, or it is not a string')
    raw_entries = document.get('entries')
    if not isinstance(raw_entries, list):
        raise rejectJsonReport(report_path, 'the entries field is absent, or it is not a list')

    entries: list[UsageEntry] = []
    rejected_lines = 0
    for raw_entry in raw_entries:
        try:
            entries.append(parseJsonEntry(raw_entry))
        except UsageReportError:
            rejected_lines += 1

    if rejected_lines:
        LOG.warning(
            'usage.entries.rejected',
            extra={'source': str(report_path), 'rejected': rejected_lines, 'total': len(raw_entries)},
        )
    return UsageReport(source=report_path, host=HostName(host), entries=tuple(entries), rejected_lines=rejected_lines)


def parseJsonEntry(raw_entry: object) -> UsageEntry:
    if not isinstance(raw_entry, dict):
        raise rejectJsonEntry('the entry is not an object')

    path_text = raw_entry.get('path')
    size = raw_entry.get('bytes')
    team = raw_entry.get('team')
    if not isinstance(path_text, str) or not path_text.strip():
        raise rejectJsonEntry('the path field is absent, empty, or not a string')
    if not isinstance(team, str) or not team.strip():
        raise rejectJsonEntry('the team field is absent, empty, or not a string')

    # `True` passes isinstance(x, int), and a JSON `true` must not become a size of 1
    if not isinstance(size, int) or isinstance(size, bool):
        raise rejectJsonEntry('the bytes field is absent, or it is not an integer')
    if size < 0:
        raise rejectJsonEntry('the bytes field is below zero')
    return UsageEntry(path=Path(path_text.strip()), size=Bytes(size), team=TeamName(team.strip()))


def rejectJsonReport(report_path: Path, reason: str) -> UsageReportError:
    LOG.debug('usage.report.rejected', extra={'source': str(report_path), 'reason': reason})
    return UsageReportError(reason)


def rejectJsonEntry(reason: str) -> UsageReportError:
    LOG.debug('usage.entry.rejected', extra={'reason': reason})
    return UsageReportError(reason)
