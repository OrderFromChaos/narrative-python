"""Read a `.usage` report, which gives a path and a size per line and names no owning team.

    # store-01, nightly sweep. This format names no owning team.
    /srv/exports/nightly.tar	1.5G
    /var/tmp/scratch	4096

The two fields are separated by a tab. A line whose first character is `#` and a line that holds
only whitespace carry no entry. The first malformed line stops the read.
"""

from __future__ import annotations

from pathlib import Path

from quota_reconcile import sizes
from quota_reconcile.common import MalformedReportError, MalformedSizeError, UsageEntry, UsageReport
from quota_reconcile.logs import LOG


_COMMENT_MARK = '#'
_FIELD_SEPARATOR = '\t'
_FIELD_COUNT = 2


def readTextReport(usage_path: Path) -> UsageReport:
    entries: list[UsageEntry] = []
    for line_number, line in enumerate(usage_path.read_text(encoding='utf-8').splitlines(), start=1):
        text = line.strip()
        if not text or text.startswith(_COMMENT_MARK):
            continue

        fields = text.split(_FIELD_SEPARATOR)
        if len(fields) != _FIELD_COUNT:
            raise _rejectLine(usage_path, line_number, 'expected a path and a size, separated by a tab')

        path_text, size_text = fields
        try:
            size = sizes.parseSize(size_text)
        except MalformedSizeError as exc:
            raise _rejectLine(usage_path, line_number, str(exc)) from exc

        entries.append(UsageEntry(path=Path(path_text), size=size, team=None, host=None))

    report = UsageReport(source=usage_path, entries=tuple(entries))
    return report


def _rejectLine(usage_path: Path, line_number: int, reason: str) -> MalformedReportError:
    LOG.debug('line.rejected', extra={'source': str(usage_path), 'line': line_number, 'reason': reason})
    return MalformedReportError(f'{usage_path.name}:{line_number}: {reason}')
