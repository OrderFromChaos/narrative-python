"""Reconcile the storage usage of a fleet of hosts against the quota of each team.

The package holds a command-line tool and a function that does the same work. A program that imports
the package does not run the tool:

    from pathlib import Path
    from quota_reconcile import reconcileDirectory

    result = reconcileDirectory(Path('fixture'), Path('fixture/quotas.json'))

To run the tool instead:

    $ python3 -m quota_reconcile fixture
"""

from __future__ import annotations

from quota_reconcile.reconcile import reconcileDirectory
from quota_reconcile.vocabulary import Reconciliation


__all__ = ['Reconciliation', 'reconcileDirectory']
