"""Render a Reconciliation as a terminal table and as a JSON document.

    TEAM                      USED     QUOTA   OVERAGE
    platform                550.0G    500.0G     50.0G
    search                    1.2T      2.0T         -

    OVER QUOTA  platform  by 50.0G
        300.0G  /srv/build/artifacts

    exempt                    5.0G
    unattributed              2.3G

    REPORT              STATUS      DETAIL
    node-a.usage        read        entries=4
    node-c.usage        malformed   line 3: expected 2 tab-separated fields

A team within its quota shows `-` for its overage. The detail block covers only the teams over
quota, and lists only their largest paths. Both calls write no file and print nothing.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Sequence

from quota_reconcile.reconcile import Reconciliation, TeamUsage
from quota_reconcile.reports import ReportOutcome
from quota_reconcile.sizes import formatSizeText


TEAM_WIDTH = 20
SIZE_WIDTH = 10
NAME_WIDTH = 20
STATUS_WIDTH = 12
LARGEST_PATHS_SHOWN = 3


def formatReconciliationTable(reconciliation: Reconciliation) -> str:
    lines = formatTeamTable(reconciliation.teams)
    lines.extend(formatOverageDetail(reconciliation.selectTeamsOverQuota()))

    # bytes that no team total carries
    lines.append('')
    lines.append(formatRow(('exempt', formatSizeText(reconciliation.exempt_bytes))))
    lines.append(formatRow(('unattributed', formatSizeText(reconciliation.unattributed_bytes))))

    lines.extend(formatOutcomeLines(reconciliation.outcomes))
    return '\n'.join(lines)


def formatTeamTable(teams: Iterable[TeamUsage]) -> list[str]:
    WITHIN_QUOTA_MARK = '-'

    lines = [formatRow(('TEAM', 'USED', 'QUOTA', 'OVERAGE'))]
    for team in teams:
        overage = formatSizeText(team.over_bytes) if team.overQuota() else WITHIN_QUOTA_MARK
        used = formatSizeText(team.used_bytes)
        quota = formatSizeText(team.quota_bytes)
        lines.append(formatRow((team.team, used, quota, overage)))
    return lines


def formatOverageDetail(teams: Iterable[TeamUsage]) -> list[str]:
    lines: list[str] = []
    for team in teams:
        lines.append('')
        lines.append(f'OVER QUOTA  {team.team}  by {formatSizeText(team.over_bytes)}')
        for usage in team.paths[:LARGEST_PATHS_SHOWN]:
            lines.append(f'{formatSizeText(usage.size_bytes):>{SIZE_WIDTH}}  {usage.path}')
    return lines


def formatOutcomeLines(outcomes: Iterable[ReportOutcome]) -> list[str]:
    header = 'REPORT'.ljust(NAME_WIDTH) + 'STATUS'.ljust(STATUS_WIDTH) + 'DETAIL'

    lines = ['', header]
    for outcome in outcomes:
        detail = outcome.detail or f'entries={len(outcome.entries)}'
        lines.append(outcome.report_path.name.ljust(NAME_WIDTH) + outcome.status.value.ljust(STATUS_WIDTH) + detail)
    return lines


def formatRow(cells: Sequence[str]) -> str:
    team, *sizes = cells
    return team.ljust(TEAM_WIDTH) + ''.join(size.rjust(SIZE_WIDTH) for size in sizes)


def buildJsonReport(reconciliation: Reconciliation) -> str:
    INDENT = 2

    document = {
        'teams': [buildTeamDocument(team) for team in reconciliation.teams],
        'exempt_bytes': reconciliation.exempt_bytes,
        'unattributed_bytes': reconciliation.unattributed_bytes,
        'reports': [buildReportDocument(outcome) for outcome in reconciliation.outcomes],
    }
    return json.dumps(document, indent=INDENT) + '\n'


def buildTeamDocument(team: TeamUsage) -> dict[str, object]:
    return {
        'team': team.team,
        'used_bytes': team.used_bytes,
        'quota_bytes': team.quota_bytes,
        'over_bytes': team.over_bytes,
        'paths': [{'path': str(usage.path), 'size_bytes': usage.size_bytes} for usage in team.paths],
    }


def buildReportDocument(outcome: ReportOutcome) -> dict[str, object]:
    return {
        'report': str(outcome.report_path),
        'status': outcome.status.value,
        'entry_count': len(outcome.entries),
        'detail': outcome.detail,
    }
