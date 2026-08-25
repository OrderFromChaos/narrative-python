"""Total the usage of every team, compare each total against its quota, and rank the overages.

    TeamUsage(team='platform', used_bytes=590558003200, quota_bytes=536870912000, over_bytes=53687091200,
              paths=(PathUsage(path=PosixPath('/srv/build/artifacts'), size_bytes=322122547200), ...))

Teams sort by (-over_bytes, -used_bytes, team); the paths inside a team sort by (-size_bytes,
path). `over_bytes` is 0 for a team within its quota. Two reports that name the same path for the
same team give one PathUsage carrying the sum. An exempt path counts toward no team, and so does
an entry that names no team; those bytes are totalled separately. The exempt test runs first, so
an exempt path that names no team counts as exempt and not as unattributed.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from itertools import chain
from pathlib import Path

from quota_reconcile.entries import TeamName, UsageEntry
from quota_reconcile.quotas import QuotaPolicy, readQuotaPolicy
from quota_reconcile.reports import ReportOutcome, readReportDirectory
from quota_reconcile.sizes import ByteCount


def reconcileDirectory(reports_dir: Path, quota_json_path: Path) -> Reconciliation:
    """Read a directory of usage reports and a quota file, and reconcile one against the other.

    Raises:
        QuotaFileError: the quota file does not state a policy the program can apply.
        OSError: the quota file or the directory could not be read. An unreadable report inside
            the directory is an outcome rather than a raise.
    """
    policy = readQuotaPolicy(quota_json_path)
    outcomes = readReportDirectory(reports_dir)
    return reconcileReports(outcomes, policy)


def reconcileReports(outcomes: Sequence[ReportOutcome], policy: QuotaPolicy) -> Reconciliation:
    """Apply a QuotaPolicy to the entries that a directory of reports yielded."""
    entries_by_team: dict[TeamName, list[UsageEntry]] = defaultdict(list)
    exempt_bytes = 0
    unattributed_bytes = 0
    for entry in chain.from_iterable(outcome.entries for outcome in outcomes):
        if policy.exempt(entry.path):
            exempt_bytes += entry.size_bytes
        elif entry.team is None:
            unattributed_bytes += entry.size_bytes
        else:
            entries_by_team[entry.team].append(entry)

    teams = sorted(
        (buildTeamUsage(team, team_entries, policy) for team, team_entries in entries_by_team.items()),
        key=lambda usage: (-usage.over_bytes, -usage.used_bytes, usage.team),
    )
    return Reconciliation(
        teams=tuple(teams),
        exempt_bytes=ByteCount(exempt_bytes),
        unattributed_bytes=ByteCount(unattributed_bytes),
        outcomes=tuple(outcomes),
    )


def buildTeamUsage(team: TeamName, entries: Iterable[UsageEntry], policy: QuotaPolicy) -> TeamUsage:
    sizes_by_path: dict[Path, int] = defaultdict(int)
    for entry in entries:
        sizes_by_path[entry.path] += entry.size_bytes

    paths = sorted(
        (PathUsage(path, ByteCount(size)) for path, size in sizes_by_path.items()),
        key=lambda usage: (-usage.size_bytes, usage.path),
    )
    used_bytes = ByteCount(sum(usage.size_bytes for usage in paths))
    quota_bytes = policy.resolveQuota(team)
    over_bytes = ByteCount(max(used_bytes - quota_bytes, 0))
    return TeamUsage(team, used_bytes, quota_bytes, over_bytes, tuple(paths))


### vocabulary #########################################################################


@dataclass(frozen=True)
class PathUsage:
    path: Path
    size_bytes: ByteCount


@dataclass(frozen=True)
class TeamUsage:
    team: TeamName
    used_bytes: ByteCount
    quota_bytes: ByteCount
    over_bytes: ByteCount
    paths: tuple[PathUsage, ...]

    def overQuota(self) -> bool:
        return self.over_bytes > 0


@dataclass(frozen=True)
class Reconciliation:
    teams: tuple[TeamUsage, ...]
    exempt_bytes: ByteCount
    unattributed_bytes: ByteCount
    outcomes: tuple[ReportOutcome, ...]

    def selectTeamsOverQuota(self) -> tuple[TeamUsage, ...]:
        return tuple(team for team in self.teams if team.overQuota())
