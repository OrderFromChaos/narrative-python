"""Reader for the ``packages.json`` format.

The document is ``{"packages": [{"name": ..., "version": ..., "source": ...}]}``.
``name`` and ``version`` are required strings. ``source`` is optional; an entry
without one gets a source of ``None``, and the policy then skips the source
check for it.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import ManifestError, Package

__all__ = ["FORMAT_NAME", "parse_packages_json", "read_packages_json"]

FORMAT_NAME = "packages.json"


def read_packages_json(path: Path) -> list[Package]:
    """Read one package document from disk.

    Raises:
        ManifestError: The file cannot be read, or its content is not a valid
            package document.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as error:
        raise ManifestError(str(path), f"cannot open file: {error.strerror}") from error
    except UnicodeDecodeError as error:
        raise ManifestError(str(path), "file is not UTF-8 text") from error
    return parse_packages_json(text, source_path=str(path))


def parse_packages_json(text: str, *, source_path: str = "<text>") -> list[Package]:
    """Read package document text that is already in memory.

    Raises:
        ManifestError: The text is not valid JSON, or its shape is wrong.
    """
    try:
        document = json.loads(text)
    except json.JSONDecodeError as error:
        raise ManifestError(
            source_path, f"invalid JSON at line {error.lineno} column {error.colno}: {error.msg}"
        ) from error

    if not isinstance(document, dict):
        raise ManifestError(source_path, "top level must be an object")
    entries = document.get("packages")
    if entries is None:
        raise ManifestError(source_path, "missing the 'packages' key")
    if not isinstance(entries, list):
        raise ManifestError(source_path, "'packages' must be an array")

    return [
        _package(entry, index=index, source_path=source_path)
        for index, entry in enumerate(entries)
    ]


def _package(entry: Any, *, index: int, source_path: str) -> Package:
    location = f"packages[{index}]"
    if not isinstance(entry, dict):
        raise ManifestError(source_path, f"{location} must be an object")

    return Package(
        name=_required_text(entry, "name", location=location, source_path=source_path),
        version=_required_text(entry, "version", location=location, source_path=source_path),
        source=_optional_text(entry, "source", location=location, source_path=source_path),
        manifest=source_path,
        location=location,
    )


def _required_text(
    entry: dict[str, Any], field: str, *, location: str, source_path: str
) -> str:
    value = _optional_text(entry, field, location=location, source_path=source_path)
    if value is None:
        raise ManifestError(source_path, f"{location} has no '{field}'")
    return value


def _optional_text(
    entry: dict[str, Any], field: str, *, location: str, source_path: str
) -> str | None:
    value = entry.get(field)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ManifestError(
            source_path, f"{location} has a '{field}' that is not a non-empty string"
        )
    return value.strip()
