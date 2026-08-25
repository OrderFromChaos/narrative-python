"""The summary table printed to stdout.

This is the human-facing output. It says the same thing as the JSON report and
is free to say it differently: the report is the contract, the table is the
reading of it. A cell the finding does not carry reads ``-``.
"""

from __future__ import annotations

import sys
from collections.abc import Sequence
from typing import TextIO

from .models import FileOutcome, Finding, FindingKind
from .pipeline import ReconcileResult

ABSENT = '-'
"""What a cell reads when the finding carries no value for it."""

_FINDING_HEADINGS = (
    'kind',
    'resource',
    'sku',
    'team',
    'monthly',
    'billed_region',
    'scanned_region',
    'grace',
)
_FILE_HEADINGS = ('file', 'format', 'status', 'accepted', 'rejected', 'problems')


def print_summary(result: ReconcileResult, stream: TextIO | None = None) -> None:
    """Print the findings, the per-file outcomes and the totals."""
    out = stream if stream is not None else sys.stdout

    _section(out, 'FINDINGS')
    if result.findings:
        _table(out, _FINDING_HEADINGS, [_finding_row(finding) for finding in result.findings])
        print('\nmonthly is in cents; grace: over = above the grace, within = at or below it', file=out)
    else:
        print('none', file=out)

    _section(out, 'FILES')
    if result.files:
        _table(out, _FILE_HEADINGS, [_file_row(outcome) for outcome in result.files])
        _problems(out, result.files)
    else:
        print('no inventory files in the input directory', file=out)

    _section(out, 'TOTALS')
    _totals(out, result)


def _finding_row(finding: Finding) -> tuple[str, ...]:
    return (
        finding.kind.value,
        finding.resource_id,
        finding.sku,
        finding.team or ABSENT,
        ABSENT if finding.monthly_cents is None else f'{finding.monthly_cents}c',
        finding.billed_region or ABSENT,
        finding.scanned_region or ABSENT,
        _grace_cell(finding),
    )


def _grace_cell(finding: Finding) -> str:
    """Say where a finding sits relative to the grace, or that the grace does not apply.

    Only a ``billed_not_found`` can be over the grace, so it is the only kind
    for which the cell says anything.
    """
    if finding.kind is not FindingKind.BILLED_NOT_FOUND:
        return ABSENT
    return 'over' if finding.above_grace else 'within'


def _file_row(outcome: FileOutcome) -> tuple[str, ...]:
    return (
        outcome.path,
        outcome.file_format.value,
        outcome.status.value,
        str(outcome.accepted),
        str(outcome.rejected),
        str(len(outcome.problems)),
    )


def _problems(out: TextIO, files: Sequence[FileOutcome]) -> None:
    """List every problem string under the file it belongs to."""
    reported = [outcome for outcome in files if outcome.problems]
    if not reported:
        return
    print('\nproblems:', file=out)
    for outcome in reported:
        for problem in outcome.problems:
            print(f'  {problem}', file=out)


def _totals(out: TextIO, result: ReconcileResult) -> None:
    totals = result.totals
    lines = [
        f'billing lines      {totals.billing_lines} '
        f'({totals.ignored_billing} ignored by sku)',
        f'scanned resources  {totals.scanned_resources} '
        f'({totals.ignored_scanned} ignored by sku)',
        f'matched pairs      {totals.matched}',
        f'findings           {totals.findings} '
        f'({totals.above_grace} above the {result.rules.grace_cents}c grace)',
    ]
    lines += [
        f'  {kind.value:<18} {count}' for kind, count in result.totals.by_kind.items()
    ]
    lines.append(f'exit code          {result.exit_code}')
    for line in lines:
        print(line, file=out)


def _section(out: TextIO, heading: str) -> None:
    print(f'\n{heading}\n{"=" * len(heading)}', file=out)


def _table(out: TextIO, headings: Sequence[str], rows: Sequence[Sequence[str]]) -> None:
    """Print a table whose columns are wide enough for their widest cell."""
    widths = [
        max([len(heading), *(len(row[column]) for row in rows)])
        for column, heading in enumerate(headings)
    ]
    print(_row(headings, widths), file=out)
    print(_row(['-' * width for width in widths], widths), file=out)
    for row in rows:
        print(_row(row, widths), file=out)


def _row(cells: Sequence[str], widths: Sequence[int]) -> str:
    return '  '.join(cell.ljust(width) for cell, width in zip(cells, widths)).rstrip()
