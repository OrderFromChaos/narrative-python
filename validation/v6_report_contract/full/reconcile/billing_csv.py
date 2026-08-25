"""Read a `*.billing.csv` of the finance export, and construct the BillingLine records it states.

    resource_id,sku,monthly_cents,region
    min-quartz-4471,compute-standard-8,182400,na1
    min-agate-2216,dns-zone,3300,NA1

The header row is mandatory and its four fields are read by position. A file with any other first
row states no records at all. The export names no owning team, so a BillingLine carries none.

A row is rejected, and the rest of the file still read, when it does not hold exactly four fields,
when `monthly_cents` is not a run of ASCII digits, when any other field is empty, or when its
`resource_id` was already accepted on the billing side. An empty row is not a record.
"""

from __future__ import annotations

from collections.abc import Container
from pathlib import Path

from reconcile.logs import LOG
from reconcile.outcomes import describeFailedFile, describeReadFile
from reconcile.vocabulary import (
    BillingLine,
    Cents,
    FileContents,
    InventoryFormat,
    RegionName,
    RejectedRecordError,
    ResourceId,
    Sku,
)


BILLING_SUFFIX = '.billing.csv'


def readBillingFile(billing_csv_path: Path, claimed_ids: set[ResourceId]) -> FileContents[BillingLine]:
    """Read every row of one billing export.

    Args:
        claimed_ids: every resource_id the billing side has accepted so far, across the files
            already read. The call adds the ids it accepts to it.

    Returns:
        The accepted lines in file order, and the outcome to report for the file.
    """
    HEADER = 'resource_id,sku,monthly_cents,region'
    basename = billing_csv_path.name
    try:
        exported_text = billing_csv_path.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError) as exc:
        return FileContents((), describeFailedFile(basename, InventoryFormat.BILLING, f'unreadable: {exc}'))
    rows = exported_text.splitlines()
    if not rows or rows[0] != HEADER:
        problem = f'the first row is not the header {HEADER}'
        return FileContents((), describeFailedFile(basename, InventoryFormat.BILLING, problem))

    accepted: list[BillingLine] = []
    problems: list[str] = []
    for row_number, row in enumerate(rows[1:], start=2):
        if not row:
            continue
        try:
            line = _readBillingLine(row, basename, claimed_ids)
        except RejectedRecordError as exc:
            LOG.debug('record.rejected', extra={'path': basename, 'row': row_number, 'reason': str(exc)})
            problems.append(f'row {row_number}: {exc}')
            continue
        claimed_ids.add(line.resource_id)
        accepted.append(line)

    return FileContents(tuple(accepted), describeReadFile(basename, InventoryFormat.BILLING, len(accepted), problems))


def _readBillingLine(row: str, source: str, claimed_ids: Container[ResourceId]) -> BillingLine:
    """Construct one BillingLine from one comma-separated row.

    Raises:
        RejectedRecordError: the row fails one of the conditions in the module docstring.
    """
    FIELD_COUNT = 4
    fields = row.split(',')
    if len(fields) != FIELD_COUNT:
        raise RejectedRecordError(f'{len(fields)} fields, expected {FIELD_COUNT}')
    resource_id, sku, monthly_cents, region = fields

    if not resource_id or not sku or not region:
        raise RejectedRecordError('resource_id, sku or region is empty')
    if not (monthly_cents.isascii() and monthly_cents.isdigit()):
        raise RejectedRecordError(f'monthly_cents {monthly_cents!r} is not a non-negative base-ten integer')
    if ResourceId(resource_id) in claimed_ids:
        raise RejectedRecordError(f'resource_id {resource_id} already appeared on the billing side')

    return BillingLine(ResourceId(resource_id), Sku(sku), Cents(int(monthly_cents)), RegionName(region), source)
