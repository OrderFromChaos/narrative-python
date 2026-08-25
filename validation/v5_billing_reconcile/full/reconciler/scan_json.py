"""Read a `*.scan.json` file from the asset scanner into InventoryRecords.

    {"scanned_at": "2026-08-24T03:00:00Z",
     "resources": [{"id": "i-0001", "sku": "compute-std", "team": "platform", "region": "use1"}]}

A scanned resource carries the owning team and no cost, so `monthly_cents` is None on every record
this module builds. Malformed JSON stops the file. One resource entry that states no `id`, or a
field that is not a string, is rejected on its own and counted.
"""

from __future__ import annotations

import json
from pathlib import Path

from reconciler.logs import LOG
from reconciler.vocabulary import (
    FileRead,
    InventoryFileError,
    InventoryFormat,
    InventoryLineError,
    InventoryRecord,
    RegionName,
    ResourceId,
    Sku,
    TeamName,
)


_SCAN_KEYS = ('id', 'sku', 'team', 'region')


def readScannedResources(scan_path: Path) -> FileRead:
    """Parse every resource entry of one scanner export.

    Returns:
        The accepted records in file order, and the count of entries rejected.

    Raises:
        InventoryFileError: the file could not be read, is not JSON, or states no resource list.
    """
    try:
        scan_text = scan_path.read_text(encoding='utf-8')
    except UnicodeDecodeError as exc:
        raise _rejectScanFile(scan_path, 'the file is not UTF-8 text') from exc
    except OSError as exc:
        raise _rejectScanFile(scan_path, 'the file could not be read') from exc

    try:
        stated = json.loads(scan_text)
    except json.JSONDecodeError as exc:
        raise _rejectScanFile(scan_path, f'not valid JSON: {exc.msg}, line {exc.lineno}') from exc

    if not isinstance(stated, dict):
        raise _rejectScanFile(scan_path, 'the file holds something other than a JSON object')
    if not isinstance(stated.get('resources'), list):
        raise _rejectScanFile(scan_path, '"resources" is absent or is not a list')

    records = []
    rejected_lines = 0
    for index, entry in enumerate(stated['resources']):
        try:
            records.append(_parseScannedResource(entry, scan_path, index))
        except InventoryLineError:
            rejected_lines += 1

    return FileRead(records=tuple(records), rejected_lines=rejected_lines)


def _parseScannedResource(entry: object, scan_path: Path, index: int) -> InventoryRecord:
    if not isinstance(entry, dict):
        raise _rejectScanEntry(scan_path, index, 'the entry is not a JSON object')
    unusable = [key for key in _SCAN_KEYS if not isinstance(entry.get(key), str)]
    if unusable:
        raise _rejectScanEntry(scan_path, index, f'no string {", no string ".join(unusable)}')
    if not entry['id'].strip():
        raise _rejectScanEntry(scan_path, index, 'the id is empty')

    return InventoryRecord(
        resource_id=ResourceId(entry['id'].strip()),
        sku=Sku(entry['sku'].strip()),
        region=RegionName(entry['region'].strip()),
        origin=InventoryFormat.SCAN_JSON,
        monthly_cents=None,
        team=TeamName(entry['team'].strip()),
    )


def _rejectScanEntry(scan_path: Path, index: int, reason: str) -> InventoryLineError:
    LOG.debug('scan.entry_rejected', extra={'path': str(scan_path), 'entry': index, 'reason': reason})
    return InventoryLineError(reason)


def _rejectScanFile(scan_path: Path, reason: str) -> InventoryFileError:
    LOG.debug('scan.file_rejected', extra={'path': str(scan_path), 'reason': reason})
    return InventoryFileError(reason)
