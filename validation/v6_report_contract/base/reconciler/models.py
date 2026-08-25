"""Value types that the readers, the join and the outputs all share.

Everything here is a plain data holder. The rules live in ``rules.py`` because
they also own their validation, and the totals live here because the join
produces them and both outputs consume them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class FileFormat(StrEnum):
    """Which reader a file is handed to, decided by its name alone."""

    BILLING = 'billing'
    SCAN = 'scan'
    UNKNOWN = 'unknown'


class FileStatus(StrEnum):
    """How completely a file was read."""

    OK = 'ok'
    PARTIAL = 'partial'
    FAILED = 'failed'
    SKIPPED = 'skipped'


class FindingKind(StrEnum):
    """The three mismatches the reconciliation reports.

    Declaration order is the order the kinds appear in the report's ``by_kind``
    block and the order the findings themselves are grouped in.
    """

    BILLED_NOT_FOUND = 'billed_not_found'
    FOUND_NOT_BILLED = 'found_not_billed'
    REGION_MISMATCH = 'region_mismatch'


@dataclass(frozen=True, slots=True)
class BillingLine:
    """One accepted data row of a ``*.billing.csv`` file.

    ``region`` is the raw string the file wrote. The alias table is applied at
    comparison time and never stored, because the report must echo the raw form.
    """

    resource_id: str
    sku: str
    monthly_cents: int
    region: str
    source: str


@dataclass(frozen=True, slots=True)
class ScannedResource:
    """One accepted entry of the ``resources`` list of a ``*.scan.json`` file."""

    resource_id: str
    sku: str
    team: str
    region: str
    source: str


@dataclass(slots=True)
class FileOutcome:
    """What the readers made of one file in the input directory.

    ``accepted`` and ``rejected`` count records, not lines, and they ignore the
    sku filter entirely: the filter runs after reading, so a record it later
    drops is still counted here as accepted.

    ``rejected`` and ``len(problems)`` are allowed to disagree. A file that
    fails as a whole has zero of both counts and one problem string.
    """

    path: str
    file_format: FileFormat
    status: FileStatus
    accepted: int = 0
    rejected: int = 0
    problems: list[str] = field(default_factory=list)

    def reject(self, problem: str) -> None:
        """Count one rejected record and keep the reason."""
        self.rejected += 1
        self.problems.append(problem)


@dataclass(frozen=True, slots=True)
class Finding:
    """One mismatch, carrying whichever values its side or sides supplied.

    A value the finding has no side for is ``None``. ``sources`` holds the
    basenames of the files that supplied an accepted record to this finding,
    sorted, so a one-sided finding names one file and a ``region_mismatch``
    names two.
    """

    kind: FindingKind
    resource_id: str
    sku: str
    monthly_cents: int | None
    team: str | None
    billed_region: str | None
    scanned_region: str | None
    above_grace: bool
    sources: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Totals:
    """The counts the report's ``totals`` block publishes.

    ``billing_lines`` and ``scanned_resources`` count accepted records before
    the sku filter; ``ignored_billing`` and ``ignored_scanned`` count how many
    of those the filter then dropped.
    """

    billing_lines: int
    scanned_resources: int
    ignored_billing: int
    ignored_scanned: int
    matched: int
    findings: int
    above_grace: int
    by_kind: dict[FindingKind, int]
