"""Record types shared by the readers, the join, the store and the report.

The two inventory formats do not carry the same fields. A billing line has a
cost and no owning team. A scanned resource has an owning team and no cost. The
finding record keeps both sides optional, so a reader of the report can tell a
missing value from an empty one.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .rules import Rules


class MalformedInputError(Exception):
    """An input file cannot be read at all.

    Raised for damage to the file as a whole, such as invalid JSON or a missing
    CSV header. A single bad row is not this error: the reader skips the row and
    records the problem in the file outcome.
    """


class FindingKind(str, Enum):
    """The three kinds of mismatch the reconciler reports."""

    BILLED_NOT_FOUND = "billed_not_found"
    FOUND_NOT_BILLED = "found_not_billed"
    REGION_MISMATCH = "region_mismatch"


@dataclass(frozen=True)
class BillingLine:
    """One line of a `*.billing.csv` file."""

    resource_id: str
    sku: str
    monthly_cents: int
    region: str
    source: str


@dataclass(frozen=True)
class ScannedResource:
    """One resource from the `resources` list of a `*.scan.json` file."""

    resource_id: str
    sku: str
    team: str
    region: str
    source: str


@dataclass(frozen=True)
class Finding:
    """One mismatch between the two sides of the join."""

    kind: FindingKind
    resource_id: str
    sku: str
    monthly_cents: int | None = None
    team: str | None = None
    billed_region: str | None = None
    scanned_region: str | None = None
    above_grace: bool = False
    sources: tuple[str, ...] = ()

    @property
    def key(self) -> str:
        """Identity of the finding, stable over runs.

        A resource has one sku and takes part in one join, so the kind and the
        resource id identify the finding. The store uses this identity to keep a
        re-run over unchanged inputs from inserting a second row.
        """
        return f"{self.kind.value}:{self.resource_id}"

    def as_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "kind": self.kind.value,
            "resource_id": self.resource_id,
            "sku": self.sku,
            "monthly_cents": self.monthly_cents,
            "team": self.team,
            "billed_region": self.billed_region,
            "scanned_region": self.scanned_region,
            "above_grace": self.above_grace,
            "sources": list(self.sources),
        }


@dataclass
class FileOutcome:
    """What happened to one file in the input directory.

    A `failed` file does not stop the other files. Its records are absent from
    the join, which can itself cause findings, so the report shows every outcome
    next to the findings.
    """

    path: str
    kind: str
    status: str
    records: int = 0
    problems: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "kind": self.kind,
            "status": self.status,
            "records": self.records,
            "problems": list(self.problems),
        }


@dataclass(frozen=True)
class JoinStats:
    """Counts that the join consumed, for the report header."""

    billing_lines: int = 0
    scanned_resources: int = 0
    ignored_billing: int = 0
    ignored_scanned: int = 0
    matched: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "billing_lines": self.billing_lines,
            "scanned_resources": self.scanned_resources,
            "ignored_billing": self.ignored_billing,
            "ignored_scanned": self.ignored_scanned,
            "matched": self.matched,
        }


@dataclass(frozen=True)
class Reconciliation:
    """The full outcome of one run: what was read, what was found."""

    input_dir: str
    generated_at: str
    rules: Rules
    findings: list[Finding]
    stats: JoinStats
    outcomes: list[FileOutcome]

    def of_kind(self, kind: FindingKind) -> list[Finding]:
        return [finding for finding in self.findings if finding.kind is kind]

    @property
    def actionable(self) -> list[Finding]:
        """Findings above the grace amount. These set the exit code."""
        return [finding for finding in self.findings if finding.above_grace]

    @property
    def failed_files(self) -> list[FileOutcome]:
        return [outcome for outcome in self.outcomes if outcome.status == "failed"]

    @property
    def exit_code(self) -> int:
        return 1 if self.actionable else 0
