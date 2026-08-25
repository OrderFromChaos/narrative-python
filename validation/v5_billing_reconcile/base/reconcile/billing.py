"""Reader for the finance export, `*.billing.csv`.

The file has a header row, then one line per charge:

    resource_id,sku,monthly_cents,region

The format carries a cost and no owning team.
"""

from __future__ import annotations

import csv
from pathlib import Path

from .model import BillingLine, MalformedInputError

SUFFIX = ".billing.csv"
COLUMNS = ("resource_id", "sku", "monthly_cents", "region")


def is_billing_file(path: Path) -> bool:
    return path.name.lower().endswith(SUFFIX)


def read_billing_file(path: Path) -> tuple[list[BillingLine], list[str]]:
    """Read one billing file.

    Returns the lines that parsed and a message for each line that did not. A
    bad line is skipped; the rest of the file is still read.

    Raises `MalformedInputError` if the file cannot be opened or its header does
    not name the four columns.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as error:
        raise MalformedInputError(f"cannot read file: {error}") from error

    reader = csv.DictReader(text.splitlines())
    header = reader.fieldnames
    if header is None:
        raise MalformedInputError("file is empty, expected a header row")

    present = {name.strip().lower() for name in header if name}
    missing = [column for column in COLUMNS if column not in present]
    if missing:
        raise MalformedInputError(
            "header does not name the columns " + ", ".join(missing)
        )

    lines: list[BillingLine] = []
    problems: list[str] = []
    for number, row in enumerate(reader, start=2):
        try:
            lines.append(_read_row(row, number, path.name))
        except ValueError as error:
            problems.append(f"line {number}: {error}")
    return lines, problems


def _read_row(row: dict[str, str | None], number: int, source: str) -> BillingLine:
    values = {
        (name or "").strip().lower(): (value or "").strip()
        for name, value in row.items()
        if name is not None
    }

    resource_id = values.get("resource_id", "")
    if not resource_id:
        raise ValueError("resource_id is empty")

    sku = values.get("sku", "")
    if not sku:
        raise ValueError(f"{resource_id}: sku is empty")

    raw_cents = values.get("monthly_cents", "")
    try:
        monthly_cents = int(raw_cents)
    except ValueError:
        raise ValueError(
            f"{resource_id}: monthly_cents is not a whole number: {raw_cents!r}"
        ) from None

    region = values.get("region", "")
    if not region:
        raise ValueError(f"{resource_id}: region is empty")

    return BillingLine(
        resource_id=resource_id,
        sku=sku,
        monthly_cents=monthly_cents,
        region=region,
        source=source,
    )
