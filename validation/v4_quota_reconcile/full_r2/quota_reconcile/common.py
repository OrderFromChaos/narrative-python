"""The types and the exceptions that the reconciler modules pass between them.

A record states only what its report carried, so a field that one report format names and the other
does not is optional.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import NewType


ByteCount = NewType('ByteCount', int)
HostName = NewType('HostName', str)
TeamName = NewType('TeamName', str)


class ReportFormat(Enum):
    """A usage report format, valued as the filename suffix that selects it."""

    TEXT = 'usage'
    JSON = 'usage.json'


class MalformedSizeError(RuntimeError):
    """A size does not read as a number with an optional unit suffix."""


class MalformedReportError(RuntimeError):
    """A usage report does not read as its format."""


class QuotaConfigError(RuntimeError):
    """The quota file does not state what the program was asked to do."""


@dataclass(frozen=True)
class UsageEntry:
    """One path that one host reports it is storing.

    `size` is a plain count of bytes. `team` and `host` are null when the report that gave the entry
    named neither.
    """

    path: Path
    size: ByteCount
    team: TeamName | None
    host: HostName | None


@dataclass(frozen=True)
class UsageReport:
    """Every entry that one report file carried."""

    source: Path
    entries: tuple[UsageEntry, ...]


@dataclass(frozen=True)
class FileOutcome:
    """What the scan made of one report file.

    `error` holds the rejection message, and is null when the file parsed. A rejected file
    contributes no entry, so `entry_count` is 0.
    """

    source: Path
    entry_count: int
    error: str | None


@dataclass(frozen=True)
class ScanResult:
    """Every report that parsed, beside an outcome for every report file that the scan opened."""

    reports: tuple[UsageReport, ...]
    outcomes: tuple[FileOutcome, ...]


@dataclass(frozen=True)
class TeamUsage:
    """What one team stores, against what that team is allowed.

    `overage` is 0 for a team within its quota. `paths` sorts by (-size, path).
    """

    team: TeamName
    used: ByteCount
    quota: ByteCount
    overage: ByteCount
    paths: tuple[UsageEntry, ...]


@dataclass(frozen=True)
class Reconciliation:
    """The result of one reconciliation run.

    `teams` sorts by (-overage, -used, team). `unattributed` totals the entries of the reports that
    named no team, which no quota covers. An exempt path reaches neither.
    """

    teams: tuple[TeamUsage, ...]
    unattributed: ByteCount
    outcomes: tuple[FileOutcome, ...]


@dataclass(frozen=True)
class QuotaPolicy:
    """What the quota file states about a team and about a path.

    A team that `team_quotas` does not name gets `default_quota`.
    """

    team_quotas: Mapping[TeamName, ByteCount]
    default_quota: ByteCount
    exempt_paths: tuple[Path, ...]

    def resolveQuota(self, team: TeamName) -> ByteCount:
        return self.team_quotas.get(team, self.default_quota)

    def exempt(self, path: Path) -> bool:
        return any(path == exempt or exempt in path.parents for exempt in self.exempt_paths)
