"""The `*.usage` format: one `path<TAB>size` per line.

A line that starts with `#` is a comment, and a blank line is ignored. The size carries a unit
suffix, so `4096`, `12K`, `1.5G`, `800M` and `2T` are all legal.

This format names no owning team. Every entry it yields therefore has `team` set to `None`, and
the reconciler decides where such usage lands. The host is not in the file either, so the reader
takes it from the file name: `web01.usage` reports host `web01`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from .errors import MalformedReportError, SizeFormatError
from .model import UsageEntry, UsageReport
from .sizes import parse_size

SUFFIX = ".usage"

_COMMENT_MARK = "#"
_FIELD_SEPARATOR = "\t"


def read_text_report(path: Path) -> UsageReport:
    """Read a `*.usage` file. Raise `MalformedReportError` if the file cannot be opened."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise MalformedReportError(str(path), f"cannot read file: {exc}") from exc
    except UnicodeDecodeError as exc:
        raise MalformedReportError(str(path), f"not UTF-8 text: {exc}") from exc

    return parse_text_report(text.splitlines(), source=path, host=host_from_name(path))


def parse_text_report(lines: Iterable[str], source: Path, host: str | None = None) -> UsageReport:
    """Turn the lines of a `*.usage` file into a report.

    A line the reader cannot use is dropped and noted in `problems`. The rest of the file still
    counts.
    """
    entries: list[UsageEntry] = []
    problems: list[str] = []

    for number, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line or line.startswith(_COMMENT_MARK):
            continue

        try:
            path, size_bytes = _parse_line(line)
        except ValueError as exc:
            problems.append(f"line {number}: {exc}")
            continue

        entries.append(
            UsageEntry(
                path=path,
                size_bytes=size_bytes,
                team=None,
                host=host,
                source=source.name,
            )
        )

    return UsageReport(
        source=source,
        host=host,
        entries=tuple(entries),
        problems=tuple(problems),
    )


def host_from_name(path: Path) -> str:
    """Return the host name a `*.usage` file name carries, such as `web01` for `web01.usage`."""
    return path.name[: -len(SUFFIX)] if path.name.endswith(SUFFIX) else path.stem


def _parse_line(line: str) -> tuple[str, int]:
    """Split one data line into a path and a byte count."""
    if _FIELD_SEPARATOR not in line:
        raise ValueError("expected 'path<TAB>size'")

    path, _, size_text = line.partition(_FIELD_SEPARATOR)
    path = path.strip()
    size_text = size_text.strip()
    if not path:
        raise ValueError("the path is empty")
    if not size_text:
        raise ValueError("the size is empty")

    try:
        return path, parse_size(size_text)
    except SizeFormatError as exc:
        raise ValueError(str(exc)) from exc
