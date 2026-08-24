"""Reconcile the storage a fleet of hosts reports against the quota of each team.

Read two report formats from one directory, total the usage per team, rank the teams that are
over quota, keep every overage in SQLite and write a JSON report.

The command-line tool is one caller of this package. Another program does the same job like this:

    from pathlib import Path
    from quota_reconcile import OverageStore, reconcile_directory, write_report

    result = reconcile_directory(Path("reports"))
    for team in result.overages:
        print(team.team, team.over_bytes)

    with OverageStore(Path("overages.sqlite3")) as store:
        store.record(result)
    write_report(result, Path("quota-report.json"))
"""

from __future__ import annotations

from .discovery import find_reports, read_directory, read_report
from .errors import (
    MalformedReportError,
    QuotaFileError,
    QuotaReconcileError,
    SizeFormatError,
)
from .model import (
    PathUsage,
    Reconciliation,
    ReportOutcome,
    TeamUsage,
    UsageEntry,
    UsageReport,
)
from .quotas import QUOTA_FILE_NAME, QuotaPolicy, load_quotas
from .reconcile import UNATTRIBUTED_TEAM, reconcile, reconcile_directory
from .report import build_report, render_outcomes, render_table, write_report
from .sizes import format_size, parse_size
from .store import OverageStore, StoreResult, fingerprint_of

__version__ = "1.0.0"

__all__ = [
    "MalformedReportError",
    "OverageStore",
    "PathUsage",
    "QUOTA_FILE_NAME",
    "QuotaFileError",
    "QuotaPolicy",
    "QuotaReconcileError",
    "Reconciliation",
    "ReportOutcome",
    "SizeFormatError",
    "StoreResult",
    "TeamUsage",
    "UNATTRIBUTED_TEAM",
    "UsageEntry",
    "UsageReport",
    "__version__",
    "build_report",
    "find_reports",
    "fingerprint_of",
    "format_size",
    "load_quotas",
    "parse_size",
    "read_directory",
    "read_report",
    "reconcile",
    "reconcile_directory",
    "render_outcomes",
    "render_table",
    "write_report",
]
