"""Render a Reconciliation as a table for a terminal, and as a JSON report.

    FINDING           RESOURCE   SKU          TEAM      CENTS  DETAIL
    billed_not_found  cache-301  redis-small  -          1200  above grace
    billed_not_found  nic-501    network-eip  -           300  within grace
    found_not_billed  gpu-401    gpu-a100     research      -  scanned in eu-west-1
    region_mismatch   db-201     postgres-ha  payments  89000  billed eu-west-1, scanned us-east-1

    FILE              OUTCOME   RECORDS  DETAIL
    east.billing.csv  read            6  -
    reconcile.json    skipped         0  -
    west.billing.csv  rejected        0  west.billing.csv: line 2: monthly_cents is not an integer: 'not-a-number'

A cell of a record that carries no such value holds `-`. The JSON report holds the same findings
in the same order, one object per finding, beside a `totals` object and the applied `grace_cents`.
"""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Sequence
from pathlib import Path

from reconcile.inventory import Cents
from reconcile.join import Finding, FindingKind, aboveGrace
from reconcile.run import FileOutcome, FileReport, Reconciliation


FINDING_HEADERS = ('FINDING', 'RESOURCE', 'SKU', 'TEAM', 'CENTS', 'DETAIL')
FILE_HEADERS = ('FILE', 'OUTCOME', 'RECORDS', 'DETAIL')
RIGHT_ALIGNED_COLUMNS = frozenset({'CENTS', 'RECORDS'})
ABSENT_CELL = '-'


def formatReconciliation(reconciliation: Reconciliation) -> str:
    """Render the findings and the per-file outcomes as two tables, in the order they are held."""
    grace_cents = reconciliation.rules.grace_cents
    findings = formatTable(FINDING_HEADERS, [formatFindingRow(each, grace_cents) for each in reconciliation.findings])
    files = formatTable(FILE_HEADERS, [formatFileRow(each) for each in reconciliation.files])
    return f'{findings}\n\n{files}'


def formatFindingRow(finding: Finding, grace_cents: Cents) -> list[str]:
    return [
        finding.kind.value,
        finding.resource_id,
        finding.sku,
        formatOptional(finding.team),
        formatOptional(finding.monthly_cents),
        describeFinding(finding, grace_cents),
    ]


def describeFinding(finding: Finding, grace_cents: Cents) -> str:
    match finding.kind:
        case FindingKind.BILLED_NOT_FOUND:
            return 'above grace' if aboveGrace(finding, grace_cents) else 'within grace'
        case FindingKind.FOUND_NOT_BILLED:
            return f'scanned in {finding.scanned_region}'
        case FindingKind.REGION_MISMATCH:
            return f'billed {finding.billed_region}, scanned {finding.scanned_region}'


def formatFileRow(file_report: FileReport) -> list[str]:
    return [
        file_report.inventory_path.name,
        file_report.outcome.value,
        str(file_report.records),
        formatOptional(file_report.detail),
    ]


def formatTable(headers: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
    """Render `rows` under `headers`, padded to the widest cell of each column.

    A column named in RIGHT_ALIGNED_COLUMNS is right-aligned, and every other column is left. Two
    spaces separate the columns, and no line carries trailing space.
    """
    COLUMN_GAP = '  '
    widths = [max(len(cell) for cell in column) for column in zip(headers, *rows, strict=True)]

    lines = []
    for row in [headers, *rows]:
        cells = [
            cell.rjust(width) if headers[index] in RIGHT_ALIGNED_COLUMNS else cell.ljust(width)
            for index, (cell, width) in enumerate(zip(row, widths, strict=True))
        ]
        lines.append(COLUMN_GAP.join(cells).rstrip())

    return '\n'.join(lines)


def formatOptional(value: object) -> str:
    return ABSENT_CELL if value is None else str(value)


def writeJsonReport(report_path: Path, reconciliation: Reconciliation) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(buildJsonReport(reconciliation), indent=2) + '\n', encoding='utf-8')


def buildJsonReport(reconciliation: Reconciliation) -> dict[str, object]:
    """Construct the JSON report of a run.

    Returns:
        A mapping of plain JSON values, so every Enum is already its `.value`.
    """
    grace_cents = reconciliation.rules.grace_cents
    findings = [
        {
            'kind': each.kind.value,
            'resource_id': each.resource_id,
            'sku': each.sku,
            'team': each.team,
            'monthly_cents': each.monthly_cents,
            'billed_region': each.billed_region,
            'scanned_region': each.scanned_region,
            'above_grace': aboveGrace(each, grace_cents),
        }
        for each in reconciliation.findings
    ]
    files = [
        {
            'file': str(each.inventory_path),
            'outcome': each.outcome.value,
            'records': each.records,
            'detail': each.detail,
        }
        for each in reconciliation.files
    ]

    outcomes = Counter(each.outcome for each in reconciliation.files)
    totals = {
        'findings': len(findings),
        'above_grace': sum(1 for each in reconciliation.findings if aboveGrace(each, grace_cents)),
        'rows_added': reconciliation.rows_added,
        'files': {outcome.value: outcomes[outcome] for outcome in FileOutcome},
    }
    return {'grace_cents': grace_cents, 'totals': totals, 'findings': findings, 'files': files}
