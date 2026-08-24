"""Total the usage per team and compare each total against the quota of that team.

This module is the importable core. `reconcile_directory` does the whole job for one directory,
and `reconcile` does it for reports another program has already read.

Two rules decide where usage lands:

- An exempt path counts toward no team. A path under an exempt path is exempt as well.
- The text format names no team, so its entries go to one collecting team, `(unattributed)` by
  default. That team has no quota of its own, so it is measured against the default quota. Name
  another team with `unattributed_team` to send this usage there instead.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence

from .discovery import read_directory
from .model import PathUsage, Reconciliation, ReportOutcome, TeamUsage, UsageReport
from .quotas import QUOTA_FILE_NAME, QuotaPolicy, load_quotas

UNATTRIBUTED_TEAM = "(unattributed)"
"""Where usage from the text format lands, since that format names no owning team."""


def reconcile_directory(
    directory: Path,
    *,
    quotas_path: Path | None = None,
    unattributed_team: str = UNATTRIBUTED_TEAM,
) -> Reconciliation:
    """Read every usage report in `directory` and measure each team against its quota.

    The quota file is `quotas.json` inside `directory` unless `quotas_path` names another file.
    Raise `QuotaFileError` if that file cannot be used, and `NotADirectoryError` if the input
    directory is not there.
    """
    if not directory.is_dir():
        raise NotADirectoryError(f"{directory} is not a directory")

    policy = load_quotas(quotas_path or directory / QUOTA_FILE_NAME)
    reports, outcomes = read_directory(directory)
    return reconcile(
        reports,
        policy,
        outcomes=outcomes,
        input_dir=directory,
        unattributed_team=unattributed_team,
    )


def reconcile(
    reports: Iterable[UsageReport],
    policy: QuotaPolicy,
    *,
    outcomes: Sequence[ReportOutcome] = (),
    input_dir: Path | None = None,
    unattributed_team: str = UNATTRIBUTED_TEAM,
    generated_at: datetime | None = None,
) -> Reconciliation:
    """Total `reports` per team and rank the result, worst overage first."""
    totals: dict[str, dict[str, _PathTally]] = {}
    exempt_bytes = 0
    exempt_entries = 0

    for report in reports:
        for entry in report.entries:
            if policy.is_exempt(entry.path):
                exempt_bytes += entry.size_bytes
                exempt_entries += 1
                continue

            team = entry.team or unattributed_team
            tally = totals.setdefault(team, {}).setdefault(entry.path, _PathTally())
            tally.add(entry.size_bytes, entry.host)

    teams = tuple(
        sorted(
            (_team_usage(team, paths, policy) for team, paths in totals.items()),
            key=_team_rank,
        )
    )

    return Reconciliation(
        input_dir=input_dir if input_dir is not None else Path("."),
        generated_at=generated_at or datetime.now(timezone.utc),
        teams=teams,
        outcomes=tuple(outcomes),
        exempt_bytes=exempt_bytes,
        exempt_entries=exempt_entries,
        unattributed_team=unattributed_team,
        quota_source=policy.source,
    )


@dataclass(slots=True)
class _PathTally:
    """The running total for one path of one team, across every host that reported it."""

    size_bytes: int = 0
    hosts: set[str] = field(default_factory=set)

    def add(self, size_bytes: int, host: str | None) -> None:
        self.size_bytes += size_bytes
        if host:
            self.hosts.add(host)


def _team_usage(team: str, paths: dict[str, _PathTally], policy: QuotaPolicy) -> TeamUsage:
    """Build the result for one team, with its paths ranked by size."""
    ranked = tuple(
        PathUsage(path=path, size_bytes=tally.size_bytes, host_count=len(tally.hosts))
        for path, tally in sorted(
            paths.items(), key=lambda item: (-item[1].size_bytes, item[0])
        )
    )
    return TeamUsage(
        team=team,
        total_bytes=sum(tally.size_bytes for tally in paths.values()),
        quota_bytes=policy.quota_for(team),
        quota_is_default=not policy.has_own_quota(team),
        paths=ranked,
    )


def _team_rank(team: TeamUsage) -> tuple[int, float, str]:
    """Rank key: the worst overage first, then the fullest quota, then the team name."""
    return (-team.over_bytes, -team.usage_ratio, team.team)
