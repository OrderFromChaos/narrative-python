"""Read a `*.billing.csv` file from the finance export into InventoryRecords.

    resource_id,sku,monthly_cents,region
    i-0001,compute-std,120000,us-east-1

A billing line carries a cost and no owning team, so `team` is None on every record this module
builds. A wrong header stops the file. A line with the wrong field count or a non-integer cost is
rejected on its own and counted.
"""

from __future__ import annotations

import csv
from pathlib import Path

from reconciler.logs import LOG
from reconciler.vocabulary import (
    Cents,
    FileRead,
    InventoryFileError,
    InventoryFormat,
    InventoryLineError,
    InventoryRecord,
    RegionName,
    ResourceId,
    Sku,
)


_BILLING_COLUMNS = ('resource_id', 'sku', 'monthly_cents', 'region')


def readBillingLines(billing_path: Path) -> FileRead:
    """Parse every line of one billing export.

    Returns:
        The accepted records in file order, and the count of lines rejected.

    Raises:
        InventoryFileError: the file could not be read, or its header is not the export's header.
    """
    try:
        billing_text = billing_path.read_text(encoding='utf-8')
    except UnicodeDecodeError as exc:
        raise _rejectBillingFile(billing_path, 'the file is not UTF-8 text') from exc
    except OSError as exc:
        raise _rejectBillingFile(billing_path, 'the file could not be read') from exc

    lines = csv.reader(billing_text.splitlines())
    header = next(lines, None)
    if header != list(_BILLING_COLUMNS):
        raise _rejectBillingFile(billing_path, f'the header row is {header}, not {list(_BILLING_COLUMNS)}')

    records = []
    rejected_lines = 0
    for line_number, fields in enumerate(lines, start=2):
        if not fields:
            continue
        try:
            records.append(_parseBillingLine(fields, billing_path, line_number))
        except InventoryLineError:
            rejected_lines += 1

    return FileRead(records=tuple(records), rejected_lines=rejected_lines)


def _parseBillingLine(fields: list[str], billing_path: Path, line_number: int) -> InventoryRecord:
    if len(fields) != len(_BILLING_COLUMNS):
        raise _rejectBillingLine(billing_path, line_number, f'{len(fields)} fields, not {len(_BILLING_COLUMNS)}')
    resource_id, sku, monthly_cents, region = (field.strip() for field in fields)
    if not resource_id:
        raise _rejectBillingLine(billing_path, line_number, 'the resource_id is empty')
    if not monthly_cents.removeprefix('-').isdigit():
        raise _rejectBillingLine(billing_path, line_number, f'monthly_cents is {monthly_cents!r}, not an integer')

    return InventoryRecord(
        resource_id=ResourceId(resource_id),
        sku=Sku(sku),
        region=RegionName(region),
        origin=InventoryFormat.BILLING_CSV,
        monthly_cents=Cents(int(monthly_cents)),
        team=None,
    )


def _rejectBillingLine(billing_path: Path, line_number: int, reason: str) -> InventoryLineError:
    LOG.debug('billing.line_rejected', extra={'path': str(billing_path), 'line': line_number, 'reason': reason})
    return InventoryLineError(reason)


def _rejectBillingFile(billing_path: Path, reason: str) -> InventoryFileError:
    LOG.debug('billing.file_rejected', extra={'path': str(billing_path), 'reason': reason})
    return InventoryFileError(reason)
