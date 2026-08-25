"""Reconcile fleet storage usage against the quota each team is allowed.

    >>> from pathlib import Path
    >>> from quota_reconcile import reconcileDirectory
    >>> reconciliation = reconcileDirectory(Path('fixture'), Path('fixture/quotas.json'))
    >>> [(team.team, team.over_bytes) for team in reconciliation.selectTeamsOverQuota()]
    [('platform', 53687091200), ('archive', 21474836480)]

The call reads the report directory and the quota file, prints nothing and writes no file.
`quota_reconcile.__main__` adds the command-line tool, the SQLite store and the report files.
"""

from __future__ import annotations

from quota_reconcile.reconcile import PathUsage, Reconciliation, TeamUsage, reconcileDirectory
from quota_reconcile.reports import ReportOutcome, ReportStatus


__all__ = [
    'PathUsage',
    'Reconciliation',
    'ReportOutcome',
    'ReportStatus',
    'TeamUsage',
    'reconcileDirectory',
]
