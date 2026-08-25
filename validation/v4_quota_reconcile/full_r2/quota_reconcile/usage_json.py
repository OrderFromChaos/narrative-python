"""Read a `.usage.json` report, which names the host once and the owning team on every entry.

    {
      "host": "store-02",
      "entries": [
        {"path": "/srv/index/shard-0", "bytes": 1319413953331, "team": "search"}
      ]
    }

A size is a plain count of bytes and carries no unit suffix. The first malformed field stops the
read.
"""

from __future__ import annotations

import json
from pathlib import Path

from quota_reconcile.common import ByteCount, HostName, MalformedReportError, TeamName, UsageEntry, UsageReport
from quota_reconcile.logs import LOG


def readJsonReport(usage_json_path: Path) -> UsageReport:
    text = usage_json_path.read_text(encoding='utf-8')
    try:
        document = json.loads(text)
    except json.JSONDecodeError as exc:
        raise _rejectReport(usage_json_path, f'unusable JSON: {exc}') from exc

    if not isinstance(document, dict):
        raise _rejectReport(usage_json_path, 'the document is not an object')

    host = document.get('host')
    raw_entries = document.get('entries')
    if not isinstance(host, str):
        raise _rejectReport(usage_json_path, 'host is missing, or is not a string')
    if not isinstance(raw_entries, list):
        raise _rejectReport(usage_json_path, 'entries is missing, or is not a list')

    entries = tuple(_readEntry(usage_json_path, HostName(host), raw_entry) for raw_entry in raw_entries)
    report = UsageReport(source=usage_json_path, entries=entries)
    return report


def _readEntry(usage_json_path: Path, host: HostName, raw_entry: object) -> UsageEntry:
    if not isinstance(raw_entry, dict):
        raise _rejectReport(usage_json_path, 'an entry is not an object')

    path_text = raw_entry.get('path')
    size = raw_entry.get('bytes')
    team = raw_entry.get('team')
    if not isinstance(path_text, str):
        raise _rejectReport(usage_json_path, 'an entry names no path')
    if not isinstance(size, int):
        raise _rejectReport(usage_json_path, f'the bytes of {path_text} is not an integer')
    if not isinstance(team, str):
        raise _rejectReport(usage_json_path, f'the entry for {path_text} names no team')

    return UsageEntry(path=Path(path_text), size=ByteCount(size), team=TeamName(team), host=host)


def _rejectReport(usage_json_path: Path, reason: str) -> MalformedReportError:
    LOG.debug('report.rejected', extra={'source': str(usage_json_path), 'reason': reason})
    return MalformedReportError(f'{usage_json_path.name}: {reason}')
