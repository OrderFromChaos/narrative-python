"""Render a reconciliation as a table for a terminal, and as a JSON file.

    TEAM                  USED     QUOTA   OVERAGE
    search                2.3T      2.0T    307.2G
    archive              12.0G    100.0G         -

    UNATTRIBUTED          2.3G

    search over quota by 307.2G, largest paths:
          1.2T  /srv/index/shard-0

    FILE                  OUTCOME   DETAIL
    store-01.usage        read      4 entries
    store-04.usage        rejected  store-04.usage:3: unusable size '12X'

A team within its quota shows `-` and lists no path. The JSON report carries the same numbers as
plain byte counts, under `teams`, `unattributed_bytes` and `files`.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path

from quota_reconcile.common import FileOutcome, Reconciliation, TeamUsage
from quota_reconcile.sizes import formatSize


_TEAM_WIDTH = 16
_SIZE_WIDTH = 10
_STATUS_WIDTH = 10
_SOURCE_WIDTH = 22
_WITHIN_QUOTA = '-'


def formatTable(reconciliation: Reconciliation) -> str:
    lines = [_formatRow('TEAM', ('USED', 'QUOTA', 'OVERAGE'))]
    for usage in reconciliation.teams:
        overage = formatSize(usage.overage) if usage.overage else _WITHIN_QUOTA
        lines.append(_formatRow(usage.team, (formatSize(usage.used), formatSize(usage.quota), overage)))

    lines.append('')
    lines.append(_formatRow('UNATTRIBUTED', (formatSize(reconciliation.unattributed),)))
    lines.extend(_formatPathLines(reconciliation.teams))
    lines.extend(_formatOutcomeLines(reconciliation.outcomes))

    table = '\n'.join(lines)
    return table


def writeJsonReport(reconciliation: Reconciliation, report_json_path: Path) -> None:
    document = {
        'teams': [_teamRecord(usage) for usage in reconciliation.teams],
        'unattributed_bytes': reconciliation.unattributed,
        'files': [_fileRecord(outcome) for outcome in reconciliation.outcomes],
    }
    report_json_path.write_text(json.dumps(document, indent=2) + '\n', encoding='utf-8')


def _formatRow(team: str, cells: Iterable[str]) -> str:
    return f'{team:<{_TEAM_WIDTH}}' + ''.join(f'{cell:>{_SIZE_WIDTH}}' for cell in cells)


def _formatPathLines(teams: Iterable[TeamUsage]) -> list[str]:
    LARGEST_PATHS = 3
    lines: list[str] = []
    for usage in teams:
        if not usage.overage:
            continue

        lines.append('')
        lines.append(f'{usage.team} over quota by {formatSize(usage.overage)}, largest paths:')
        lines.extend(f'{formatSize(entry.size):>{_SIZE_WIDTH}}  {entry.path}' for entry in usage.paths[:LARGEST_PATHS])

    return lines


def _formatOutcomeLines(outcomes: Iterable[FileOutcome]) -> list[str]:
    lines = ['', _formatOutcomeRow('FILE', 'OUTCOME', 'DETAIL')]
    for outcome in outcomes:
        detail = outcome.error if outcome.error is not None else f'{outcome.entry_count} entries'
        status = 'rejected' if outcome.error is not None else 'read'
        lines.append(_formatOutcomeRow(outcome.source.name, status, detail))

    return lines


def _formatOutcomeRow(source: str, status: str, detail: str) -> str:
    return f'{source:<{_SOURCE_WIDTH}}{status:<{_STATUS_WIDTH}}{detail}'


def _teamRecord(usage: TeamUsage) -> dict[str, object]:
    return {
        'team': usage.team,
        'used_bytes': usage.used,
        'quota_bytes': usage.quota,
        'overage_bytes': usage.overage,
        'paths': [{'path': str(entry.path), 'bytes': entry.size, 'host': entry.host} for entry in usage.paths],
    }


def _fileRecord(outcome: FileOutcome) -> dict[str, object]:
    return {'source': str(outcome.source), 'entry_count': outcome.entry_count, 'error': outcome.error}
