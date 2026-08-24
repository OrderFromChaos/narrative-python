"""Compare what each team stores against the quota of that team.

The team with the largest overage comes first, and every team within its quota comes after every
team above its quota. The paths of a team come largest first.

An entry that names no team counts toward no team. The reconciler reports those bytes on their own,
because the report of a team must hold only the bytes that a file gave to that team.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable

from quota_reconcile import quotas
from quota_reconcile.vocabulary import (
    ByteCount,
    PathUsage,
    QuotaPolicy,
    TeamName,
    TeamUsage,
    UnattributedUsage,
    UsageEntry,
)


def rankTeamUsage(entries: Iterable[UsageEntry], policy: QuotaPolicy) -> tuple[TeamUsage, ...]:
    by_team: dict[TeamName, list[UsageEntry]] = defaultdict(list)
    for entry in entries:
        if entry.team is not None:
            by_team[entry.team].append(entry)
    usage = [_computeTeamUsage(team, team_entries, policy) for team, team_entries in by_team.items()]
    return tuple(sorted(usage, key=lambda team_usage: (-team_usage.over, -team_usage.used, team_usage.team)))


def totalUnattributedUsage(entries: Iterable[UsageEntry]) -> UnattributedUsage:
    unattributed = [entry for entry in entries if entry.team is None]
    total = ByteCount(sum(entry.size for entry in unattributed))
    return UnattributedUsage(total=total, entry_count=len(unattributed))


def selectOverQuotaTeams(teams: Iterable[TeamUsage]) -> tuple[TeamUsage, ...]:
    return tuple(team_usage for team_usage in teams if team_usage.over > 0)


def _computeTeamUsage(team: TeamName, entries: Iterable[UsageEntry], policy: QuotaPolicy) -> TeamUsage:
    paths = [PathUsage(path=entry.path, size=entry.size, host=entry.host) for entry in entries]
    largest_first = sorted(paths, key=lambda path_usage: (-path_usage.size, str(path_usage.path)))
    used = ByteCount(sum(path_usage.size for path_usage in largest_first))
    quota = quotas.resolveQuota(team, policy)
    return TeamUsage(
        team=team,
        used=used,
        quota=quota,
        over=ByteCount(max(0, used - quota)),
        paths=tuple(largest_first),
    )
