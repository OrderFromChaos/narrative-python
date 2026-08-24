"""Reconcile what a fleet of hosts reports that it stores against the quota of each team.

Call `reconcileDirectory` to reconcile one directory from another program:

    from pathlib import Path
    from quota_reconcile import reconcileDirectory

    result = reconcileDirectory(Path('fixture'), Path('fixture/quotas.json'))
    for team_usage in result.teams:
        print(team_usage.team, team_usage.over)

Run `python3 -m quota_reconcile <directory>` for the command-line tool.
"""

from __future__ import annotations

from quota_reconcile.json_report import writeJsonReport
from quota_reconcile.reconcile import reconcileDirectory
from quota_reconcile.store import OverageStore
from quota_reconcile.summary_table import formatSummaryTable
from quota_reconcile.vocabulary import (
    ByteCount,
    FileOutcome,
    HostName,
    MalformedEntryError,
    MalformedReportError,
    MalformedSizeError,
    PathUsage,
    QuotaFileError,
    QuotaPolicy,
    ReadStatus,
    ReconcileResult,
    ReportBatch,
    StoreError,
    TeamName,
    TeamUsage,
    UnattributedUsage,
    UsageEntry,
    UsageReport,
)


__all__ = [
    'ByteCount',
    'FileOutcome',
    'HostName',
    'MalformedEntryError',
    'MalformedReportError',
    'MalformedSizeError',
    'OverageStore',
    'PathUsage',
    'QuotaFileError',
    'QuotaPolicy',
    'ReadStatus',
    'ReconcileResult',
    'ReportBatch',
    'StoreError',
    'TeamName',
    'TeamUsage',
    'UnattributedUsage',
    'UsageEntry',
    'UsageReport',
    'formatSummaryTable',
    'reconcileDirectory',
    'writeJsonReport',
]
