"""Reconcile a cloud bill against an asset scan and report every mismatch.

The reconciliation is a join, not a total. Every billing line matches at most
one scanned resource and the other way round, and the records that fail to
match are the point of the report.

To run it from another program, call :func:`reconcile` and then whichever
output you want::

    from pathlib import Path
    from reconciler import build_report, reconcile, record_findings, write_report

    result = reconcile('fixture')
    write_report(Path('report.json'), build_report(result))
    record_findings(Path('reconcile.db'), result.findings, result.generated_at)
    raise SystemExit(result.exit_code)

:func:`reconcile` writes nothing and reads only the input directory, so a
caller that wants the findings and none of the files can stop after the first
line. It raises :class:`ReconcileError` when the rules file or the input
directory is unusable, which is the only failure that stops a whole run; an
unreadable inventory file is recorded against that file and the rest are read.

The modules behind it: ``rules`` reads and checks the rules file,
``billing_csv`` and ``scan_json`` read the two inventory formats, ``inventory``
walks the input directory, ``join`` decides which findings exist, ``store``
keeps them in SQLite, ``report`` writes the JSON, ``summary`` prints the table
and ``cli`` wires the command-line tool together.
"""

from __future__ import annotations

from .errors import ReconcileError
from .inventory import Inventory, read_inventory
from .join import JoinResult, join_inventory
from .models import (
    BillingLine,
    FileFormat,
    FileOutcome,
    FileStatus,
    Finding,
    FindingKind,
    ScannedResource,
    Totals,
)
from .pipeline import ReconcileResult, reconcile
from .report import build_report, write_report
from .rules import Rules, load_rules
from .store import StoreOutcome, record_findings
from .summary import print_summary

__all__ = [
    'BillingLine',
    'FileFormat',
    'FileOutcome',
    'FileStatus',
    'Finding',
    'FindingKind',
    'Inventory',
    'JoinResult',
    'ReconcileError',
    'ReconcileResult',
    'Rules',
    'ScannedResource',
    'StoreOutcome',
    'Totals',
    'build_report',
    'join_inventory',
    'load_rules',
    'print_summary',
    'read_inventory',
    'reconcile',
    'record_findings',
    'write_report',
]
