"""Read one asset scan, and construct the Resource records that it found.

    {
      "scanned_at": "2026-08-24T09:00:00Z",
      "resources": [
        {"id": "vm-101", "sku": "compute-std", "team": "platform", "region": "use1"}
      ]
    }

`id` names the same thing as `resource_id` of a billing export. The scan names no cost, so every
record holds `monthly_cents=None`. `scanned_at` is not read.

The first malformed entry rejects the whole file, because a dropped entry becomes a resource that
the report calls unscanned.
"""

from __future__ import annotations

import json
from pathlib import Path

from reconcile.inventory import RegionName, Resource, ResourceId, Sku, TeamName, rejectInventory


SCAN_FIELDS = ('id', 'sku', 'team', 'region')


def readScannedResources(scan_path: Path) -> tuple[Resource, ...]:
    """Construct the Resource records that the scan at `scan_path` found.

    Raises:
        MalformedInventoryError: the file is unreadable, is not JSON, holds no `resources` list,
            or holds an entry that does not name every field of SCAN_FIELDS.
    """
    try:
        document: object = json.loads(scan_path.read_text(encoding='utf-8'))
    except OSError as exc:
        raise rejectInventory(scan_path, f'unreadable: {exc}') from exc
    except UnicodeDecodeError as exc:
        raise rejectInventory(scan_path, 'not UTF-8 text') from exc
    except json.JSONDecodeError as exc:
        raise rejectInventory(scan_path, f'not JSON: {exc}') from exc

    if not isinstance(document, dict):
        raise rejectInventory(scan_path, 'the top level is not an object')
    scanned = document.get('resources')
    if not isinstance(scanned, list):
        raise rejectInventory(scan_path, 'resources is not a list')

    return tuple(parseScanEntry(entry, index, scan_path) for index, entry in enumerate(scanned))


def parseScanEntry(entry: object, index: int, scan_path: Path) -> Resource:
    if not isinstance(entry, dict):
        raise rejectInventory(scan_path, f'resource {index} is a {type(entry).__name__}, and must be an object')

    # One loop over SCAN_FIELDS rather than four near-identical checks.
    named: dict[str, str] = {}
    for field in SCAN_FIELDS:
        value = entry.get(field)
        if not isinstance(value, str) or not value:
            raise rejectInventory(scan_path, f'resource {index} names no {field}')
        named[field] = value

    return Resource(
        resource_id=ResourceId(named['id']),
        sku=Sku(named['sku']),
        region=RegionName(named['region']),
        monthly_cents=None,
        team=TeamName(named['team']),
    )
