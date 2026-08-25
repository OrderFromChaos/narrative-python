"""Read one finance export, and construct the Resource records that its lines bill for.

    resource_id,sku,monthly_cents,region
    vm-101,compute-std,42000,us-east-1
    cache-301,redis-small,1200,us-east-1

The export names no owning team, so every record holds `team=None`. `monthly_cents` is a whole
number of cents per month, and may be negative for a credit. An empty line is skipped.

The first malformed line rejects the whole file. Every finding of the join is an absence, so a
half-read export reports resources as unscanned that the dropped lines account for.
"""

from __future__ import annotations

import csv
from collections.abc import Sequence
from pathlib import Path

from reconcile.inventory import Cents, RegionName, Resource, ResourceId, Sku, rejectInventory


BILLING_HEADER = ('resource_id', 'sku', 'monthly_cents', 'region')


def readBilledResources(billing_path: Path) -> tuple[Resource, ...]:
    """Construct the Resource records that the billing export at `billing_path` lists.

    Raises:
        MalformedInventoryError: the file is unreadable, the header differs from BILLING_HEADER,
            or a line holds the wrong number of fields or an unusable value.
    """
    try:
        text = billing_path.read_text(encoding='utf-8')
    except OSError as exc:
        raise rejectInventory(billing_path, f'unreadable: {exc}') from exc
    except UnicodeDecodeError as exc:
        raise rejectInventory(billing_path, 'not UTF-8 text') from exc

    rows = list(csv.reader(text.splitlines()))
    if not rows:
        raise rejectInventory(billing_path, 'the file holds no header')
    if tuple(rows[0]) != BILLING_HEADER:
        raise rejectInventory(billing_path, f'the header is {",".join(rows[0])!r}')

    return tuple(parseBillingRow(row, number, billing_path) for number, row in enumerate(rows[1:], start=2) if row)


def parseBillingRow(row: Sequence[str], line_number: int, billing_path: Path) -> Resource:
    if len(row) != len(BILLING_HEADER):
        raise rejectInventory(billing_path, f'line {line_number} holds {len(row)} of {len(BILLING_HEADER)} fields')
    resource_id, sku, monthly_cents, region = row
    if not resource_id:
        raise rejectInventory(billing_path, f'line {line_number} names no resource_id')
    if not monthly_cents.removeprefix('-').isdigit():
        raise rejectInventory(billing_path, f'line {line_number}: monthly_cents is not an integer: {monthly_cents!r}')

    return Resource(
        resource_id=ResourceId(resource_id),
        sku=Sku(sku),
        region=RegionName(region),
        monthly_cents=Cents(int(monthly_cents)),
        team=None,
    )
