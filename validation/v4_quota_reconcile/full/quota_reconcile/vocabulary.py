"""The records, the errors and the domain types that the modules of this package pass to each other.

Every record is frozen. A field is optional when one of the two usage report formats does not carry
it. Such a field holds `None`, and it never holds a value that the file did not state.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import NewType


ByteCount = NewType('ByteCount', int)
TeamName = NewType('TeamName', str)
HostName = NewType('HostName', str)


class ReadStatus(Enum):
    READ = 'read'
    REJECTED = 'rejected'


class QuotaFileError(RuntimeError):
    """The quota file does not state the quotas that the program must apply."""


class StoreError(RuntimeError):
    """The database does not accept the overages that the program found."""


class MalformedSizeError(RuntimeError):
    """A size does not state a count of bytes."""


class MalformedReportError(RuntimeError):
    """A usage report does not hold the format that its name declares."""


class MalformedEntryError(RuntimeError):
    """One entry of a usage report does not state a path and a size."""


@dataclass(frozen=True)
class QuotaPolicy:
    team_quotas: Mapping[TeamName, ByteCount]
    default_quota: ByteCount  # the quota of a team that team_quotas does not name
    exempt_paths: tuple[Path, ...]


@dataclass(frozen=True)
class UsageEntry:
    path: Path
    size: ByteCount
    team: TeamName | None  # the text format does not name a team
    host: HostName | None  # the text format does not name a host


@dataclass(frozen=True)
class UsageReport:
    source: Path
    host: HostName | None
    entries: tuple[UsageEntry, ...]
    rejected_lines: int


@dataclass(frozen=True)
class FileOutcome:
    source: Path
    status: ReadStatus
    entry_count: int
    rejected_lines: int
    detail: str  # why the program rejected the file, and empty when it read the file


@dataclass(frozen=True)
class ReportBatch:
    reports: tuple[UsageReport, ...]
    outcomes: tuple[FileOutcome, ...]


@dataclass(frozen=True)
class PathUsage:
    path: Path
    size: ByteCount
    host: HostName | None


@dataclass(frozen=True)
class TeamUsage:
    team: TeamName
    used: ByteCount
    quota: ByteCount
    over: ByteCount  # the bytes above the quota, and 0 when the team is within the quota
    paths: tuple[PathUsage, ...]  # largest first


@dataclass(frozen=True)
class UnattributedUsage:
    total: ByteCount
    entry_count: int


@dataclass(frozen=True)
class ReconcileResult:
    usage_dir: Path
    teams: tuple[TeamUsage, ...]  # worst overage first, then the teams within their quota
    unattributed: UnattributedUsage
    exempt_entries: int
    outcomes: tuple[FileOutcome, ...]
