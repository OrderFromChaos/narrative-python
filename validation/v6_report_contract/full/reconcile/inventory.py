"""Read every inventory file of an input directory, and construct the Inventory they state.

Only the top level of the directory is read. A name that starts with `.` is passed over, and so is
the rules file in use, which is neither an inventory file nor a reported outcome. Every other file
is reported, and one that matches neither format suffix is reported as skipped without being opened.

Files are read in ascending basename order, so a resource_id repeated on one side across two files
keeps the record of the earlier basename. The two sides claim ids separately: the same resource_id
on the billing side and on the scan side is a match, not a repeat.

The directory is never written to.
"""

from __future__ import annotations

import logging
from pathlib import Path

from reconcile.billing_csv import BILLING_SUFFIX, readBillingFile
from reconcile.logs import LOG
from reconcile.outcomes import describeSkippedFile
from reconcile.scan_json import SCAN_SUFFIX, readScanFile
from reconcile.vocabulary import (
    BillingLine,
    FileOutcome,
    FileStatus,
    InputDirectoryError,
    Inventory,
    InventoryFormat,
    ResourceId,
    ScannedResource,
)


def readInventory(input_dir: Path, rules_path: Path) -> Inventory:
    """Read every file of input_dir that the rules file did not claim.

    Args:
        rules_path: the rules file in use, excluded from the walk when it lies inside input_dir.

    Raises:
        InputDirectoryError: input_dir does not exist, or is not a directory.
    """
    if not input_dir.is_dir():
        LOG.error('input_dir.unusable', extra={'path': str(input_dir)})
        raise InputDirectoryError(f'{input_dir}: not a directory')

    billing_lines: list[BillingLine] = []
    scanned_resources: list[ScannedResource] = []
    outcomes: list[FileOutcome] = []
    claimed_ids: dict[InventoryFormat, set[ResourceId]] = {
        inventory_format: set() for inventory_format in InventoryFormat
    }
    for inventory_path in _listInventoryPaths(input_dir, rules_path):
        outcome = _readInventoryFile(inventory_path, billing_lines, scanned_resources, claimed_ids)
        _logFileOutcome(outcome)
        outcomes.append(outcome)

    return Inventory(tuple(billing_lines), tuple(scanned_resources), tuple(outcomes))


def _listInventoryPaths(input_dir: Path, rules_path: Path) -> list[Path]:
    rules_in_use = rules_path.resolve()
    candidates = [
        path
        for path in input_dir.iterdir()
        if path.is_file() and not path.name.startswith('.') and path.resolve() != rules_in_use
    ]
    return sorted(candidates, key=lambda path: path.name)


def _readInventoryFile(
    inventory_path: Path,
    billing_lines: list[BillingLine],
    scanned_resources: list[ScannedResource],
    claimed_ids: dict[InventoryFormat, set[ResourceId]],
) -> FileOutcome:
    """Read one file into the record list of its side.

    Args:
        billing_lines: extended in place with what a billing export accepted.
        scanned_resources: extended in place with what a scan document accepted.
        claimed_ids: the ids each side has already accepted, extended in place the same way.
    """
    inventory_format = _inventoryFormatOf(inventory_path.name)
    match inventory_format:
        case InventoryFormat.BILLING:
            billing = readBillingFile(inventory_path, claimed_ids[inventory_format])
            billing_lines.extend(billing.records)
            return billing.outcome
        case InventoryFormat.SCAN:
            scan = readScanFile(inventory_path, claimed_ids[inventory_format])
            scanned_resources.extend(scan.records)
            return scan.outcome
        case InventoryFormat.UNKNOWN:
            return describeSkippedFile(inventory_path.name)


def _inventoryFormatOf(basename: str) -> InventoryFormat:
    # the suffix alone decides, so a *.scan.json holding no JSON is a scan document that failed
    if basename.endswith(BILLING_SUFFIX):
        return InventoryFormat.BILLING
    if basename.endswith(SCAN_SUFFIX):
        return InventoryFormat.SCAN
    return InventoryFormat.UNKNOWN


def _logFileOutcome(outcome: FileOutcome) -> None:
    fields = {
        'path': outcome.path,
        'status': outcome.status.value,
        'accepted': outcome.accepted,
        'rejected': outcome.rejected,
    }
    LOG.log(_chooseLogLevel(outcome.status), 'file.read', extra=fields)


def _chooseLogLevel(status: FileStatus) -> int:
    # an operator can act on a per-file tally, and not on one rejected row of ten thousand
    match status:
        case FileStatus.OK | FileStatus.SKIPPED:
            return logging.DEBUG
        case FileStatus.PARTIAL | FileStatus.FAILED:
            return logging.WARNING
