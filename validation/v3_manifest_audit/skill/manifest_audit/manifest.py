"""Hold what a dependency manifest declares, and name the two formats this package reads.

A manifest declares one package per entry. The `requirements.lock` format declares a name and a
version. The `packages.json` format declares a name, a version and a source. A package that comes
from a lock file therefore has no source, and the source part of the policy does not apply to it.

The readers live in `requirements_lock.py` and `packages_json.py`. This module holds only what both
of them produce, so that neither reader has to import the other.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


LOCK_SUFFIX = '.lock'
PACKAGES_SUFFIX = '.json'

LOG = logging.getLogger(__name__)


def rejectManifest(path: Path, reason: str) -> ManifestError:
    """Log one rejected manifest and return the exception for the caller to raise.

    A manifest is one item of the batch, so the record is DEBUG. The caller counts the rejections
    and reports the total at WARNING, which is the number an operator can act on.
    """
    LOG.debug('manifest.rejected', extra={'manifest': str(path), 'reason': reason})
    return ManifestError(f'{path}: {reason}')


### vocabulary #########################################################################


class ManifestFormat(Enum):
    REQUIREMENTS_LOCK = 'requirements.lock'
    PACKAGES_JSON = 'packages.json'


class ManifestError(RuntimeError):
    """A manifest file could not be read, or its content is not the format its name promises."""


@dataclass(frozen=True)
class Package:
    name: str
    version: str
    source: str | None


@dataclass(frozen=True)
class ManifestContents:
    format: ManifestFormat
    packages: tuple[Package, ...]
    skipped: int
