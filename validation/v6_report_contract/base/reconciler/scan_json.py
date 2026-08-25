"""Reader for the asset scanner export, ``*.scan.json``.

The scanner carries the owning team and no cost. Its ``scanned_at`` stamp is
read past: the reconciliation compares inventories, not times.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import FileFormat, FileOutcome, FileStatus, ScannedResource

REQUIRED_FIELDS = ('id', 'sku', 'team', 'region')
"""Every field a scanned resource must carry, as a non-empty string."""


def read_scan_file(
    path: Path, accepted_resource_ids: set[str]
) -> tuple[list[ScannedResource], FileOutcome]:
    """Read one scan file and report what became of every resource.

    Args:
        path: The file to read.
        accepted_resource_ids: Every ``id`` already accepted on the scan side,
            across the files read so far. See :func:`~reconciler.billing_csv.read_billing_file`
            for how the set is used; the two sides keep separate sets, so the
            same id on both sides is a match rather than a repeat.

    Returns:
        The accepted records in file order, and the file's outcome.
    """
    outcome = FileOutcome(path=path.name, file_format=FileFormat.SCAN, status=FileStatus.OK)

    resources = _read_resource_list(path, outcome)
    if resources is None:
        return [], outcome

    records: list[ScannedResource] = []
    for position, entry in enumerate(resources):
        record = _read_resource(entry, path.name, position, outcome, accepted_resource_ids)
        if record is not None:
            records.append(record)
            accepted_resource_ids.add(record.resource_id)

    if outcome.rejected:
        outcome.status = FileStatus.PARTIAL
    outcome.accepted = len(records)
    return records, outcome


def _read_resource_list(path: Path, outcome: FileOutcome) -> list[Any] | None:
    """Return the file's ``resources`` list, or fail the whole file and return ``None``."""
    try:
        document = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, UnicodeDecodeError) as error:
        outcome.status = FileStatus.FAILED
        outcome.problems.append(f'{path.name}: unreadable ({error})')
        return None
    except json.JSONDecodeError as error:
        outcome.status = FileStatus.FAILED
        outcome.problems.append(f'{path.name}: is not valid JSON ({error})')
        return None

    if not isinstance(document, dict) or not isinstance(document.get('resources'), list):
        outcome.status = FileStatus.FAILED
        outcome.problems.append(f'{path.name}: is not an object holding a "resources" list')
        return None

    return document['resources']


def _read_resource(
    entry: Any,
    source: str,
    position: int,
    outcome: FileOutcome,
    accepted_resource_ids: set[str],
) -> ScannedResource | None:
    """Turn one ``resources`` entry into a record, or reject it and return ``None``."""
    where = f'{source} resource {position}'

    if not isinstance(entry, dict):
        outcome.reject(f'{where}: is not a JSON object')
        return None

    unusable = [
        name
        for name in REQUIRED_FIELDS
        if not isinstance(entry.get(name), str) or not entry[name]
    ]
    if unusable:
        outcome.reject(f'{where}: missing or empty {", ".join(unusable)}')
        return None

    resource_id = entry['id']
    if resource_id in accepted_resource_ids:
        outcome.reject(f'{where}: id {resource_id!r} already scanned, keeping the first')
        return None

    return ScannedResource(
        resource_id=resource_id,
        sku=entry['sku'],
        team=entry['team'],
        region=entry['region'],
        source=source,
    )
