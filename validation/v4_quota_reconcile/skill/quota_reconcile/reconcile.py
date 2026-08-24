"""Total the usage of each team, and compare each total against the quota of that team.

A program that does not run the command-line tool calls `reconcileDirectory`:

    from pathlib import Path
    from quota_reconcile.reconcile import reconcileDirectory

    result = reconcileDirectory(Path('fixture'), Path('fixture/quotas.json'))
    for team in result.overages:
        print(team.team, team.overage)

An exempt path counts toward no total. An entry that names no team counts toward no team total
either, because the text report format carries no team and the reconciler adds no team of its own.
The result counts those bytes apart, in `unattributed_bytes`, so that an operator can see them.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Iterable
from operator import attrgetter
from pathlib import Path

from quota_reconcile.quotas import QuotaPolicy, readQuotaFile
from quota_reconcile.usage_reports import readUsageReports
from quota_reconcile.vocabulary import (
    Bytes,
    FileOutcome,
    InputDirectoryError,
    PathUsage,
    Reconciliation,
    TeamName,
    TeamUsage,
)


LOG = logging.getLogger(__name__)


def reconcileDirectory(input_dir: Path, quota_json_path: Path) -> Reconciliation:
    """Read the quota file and every usage report in a directory, then reconcile the two.

    Raises:
        InputDirectoryError: the input directory is absent, or it is not a directory.
        QuotaFileError: the quota file is absent, or it holds a bad field.
    """
    if not input_dir.is_dir():
        raise rejectInputDirectory(input_dir)

    policy = readQuotaFile(quota_json_path)
    outcomes = readUsageReports(input_dir)
    return reconcileOutcomes(input_dir, policy, outcomes)


def reconcileOutcomes(input_dir: Path, policy: QuotaPolicy, outcomes: Iterable[FileOutcome]) -> Reconciliation:
    """Total the entries of every report the reader could read, and rank each team against its quota.

    Returns:
        A result whose `teams` holds the largest total first, and whose `overages` holds the worst
        overage first. `overages` holds the same records as `teams`, for the teams above quota only.
    """
    file_outcomes = tuple(outcomes)
    used_by_team: TeamTotals = defaultdict(int)
    paths_by_team: TeamPaths = defaultdict(list)
    unattributed = 0
    exempt = 0

    # total every entry of every report that the reader could read
    for outcome in file_outcomes:
        if outcome.report is None:
            continue
        for entry in outcome.report.entries:
            if policy.exempt(entry.path):
                exempt += entry.size
            elif entry.team is None:
                unattributed += entry.size
            else:
                used_by_team[entry.team] += entry.size
                paths_by_team[entry.team].append(PathUsage(entry.path, entry.size))

    teams = rankTeamUsage(policy, used_by_team, paths_by_team)
    overages = tuple(sorted((team for team in teams if team.overage > 0), key=attrgetter('overage'), reverse=True))
    LOG.info(
        'reconcile.totalled',
        extra={'teams': len(teams), 'over_quota': len(overages), 'unattributed': unattributed, 'exempt': exempt},
    )

    return Reconciliation(
        input_dir=input_dir,
        teams=teams,
        overages=overages,
        unattributed_bytes=Bytes(unattributed),
        exempt_bytes=Bytes(exempt),
        outcomes=file_outcomes,
    )


def rankTeamUsage(policy: QuotaPolicy, used_by_team: TeamTotals, paths_by_team: TeamPaths) -> tuple[TeamUsage, ...]:
    """Turn the totals of every team into ranked records.

    Returns:
        One record per team, largest total first, and the paths of each team largest first.
    """
    teams: list[TeamUsage] = []
    for team, used in used_by_team.items():
        quota = policy.resolveQuota(team)
        paths = tuple(sorted(paths_by_team[team], key=attrgetter('size'), reverse=True))
        overage = Bytes(max(0, used - quota))
        teams.append(TeamUsage(team=team, used=Bytes(used), quota=quota, overage=overage, paths=paths))
    return tuple(sorted(teams, key=attrgetter('used'), reverse=True))


def rejectInputDirectory(input_dir: Path) -> InputDirectoryError:
    LOG.error('input.rejected', extra={'input_dir': str(input_dir)})
    return InputDirectoryError(f'{input_dir}: the input directory is absent, or it is not a directory')


### vocabulary #########################################################################


TeamTotals = dict[TeamName, int]
TeamPaths = dict[TeamName, list[PathUsage]]
