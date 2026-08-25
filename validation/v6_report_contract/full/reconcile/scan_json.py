"""Read a `*.scan.json` of the asset scanner, and construct the ScannedResource records it states.

    {"scanned_at": "2026-03-04T11:20:00Z",
     "resources": [{"id": "min-quartz-4471", "sku": "compute-standard-8",
                    "team": "platform-core", "region": "na1"}]}

The scanner names the owning team and no cost, so a ScannedResource carries no monthly_cents. Only
`resources` is read; every other key of the document, `scanned_at` among them, is ignored.

A resource is rejected, and the rest of the file still read, when it is not an object, when it
omits `id`, `sku`, `team` or `region`, when one of those four is not a string or is empty, or when
its `id` was already accepted on the scan side.
"""

from __future__ import annotations

import json
from collections.abc import Container
from pathlib import Path

from reconcile.logs import LOG
from reconcile.outcomes import describeFailedFile, describeReadFile
from reconcile.vocabulary import (
    FileContents,
    InventoryFormat,
    RegionName,
    RejectedRecordError,
    ResourceId,
    ScannedResource,
    Sku,
    TeamName,
)


SCAN_SUFFIX = '.scan.json'


def readScanFile(scan_json_path: Path, claimed_ids: set[ResourceId]) -> FileContents[ScannedResource]:
    """Read every entry of the `resources` list of one scan document.

    Args:
        claimed_ids: every resource_id the scan side has accepted so far, across the files already
            read. The call adds the ids it accepts to it.

    Returns:
        The accepted resources in document order, and the outcome to report for the file.
    """
    basename = scan_json_path.name
    try:
        scanned = json.loads(scan_json_path.read_text(encoding='utf-8'))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return FileContents((), describeFailedFile(basename, InventoryFormat.SCAN, f'unreadable: {exc}'))
    if not isinstance(scanned, dict) or not isinstance(scanned.get('resources'), list):
        problem = 'the top level is not an object holding a resources list'
        return FileContents((), describeFailedFile(basename, InventoryFormat.SCAN, problem))

    accepted: list[ScannedResource] = []
    problems: list[str] = []
    for position, entry in enumerate(scanned['resources'], start=1):
        try:
            resource = _readScannedResource(entry, basename, claimed_ids)
        except RejectedRecordError as exc:
            LOG.debug('record.rejected', extra={'path': basename, 'resource': position, 'reason': str(exc)})
            problems.append(f'resource {position}: {exc}')
            continue
        claimed_ids.add(resource.resource_id)
        accepted.append(resource)

    return FileContents(tuple(accepted), describeReadFile(basename, InventoryFormat.SCAN, len(accepted), problems))


def _readScannedResource(entry: object, source: str, claimed_ids: Container[ResourceId]) -> ScannedResource:
    """Construct one ScannedResource from one entry of the `resources` list.

    Raises:
        RejectedRecordError: the entry fails one of the conditions in the module docstring.
    """
    FIELDS = ('id', 'sku', 'team', 'region')
    if not isinstance(entry, dict):
        raise RejectedRecordError('not an object')
    for field in FIELDS:
        if field not in entry:
            raise RejectedRecordError(f'{field} is missing')
        if not isinstance(entry[field], str) or not entry[field]:
            raise RejectedRecordError(f'{field} is not a non-empty string')
    if ResourceId(entry['id']) in claimed_ids:
        raise RejectedRecordError(f'id {entry["id"]} already appeared on the scan side')

    return ScannedResource(
        ResourceId(entry['id']),
        Sku(entry['sku']),
        TeamName(entry['team']),
        RegionName(entry['region']),
        source,
    )
