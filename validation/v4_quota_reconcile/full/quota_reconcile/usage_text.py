"""Read the entries of a `.usage` report.

Each line holds a path, a TAB, then a size, thus `/srv/index<TAB>12K`. A line that starts with `#`
is a comment. An empty line holds nothing. The format names no team and no host, so an entry that
comes from it carries neither.

A line that states no size does not stop the report. The parser counts that line and continues.
"""

from __future__ import annotations

from pathlib import Path

from quota_reconcile import byte_size
from quota_reconcile.logs import LOG
from quota_reconcile.vocabulary import MalformedEntryError, MalformedSizeError, UsageEntry, UsageReport


def parseTextReport(report_text: str, source: Path) -> UsageReport:
    COMMENT_MARKER = '#'
    entries: list[UsageEntry] = []
    rejected = 0

    for number, line in enumerate(report_text.splitlines(), start=1):
        content = line.strip()
        if not content or content.startswith(COMMENT_MARKER):
            continue
        try:
            entries.append(_parseUsageLine(content, number, source))
        except MalformedEntryError:
            rejected += 1

    return UsageReport(source=source, host=None, entries=tuple(entries), rejected_lines=rejected)


def _parseUsageLine(line: str, number: int, source: Path) -> UsageEntry:
    FIELD_SEPARATOR = '\t'
    path_text, separator, size_text = line.partition(FIELD_SEPARATOR)
    if not separator:
        raise _rejectLine(source, number, 'the line holds no TAB')
    if not path_text.strip():
        raise _rejectLine(source, number, 'the line names no path')

    try:
        size = byte_size.parseByteSize(size_text)
    except MalformedSizeError as exc:
        raise _rejectLine(source, number, str(exc)) from exc

    return UsageEntry(path=Path(path_text.strip()), size=size, team=None, host=None)


def _rejectLine(source: Path, number: int, reason: str) -> MalformedEntryError:
    LOG.debug('usage_line.rejected', extra={'source': str(source), 'line': number, 'reason': reason})
    return MalformedEntryError(f'{source}:{number}: {reason}')
