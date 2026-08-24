"""Every data type that the audit modules pass between them.

A type moves here as soon as it appears in a signature that crosses a module. The two parsers build
`DeclaredPackage`, the policy names a `Violation`, the store writes a `Finding` and the entry point
prints an `AuditReport`, so no single module owns these names. The failure types are shared in the
same way and live in `errors.py`, beside the helpers that build them.

The module holds no code, so it has no `### vocabulary` divider.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import NewType


PackageName = NewType('PackageName', str)
SourceName = NewType('SourceName', str)
VersionText = NewType('VersionText', str)


class ManifestFormat(Enum):
    REQUIREMENTS_LOCK = 'requirements_lock'
    PACKAGES_JSON = 'packages_json'


class Violation(Enum):
    BANNED = 'banned'
    BELOW_MINIMUM = 'below_minimum'
    DISALLOWED_SOURCE = 'disallowed_source'


@dataclass(frozen=True)
class DeclaredPackage:
    """One package that a manifest declares.

    A format that records no source supplies the source its own module assumes, so every package
    reaches the policy with all three fields filled.
    """

    name: PackageName
    version: VersionText
    source: SourceName


@dataclass(frozen=True)
class Policy:
    """The rules that every declared package must satisfy."""

    banned: frozenset[PackageName]
    minimum_versions: Mapping[PackageName, VersionText]
    allowed_sources: frozenset[SourceName]


@dataclass(frozen=True)
class Finding:
    """One package that broke one rule.

    The first four fields are the store key. A second run over an unchanged manifest produces the
    same four values and inserts nothing.
    """

    manifest: Path
    package: PackageName
    version: VersionText
    violation: Violation
    detail: str


@dataclass(frozen=True)
class ManifestOutcome:
    """What happened to one manifest file.

    `error` is `None` when the file parsed. A file that failed carries the reason and a count of 0,
    and the other manifests still run.
    """

    manifest: Path
    manifest_format: ManifestFormat | None
    packages_read: int
    findings: tuple[Finding, ...]
    error: str | None


@dataclass(frozen=True)
class AuditReport:
    """The result of one audit of one directory.

    Every finding hangs off the manifest it came from. `audit.everyFinding` gives the flat view.
    """

    manifest_directory: Path
    outcomes: tuple[ManifestOutcome, ...]
    findings_stored: int
