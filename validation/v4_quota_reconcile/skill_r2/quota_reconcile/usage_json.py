"""Read a `*.usage.json` report, which names the host once and the owning team on every entry.

    {
      "host": "node-b",
      "entries": [
        {"path": "/srv/build/artifacts", "bytes": 322122547200, "team": "platform"}
      ]
    }

`bytes` is a plain byte count and carries no unit letter.
"""

from __future__ import annotations

import json
from pathlib import Path

from quota_reconcile.entries import HostName, TeamName, UsageEntry, rejectEntry
from quota_reconcile.sizes import ByteCount


def readJsonReport(report_path: Path) -> list[UsageEntry]:
    """Read a `*.usage.json` file into UsageEntry records, in the order the array lists them.

    Raises:
        MalformedReportError: the file is not JSON, or `host` or `entries` is absent or of the
            wrong type, or an element does not read as an entry. The first such fault stops the
            read.
    """
    try:
        document = json.loads(report_path.read_text(encoding='utf-8'))
    except json.JSONDecodeError as exc:
        raise rejectEntry(report_path, 'document', str(exc)) from exc

    if not isinstance(document, dict):
        raise rejectEntry(report_path, 'document', 'expected an object')
    host = document.get('host')
    if not isinstance(host, str):
        raise rejectEntry(report_path, 'host', 'expected a string')
    raw_entries = document.get('entries')
    if not isinstance(raw_entries, list):
        raise rejectEntry(report_path, 'entries', 'expected an array')

    return [
        parseJsonEntry(report_path, HostName(host), f'entries[{index}]', raw_entry)
        for index, raw_entry in enumerate(raw_entries)
    ]


def parseJsonEntry(
    report_path: Path,
    host: HostName,
    locator: str,
    raw_entry: object,
) -> UsageEntry:
    """Parse one element of the `entries` array into a UsageEntry.

    Args:
        report_path: Where the element came from, for the rejection message.
        locator: Which element of the array, for the rejection message.

    Raises:
        MalformedReportError: the element is not an object, or `path`, `bytes` or `team` is absent
            or of the wrong type.
    """
    if not isinstance(raw_entry, dict):
        raise rejectEntry(report_path, locator, 'expected an object')

    path_text = raw_entry.get('path')
    size_bytes = raw_entry.get('bytes')
    team = raw_entry.get('team')
    if not isinstance(path_text, str):
        raise rejectEntry(report_path, locator, 'path: expected a string')
    if not isinstance(size_bytes, int) or isinstance(size_bytes, bool):
        raise rejectEntry(report_path, locator, 'bytes: expected an integer')
    if not isinstance(team, str):
        raise rejectEntry(report_path, locator, 'team: expected a string')

    return UsageEntry(
        path=Path(path_text),
        size_bytes=ByteCount(size_bytes),
        team=TeamName(team),
        host=host,
    )
