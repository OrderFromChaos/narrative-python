"""Read the `packages.json` format: a JSON object that holds a `packages` list.

Each entry declares three strings:

    {"packages": [{"name": "requests", "version": "2.32.0", "source": "pypi"}]}

An entry that omits one of the three is skipped and counted. A file that is not JSON, or whose top
level is not an object with a `packages` list, is rejected whole, because nothing in it can be
read as an entry.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from manifest_audit.manifest import ManifestContents, ManifestFormat, Package, rejectManifest


PACKAGES_KEY = 'packages'
ENTRY_KEYS = ('name', 'version', 'source')

LOG = logging.getLogger(__name__)


def readPackagesJson(path: Path) -> ManifestContents:
    """Read every declared package from a JSON manifest.

    Raises:
        ManifestError: the file could not be read, is not JSON, or holds no `packages` list.
    """
    try:
        text = path.read_text(encoding='utf-8')
    except OSError as exc:
        raise rejectManifest(path, f'cannot read the file: {exc}') from exc

    try:
        document = json.loads(text)
    except json.JSONDecodeError as exc:
        raise rejectManifest(path, f'the file is not valid JSON: {exc}') from exc

    if not isinstance(document, dict) or not isinstance(document.get(PACKAGES_KEY), list):
        raise rejectManifest(path, f'the top level is not an object with a {PACKAGES_KEY!r} list')

    packages: list[Package] = []
    skipped = 0
    for entry in document[PACKAGES_KEY]:
        package = packageFrom(entry)
        if package is None:
            LOG.debug('packages.entry_skipped', extra={'manifest': str(path), 'entry': repr(entry)})
            skipped += 1
            continue

        packages.append(package)

    if skipped:
        tally = {'manifest': str(path), 'skipped': skipped, 'kept': len(packages)}
        LOG.warning('packages.entries_skipped', extra=tally)

    return ManifestContents(ManifestFormat.PACKAGES_JSON, tuple(packages), skipped)


def packageFrom(entry: object) -> Package | None:
    # An entry is untrusted, so every field is checked here and nowhere downstream.
    if not isinstance(entry, dict):
        return None

    name, version, source = (entry.get(key) for key in ENTRY_KEYS)
    if not isinstance(name, str) or not isinstance(version, str) or not isinstance(source, str):
        return None

    return Package(name, version, source)
