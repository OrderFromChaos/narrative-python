"""Walk the input directory and hand each file to the reader its name selects.

This module owns two rules that neither reader can see on its own: which files
exist at all, and the order they are read in. The order matters, because the
first accepted record for a ``resource_id`` on a side is the one that is kept.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .billing_csv import read_billing_file
from .errors import ReconcileError
from .models import BillingLine, FileFormat, FileOutcome, FileStatus, ScannedResource
from .scan_json import read_scan_file

BILLING_SUFFIX = '.billing.csv'
SCAN_SUFFIX = '.scan.json'


@dataclass(slots=True)
class Inventory:
    """Every accepted record from the input directory, and every file outcome.

    ``billing`` and ``scanned`` hold the records the sku filter has not yet
    seen. ``files`` is in the order the files were read, which is ascending
    basename order, and is also the order the report prints them in.
    """

    billing: list[BillingLine] = field(default_factory=list)
    scanned: list[ScannedResource] = field(default_factory=list)
    files: list[FileOutcome] = field(default_factory=list)


def classify(name: str) -> FileFormat:
    """Decide which reader a file goes to, from its name alone.

    A ``*.scan.json`` holding no JSON is still a scan file. It fails as a scan
    file rather than being quietly reclassified.
    """
    if name.endswith(BILLING_SUFFIX):
        return FileFormat.BILLING
    if name.endswith(SCAN_SUFFIX):
        return FileFormat.SCAN
    return FileFormat.UNKNOWN


def read_inventory(input_dir: Path, rules_path: Path) -> Inventory:
    """Read every inventory file at the top level of ``input_dir``.

    Args:
        input_dir: The directory to read. It is never written to.
        rules_path: The rules file in use. When it sits inside ``input_dir`` it
            is passed over silently: it is neither an inventory file nor a
            per-file outcome.

    Returns:
        The accepted records of both formats and one outcome per file
        considered.

    Raises:
        ReconcileError: ``input_dir`` does not exist or is not a directory.
    """
    if not input_dir.is_dir():
        raise ReconcileError(f'input directory {input_dir} does not exist or is not a directory')

    inventory = Inventory()
    billed_ids: set[str] = set()
    scanned_ids: set[str] = set()

    for path in _inventory_files(input_dir, rules_path):
        file_format = classify(path.name)
        if file_format is FileFormat.BILLING:
            records, outcome = read_billing_file(path, billed_ids)
            inventory.billing.extend(records)
        elif file_format is FileFormat.SCAN:
            resources, outcome = read_scan_file(path, scanned_ids)
            inventory.scanned.extend(resources)
        else:
            # Never opened, so it has no records to accept or reject.
            outcome = FileOutcome(
                path=path.name, file_format=FileFormat.UNKNOWN, status=FileStatus.SKIPPED
            )
        inventory.files.append(outcome)

    return inventory


def _inventory_files(input_dir: Path, rules_path: Path) -> list[Path]:
    """List the files to consider, in ascending basename order.

    Only the top level is read. Directories, dotfiles and the rules file are
    left out; every other entry is considered, even one whose name matches
    neither format.
    """
    try:
        resolved_rules = rules_path.resolve()
    except OSError:
        resolved_rules = rules_path

    candidates = [
        path
        for path in input_dir.iterdir()
        if path.is_file() and not path.name.startswith('.') and path.resolve() != resolved_rules
    ]
    return sorted(candidates, key=lambda path: path.name)
