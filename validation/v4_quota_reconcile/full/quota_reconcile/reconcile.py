"""Reconcile the usage reports of one directory against one quota file.

A program that does not run the command-line tool calls `reconcileDirectory`:

    from pathlib import Path
    from quota_reconcile import reconcileDirectory

    result = reconcileDirectory(Path('fixture'), Path('fixture/quotas.json'))

The call reads the reports and totals them. It writes no file, it prints nothing, and it records
nothing in a database.
"""

from __future__ import annotations

from itertools import chain
from pathlib import Path

from quota_reconcile import overages, quotas, reports
from quota_reconcile.logs import LOG
from quota_reconcile.vocabulary import ReconcileResult


def reconcileDirectory(usage_dir: Path, quota_path: Path) -> ReconcileResult:
    """Total the usage of every report in the directory, and compare each total against its quota.

    Raises:
        QuotaFileError: The quota file is unreadable, or it states no usable quota. A malformed
            usage report raises nothing, because the result holds the outcome of every file.
    """
    policy = quotas.readQuotaPolicy(quota_path)
    batch = reports.readReports(usage_dir)

    entries = tuple(chain.from_iterable(report.entries for report in batch.reports))
    counted = tuple(entry for entry in entries if not quotas.exemptFromQuota(entry.path, policy))
    exempt_entries = len(entries) - len(counted)
    LOG.info('reports.totalled', extra={'entries': len(entries), 'exempt': exempt_entries})

    result = ReconcileResult(
        usage_dir=usage_dir,
        teams=overages.rankTeamUsage(counted, policy),
        unattributed=overages.totalUnattributedUsage(counted),
        exempt_entries=exempt_entries,
        outcomes=batch.outcomes,
    )
    return result
