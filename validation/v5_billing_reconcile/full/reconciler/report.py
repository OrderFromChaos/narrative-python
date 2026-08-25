"""Format a Reconciliation as a table for a terminal, and write it as a JSON report.

    KIND              RESOURCE  SKU             CENTS  TEAM     BILLED_REGION  SCANNED_REGION  GRACE
    billed_not_found  i-0004    compute-gpu   250,000  -        us-east-1      -               over
    found_not_billed  i-0008    object-store        -  search   -              us-west-2       -
    region_mismatch   i-0003    object-store      900  archive  us-west-2      eu-west-1       -

    FILE              ACCEPTED  REJECTED  ERROR
    edge.scan.json           0         0  not valid JSON: Expecting property name enclosed in double quotes, line 5
    prod.billing.csv         6         1  -

    5 findings, 1 above the 500c grace, 3 files read, 1 unreadable

A cell that the finding does not state shows `-`. GRACE says `over` on a finding that fails the
run. Costs are plain cents. Findings keep the order the join gave them; files are in filename
order.
"""

from __future__ import annotations

import json
from collections.abc import Container, Sequence
from pathlib import Path

from reconciler import rules
from reconciler.vocabulary import FileOutcome, Finding, ReconcileRules, Reconciliation


_FINDING_HEADERS = ('KIND', 'RESOURCE', 'SKU', 'CENTS', 'TEAM', 'BILLED_REGION', 'SCANNED_REGION', 'GRACE')
_FILE_HEADERS = ('FILE', 'ACCEPTED', 'REJECTED', 'ERROR')
_ABSENT = '-'


def formatSummaryTable(reconciliation: Reconciliation, reconcile_rules: ReconcileRules) -> str:
    """Render the findings, the per-file outcomes and one tally line as one block of text."""
    finding_rows = [_findingCells(finding, reconcile_rules) for finding in reconciliation.findings]
    file_rows = [_fileCells(outcome) for outcome in reconciliation.outcomes]

    lines = _renderTable(_FINDING_HEADERS, finding_rows, right_aligned=(3,))
    lines.append('')
    lines.extend(_renderTable(_FILE_HEADERS, file_rows, right_aligned=(1, 2)))
    lines.append('')

    above_grace = sum(1 for finding in reconciliation.findings if rules.aboveGrace(finding, reconcile_rules))
    failed_files = sum(1 for outcome in reconciliation.outcomes if outcome.error is not None)
    lines.append(
        f'{len(reconciliation.findings)} findings, {above_grace} above the '
        f'{reconcile_rules.grace_cents}c grace, '
        f'{len(reconciliation.outcomes)} files read, {failed_files} unreadable',
    )
    return '\n'.join(lines)


def writeJsonReport(report_path: Path, reconciliation: Reconciliation, reconcile_rules: ReconcileRules) -> None:
    """Write every finding and every file outcome as one JSON object."""
    report = {
        'grace_cents': reconcile_rules.grace_cents,
        'findings': [
            {
                'kind': finding.kind.value,
                'resource_id': finding.resource_id,
                'sku': finding.sku,
                'monthly_cents': finding.monthly_cents,
                'team': finding.team,
                'billed_region': finding.billed_region,
                'scanned_region': finding.scanned_region,
                'above_grace': rules.aboveGrace(finding, reconcile_rules),
            }
            for finding in reconciliation.findings
        ],
        'files': [
            {
                'path': str(outcome.path),
                'accepted_lines': outcome.accepted_lines,
                'rejected_lines': outcome.rejected_lines,
                'error': outcome.error,
            }
            for outcome in reconciliation.outcomes
        ],
    }
    report_path.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')


def _findingCells(finding: Finding, reconcile_rules: ReconcileRules) -> list[str]:
    cents = _ABSENT if finding.monthly_cents is None else f'{finding.monthly_cents:,}'
    return [
        finding.kind.value,
        finding.resource_id,
        finding.sku,
        cents,
        finding.team or _ABSENT,
        finding.billed_region or _ABSENT,
        finding.scanned_region or _ABSENT,
        'over' if rules.aboveGrace(finding, reconcile_rules) else _ABSENT,
    ]


def _fileCells(outcome: FileOutcome) -> list[str]:
    return [
        outcome.path.name,
        str(outcome.accepted_lines),
        str(outcome.rejected_lines),
        outcome.error or _ABSENT,
    ]


def _renderTable(headers: Sequence[str], rows: Sequence[Sequence[str]], right_aligned: Container[int]) -> list[str]:
    widths = [max(len(cell) for cell in column) for column in zip(headers, *rows, strict=True)]

    lines = []
    for row in [headers, *rows]:
        cells = [
            cell.rjust(width) if index in right_aligned else cell.ljust(width)
            for index, (cell, width) in enumerate(zip(row, widths, strict=True))
        ]
        lines.append('  '.join(cells).rstrip())
    return lines
