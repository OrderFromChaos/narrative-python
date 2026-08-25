"""Run one reconciliation over an input directory.

    reconciliation = reconcileDirectory(Path('fixture'), readRules(Path('fixture/reconcile.json')))

The call prints nothing, writes no file and records nothing, so a caller that wants the findings
and not the report can use it on its own.
"""

from __future__ import annotations

from pathlib import Path

from reconciler import inventory, join
from reconciler.vocabulary import ReconcileRules, Reconciliation


def reconcileDirectory(input_directory: Path, reconcile_rules: ReconcileRules) -> Reconciliation:
    """Read every inventory file of the directory and join the two sides into findings.

    Raises:
        InventoryFileError: the input path is not a directory, so there is nothing to reconcile.
    """
    inventory_read = inventory.readInventoryDirectory(input_directory)
    findings = join.findMismatches(inventory_read.records, reconcile_rules)

    reconciliation = Reconciliation(findings=findings, outcomes=inventory_read.outcomes)
    return reconciliation
