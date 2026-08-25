"""Match a cloud bill against an asset scan, and report every mismatch.

Import reconcileDirectory to reconcile a directory without running the command-line tool:

    from pathlib import Path
    from reconciler import readRules, reconcileDirectory

    reconciliation = reconcileDirectory(Path('fixture'), readRules(Path('fixture/reconcile.json')))
"""

from __future__ import annotations

from reconciler.reconcile import reconcileDirectory
from reconciler.rules import readRules
from reconciler.vocabulary import Finding, FindingKind, ReconcileRules, Reconciliation


__all__ = [
    'Finding',
    'FindingKind',
    'ReconcileRules',
    'Reconciliation',
    'readRules',
    'reconcileDirectory',
]
