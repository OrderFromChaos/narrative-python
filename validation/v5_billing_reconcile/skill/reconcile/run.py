"""Reconcile one directory of inventory files, and record every mismatch. The importable entry point.

    >>> reconcileDirectory(Path('fixture'), Path('reconcile.db')).rows_added
    4

A file named `*.billing.csv` is a finance export, a file named `*.scan.json` is an asset scan, and
any other file is skipped. A file that does not parse is rejected, and the files beside it still
reconcile. Every file is reported, whichever of the three outcomes it took.

`rows_added` counts the findings that the SQLite file did not already hold, so a second run of the
call above gives 0. The rules file defaults to `reconcile.json` inside the input directory.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from reconcile.billing_csv import readBilledResources
from reconcile.inventory import MalformedInventoryError, Resource
from reconcile.join import Finding, joinResources
from reconcile.rules import ReconcileRules, readReconcileRules
from reconcile.scan_json import readScannedResources
from reconcile.store import recordFindings


RULES_FILENAME = 'reconcile.json'

LOG = logging.getLogger(__name__)


def reconcileDirectory(input_dir: Path, database_path: Path, *, rules_path: Path | None = None) -> Reconciliation:
    """Read `input_dir`, join the two sides, and record the findings in the SQLite file.

    The call prints nothing. `reconcile.report` renders the result.

    Raises:
        RulesError: the rules file is absent or does not state a usable set of rules.
        InputDirectoryError: `input_dir` is not a directory, or holds no file of either format.
    """
    rules = readReconcileRules(rules_path if rules_path is not None else input_dir / RULES_FILENAME)
    inventory = readInventoryDirectory(input_dir)
    findings = joinResources(inventory.billed, inventory.scanned, rules)
    rows_added = recordFindings(database_path, findings)
    return Reconciliation(rules=rules, findings=findings, files=inventory.files, rows_added=rows_added)


def readInventoryDirectory(input_dir: Path) -> InventoryRead:
    """Read every inventory file of `input_dir`, and report the outcome of each file.

    Raises:
        InputDirectoryError: `input_dir` is not a directory, or holds no file of either format.
    """
    if not input_dir.is_dir():
        raise InputDirectoryError(f'{input_dir}: not a directory')

    resources: dict[InventoryFormat, list[Resource]] = {each: [] for each in InventoryFormat}
    files: list[FileReport] = []
    rejected = 0
    for inventory_path in sorted(input_dir.iterdir()):
        inventory_format = detectInventoryFormat(inventory_path)
        if inventory_format is None:
            files.append(FileReport(inventory_path=inventory_path, outcome=FileOutcome.SKIPPED, records=0, detail=None))
            continue

        try:
            read = readInventoryFile(inventory_path, inventory_format)
        except MalformedInventoryError as exc:
            rejected += 1
            files.append(
                FileReport(inventory_path=inventory_path, outcome=FileOutcome.REJECTED, records=0, detail=str(exc)),
            )
            continue

        resources[inventory_format].extend(read)
        files.append(
            FileReport(inventory_path=inventory_path, outcome=FileOutcome.READ, records=len(read), detail=None),
        )

    # An empty directory takes the first arm too, because all() of nothing is True.
    if all(each.outcome is FileOutcome.SKIPPED for each in files):
        raise InputDirectoryError(f'{input_dir}: holds no *.billing.csv and no *.scan.json')
    if rejected:
        LOG.warning('inventory.files_rejected', extra={'rejected': rejected, 'files': len(files)})

    return InventoryRead(
        billed=tuple(resources[InventoryFormat.BILLING_CSV]),
        scanned=tuple(resources[InventoryFormat.SCAN_JSON]),
        files=tuple(files),
    )


def detectInventoryFormat(inventory_path: Path) -> InventoryFormat | None:
    if not inventory_path.is_file():
        return None
    for inventory_format in InventoryFormat:
        if inventory_path.name.endswith(f'.{inventory_format.value}'):
            return inventory_format
    return None


def readInventoryFile(inventory_path: Path, inventory_format: InventoryFormat) -> tuple[Resource, ...]:
    match inventory_format:
        case InventoryFormat.BILLING_CSV:
            return readBilledResources(inventory_path)
        case InventoryFormat.SCAN_JSON:
            return readScannedResources(inventory_path)


### vocabulary #########################################################################


class InputDirectoryError(RuntimeError):
    """The input directory cannot be reconciled at all."""


class InventoryFormat(Enum):
    BILLING_CSV = 'billing.csv'
    SCAN_JSON = 'scan.json'


class FileOutcome(Enum):
    READ = 'read'
    REJECTED = 'rejected'
    SKIPPED = 'skipped'


@dataclass(frozen=True)
class FileReport:
    """What one file of the input directory contributed.

    `records` counts the resources that a read file gave, and is 0 for any other outcome. `detail`
    holds the rejection reason of a rejected file.
    """

    inventory_path: Path
    outcome: FileOutcome
    records: int
    detail: str | None


@dataclass(frozen=True)
class InventoryRead:
    """The two sides of the join, and the outcome of every file that the input directory holds."""

    billed: tuple[Resource, ...]
    scanned: tuple[Resource, ...]
    files: tuple[FileReport, ...]


@dataclass(frozen=True)
class Reconciliation:
    """Everything one run found, in the order that `reconcile.report` renders it."""

    rules: ReconcileRules
    findings: tuple[Finding, ...]
    files: tuple[FileReport, ...]
    rows_added: int
