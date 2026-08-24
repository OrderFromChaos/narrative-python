"""Read the text usage report format, which the suffix `.usage` selects.

Each line holds a path, one TAB character, and a size. A line that starts with `#` is a comment, and
a blank line has no meaning. The format names no host and no team, so every entry from it has no
team and the report has no host.

    # storage report
    /srv/index<TAB>1.5G
    /var/log/audit<TAB>12K

The reader throws away a line that it cannot read, counts that line, and reads the lines after it.
"""

from __future__ import annotations

import logging
from pathlib import Path

from quota_reconcile.sizes import parseSizeText
from quota_reconcile.vocabulary import SizeTextError, UsageEntry, UsageReport, UsageReportError


COMMENT_MARKER = '#'
FIELD_SEPARATOR = '\t'

LOG = logging.getLogger(__name__)


def parseTextUsageReport(report_path: Path, report_text: str) -> UsageReport:
    """Read the text of one `*.usage` file as a usage report.

    Args:
        report_path: Where the text came from. The reader puts it on the report and in the log.

    Returns:
        A report whose host is None, because the text format names no host.
    """
    entries: list[UsageEntry] = []
    rejected_lines = 0
    for line in report_text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(COMMENT_MARKER):
            continue

        try:
            entries.append(parseUsageLine(stripped))
        except UsageReportError:
            rejected_lines += 1

    if rejected_lines:
        LOG.warning(
            'usage.lines.rejected',
            extra={'source': str(report_path), 'rejected': rejected_lines, 'total': len(entries) + rejected_lines},
        )
    return UsageReport(source=report_path, host=None, entries=tuple(entries), rejected_lines=rejected_lines)


def parseUsageLine(line: str) -> UsageEntry:
    FIELD_COUNT = 2
    fields = line.split(FIELD_SEPARATOR)
    if len(fields) != FIELD_COUNT:
        raise rejectUsageLine(line, 'the line does not hold a path, a TAB and a size')

    path_text, size_text = fields
    if not path_text.strip():
        raise rejectUsageLine(line, 'the path is empty')

    try:
        size = parseSizeText(size_text)
    except SizeTextError as exc:
        raise rejectUsageLine(line, 'the size is unreadable') from exc
    return UsageEntry(path=Path(path_text.strip()), size=size, team=None)


def rejectUsageLine(line: str, reason: str) -> UsageReportError:
    LOG.debug('usage.line.rejected', extra={'line': line, 'reason': reason})
    return UsageReportError(f'{reason}: {line!r}')
