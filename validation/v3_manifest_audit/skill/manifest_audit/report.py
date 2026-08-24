"""Render an audit run for a person at a terminal, and for a program that reads the run later.

`summaryTable` returns two tables of plain text: one row per finding, then one row per manifest.
`writeReport` writes the same information as JSON, with the paths and the counts, so that a later
run can be compared against this one.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

from manifest_audit.audit import AuditRun, ManifestOutcome, everyFinding
from manifest_audit.policy import Finding, FindingKind


FINDING_HEADERS = ('manifest', 'package', 'version', 'rule', 'detail')
MANIFEST_HEADERS = ('manifest', 'format', 'packages', 'skipped', 'outcome')
UNREADABLE_LABEL = 'unreadable'
SECTION_SEPARATOR = '\n\n'


def summaryTable(run: AuditRun) -> str:
    """Render the findings and the per-manifest outcomes as two tables of plain text."""
    findings = everyFinding(run.manifests)
    finding_rows = [
        [finding.manifest.name, finding.package, finding.version, kindLabel(finding.kind), finding.detail]
        for finding in findings
    ]
    manifest_rows = [
        [
            outcome.path.name,
            formatLabel(outcome),
            str(outcome.packages),
            str(outcome.skipped),
            outcome.error or 'ok',
        ]
        for outcome in run.manifests
    ]

    sections = (
        f'findings ({len(findings)}), recorded {run.recorded}',
        renderTable(FINDING_HEADERS, finding_rows),
        f'manifests ({len(run.manifests)})',
        renderTable(MANIFEST_HEADERS, manifest_rows),
    )
    return SECTION_SEPARATOR.join(sections)


def writeReport(path: Path, run: AuditRun) -> None:
    """Write the run as one JSON object with a `manifests` list and a `findings` list."""
    document: dict[str, object] = {
        'manifests': [manifestEntry(outcome) for outcome in run.manifests],
        'findings': [findingEntry(finding) for finding in everyFinding(run.manifests)],
        'recorded': run.recorded,
    }
    path.write_text(json.dumps(document, indent=2) + '\n', encoding='utf-8')


def renderTable(headers: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
    """Lay out the rows in columns as wide as the widest cell of each column."""
    COLUMN_GAP = '  '

    widths = [max(len(cell) for cell in column) for column in zip(headers, *rows, strict=True)]
    lines: list[str] = []
    for row in [headers, *rows]:
        cells = [cell.ljust(width) for cell, width in zip(row, widths, strict=True)]
        lines.append(COLUMN_GAP.join(cells).rstrip())

    return '\n'.join(lines)


def manifestEntry(outcome: ManifestOutcome) -> dict[str, object]:
    return {
        'path': str(outcome.path),
        'format': formatLabel(outcome),
        'packages': outcome.packages,
        'skipped': outcome.skipped,
        'error': outcome.error,
        'findings': len(outcome.findings),
    }


def findingEntry(finding: Finding) -> dict[str, object]:
    return {
        'manifest': str(finding.manifest),
        'package': finding.package,
        'version': finding.version,
        'kind': finding.kind.value,
        'detail': finding.detail,
    }


def formatLabel(outcome: ManifestOutcome) -> str:
    # A manifest that could not be read has no format, because no reader ever reported one.
    return outcome.format.value if outcome.format is not None else UNREADABLE_LABEL


def kindLabel(kind: FindingKind) -> str:
    match kind:
        case FindingKind.BANNED:
            return 'banned'
        case FindingKind.BELOW_MINIMUM:
            return 'below minimum'
        case FindingKind.DISALLOWED_SOURCE:
            return 'source not allowed'
