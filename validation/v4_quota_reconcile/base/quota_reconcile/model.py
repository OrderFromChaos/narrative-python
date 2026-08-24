"""The data the reconciler moves between its stages.

Every type here is frozen. A reader turns a file into a `UsageReport`, the reconciler turns
reports into a `Reconciliation`, and the store and the report writer read that result.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal

ReportStatus = Literal["ok", "partial", "failed"]
"""`ok`: every line was read. `partial`: some lines were dropped. `failed`: nothing was read."""


@dataclass(frozen=True, slots=True)
class UsageEntry:
    """One path on one host, and the space it takes."""

    path: str
    size_bytes: int
    team: str | None
    host: str | None
    source: str


@dataclass(frozen=True, slots=True)
class UsageReport:
    """The result of reading one usage report file.

    `problems` holds one message per line that the reader dropped. A report with entries and
    problems is a partial read: the good lines still count.
    """

    source: Path
    host: str | None
    entries: tuple[UsageEntry, ...] = ()
    problems: tuple[str, ...] = ()

    @property
    def status(self) -> ReportStatus:
        if not self.problems:
            return "ok"
        return "partial" if self.entries else "failed"

    @property
    def total_bytes(self) -> int:
        return sum(entry.size_bytes for entry in self.entries)


@dataclass(frozen=True, slots=True)
class ReportOutcome:
    """What happened to one report file, for the per-file summary."""

    source: Path
    status: ReportStatus
    entry_count: int
    byte_count: int
    problems: tuple[str, ...] = ()

    @classmethod
    def from_report(cls, report: UsageReport) -> ReportOutcome:
        return cls(
            source=report.source,
            status=report.status,
            entry_count=len(report.entries),
            byte_count=report.total_bytes,
            problems=report.problems,
        )

    @classmethod
    def failure(cls, source: Path, reason: str) -> ReportOutcome:
        return cls(source=source, status="failed", entry_count=0, byte_count=0, problems=(reason,))


@dataclass(frozen=True, slots=True)
class PathUsage:
    """One path a team owns, with the space it takes on every host that reported it."""

    path: str
    size_bytes: int
    host_count: int


@dataclass(frozen=True, slots=True)
class TeamUsage:
    """What one team stores, next to what it is allowed to store."""

    team: str
    total_bytes: int
    quota_bytes: int
    quota_is_default: bool
    paths: tuple[PathUsage, ...] = ()

    @property
    def over_bytes(self) -> int:
        """Bytes above quota, or 0 for a team that is within quota."""
        return max(0, self.total_bytes - self.quota_bytes)

    @property
    def is_over_quota(self) -> bool:
        return self.total_bytes > self.quota_bytes

    @property
    def usage_ratio(self) -> float:
        """Usage as a fraction of quota. A zero quota with any usage reads as infinite."""
        if self.quota_bytes > 0:
            return self.total_bytes / self.quota_bytes
        return float("inf") if self.total_bytes else 0.0


@dataclass(frozen=True, slots=True)
class Reconciliation:
    """Everything one run found.

    `teams` is ranked worst first, so the over-quota teams lead the list and `overages` is its
    leading slice.
    """

    input_dir: Path
    generated_at: datetime
    teams: tuple[TeamUsage, ...] = ()
    outcomes: tuple[ReportOutcome, ...] = ()
    exempt_bytes: int = 0
    exempt_entries: int = 0
    unattributed_team: str = ""
    quota_source: Path | None = None

    @property
    def overages(self) -> tuple[TeamUsage, ...]:
        """The over-quota teams, worst overage first."""
        return tuple(team for team in self.teams if team.is_over_quota)

    @property
    def has_overage(self) -> bool:
        return any(team.is_over_quota for team in self.teams)

    @property
    def failed_reports(self) -> tuple[ReportOutcome, ...]:
        return tuple(outcome for outcome in self.outcomes if outcome.status == "failed")

    @property
    def partial_reports(self) -> tuple[ReportOutcome, ...]:
        return tuple(outcome for outcome in self.outcomes if outcome.status == "partial")

    @property
    def counted_bytes(self) -> int:
        return sum(team.total_bytes for team in self.teams)
