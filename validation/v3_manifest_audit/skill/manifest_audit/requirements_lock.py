"""Read the `requirements.lock` format: one `name==version` per line.

A `#` starts a comment, and a blank line carries nothing. A line that holds no `==` is skipped and
counted, because one unusable line does not make the other lines wrong. The format declares no
source, so every package this reader returns has none.

Example input:

    # api service, pinned 2026-02-01
    requests==2.28.1
    flask==3.0.0
"""

from __future__ import annotations

import logging
from pathlib import Path

from manifest_audit.manifest import ManifestContents, ManifestFormat, Package, rejectManifest


COMMENT_MARKER = '#'
VERSION_SEPARATOR = '=='

LOG = logging.getLogger(__name__)


def readRequirementsLock(path: Path) -> ManifestContents:
    """Read every pinned package from a lock file.

    Raises:
        ManifestError: the file could not be read.
    """
    try:
        text = path.read_text(encoding='utf-8')
    except OSError as exc:
        raise rejectManifest(path, f'cannot read the file: {exc}') from exc

    packages: list[Package] = []
    skipped = 0
    for line in text.splitlines():
        entry = line.split(COMMENT_MARKER, maxsplit=1)[0].strip()
        if not entry:
            continue

        name, separator, version = entry.partition(VERSION_SEPARATOR)
        if not separator or not name.strip() or not version.strip():
            LOG.debug('lock.line_skipped', extra={'manifest': str(path), 'line': entry})
            skipped += 1
            continue

        packages.append(Package(name.strip(), version.strip(), None))

    if skipped:
        tally = {'manifest': str(path), 'skipped': skipped, 'kept': len(packages)}
        LOG.warning('lock.lines_skipped', extra=tally)

    return ManifestContents(ManifestFormat.REQUIREMENTS_LOCK, tuple(packages), skipped)
