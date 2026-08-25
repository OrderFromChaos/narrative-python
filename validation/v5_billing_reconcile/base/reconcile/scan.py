"""Reader for the asset scanner export, `*.scan.json`.

The file holds one object:

    {"scanned_at": ..., "resources": [{"id": ..., "sku": ..., "team": ...,
                                       "region": ...}]}

The format carries an owning team and no cost. The `id` field names the same
thing as `resource_id` in the billing format.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .model import MalformedInputError, ScannedResource

SUFFIX = ".scan.json"
FIELDS = ("id", "sku", "team", "region")


def is_scan_file(path: Path) -> bool:
    return path.name.lower().endswith(SUFFIX)


def read_scan_file(path: Path) -> tuple[list[ScannedResource], list[str]]:
    """Read one scan file.

    Returns the resources that parsed and a message for each entry that did
    not. A bad entry is skipped; the rest of the file is still read.

    Raises `MalformedInputError` if the file cannot be opened, is not valid
    JSON, or has no `resources` list.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as error:
        raise MalformedInputError(f"cannot read file: {error}") from error

    try:
        raw = json.loads(text)
    except json.JSONDecodeError as error:
        raise MalformedInputError(f"file is not valid JSON: {error}") from error

    if not isinstance(raw, dict):
        raise MalformedInputError("file must hold a JSON object")

    resources = raw.get("resources")
    if not isinstance(resources, list):
        raise MalformedInputError("file has no resources list")

    scanned: list[ScannedResource] = []
    problems: list[str] = []
    for index, entry in enumerate(resources):
        try:
            scanned.append(_read_resource(entry, path.name))
        except ValueError as error:
            problems.append(f"resources[{index}]: {error}")
    return scanned, problems


def _read_resource(entry: Any, source: str) -> ScannedResource:
    if not isinstance(entry, dict):
        raise ValueError("entry is not an object")

    values: dict[str, str] = {}
    for name in FIELDS:
        value = entry.get(name)
        if value is None:
            raise ValueError(f"{name} is absent")
        if not isinstance(value, str):
            raise ValueError(f"{name} is not a string")
        text = value.strip()
        if not text:
            raise ValueError(f"{name} is empty")
        values[name] = text

    return ScannedResource(
        resource_id=values["id"],
        sku=values["sku"],
        team=values["team"],
        region=values["region"],
        source=source,
    )
