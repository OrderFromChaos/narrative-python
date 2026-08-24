"""Read the entries of a `.usage.json` report.

The file holds one JSON object:

    {"host": "node-01", "entries": [{"path": "/srv/index", "bytes": 12288, "team": "search"}]}

A size is a plain count of bytes. The format names the team that owns each entry, and it names the
host of the whole report.

An entry that states no path, no size or no team does not stop the report. The parser counts that
entry and continues. A file that holds no JSON object is a malformed report, and the parser rejects
the whole file.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import TypeVar

from quota_reconcile.logs import LOG
from quota_reconcile.vocabulary import (
    ByteCount,
    HostName,
    MalformedEntryError,
    MalformedReportError,
    TeamName,
    UsageEntry,
    UsageReport,
)


def parseJsonReport(report_text: str, source: Path) -> UsageReport:
    document = _readReportObject(report_text, source)
    raw_entries = document.get('entries')
    if not isinstance(raw_entries, list):
        raise _rejectReport(source, 'the object states no list of entries')
    raw_host = document.get('host')
    host = HostName(raw_host) if isinstance(raw_host, str) else None

    entries: list[UsageEntry] = []
    rejected = 0
    for number, raw_entry in enumerate(raw_entries, start=1):
        try:
            entries.append(_parseEntry(raw_entry, number, source, host))
        except MalformedEntryError:
            rejected += 1

    return UsageReport(source=source, host=host, entries=tuple(entries), rejected_lines=rejected)


def _readReportObject(report_text: str, source: Path) -> Mapping[str, object]:
    try:
        document = json.loads(report_text)
    except json.JSONDecodeError as exc:
        raise _rejectReport(source, str(exc)) from exc

    if not isinstance(document, dict):
        raise _rejectReport(source, 'the file holds no JSON object')
    return document


def _parseEntry(
    raw_entry: object,
    number: int,
    source: Path,
    host: HostName | None,
) -> UsageEntry:
    """Make one usage entry from one element of the `entries` list.

    Args:
        number: The position of the element in the list, for the rejection message.

    Raises:
        MalformedEntryError: The element is not an object, or one field is absent or of the wrong
            type, or the size is negative.
    """
    if not isinstance(raw_entry, dict):
        raise _rejectEntry(source, number, 'the entry is not a JSON object')

    try:
        path_text = _requiredField(raw_entry, 'path', str)
        size = _requiredField(raw_entry, 'bytes', int)
        team = _requiredField(raw_entry, 'team', str)
    except MalformedEntryError as exc:
        raise _rejectEntry(source, number, str(exc)) from exc
    if size < 0:
        raise _rejectEntry(source, number, 'the count of bytes is negative')

    return UsageEntry(path=Path(path_text), size=ByteCount(size), team=TeamName(team), host=host)


def _requiredField(fields: Mapping[str, object], field_name: str, expected: type[_Value]) -> _Value:
    value = fields.get(field_name)
    # No field of this format holds a boolean, and `json` reads `true` into a Python `int`.
    if isinstance(value, bool) or not isinstance(value, expected):
        raise MalformedEntryError(f'field {field_name!r} does not hold a {expected.__name__}')
    return value


def _rejectEntry(source: Path, number: int, reason: str) -> MalformedEntryError:
    LOG.debug('usage_entry.rejected', extra={'source': str(source), 'entry': number, 'reason': reason})
    return MalformedEntryError(f'{source}: entry {number}: {reason}')


def _rejectReport(source: Path, reason: str) -> MalformedReportError:
    LOG.debug('usage_report.rejected', extra={'source': str(source), 'reason': reason})
    return MalformedReportError(f'{source}: {reason}')


### vocabulary #########################################################################

_Value = TypeVar('_Value')
