"""Find the manifests in a directory, and read each one in the format its name declares.

The file suffix names the format. `.lock` is the text format that `requirements_lock` reads, and
`.json` is the object format that `packages_json` reads. Every other file in the directory is
rejected as unrecognised, and the run continues with the rest.

This is the only module that knows both formats exist. A third format is two edits: a member of
`ManifestFormat`, and an arm in each `match` below. Neither `match` carries a `case _`, so the type
check fails until both arms exist, and detection then picks the new suffix up on its own.
"""

from __future__ import annotations

from pathlib import Path

from manifest_audit import packages_json, requirements_lock
from manifest_audit.errors import rejectManifest
from manifest_audit.vocabulary import DeclaredPackage, ManifestFormat


def pathsIn(directory: Path) -> list[Path]:
    # Sorted, so the summary table and the JSON report keep one order across runs and diff cleanly.
    return sorted(path for path in directory.iterdir() if path.is_file())


def packagesIn(manifest: Path) -> tuple[DeclaredPackage, ...]:
    """Read one manifest in whichever format it is.

    Args:
        manifest: The file to read.

    Returns:
        Every package the file declares.

    Raises:
        ManifestError: The suffix names no format, the file is unreadable, or the content did not
            fit the format.
    """
    manifest_format = formatOf(manifest)
    if manifest_format is None:
        raise rejectManifest(manifest, f'unrecognised format for suffix {manifest.suffix!r}')

    try:
        text = manifest.read_text(encoding='utf-8')
    except OSError as exc:
        raise rejectManifest(manifest, f'unreadable: {exc.strerror}') from exc
    except UnicodeDecodeError as exc:
        raise rejectManifest(manifest, f'not UTF-8: {exc.reason}') from exc

    match manifest_format:
        case ManifestFormat.REQUIREMENTS_LOCK:
            return requirements_lock.packagesIn(text, manifest)
        case ManifestFormat.PACKAGES_JSON:
            return packages_json.packagesIn(text, manifest)


def formatOf(manifest: Path) -> ManifestFormat | None:
    # Driven from the enum rather than from a suffix mapping. A mapping from suffix to member lets
    # a new member exist that nothing detects, and no tool reports that.
    for candidate in ManifestFormat:
        if _suffixOf(candidate) == manifest.suffix:
            return candidate

    return None


def _suffixOf(manifest_format: ManifestFormat) -> str:
    match manifest_format:
        case ManifestFormat.REQUIREMENTS_LOCK:
            return '.lock'
        case ManifestFormat.PACKAGES_JSON:
            return '.json'
