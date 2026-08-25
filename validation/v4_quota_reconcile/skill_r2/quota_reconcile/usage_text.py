"""Read a `*.usage` report, which names no owning team and no host.

    # node-a, collected 2026-08-24

    /srv/build/artifacts	1.5G
    /home/build/cache	4096
    /var/log/audit/2026-08	12K

The separator between the path and the size is a tab. A size carries an optional unit letter; see
`sizes`. A blank line and a `#` comment hold no entry.
"""

from __future__ import annotations

from pathlib import Path

from quota_reconcile.entries import UsageEntry, rejectEntry
from quota_reconcile.sizes import MalformedSizeError, parseSizeBytes


def readTextReport(report_path: Path) -> list[UsageEntry]:
    """Read a `*.usage` file into UsageEntry records, in the order the file lists them.

    Raises:
        MalformedReportError: a line holds other than two tab-separated fields, or a size that
            does not parse. The first such line stops the read.
    """
    COMMENT_MARKER = '#'
    FIELD_SEPARATOR = '\t'
    FIELD_COUNT = 2

    entries: list[UsageEntry] = []
    for number, line in enumerate(report_path.read_text(encoding='utf-8').splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith(COMMENT_MARKER):
            continue

        # split
        fields = line.split(FIELD_SEPARATOR)
        if len(fields) != FIELD_COUNT:
            raise rejectEntry(report_path, f'line {number}', f'expected {FIELD_COUNT} tab-separated fields')
        path_text, size_text = fields

        # size
        try:
            size_bytes = parseSizeBytes(size_text)
        except MalformedSizeError as exc:
            raise rejectEntry(report_path, f'line {number}', str(exc)) from exc
        entries.append(UsageEntry(path=Path(path_text), size_bytes=size_bytes, team=None, host=None))

    return entries
