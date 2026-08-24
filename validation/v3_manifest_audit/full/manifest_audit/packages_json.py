"""Read the object lockfile format.

    {"packages": [{"name": "requests", "version": "2.31.0", "source": "pypi"}]}

The three fields are all required and all must be strings. An entry that misses one rejects the
whole file, for the reason `requirements_lock` gives: a partial read reports a clean result for the
packages it never saw.

Unlike the text format, this one records the source, so nothing is assumed here.
"""

from __future__ import annotations

import json
from pathlib import Path

from manifest_audit.errors import rejectManifest
from manifest_audit.vocabulary import DeclaredPackage, PackageName, SourceName, VersionText


def packagesIn(text: str, manifest: Path) -> tuple[DeclaredPackage, ...]:
    """Parse every entry in a packages document.

    Args:
        text: The whole file.
        manifest: Where it came from, for the rejection message.

    Returns:
        One record per entry, in document order.

    Raises:
        ManifestError: The text is not JSON, or an entry does not carry three string fields.
    """
    PACKAGES_KEY = 'packages'

    try:
        document = json.loads(text)
    except json.JSONDecodeError as exc:
        raise rejectManifest(manifest, f'not JSON: {exc.msg} at line {exc.lineno}') from exc

    if not isinstance(document, dict):
        raise rejectManifest(manifest, f'the top level is {type(document).__name__}, not an object')

    entries = document.get(PACKAGES_KEY)
    if not isinstance(entries, list):
        raise rejectManifest(manifest, f'{PACKAGES_KEY} is missing, or it is not a list')

    declared = []
    for position, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise rejectManifest(manifest, f'package {position} is {type(entry).__name__}, not an object')

        # One guard for the three fields. Three separate guards would say the same thing three
        # times, and the message already names which field is wrong once the reader opens the file.
        name = entry.get('name')
        version = entry.get('version')
        source = entry.get('source')
        if not isinstance(name, str) or not isinstance(version, str) or not isinstance(source, str):
            raise rejectManifest(manifest, f'package {position} needs a string name, version and source')

        package = DeclaredPackage(
            name=PackageName(name),
            version=VersionText(version),
            source=SourceName(source),
        )
        declared.append(package)

    return tuple(declared)
