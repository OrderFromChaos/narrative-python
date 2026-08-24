"""Hold the record types that more than one module of the reconciler names.

The two usage report formats do not carry the same fields. A `*.usage` file names no host and no
team, and a `*.usage.json` file names both. A record therefore makes `host` and `team` optional, and
each holds None when the file that gave the record does not name it. A check that needs a team skips
an entry that has none.

    /var/log/audit<TAB>12K       ->  UsageEntry(path=/var/log/audit, size=12288, team=None)
    {"path": "/srv/a", "bytes": 4096, "team": "search"}
                                 ->  UsageEntry(path=/srv/a, size=4096, team='search')

This module imports no other module of the package.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import NewType, Protocol


Bytes = NewType('Bytes', int)
HostName = NewType('HostName', str)
TeamName = NewType('TeamName', str)


class ReportFormat(Enum):
    """The usage report format that the name of a file selects."""

    TEXT = 'text'
    JSON = 'json'


class ReadOutcome(Enum):
    """What the reconciler got from one usage report file."""

    READ = 'read'
    DEGRADED = 'degraded'
    UNREADABLE = 'unreadable'


class SizeTextError(RuntimeError):
    """A size text does not hold a number and an optional unit suffix."""


class UsageReportError(RuntimeError):
    """A usage report file does not agree with its format."""


class InputDirectoryError(RuntimeError):
    """The input directory is absent, or it is not a directory."""


class QuotaFileError(RuntimeError):
    """The quota file is absent, or it holds a field of the wrong shape."""


@dataclass(frozen=True)
class UsageEntry:
    """One path that one host stores, and the size of that path."""

    path: Path
    size: Bytes
    team: TeamName | None


@dataclass(frozen=True)
class UsageReport:
    """The entries of one usage report file, and the count of the lines that the reader threw away."""

    source: Path
    host: HostName | None
    entries: tuple[UsageEntry, ...]
    rejected_lines: int


@dataclass(frozen=True)
class FileOutcome:
    """What one usage report file gave the reconciler.

    `report` holds None when, and only when, `outcome` is UNREADABLE. `detail` holds the reason for
    an UNREADABLE file and an empty string for every other outcome.
    """

    source: Path
    report_format: ReportFormat
    outcome: ReadOutcome
    report: UsageReport | None
    detail: str


@dataclass(frozen=True)
class PathUsage:
    """One path of one team, and the size of that path."""

    path: Path
    size: Bytes


@dataclass(frozen=True)
class TeamUsage:
    """The total that one team stores, the quota of that team, and the paths behind the total.

    `overage` holds the count of bytes above the quota, and holds 0 when the team is inside its
    quota. `paths` holds the largest path first.
    """

    team: TeamName
    used: Bytes
    quota: Bytes
    overage: Bytes
    paths: tuple[PathUsage, ...]


@dataclass(frozen=True)
class Reconciliation:
    """The result of one run over one input directory.

    `teams` holds the team with the largest total first. `overages` holds the same records for the
    teams above their quota only, and holds the worst overage first.
    """

    input_dir: Path
    teams: tuple[TeamUsage, ...]
    overages: tuple[TeamUsage, ...]
    unattributed_bytes: Bytes
    exempt_bytes: Bytes
    outcomes: tuple[FileOutcome, ...]


class ReportReader(Protocol):
    """Turn the text of one usage report file into a report.

    An implementation raises UsageReportError when the text does not agree with the format that the
    implementation reads. An implementation throws away a bad entry, counts it in `rejected_lines`,
    and reads the entries after it.
    """

    def __call__(self, report_path: Path, report_text: str) -> UsageReport: ...
