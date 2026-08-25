"""Total the usage of every team against its quota, and rank what is over.

    Reconciliation(teams=(TeamUsage(team='search', used=2528876743884, quota=2199023255552,
                                    overage=329853488332, paths=(...)), ...),
                   unattributed=2449477632, outcomes=(...))

An exempt path counts toward no total. An entry from a report that named no team counts toward
`unattributed` and toward no quota. Teams sort by (-overage, -used, team).
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path

from quota_reconcile import quotas, scan
from quota_reconcile.common import ByteCount, QuotaPolicy, Reconciliation, TeamName, TeamUsage, UsageEntry


def reconcileUsage(input_dir: Path, quota_json_path: Path) -> Reconciliation:
    """Read the quota file and every usage report under `input_dir`, and reconcile the two.

    Raises:
        QuotaConfigError: the quota file is absent or malformed. A malformed usage report is
            reported as an outcome instead, and does not raise.
    """
    policy = quotas.readPolicy(quota_json_path)
    scan_result = scan.readReports(input_dir)

    counted: list[UsageEntry] = []
    for report in scan_result.reports:
        counted.extend(entry for entry in report.entries if not policy.exempt(entry.path))

    unattributed = ByteCount(sum(entry.size for entry in counted if entry.team is None))
    reconciliation = Reconciliation(
        teams=rankTeams(counted, policy),
        unattributed=unattributed,
        outcomes=scan_result.outcomes,
    )
    return reconciliation


def rankTeams(entries: Iterable[UsageEntry], policy: QuotaPolicy) -> tuple[TeamUsage, ...]:
    entries_by_team: dict[TeamName, list[UsageEntry]] = defaultdict(list)
    for entry in entries:
        if entry.team is not None:
            entries_by_team[entry.team].append(entry)

    usages = [_summariseTeam(team, team_entries, policy) for team, team_entries in entries_by_team.items()]
    usages.sort(key=lambda usage: (-usage.overage, -usage.used, usage.team))
    return tuple(usages)


def _summariseTeam(team: TeamName, entries: Iterable[UsageEntry], policy: QuotaPolicy) -> TeamUsage:
    ranked = sorted(entries, key=lambda entry: (-entry.size, entry.path))
    used = ByteCount(sum(entry.size for entry in ranked))
    quota = policy.resolveQuota(team)

    overage = ByteCount(max(0, used - quota))
    usage = TeamUsage(team=team, used=used, quota=quota, overage=overage, paths=tuple(ranked))
    return usage
