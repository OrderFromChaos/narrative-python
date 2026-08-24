"""Read the text lockfile format: one `name==version` per line.

    # pinned by the release job
    requests==2.31.0
    leftpad==1.0.0

A blank line is ignored. Everything after a `#` on a line is ignored. Any other line rejects the
whole file, because a lockfile the parser cannot read is not a lockfile, and to audit the part it
did read would report a clean result for packages it never saw.

The format records no source. This module supplies the one the format implies, so the policy sees a
complete package.
"""

from __future__ import annotations

from pathlib import Path

from manifest_audit.errors import rejectManifest
from manifest_audit.vocabulary import DeclaredPackage, PackageName, SourceName, VersionText


# A `.lock` file is what a package installer writes, so its packages came from the index that
# installer was pointed at. Change this where the fleet installs from somewhere else.
_ASSUMED_SOURCE = SourceName('pypi')


def packagesIn(text: str, manifest: Path) -> tuple[DeclaredPackage, ...]:
    """Parse every declaration in a lockfile.

    Args:
        text: The whole file.
        manifest: Where it came from, for the rejection message.

    Returns:
        One record per declaration, in file order.

    Raises:
        ManifestError: A line is neither blank, nor a comment, nor `name==version`.
    """
    SEPARATOR = '=='
    COMMENT = '#'

    declared = []
    for number, line in enumerate(text.splitlines(), start=1):
        stripped = line.split(COMMENT, 1)[0].strip()
        if not stripped:
            continue

        name, separator, version = stripped.partition(SEPARATOR)
        if not separator or not name.strip() or not version.strip():
            reason = f'line {number} is not name{SEPARATOR}version: {stripped!r}'
            raise rejectManifest(manifest, reason)

        package = DeclaredPackage(
            name=PackageName(name.strip()),
            version=VersionText(version.strip()),
            source=_ASSUMED_SOURCE,
        )
        declared.append(package)

    return tuple(declared)
