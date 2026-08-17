"""Find the files under a directory tree that hold identical content.

The program groups every file by size, then hashes only inside a group that holds more than one
file. It reports each group of duplicates, the group that wastes the most space first, and the total
recoverable bytes. It counts a path it cannot read and then continues. A symlink is never a
candidate, because deleting one recovers no space.

The program exits 1 if it skipped any path, and it still prints the answer it reached. It also exits
1 if the root is not a directory, and then prints no answer at all. Each log record is one JSON
object on stderr. Without --verbose, stderr carries the tally alone. With it, each skipped path also
gets a record of its own.

Usage:
    $ python3 narrative.py /var/data
    $ python3 narrative.py /var/data --min-size 4096 --verbose
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import NewType


EXIT_SUCCESS = 0
EXIT_FAILURE = 1
DEFAULT_MIN_SIZE_BYTES = 1

LOG = logging.getLogger('duplicates')


def main() -> int:
    """Report files under a directory tree that have identical content.

    Returns:
        0 when every file under the root was inspected, 1 when the root is not a directory or any
        path had to be skipped -- the answer is still printed, it is just incomplete.
    """
    parser = argparse.ArgumentParser(description='Find duplicate files by content.')
    parser.add_argument('root', type=Path, help='directory to search, recursively')
    parser.add_argument(
        '--min-size',
        type=int,
        default=DEFAULT_MIN_SIZE_BYTES,
        help=f'ignore files smaller than this many bytes (default {DEFAULT_MIN_SIZE_BYTES})',
    )

    parser.add_argument('--verbose', action='store_true', help='log every skipped path, not just the tally')
    args = parser.parse_args()

    configureLogging(verbose=args.verbose)
    if not args.root.is_dir():
        print(f'{args.root} is not a directory', file=sys.stderr)
        return EXIT_FAILURE

    index = walkFiles(args.root, args.min_size)
    report = hashDuplicates(index)
    reportDuplicates(report)
    return EXIT_FAILURE if report.unreadable else EXIT_SUCCESS


def configureLogging(*, verbose: bool) -> None:
    global LOG
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(JsonlFormatter())
    LOG.addHandler(handler)
    LOG.setLevel(logging.DEBUG if verbose else logging.INFO)


def walkFiles(root: Path, min_size: int) -> SizeIndex:
    """Group every regular file under the root by its size in bytes.

    Grouping by size before hashing is what keeps the second pass cheap: a file whose size is unique
    in the tree cannot have a duplicate, and is therefore never opened at all.

    Args:
        root: Directory to walk. Symlinks are not followed, and directory loops cannot occur.
        min_size: Files smaller than this are left out entirely.

    Returns:
        Paths grouped by size, with a count of the paths that could not be inspected.
    """
    by_size: dict[int, list[Path]] = {}
    unreadable = 0

    def noteUnreadable(error: OSError) -> None:
        nonlocal unreadable
        unreadable += 1
        LOG.debug('path_skipped', extra={'fields': {'path': str(error.filename), 'error': str(error)}})

    for directory, _, names in os.walk(root, onerror=noteUnreadable):
        for name in names:
            path = Path(directory) / name
            # A symlink's bytes are its target's. Reporting it as a duplicate would offer to
            # recover space that deleting it does not actually free.
            if path.is_symlink():
                continue

            try:
                size = path.stat().st_size
            except OSError as exc:
                noteUnreadable(exc)
                continue

            if size >= min_size:
                by_size.setdefault(size, []).append(path)

    return SizeIndex({size: tuple(paths) for size, paths in by_size.items()}, unreadable)


def hashDuplicates(index: SizeIndex) -> DuplicateReport:
    """Hash the files inside each same-size group and keep the sets whose digests agree.

    Args:
        index: Paths grouped by size, as returned by walkFiles().

    Returns:
        One group per set of identical files, ordered by recoverable bytes, largest first, and the
        running total of skipped paths including the ones walkFiles() could not stat.
    """
    groups: list[DuplicateGroup] = []
    unreadable = index.unreadable
    for size, paths in index.by_size.items():
        if len(paths) < 2:
            continue

        by_digest: dict[Digest, list[Path]] = {}
        for path in paths:
            digest = fileDigest(path)
            if digest is None:
                unreadable += 1
                continue

            by_digest.setdefault(digest, []).append(path)

        groups.extend(
            DuplicateGroup(digest, size, tuple(sorted(same))) for digest, same in by_digest.items() if len(same) > 1
        )

    if unreadable:
        LOG.warning('paths_skipped', extra={'fields': {'skipped': unreadable, 'groups': len(groups)}})

    ordered = sorted(groups, key=lambda group: (-group.wastedBytes(), group.paths[0]))
    return DuplicateReport(tuple(ordered), unreadable)


def fileDigest(path: Path) -> Digest | None:
    # None rather than an exception: one unreadable file in a tree of 100,000 is a line in a tally,
    # not a reason to stop. hashlib.file_digest would do the chunking, but it is 3.11+.
    DIGEST_ALGORITHM = 'sha256'
    READ_CHUNK_BYTES = 1 << 20
    digest = hashlib.new(DIGEST_ALGORITHM)
    try:
        with path.open('rb') as handle:
            for chunk in iter(lambda: handle.read(READ_CHUNK_BYTES), b''):
                digest.update(chunk)
    except OSError as exc:
        LOG.debug('path_skipped', extra={'fields': {'path': str(path), 'error': str(exc)}})
        return None

    return Digest(digest.hexdigest())


def reportDuplicates(report: DuplicateReport) -> None:
    for group in report.groups:
        copies = len(group.paths)
        print(f'{group.wastedBytes()} bytes recoverable -- {copies} copies of {group.size_bytes} bytes')
        for path in group.paths:
            print(f'  {path}')

    recoverable = sum(group.wastedBytes() for group in report.groups)
    print(f'{len(report.groups)} duplicate groups, {recoverable} bytes recoverable, {report.unreadable} paths skipped')


### vocabulary #########################################################################

Digest = NewType('Digest', str)


@dataclass(frozen=True)
class SizeIndex:
    """Every candidate file in the tree, grouped by size, plus what the walk could not read."""

    by_size: Mapping[int, tuple[Path, ...]]
    unreadable: int


@dataclass(frozen=True)
class DuplicateGroup:
    """A set of files with identical content, all necessarily of the same size."""

    digest: Digest
    size_bytes: int
    paths: tuple[Path, ...]

    def wastedBytes(self) -> int:
        # One copy has to survive, so three 10-byte files waste 20 bytes and not 30.
        return self.size_bytes * (len(self.paths) - 1)


@dataclass(frozen=True)
class DuplicateReport:
    groups: tuple[DuplicateGroup, ...]
    unreadable: int


class JsonlFormatter(logging.Formatter):
    """Render each record as one JSON object per line, with the message as a stable event name."""

    def format(self, record: logging.LogRecord) -> str:
        # Nested rather than splatted: a field named 'level' or 'event' in the payload must not be
        # able to overwrite the record's own, and LogRecord attributes are a minefield besides.
        fields: Mapping[str, object] = getattr(record, 'fields', {})
        payload = {
            'time': datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            'level': record.levelname,
            'event': record.getMessage(),
            'fields': dict(fields),
        }

        return json.dumps(payload, default=str)


if __name__ == '__main__':
    sys.exit(main())
