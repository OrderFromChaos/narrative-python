"""Reader for the ``requirements.lock`` format.

One ``name==version`` per line. A ``#`` starts a comment, which can be on its
own line or after a requirement. Blank lines are ignored. The format carries
no source field, so every package from this format has a source of ``None``.
"""

from __future__ import annotations

import re
from pathlib import Path

from .models import ManifestError, Package

__all__ = ["FORMAT_NAME", "parse_requirements_lock", "read_requirements_lock"]

FORMAT_NAME = "requirements.lock"

_MAX_REPORTED_ERRORS = 3

_REQUIREMENT = re.compile(
    r"^(?P<name>[A-Za-z0-9][A-Za-z0-9._-]*)\s*==\s*(?P<version>[A-Za-z0-9][A-Za-z0-9.!+_-]*)$"
)


def read_requirements_lock(path: Path) -> list[Package]:
    """Read one lock file from disk.

    Raises:
        ManifestError: The file cannot be read or holds an unreadable line.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as error:
        raise ManifestError(str(path), f"cannot open file: {error.strerror}") from error
    except UnicodeDecodeError as error:
        raise ManifestError(str(path), "file is not UTF-8 text") from error
    return parse_requirements_lock(text, source_path=str(path))


def parse_requirements_lock(text: str, *, source_path: str = "<text>") -> list[Package]:
    """Read lock file text that is already in memory.

    Raises:
        ManifestError: A line is not ``name==version``.
    """
    packages: list[Package] = []
    problems: list[str] = []

    for number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        match = _REQUIREMENT.match(line)
        if match is None:
            problems.append(f"line {number}: expected name==version, found {line!r}")
            continue
        packages.append(
            Package(
                name=match["name"],
                version=match["version"],
                source=None,
                manifest=source_path,
                location=f"line {number}",
            )
        )

    if problems:
        raise ManifestError(source_path, _summarize(problems))
    return packages


def _summarize(problems: list[str]) -> str:
    shown = "; ".join(problems[:_MAX_REPORTED_ERRORS])
    hidden = len(problems) - _MAX_REPORTED_ERRORS
    if hidden > 0:
        return f"{shown}; and {hidden} more"
    return shown
