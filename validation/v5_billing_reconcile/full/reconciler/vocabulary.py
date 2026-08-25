"""The types the reconciler modules pass between them.

An InventoryRecord states only what its own file carried: `monthly_cents` is None on a scanned
resource, and `team` is None on a billing line. A check that reads an absent field skips the record
rather than assuming a value.

Costs are plain integer cents. A region is the string the file wrote, before `region_aliases` is
applied.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import NewType


Cents = NewType('Cents', int)
RegionName = NewType('RegionName', str)
ResourceId = NewType('ResourceId', str)
Sku = NewType('Sku', str)
TeamName = NewType('TeamName', str)


class InventoryFormat(Enum):
    # The value is the filename suffix that the writing tool gives the format.
    BILLING_CSV = 'billing.csv'
    SCAN_JSON = 'scan.json'


class FindingKind(Enum):
    BILLED_NOT_FOUND = 'billed_not_found'
    FOUND_NOT_BILLED = 'found_not_billed'
    REGION_MISMATCH = 'region_mismatch'


class InventoryFileError(RuntimeError):
    """An inventory file was unreadable as a whole, so none of its records were used."""


class InventoryLineError(RuntimeError):
    """One record of an inventory file was unreadable, and the rest of the file still counts."""


class RulesFileError(RuntimeError):
    """The rules file did not state what to reconcile, so the run cannot start."""


@dataclass(frozen=True)
class InventoryRecord:
    resource_id: ResourceId
    sku: Sku
    region: RegionName
    origin: InventoryFormat
    monthly_cents: Cents | None
    team: TeamName | None


@dataclass(frozen=True)
class FileRead:
    records: tuple[InventoryRecord, ...]
    rejected_lines: int


@dataclass(frozen=True)
class FileOutcome:
    path: Path
    accepted_lines: int
    rejected_lines: int
    error: str | None


@dataclass(frozen=True)
class Inventory:
    records: tuple[InventoryRecord, ...]
    outcomes: tuple[FileOutcome, ...]


@dataclass(frozen=True)
class Finding:
    kind: FindingKind
    resource_id: ResourceId
    sku: Sku
    monthly_cents: Cents | None
    team: TeamName | None
    billed_region: RegionName | None
    scanned_region: RegionName | None


@dataclass(frozen=True)
class ReconcileRules:
    ignored_skus: frozenset[Sku]
    region_aliases: Mapping[RegionName, RegionName]
    grace_cents: Cents


@dataclass(frozen=True)
class Reconciliation:
    findings: tuple[Finding, ...]
    outcomes: tuple[FileOutcome, ...]
