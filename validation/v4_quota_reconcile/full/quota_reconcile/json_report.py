"""Write the result of a reconciliation as one JSON file.

The file holds one object with these fields:

    {"usage_dir": ..., "teams": [...], "over_quota": [...], "unattributed": {...}, "files": [...]}

Every size is a plain count of bytes, thus a program that reads the file needs no unit table. A host
field holds `null` when the report that gave the entry named no host.
"""

from __future__ import annotations

import json
from pathlib import Path

from quota_reconcile import overages
from quota_reconcile.logs import LOG
from quota_reconcile.vocabulary import FileOutcome, PathUsage, ReconcileResult, TeamUsage


def writeJsonReport(report_path: Path, result: ReconcileResult) -> None:
    INDENT_SPACES = 2
    document = {
        'usage_dir': str(result.usage_dir),
        'teams': [_teamPayload(team_usage) for team_usage in result.teams],
        'over_quota': [team_usage.team for team_usage in overages.selectOverQuotaTeams(result.teams)],
        'unattributed': {'bytes': result.unattributed.total, 'entries': result.unattributed.entry_count},
        'exempt_entries': result.exempt_entries,
        'files': [_outcomePayload(outcome) for outcome in result.outcomes],
    }
    report_path.write_text(json.dumps(document, indent=INDENT_SPACES) + '\n', encoding='utf-8')
    LOG.info('report.written', extra={'report': str(report_path), 'teams': len(result.teams)})


def _teamPayload(team_usage: TeamUsage) -> dict[str, object]:
    return {
        'team': team_usage.team,
        'used_bytes': team_usage.used,
        'quota_bytes': team_usage.quota,
        'over_bytes': team_usage.over,
        'paths': [_pathPayload(path_usage) for path_usage in team_usage.paths],
    }


def _pathPayload(path_usage: PathUsage) -> dict[str, object]:
    return {'path': str(path_usage.path), 'bytes': path_usage.size, 'host': path_usage.host}


def _outcomePayload(outcome: FileOutcome) -> dict[str, object]:
    return {
        'source': str(outcome.source),
        'status': outcome.status.value,
        'entries': outcome.entry_count,
        'rejected_entries': outcome.rejected_lines,
        'detail': outcome.detail,
    }
