"""The records, the closed sets and the errors that the reconciler modules pass between them.

Which fields a Finding carries follows from the side or sides it has, and a field the finding does
not carry is None:

    kind              sku       monthly_cents  team   billed_region  scanned_region
    billed_not_found  billing   the cost       None   the region     None
    found_not_billed  scan      None           owner  None           the region
    region_mismatch   billing   the cost       owner  the region     the region

A region is the raw string its file wrote. An alias resolves during the join and is never stored.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from typing import Generic, NewType, TypeVar


ResourceId = NewType('ResourceId', str)
Sku = NewType('Sku', str)
RegionName = NewType('RegionName', str)
TeamName = NewType('TeamName', str)
Cents = NewType('Cents', int)

_RecordT = TypeVar('_RecordT')


class RulesError(RuntimeError):
    """The rules file is missing, unreadable, or states a value of the wrong type."""


class InputDirectoryError(RuntimeError):
    """The input path is missing, or names something that is not a directory."""


class RejectedRecordError(RuntimeError):
    """One record of an inventory file met a condition on the closed list of rejections.

    The message is the problem string that the file's outcome reports, minus its position.
    """


class FindingKind(Enum):
    BILLED_NOT_FOUND = 'billed_not_found'
    FOUND_NOT_BILLED = 'found_not_billed'
    REGION_MISMATCH = 'region_mismatch'


class InventoryFormat(Enum):
    BILLING = 'billing'
    SCAN = 'scan'
    UNKNOWN = 'unknown'


class FileStatus(Enum):
    OK = 'ok'
    PARTIAL = 'partial'
    FAILED = 'failed'
    SKIPPED = 'skipped'


@dataclass(frozen=True)
class ReconcileRules:
    ignored_skus: frozenset[Sku]
    region_aliases: Mapping[RegionName, RegionName]
    grace_cents: Cents


@dataclass(frozen=True)
class BillingLine:
    resource_id: ResourceId
    sku: Sku
    monthly_cents: Cents
    region: RegionName
    source: str


@dataclass(frozen=True)
class ScannedResource:
    resource_id: ResourceId
    sku: Sku
    team: TeamName
    region: RegionName
    source: str


@dataclass(frozen=True)
class FileOutcome:
    path: str
    inventory_format: InventoryFormat
    status: FileStatus
    accepted: int
    rejected: int
    problems: tuple[str, ...]


@dataclass(frozen=True)
class FileContents(Generic[_RecordT]):
    """What one inventory file gave the reader: its accepted records, and how it went."""

    records: tuple[_RecordT, ...]
    outcome: FileOutcome


@dataclass(frozen=True)
class Inventory:
    """Every accepted record of an input directory, before the ignore and before the join.

    A record of either side keeps the file order of its source, and file_outcomes sorts by path.
    """

    billing_lines: tuple[BillingLine, ...]
    scanned_resources: tuple[ScannedResource, ...]
    file_outcomes: tuple[FileOutcome, ...]


@dataclass(frozen=True, kw_only=True)
class Finding:
    """One mismatch. A field the kind does not carry stays None, and a caller states the rest.

    sources holds the sorted basenames of the files that supplied an accepted record to it, so a
    region_mismatch drawn from two files names both.
    """

    kind: FindingKind
    resource_id: ResourceId
    sku: Sku
    monthly_cents: Cents | None = None
    team: TeamName | None = None
    billed_region: RegionName | None = None
    scanned_region: RegionName | None = None
    above_grace: bool
    sources: tuple[str, ...]


@dataclass(frozen=True)
class ReconciliationTotals:
    """Counts over one run. by_kind holds every FindingKind, and its values sum to findings."""

    billing_lines: int
    scanned_resources: int
    ignored_billing: int
    ignored_scanned: int
    matched: int
    findings: int
    above_grace: int
    by_kind: Mapping[FindingKind, int]


@dataclass(frozen=True)
class Reconciliation:
    """The whole result of one run, and the only thing an importing program needs.

    findings sorts by (kind in FindingKind order, -monthly_cents, resource_id) for
    billed_not_found and by (kind, resource_id) for the other two kinds.
    """

    rules: ReconcileRules
    totals: ReconciliationTotals
    findings: tuple[Finding, ...]
    file_outcomes: tuple[FileOutcome, ...]
