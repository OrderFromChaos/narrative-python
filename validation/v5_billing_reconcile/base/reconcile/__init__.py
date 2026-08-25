"""Billing reconciler.

Matches what a cloud bill charges for against what an asset scan found, and
reports every mismatch: a billing line with no resource, a resource with no
billing line, and a pair that disagrees about the region.

Command line:

    python3 -m reconcile <input-dir>

Program:

    from pathlib import Path
    from reconcile import build_report, reconcile_directory, record_findings

    result = reconcile_directory(Path("fixture"))
    record_findings(Path("reconcile.db"), result.findings, result.generated_at)
    payload = build_report(result)

The modules under this package hold one concern each: `billing` and `scan` read
the two input formats, `rules` reads the rules file, `loader` walks the input
directory, `join` matches the two sides, `store` writes SQLite, `report` builds
the table and the JSON, and `cli` is the command-line tool.
"""

from __future__ import annotations

from .billing import read_billing_file
from .join import JoinResult, reconcile
from .loader import Inventory, load_inventory
from .model import (
    BillingLine,
    FileOutcome,
    Finding,
    FindingKind,
    JoinStats,
    MalformedInputError,
    Reconciliation,
    ScannedResource,
)
from .report import build_report, render, write_report
from .rules import Rules, RulesError, load_rules
from .scan import read_scan_file
from .service import reconcile_directory
from .store import StoreStats, read_findings, record_findings

__all__ = [
    "BillingLine",
    "FileOutcome",
    "Finding",
    "FindingKind",
    "Inventory",
    "JoinResult",
    "JoinStats",
    "MalformedInputError",
    "Reconciliation",
    "Rules",
    "RulesError",
    "ScannedResource",
    "StoreStats",
    "build_report",
    "load_inventory",
    "load_rules",
    "read_billing_file",
    "read_findings",
    "read_scan_file",
    "reconcile",
    "reconcile_directory",
    "record_findings",
    "render",
    "write_report",
]
