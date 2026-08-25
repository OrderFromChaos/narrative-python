"""Reads every inventory file in an input directory.

The loader decides which reader applies to each file, keeps the records that
parsed, and records one outcome per file. A file that fails does not stop the
others, so the join runs on what was readable and the report shows what was
not.

Outcome status values:

    ok       every record in the file parsed
    partial  the file was read, but one or more records were skipped
    failed   the file could not be read at all
    skipped  the file is not an inventory file
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from . import billing, scan
from .model import BillingLine, FileOutcome, MalformedInputError, ScannedResource
from .rules import RULES_FILENAME


@dataclass
class Inventory:
    """The records read from an input directory, and how each file went."""

    billing: list[BillingLine] = field(default_factory=list)
    scanned: list[ScannedResource] = field(default_factory=list)
    outcomes: list[FileOutcome] = field(default_factory=list)


def load_inventory(input_dir: Path, rules_path: Path | None = None) -> Inventory:
    """Read every inventory file directly inside `input_dir`.

    `rules_path` names the rules file, which is not an inventory file and is
    left out of the outcomes when it sits in the input directory.

    Raises `NotADirectoryError` if the input directory is absent, because there
    is then nothing to reconcile.
    """
    if not input_dir.is_dir():
        raise NotADirectoryError(f"input directory not found: {input_dir}")

    rules_file = rules_path.resolve() if rules_path is not None else None
    inventory = Inventory()
    seen_billing: dict[str, str] = {}
    seen_scanned: dict[str, str] = {}

    for path in sorted(p for p in input_dir.iterdir() if p.is_file()):
        if path.name == RULES_FILENAME or (
            rules_file is not None and path.resolve() == rules_file
        ):
            continue

        if billing.is_billing_file(path):
            outcome = _load_billing(path, inventory, seen_billing)
        elif scan.is_scan_file(path):
            outcome = _load_scan(path, inventory, seen_scanned)
        else:
            outcome = FileOutcome(
                path=path.name,
                kind="unknown",
                status="skipped",
                problems=["not a *.billing.csv or *.scan.json file"],
            )
        inventory.outcomes.append(outcome)

    return inventory


def _load_billing(
    path: Path, inventory: Inventory, seen: dict[str, str]
) -> FileOutcome:
    outcome = FileOutcome(path=path.name, kind="billing", status="ok")
    try:
        lines, problems = billing.read_billing_file(path)
    except MalformedInputError as error:
        outcome.status = "failed"
        outcome.problems.append(str(error))
        return outcome

    outcome.problems.extend(problems)
    for line in lines:
        first = seen.get(line.resource_id)
        if first is not None:
            outcome.problems.append(
                f"{line.resource_id}: already billed in {first}, line dropped"
            )
            continue
        seen[line.resource_id] = path.name
        inventory.billing.append(line)
        outcome.records += 1

    outcome.status = "partial" if outcome.problems else "ok"
    return outcome


def _load_scan(path: Path, inventory: Inventory, seen: dict[str, str]) -> FileOutcome:
    outcome = FileOutcome(path=path.name, kind="scan", status="ok")
    try:
        resources, problems = scan.read_scan_file(path)
    except MalformedInputError as error:
        outcome.status = "failed"
        outcome.problems.append(str(error))
        return outcome

    outcome.problems.extend(problems)
    for resource in resources:
        first = seen.get(resource.resource_id)
        if first is not None:
            outcome.problems.append(
                f"{resource.resource_id}: already scanned in {first}, entry dropped"
            )
            continue
        seen[resource.resource_id] = path.name
        inventory.scanned.append(resource)
        outcome.records += 1

    outcome.status = "partial" if outcome.problems else "ok"
    return outcome
