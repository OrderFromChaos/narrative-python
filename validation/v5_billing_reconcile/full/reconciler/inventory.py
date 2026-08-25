"""Read every inventory file of an input directory, whichever format each one is.

A file whose name ends in neither `.billing.csv` nor `.scan.json` is not inventory and is passed
over, which is what lets the rules file share the directory. A file that fails as a whole becomes an
outcome carrying the reason and contributes no record, so the files after it are still read.

Outcomes are in filename order, one per inventory file. This module logs the per-file tally; the
readers log the individual line.
"""

from __future__ import annotations

from pathlib import Path

from reconciler import billing_csv, scan_json
from reconciler.logs import LOG
from reconciler.vocabulary import (
    FileOutcome,
    FileRead,
    Inventory,
    InventoryFileError,
    InventoryFormat,
    InventoryRecord,
)


def readInventoryDirectory(input_directory: Path) -> Inventory:
    """Read the inventory of one directory, in filename order.

    Returns:
        Every accepted record of every file, and one outcome per inventory file found.

    Raises:
        InventoryFileError: the input path is not a directory, so there is nothing to reconcile.
    """
    if not input_directory.is_dir():
        LOG.error('inventory.directory_rejected', extra={'path': str(input_directory)})
        raise InventoryFileError(f'{input_directory}: not a directory')

    records: list[InventoryRecord] = []
    outcomes = []
    for inventory_path in sorted(input_directory.iterdir()):
        inventory_format = _detectInventoryFormat(inventory_path)
        if inventory_format is None:
            continue

        try:
            file_read = _readInventoryFile(inventory_path, inventory_format)
        except InventoryFileError as exc:
            LOG.warning('inventory.file_failed', extra={'path': str(inventory_path), 'reason': str(exc)})
            outcomes.append(FileOutcome(inventory_path, accepted_lines=0, rejected_lines=0, error=str(exc)))
            continue

        if file_read.rejected_lines:
            LOG.warning(
                'inventory.lines_rejected',
                extra={
                    'path': str(inventory_path),
                    'rejected': file_read.rejected_lines,
                    'accepted': len(file_read.records),
                },
            )
        records.extend(file_read.records)
        outcomes.append(
            FileOutcome(
                inventory_path,
                accepted_lines=len(file_read.records),
                rejected_lines=file_read.rejected_lines,
                error=None,
            ),
        )

    inventory = Inventory(records=tuple(records), outcomes=tuple(outcomes))
    return inventory


def _detectInventoryFormat(inventory_path: Path) -> InventoryFormat | None:
    for inventory_format in InventoryFormat:
        if inventory_path.name.endswith(f'.{inventory_format.value}'):
            return inventory_format
    return None


def _readInventoryFile(inventory_path: Path, inventory_format: InventoryFormat) -> FileRead:
    match inventory_format:
        case InventoryFormat.BILLING_CSV:
            return billing_csv.readBillingLines(inventory_path)
        case InventoryFormat.SCAN_JSON:
            return scan_json.readScannedResources(inventory_path)
