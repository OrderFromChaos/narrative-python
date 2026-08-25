"""Match what a cloud bill charges for against what an asset scan found, and report every mismatch.

    >>> from reconcile import reconcileDirectory
    >>> len(reconcileDirectory(Path('fixture'), Path('reconcile.db')).findings)
    4

The package exports the entry point and the types a caller reads off its result. Anything else is
imported from the module that defines it. `python3 -m reconcile --help` documents the tool.
"""

from __future__ import annotations

from reconcile.inventory import Cents, RegionName, Resource, ResourceId, Sku, TeamName
from reconcile.join import Finding, FindingKind, aboveGrace
from reconcile.rules import ReconcileRules, RulesError, readReconcileRules
from reconcile.run import FileOutcome, FileReport, InputDirectoryError, Reconciliation, reconcileDirectory


__all__ = [
    'Cents',
    'FileOutcome',
    'FileReport',
    'Finding',
    'FindingKind',
    'InputDirectoryError',
    'ReconcileRules',
    'Reconciliation',
    'RegionName',
    'Resource',
    'ResourceId',
    'RulesError',
    'Sku',
    'TeamName',
    'aboveGrace',
    'readReconcileRules',
    'reconcileDirectory',
]
