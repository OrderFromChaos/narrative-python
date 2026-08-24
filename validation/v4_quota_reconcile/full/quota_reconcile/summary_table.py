"""Format the result of a reconciliation as a table for a terminal.

The table holds one row for each team, then the largest paths of each team above its quota, then the
bytes that no team owns, then the outcome of every file. Every size carries a unit suffix.
"""

from __future__ import annotations

from collections.abc import Iterable

from quota_reconcile import byte_size, overages
from quota_reconcile.vocabulary import (
    FileOutcome,
    PathUsage,
    ReadStatus,
    ReconcileResult,
    TeamUsage,
    UnattributedUsage,
)


_TOP_PATHS = 3
_TEAM_ROW = '{team:<24} {used:>10} {quota:>10} {over:>10} {paths:>6}'
_PATH_ROW = '    {size:>10}  {path:<44} {host}'
_FILE_ROW = '  {status:<10} {source:<26} {detail}'


def formatSummaryTable(result: ReconcileResult) -> str:
    sections = [
        _formatTeamSection(result.teams),
        _formatPathSection(result.teams),
        _formatUnattributedSection(result.unattributed, result.exempt_entries),
        _formatFileSection(result.outcomes),
    ]
    heading = f'QUOTA RECONCILIATION OF {result.usage_dir}'
    return '\n\n'.join([heading, *sections])


def _formatTeamSection(teams: Iterable[TeamUsage]) -> str:
    header = _TEAM_ROW.format(team='TEAM', used='USED', quota='QUOTA', over='OVER', paths='PATHS')
    rows = [
        _TEAM_ROW.format(
            team=team_usage.team,
            used=byte_size.formatByteSize(team_usage.used),
            quota=byte_size.formatByteSize(team_usage.quota),
            over=byte_size.formatByteSize(team_usage.over),
            paths=len(team_usage.paths),
        )
        for team_usage in teams
    ]
    if not rows:
        return 'TEAMS  no report named a team'
    return '\n'.join([header, *rows])


def _formatPathSection(teams: Iterable[TeamUsage]) -> str:
    rows: list[str] = []
    for team_usage in overages.selectOverQuotaTeams(teams):
        rows.append(f'  {team_usage.team} is over quota by {byte_size.formatByteSize(team_usage.over)}')
        rows.extend(_formatPathRow(path_usage) for path_usage in team_usage.paths[:_TOP_PATHS])

    if not rows:
        return 'OVER QUOTA  no team is over its quota'
    return '\n'.join(['OVER QUOTA', *rows])


def _formatUnattributedSection(unattributed: UnattributedUsage, exempt_entries: int) -> str:
    total = byte_size.formatByteSize(unattributed.total)
    return (
        f'UNATTRIBUTED  {total} in {unattributed.entry_count} entries that name no team\n'
        f'EXEMPT        {exempt_entries} entries below an exempt path'
    )


def _formatFileSection(outcomes: Iterable[FileOutcome]) -> str:
    rows = [_formatFileRow(outcome) for outcome in outcomes]
    if not rows:
        return 'FILES  the directory holds no usage report'
    return '\n'.join(['FILES', *rows])


def _formatPathRow(path_usage: PathUsage) -> str:
    host = path_usage.host if path_usage.host is not None else '-'
    size = byte_size.formatByteSize(path_usage.size)
    return _PATH_ROW.format(size=size, path=str(path_usage.path), host=host)


def _formatFileRow(outcome: FileOutcome) -> str:
    return _FILE_ROW.format(
        status=outcome.status.value,
        source=outcome.source.name,
        detail=_describeOutcome(outcome),
    )


def _describeOutcome(outcome: FileOutcome) -> str:
    match outcome.status:
        case ReadStatus.READ:
            return f'{outcome.entry_count} entries, {outcome.rejected_lines} rejected'
        case ReadStatus.REJECTED:
            return outcome.detail
