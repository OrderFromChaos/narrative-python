"""Reconcile an input directory end to end, and construct the Reconciliation it yields.

This is the importable entry point: a program that wants the findings and not the command-line
tool calls reconcileDirectory and reads the record it returns.

    >>> reconciliation = reconcileDirectory(Path('../fixture'))
    >>> reconciliation.totals.matched
    7

The call writes no file, prints nothing and records nothing.
"""

from __future__ import annotations

from pathlib import Path

from reconcile.inventory import readInventory
from reconcile.join import joinInventory
from reconcile.rules import RULES_FILENAME, readReconcileRules
from reconcile.vocabulary import Reconciliation


def reconcileDirectory(input_dir: Path, *, rules_path: Path | None = None) -> Reconciliation:
    """Read the rules, read every inventory file of input_dir, and join the two sides.

    Args:
        rules_path: the rules file to apply. `reconcile.json` inside input_dir when absent, and a
            path anywhere on the filesystem when given.

    Raises:
        RulesError: the rules file is missing, unreadable, or states a value of the wrong type.
        InputDirectoryError: input_dir does not exist, or is not a directory.
    """
    rules_in_use = rules_path if rules_path is not None else input_dir / RULES_FILENAME
    rules = readReconcileRules(rules_in_use)
    inventory = readInventory(input_dir, rules_in_use)
    return joinInventory(inventory, rules)
