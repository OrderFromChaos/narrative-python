"""The `*.usage.json` format.

The file is one JSON object:

    {"host": "store03", "entries": [{"path": "/srv/x", "bytes": 4096, "team": "platform"}]}

Sizes are plain integers, and every entry names the owning team. An entry without a team is
therefore a defect in the file, not a fact about the data, so the reader drops that entry and
notes it. Damage to the JSON itself, or to the shape of the document, fails the whole file.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .errors import MalformedReportError
from .model import UsageEntry, UsageReport

SUFFIX = ".usage.json"


def read_json_report(path: Path) -> UsageReport:
    """Read a `*.usage.json` file. Raise `MalformedReportError` if the document is unusable."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise MalformedReportError(str(path), f"cannot read file: {exc}") from exc
    except UnicodeDecodeError as exc:
        raise MalformedReportError(str(path), f"not UTF-8 text: {exc}") from exc

    return parse_json_report(text, source=path)


def parse_json_report(text: str, source: Path) -> UsageReport:
    """Turn the text of a `*.usage.json` file into a report."""
    try:
        document: Any = json.loads(text)
    except json.JSONDecodeError as exc:
        raise MalformedReportError(str(source), f"not valid JSON: {exc}") from exc

    if not isinstance(document, dict):
        raise MalformedReportError(str(source), "the document must be a JSON object")

    raw_entries = document.get("entries")
    if raw_entries is None:
        raise MalformedReportError(str(source), "the document has no 'entries' list")
    if not isinstance(raw_entries, list):
        raise MalformedReportError(str(source), "'entries' must be a list")

    host = document.get("host")
    if host is not None and not isinstance(host, str):
        raise MalformedReportError(str(source), f"'host' must be a string, found {host!r}")

    entries: list[UsageEntry] = []
    problems: list[str] = []

    for index, raw_entry in enumerate(raw_entries):
        try:
            entries.append(_read_entry(raw_entry, host=host, source=source))
        except ValueError as exc:
            problems.append(f"entry {index}: {exc}")

    return UsageReport(
        source=source,
        host=host,
        entries=tuple(entries),
        problems=tuple(problems),
    )


def _read_entry(raw_entry: Any, host: str | None, source: Path) -> UsageEntry:
    """Read one element of the `entries` list."""
    if not isinstance(raw_entry, dict):
        raise ValueError(f"expected an object, found {raw_entry!r}")

    path = raw_entry.get("path")
    if not isinstance(path, str) or not path.strip():
        raise ValueError(f"'path' must be a non-empty string, found {path!r}")

    size_bytes = raw_entry.get("bytes")
    if isinstance(size_bytes, bool) or not isinstance(size_bytes, int):
        raise ValueError(f"'bytes' must be an integer, found {size_bytes!r}")
    if size_bytes < 0:
        raise ValueError(f"'bytes' must not be negative, found {size_bytes}")

    team = raw_entry.get("team")
    if not isinstance(team, str) or not team.strip():
        raise ValueError(f"'team' must be a non-empty string, found {team!r}")

    return UsageEntry(
        path=path.strip(),
        size_bytes=size_bytes,
        team=team.strip(),
        host=host,
        source=source.name,
    )
