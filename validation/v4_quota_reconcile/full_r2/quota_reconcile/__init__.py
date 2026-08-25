"""Reconcile what a fleet of hosts reports it is storing against the quota each team is allowed.

    from pathlib import Path

    from quota_reconcile import reconcileUsage

    reconciliation = reconcileUsage(Path('fixture'), Path('fixture/quotas.json'))

The call writes no file, prints nothing and records nothing. `python3 -m quota_reconcile` is the
command-line tool over the same call.
"""

from __future__ import annotations

from quota_reconcile.common import (
    ByteCount,
    FileOutcome,
    HostName,
    MalformedReportError,
    MalformedSizeError,
    QuotaConfigError,
    QuotaPolicy,
    Reconciliation,
    ReportFormat,
    ScanResult,
    TeamName,
    TeamUsage,
    UsageEntry,
    UsageReport,
)
from quota_reconcile.reconcile import rankTeams, reconcileUsage


__all__ = [
    'ByteCount',
    'FileOutcome',
    'HostName',
    'MalformedReportError',
    'MalformedSizeError',
    'QuotaConfigError',
    'QuotaPolicy',
    'Reconciliation',
    'ReportFormat',
    'ScanResult',
    'TeamName',
    'TeamUsage',
    'UsageEntry',
    'UsageReport',
    'rankTeams',
    'reconcileUsage',
]
