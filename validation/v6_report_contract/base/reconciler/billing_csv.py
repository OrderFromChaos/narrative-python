"""Reader for the finance export, ``*.billing.csv``.

The export carries a cost and no owning team. Fields are read by position, so
the header is checked once and then discarded.
"""

from __future__ import annotations

import csv
import io
import re
from pathlib import Path

from .models import BillingLine, FileFormat, FileOutcome, FileStatus

HEADER = ['resource_id', 'sku', 'monthly_cents', 'region']
"""The exact header row a billing file must open with."""

_DIGITS = re.compile(r'[0-9]+')
"""``monthly_cents`` is a run of ASCII digits and nothing else.

No sign, no surrounding space and no underscore, which rules out the several
spellings ``int()`` would otherwise accept.
"""


def read_billing_file(
    path: Path, accepted_resource_ids: set[str]
) -> tuple[list[BillingLine], FileOutcome]:
    """Read one billing file and report what became of every row.

    Args:
        path: The file to read.
        accepted_resource_ids: Every ``resource_id`` already accepted on the
            billing side, across the files read so far. A row repeating one of
            them is rejected, and an accepted row adds its own. The caller owns
            this set and it is updated in place, which is what makes the
            first-record-wins rule hold across files as well as within one.

    Returns:
        The accepted records in file order, and the file's outcome.
    """
    outcome = FileOutcome(path=path.name, file_format=FileFormat.BILLING, status=FileStatus.OK)

    try:
        raw_text = path.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError) as error:
        outcome.status = FileStatus.FAILED
        outcome.problems.append(f'{path.name}: unreadable ({error})')
        return [], outcome

    rows = csv.reader(io.StringIO(raw_text, newline=''))
    if next(rows, None) != HEADER:
        outcome.status = FileStatus.FAILED
        outcome.problems.append(
            f'{path.name}: does not open with the header {",".join(HEADER)}'
        )
        return [], outcome

    records: list[BillingLine] = []
    for row in rows:
        # A blank line is not a record. Without this, every file that ends in a
        # newline would reject a phantom row.
        if not row:
            continue
        record = _read_row(row, path.name, rows.line_num, outcome, accepted_resource_ids)
        if record is not None:
            records.append(record)
            accepted_resource_ids.add(record.resource_id)

    if outcome.rejected:
        outcome.status = FileStatus.PARTIAL
    outcome.accepted = len(records)
    return records, outcome


def _read_row(
    row: list[str],
    source: str,
    line_number: int,
    outcome: FileOutcome,
    accepted_resource_ids: set[str],
) -> BillingLine | None:
    """Turn one data row into a record, or reject it and return ``None``."""
    where = f'{source} line {line_number}'

    if len(row) != 4:
        outcome.reject(f'{where}: holds {len(row)} fields, not 4')
        return None

    resource_id, sku, monthly_cents, region = row

    empty = [
        name
        for name, value in (('resource_id', resource_id), ('sku', sku), ('region', region))
        if not value
    ]
    if empty:
        outcome.reject(f'{where}: empty {", ".join(empty)}')
        return None

    if not _DIGITS.fullmatch(monthly_cents):
        outcome.reject(f'{where}: monthly_cents {monthly_cents!r} is not a whole number of cents')
        return None

    if resource_id in accepted_resource_ids:
        outcome.reject(f'{where}: resource_id {resource_id!r} already billed, keeping the first')
        return None

    return BillingLine(
        resource_id=resource_id,
        sku=sku,
        monthly_cents=int(monthly_cents),
        region=region,
        source=source,
    )
