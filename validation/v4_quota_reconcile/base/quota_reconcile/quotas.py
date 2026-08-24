"""The quota file: how much each team may store, and which paths do not count.

The file is JSON:

    {
      "team_quotas": {"platform": "500G", "search": "2T"},
      "default_quota": "100G",
      "exempt_paths": ["/var/log/audit"]
    }

`team_quotas` and `exempt_paths` may be left out. `default_quota` may not, because a team the file
does not name has no other quota to fall back on.
"""

from __future__ import annotations

import json
import posixpath
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .errors import QuotaFileError, SizeFormatError
from .sizes import parse_size

QUOTA_FILE_NAME = "quotas.json"
"""The name the reconciler looks for in the input directory."""


@dataclass(frozen=True, slots=True)
class QuotaPolicy:
    """Quotas per team, one default quota, and the paths that count toward no team."""

    team_quotas: Mapping[str, int]
    default_quota: int
    exempt_paths: tuple[str, ...] = ()
    source: Path | None = None

    def quota_for(self, team: str) -> int:
        """Return the quota of `team` in bytes, or the default quota for a team not named."""
        return self.team_quotas.get(team, self.default_quota)

    def has_own_quota(self, team: str) -> bool:
        """Return whether the quota file names `team` itself."""
        return team in self.team_quotas

    def is_exempt(self, path: str) -> bool:
        """Return whether `path` is an exempt path, or sits under one.

        An exempt path names a directory tree, so `/var/log/audit` exempts `/var/log/audit` and
        `/var/log/audit/2026-08` but not `/var/log/audit-old`.
        """
        candidate = _normalise(path)
        for exempt in self.exempt_paths:
            if candidate == exempt or candidate.startswith(exempt.rstrip("/") + "/"):
                return True
        return False


def load_quotas(path: Path) -> QuotaPolicy:
    """Read a quota file. Raise `QuotaFileError` if it cannot be read or is not well formed."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise QuotaFileError(f"cannot read quota file {path}: {exc}") from exc

    try:
        document: Any = json.loads(text)
    except json.JSONDecodeError as exc:
        raise QuotaFileError(f"{path} is not valid JSON: {exc}") from exc

    if not isinstance(document, dict):
        raise QuotaFileError(f"{path} must hold a JSON object")

    return QuotaPolicy(
        team_quotas=_read_team_quotas(document.get("team_quotas", {}), path),
        default_quota=_read_default_quota(document, path),
        exempt_paths=_read_exempt_paths(document.get("exempt_paths", []), path),
        source=path,
    )


def _read_team_quotas(raw: Any, path: Path) -> dict[str, int]:
    if not isinstance(raw, dict):
        raise QuotaFileError(f"{path}: 'team_quotas' must be an object")

    quotas: dict[str, int] = {}
    for team, size in raw.items():
        quotas[team] = _read_size(size, f"{path}: quota for team {team!r}")
    return quotas


def _read_default_quota(document: Mapping[str, Any], path: Path) -> int:
    if "default_quota" not in document:
        raise QuotaFileError(f"{path}: 'default_quota' is required")
    return _read_size(document["default_quota"], f"{path}: 'default_quota'")


def _read_exempt_paths(raw: Any, path: Path) -> tuple[str, ...]:
    if not isinstance(raw, list):
        raise QuotaFileError(f"{path}: 'exempt_paths' must be a list")

    exempt: list[str] = []
    for item in raw:
        if not isinstance(item, str):
            raise QuotaFileError(f"{path}: every exempt path must be a string, found {item!r}")
        exempt.append(_normalise(item))
    return tuple(exempt)


def _read_size(value: Any, label: str) -> int:
    """Read a quota size, which may be written as text such as `500G` or as a plain integer."""
    if isinstance(value, bool):
        raise QuotaFileError(f"{label} must be a size, found {value!r}")
    if isinstance(value, int):
        if value < 0:
            raise QuotaFileError(f"{label} must not be negative")
        return value
    if not isinstance(value, str):
        raise QuotaFileError(f"{label} must be a size, found {value!r}")

    try:
        return parse_size(value)
    except SizeFormatError as exc:
        raise QuotaFileError(f"{label}: {exc}") from exc


def _normalise(path: str) -> str:
    """Collapse `.`, `..` and repeated slashes so paths compare as written on one host."""
    return posixpath.normpath(path.strip()) if path.strip() else path
