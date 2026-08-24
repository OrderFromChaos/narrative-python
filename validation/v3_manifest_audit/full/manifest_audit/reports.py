"""Render one audit two ways: a table for a person, and a JSON document for a program.

Both carry the same facts. The table is padded to the widest cell in each column, and a manifest
path is shown relative to the audited directory:

    manifest         package    version  violation           detail
    service.lock     leftpad    1.0.0    banned              the policy bans this package
    service.lock     requests   2.28.1   below_minimum       below the minimum 2.31.0

    service.lock: 4 packages, 2 findings
    broken.json: FAILED, broken.json: not JSON: Expecting value at line 1

The JSON document has the same three parts: the directory, the flat list of findings, and one entry
per manifest with its outcome.
"""

from __future__ import annotations

import json
from pathlib import Path

from manifest_audit import audit
from manifest_audit.vocabulary import AuditReport, Finding, ManifestOutcome


def summaryTable(report: AuditReport) -> str:
    """Render the findings and the per-manifest outcomes as one padded table.

    Returns:
        The whole table, with no trailing newline.
    """
    HEADINGS = ('manifest', 'package', 'version', 'violation', 'detail')
    GAP = '  '

    rows: list[tuple[str, ...]] = [HEADINGS]
    for finding in audit.everyFinding(report.outcomes):
        rows.append(_findingRow(finding, report.manifest_directory))

    widths = [0] * len(HEADINGS)
    for row in rows:
        for column, cell in enumerate(row):
            widths[column] = max(widths[column], len(cell))

    # The table first, then a blank line, then one line per manifest, so a failed manifest is
    # visible even when it produced no findings at all.
    lines = []
    for row in rows:
        padded = [cell.ljust(width) for cell, width in zip(row, widths, strict=True)]
        lines.append(GAP.join(padded).rstrip())

    lines.append('')
    for outcome in report.outcomes:
        lines.append(_outcomeLine(outcome, report.manifest_directory))

    lines.append('')
    lines.append(_tallyLine(report))

    return '\n'.join(lines)


def writeReport(report: AuditReport, destination: Path) -> None:
    INDENT = 2

    document = {
        'manifest_directory': str(report.manifest_directory),
        'findings_stored': report.findings_stored,
        'findings': [_findingDocument(found) for found in audit.everyFinding(report.outcomes)],
        'manifests': [_outcomeDocument(outcome) for outcome in report.outcomes],
    }
    destination.write_text(json.dumps(document, indent=INDENT) + '\n', encoding='utf-8')


def _findingRow(finding: Finding, root: Path) -> tuple[str, ...]:
    return (
        _relativeTo(finding.manifest, root),
        finding.package,
        finding.version,
        finding.violation.value,
        finding.detail,
    )


def _outcomeLine(outcome: ManifestOutcome, root: Path) -> str:
    where = _relativeTo(outcome.manifest, root)
    if outcome.error is not None:
        return f'{where}: FAILED, {outcome.error}'

    return f'{where}: {outcome.packages_read} packages, {len(outcome.findings)} findings'


def _tallyLine(report: AuditReport) -> str:
    findings = len(audit.everyFinding(report.outcomes))
    failed = len([outcome for outcome in report.outcomes if outcome.error is not None])
    counted = f'{findings} findings across {len(report.outcomes)} manifests, {report.findings_stored} newly stored'

    return f'{counted}, {failed} manifests unreadable'


def _findingDocument(finding: Finding) -> dict[str, str]:
    return {
        'manifest': str(finding.manifest),
        'package': finding.package,
        'version': finding.version,
        'violation': finding.violation.value,
        'detail': finding.detail,
    }


def _outcomeDocument(outcome: ManifestOutcome) -> dict[str, object]:
    manifest_format = outcome.manifest_format.value if outcome.manifest_format is not None else None

    return {
        'manifest': str(outcome.manifest),
        'format': manifest_format,
        'packages_read': outcome.packages_read,
        'findings': len(outcome.findings),
        'error': outcome.error,
    }


def _relativeTo(path: Path, root: Path) -> str:
    # A path under the audited directory reads better shortened, and it stays the same string on
    # another machine. Anything outside that directory is printed whole.
    if root in path.parents:
        return str(path.relative_to(root))

    return str(path)
