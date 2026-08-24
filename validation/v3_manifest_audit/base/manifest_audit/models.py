"""Data types shared by every part of the auditor.

This module holds no logic beyond field validation and small derived values, so
that the readers, the policy, the store and the report can all depend on it
without depending on each other.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

__all__ = [
    "Finding",
    "FindingKind",
    "ManifestError",
    "ManifestOutcome",
    "ManifestStatus",
    "Package",
    "AuditResult",
    "normalize_name",
]

_NAME_SEPARATORS = re.compile(r"[-_.]+")


def normalize_name(name: str) -> str:
    """Fold a package name to the form used for policy lookups.

    Names are compared case-insensitively, and runs of ``-``, ``_`` and ``.``
    are equivalent. This follows the PEP 503 rule, which also gives sensible
    results for the JavaScript-style names that appear in ``packages.json``.
    """
    return _NAME_SEPARATORS.sub("-", name.strip().lower())


class ManifestError(Exception):
    """A manifest could not be read.

    The auditor catches this per manifest, so one bad file does not stop the
    others.
    """

    def __init__(self, path: str, message: str) -> None:
        super().__init__(f"{path}: {message}")
        self.path = path
        self.message = message


class FindingKind(str, Enum):
    """The rule that a package broke."""

    BANNED = "banned_package"
    BELOW_MINIMUM = "below_minimum_version"
    DISALLOWED_SOURCE = "disallowed_source"
    UNREADABLE_VERSION = "unreadable_version"

    def __str__(self) -> str:
        return self.value


class ManifestStatus(str, Enum):
    """Whether a manifest was read."""

    OK = "ok"
    FAILED = "failed"

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class Package:
    """One declared dependency, as read from a manifest."""

    name: str
    version: str
    source: str | None
    manifest: str
    location: str

    @property
    def key(self) -> str:
        """The normalized name, for policy lookups."""
        return normalize_name(self.name)


@dataclass(frozen=True, slots=True)
class Finding:
    """One policy break, for one package, in one manifest."""

    manifest: str
    package: str
    version: str
    source: str | None
    kind: FindingKind
    detail: str
    location: str

    @property
    def is_banned(self) -> bool:
        return self.kind is FindingKind.BANNED

    def to_dict(self) -> dict[str, object]:
        return {
            "manifest": self.manifest,
            "package": self.package,
            "version": self.version,
            "source": self.source,
            "kind": self.kind.value,
            "detail": self.detail,
            "location": self.location,
        }


@dataclass(frozen=True, slots=True)
class ManifestOutcome:
    """What happened to one manifest during a run."""

    path: str
    format: str
    status: ManifestStatus
    package_count: int = 0
    finding_count: int = 0
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.status is ManifestStatus.OK

    def to_dict(self) -> dict[str, object]:
        return {
            "manifest": self.path,
            "format": self.format,
            "status": self.status.value,
            "packages": self.package_count,
            "findings": self.finding_count,
            "error": self.error,
        }


@dataclass(frozen=True, slots=True)
class AuditResult:
    """Everything one audit produced."""

    root: str
    policy_path: str | None
    outcomes: tuple[ManifestOutcome, ...] = ()
    findings: tuple[Finding, ...] = ()

    @property
    def banned_findings(self) -> tuple[Finding, ...]:
        return tuple(finding for finding in self.findings if finding.is_banned)

    @property
    def has_banned(self) -> bool:
        return any(finding.is_banned for finding in self.findings)

    @property
    def failed_manifests(self) -> tuple[ManifestOutcome, ...]:
        return tuple(outcome for outcome in self.outcomes if not outcome.ok)

    @property
    def package_count(self) -> int:
        return sum(outcome.package_count for outcome in self.outcomes)

    def counts_by_kind(self) -> dict[str, int]:
        """Finding totals, one entry per kind that occurred, largest first."""
        counts: dict[str, int] = {}
        for finding in self.findings:
            counts[finding.kind.value] = counts.get(finding.kind.value, 0) + 1
        return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))
