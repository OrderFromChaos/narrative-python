"""Format a Reconciliation as the table a terminal shows.

    FINDINGS
    kind              resource  sku    team         monthly  billed_region     scanned_region  grace
    billed_not_found  r-1       gpu    -            41200c   na1               -               over
    billed_not_found  r-2       dns    -            300c     na1               -               within
    found_not_billed  r-5       queue  ml-research  -        -                 sp2             -
    region_mismatch   r-3       nat    network-eng  9600c    north-atlantic-1  sp2             -

    FILES
    path              format   status   accepted  rejected  problems
    east.billing.csv  billing  ok       3         0         0
    east.scan.json    scan     partial  2         1         1
    notes.txt         unknown  skipped  0         0         0
    west.scan.json    scan     failed   0         0         1

    TOTALS
    total              count
    billing_lines      3
    scanned_resources  2
    ignored_billing    0
    ignored_scanned    0
    matched            1
    findings           4
    above_grace        1
    by_kind            billed_not_found 2  found_not_billed 1  region_mismatch 1

Findings keep the order of the report and the file rows sort by path. `monthly` is a count of
cents, `problems` is a count of them, and a cell the finding does not carry reads `-`. `grace`
reads `over` or `within` on a billed_not_found, and `-` on a kind the grace does not reach.
"""

from __future__ import annotations

from collections.abc import Sequence

from reconcile.vocabulary import (
    FileOutcome,
    Finding,
    FindingKind,
    Reconciliation,
    ReconciliationTotals,
)


def formatSummary(reconciliation: Reconciliation) -> str:
    """Render the findings, the per-file outcomes and the totals.

    Returns:
        The whole block, newline-separated and without a trailing newline. The call prints nothing
        and writes no file.
    """
    sections = [
        *_formatFindings(reconciliation.findings),
        '',
        *_formatFiles(reconciliation.file_outcomes),
        '',
        *_formatTotals(reconciliation.totals),
    ]
    return '\n'.join(sections)


def _formatFindings(findings: Sequence[Finding]) -> list[str]:
    HEADINGS = ('kind', 'resource', 'sku', 'team', 'monthly', 'billed_region', 'scanned_region', 'grace')
    rows = [
        (
            finding.kind.value,
            finding.resource_id,
            finding.sku,
            _describeCell(finding.team),
            f'{finding.monthly_cents}c' if finding.monthly_cents is not None else '-',
            _describeCell(finding.billed_region),
            _describeCell(finding.scanned_region),
            _describeGrace(finding),
        )
        for finding in findings
    ]
    return ['FINDINGS', *_renderTable(HEADINGS, rows)]


def _describeGrace(finding: Finding) -> str:
    match finding.kind:
        case FindingKind.BILLED_NOT_FOUND:
            return 'over' if finding.above_grace else 'within'
        case FindingKind.FOUND_NOT_BILLED | FindingKind.REGION_MISMATCH:
            return '-'


def _describeCell(value: str | None) -> str:
    return value if value is not None else '-'


def _formatFiles(file_outcomes: Sequence[FileOutcome]) -> list[str]:
    HEADINGS = ('path', 'format', 'status', 'accepted', 'rejected', 'problems')
    rows = [
        (
            outcome.path,
            outcome.inventory_format.value,
            outcome.status.value,
            str(outcome.accepted),
            str(outcome.rejected),
            str(len(outcome.problems)),
        )
        for outcome in file_outcomes
    ]
    return ['FILES', *_renderTable(HEADINGS, rows)]


def _formatTotals(totals: ReconciliationTotals) -> list[str]:
    by_kind = '  '.join(f'{kind.value} {totals.by_kind[kind]}' for kind in FindingKind)
    rows = [
        ('billing_lines', str(totals.billing_lines)),
        ('scanned_resources', str(totals.scanned_resources)),
        ('ignored_billing', str(totals.ignored_billing)),
        ('ignored_scanned', str(totals.ignored_scanned)),
        ('matched', str(totals.matched)),
        ('findings', str(totals.findings)),
        ('above_grace', str(totals.above_grace)),
        ('by_kind', by_kind),
    ]
    return ['TOTALS', *_renderTable(('total', 'count'), rows)]


def _renderTable(headings: Sequence[str], rows: Sequence[Sequence[str]]) -> list[str]:
    """Pad every column to its widest cell, and separate columns with two spaces.

    Returns:
        The heading line, then one line per row. A table with no row is its heading alone.
    """
    COLUMN_GAP = '  '
    all_rows = [list(headings), *(list(row) for row in rows)]
    widths = [max(len(row[column]) for row in all_rows) for column in range(len(headings))]
    return [
        COLUMN_GAP.join(cell.ljust(width) for cell, width in zip(row, widths, strict=True)).rstrip() for row in all_rows
    ]
