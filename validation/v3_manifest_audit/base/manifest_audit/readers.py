"""Manifest discovery and format dispatch.

This is the only module that knows both formats. It decides which reader a
file gets, and which files in a directory are manifests at all.

The format comes from the file name:

* ``*.lock`` and ``requirements.txt`` use the ``requirements.lock`` reader.
* ``*.json`` uses the ``packages.json`` reader.

Every other file is ignored, as is the policy file itself when it sits in the
directory being audited.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from pathlib import Path

from .models import ManifestError, Package
from .packages_json import FORMAT_NAME as PACKAGES_JSON_FORMAT
from .packages_json import read_packages_json
from .requirements_lock import FORMAT_NAME as REQUIREMENTS_LOCK_FORMAT
from .requirements_lock import read_requirements_lock

__all__ = [
    "PACKAGES_JSON_FORMAT",
    "REQUIREMENTS_LOCK_FORMAT",
    "discover_manifests",
    "format_of",
    "read_manifest",
]

_Reader = Callable[[Path], list[Package]]

_READERS: dict[str, _Reader] = {
    REQUIREMENTS_LOCK_FORMAT: read_requirements_lock,
    PACKAGES_JSON_FORMAT: read_packages_json,
}

_LOCK_SUFFIXES = frozenset({".lock"})
_JSON_SUFFIXES = frozenset({".json"})
_LOCK_NAMES = frozenset({"requirements.txt"})


def format_of(path: Path) -> str | None:
    """Return the format name for a path, or ``None`` if it is not a manifest."""
    suffix = path.suffix.lower()
    if suffix in _LOCK_SUFFIXES or path.name.lower() in _LOCK_NAMES:
        return REQUIREMENTS_LOCK_FORMAT
    if suffix in _JSON_SUFFIXES:
        return PACKAGES_JSON_FORMAT
    return None


def discover_manifests(root: Path, *, exclude: Iterable[Path] = ()) -> list[Path]:
    """List the manifests directly inside ``root``, sorted by name.

    Args:
        root: The directory to look in. The search does not go into
            subdirectories.
        exclude: Paths to leave out, such as the policy file and the report
            file.

    Raises:
        NotADirectoryError: ``root`` is not a directory.
    """
    if not root.is_dir():
        raise NotADirectoryError(f"{root}: not a directory")

    skip = {_resolved(path) for path in exclude}
    found = [
        path
        for path in sorted(root.iterdir())
        if path.is_file() and format_of(path) is not None and _resolved(path) not in skip
    ]
    return found


def read_manifest(path: Path) -> list[Package]:
    """Read one manifest, choosing the reader by file name.

    Raises:
        ManifestError: The file is not a known format, or cannot be read.
    """
    manifest_format = format_of(path)
    if manifest_format is None:
        raise ManifestError(str(path), "unknown manifest format")
    return _READERS[manifest_format](path)


def _resolved(path: Path) -> Path:
    try:
        return path.resolve()
    except OSError:
        return path.absolute()
