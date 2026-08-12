#!/usr/bin/env python3
"""Find duplicate files under a directory tree by content.

Files are grouped by size first, since files of different sizes cannot be
identical. Within each size group the files are hashed: first a small prefix,
which separates most non-duplicates after one short read, then in full for the
candidates that survive. Groups are reported largest wasted space first, where
the waste of a group is the size of all but one of its members.

Symbolic links are never followed, and files sharing an inode (hard links) are
counted once, since deleting one of them recovers nothing.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import stat
import sys
from collections import defaultdict
from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import TextIO

PREFIX_BYTES = 8 * 1024
READ_CHUNK_BYTES = 1024 * 1024
HASH_NAME = "blake2b"


@dataclass(slots=True)
class Candidate:
    """A file that might have a duplicate somewhere else in the tree."""

    path: Path
    size: int


@dataclass(slots=True)
class DuplicateGroup:
    """Two or more files with identical content."""

    size: int
    paths: list[Path]

    @property
    def wasted(self) -> int:
        """Bytes recoverable by keeping one copy and deleting the rest."""
        return self.size * (len(self.paths) - 1)


@dataclass(slots=True)
class ScanResult:
    groups: list[DuplicateGroup] = field(default_factory=list)
    files_examined: int = 0
    skipped: list[tuple[Path, str]] = field(default_factory=list)

    @property
    def total_wasted(self) -> int:
        return sum(group.wasted for group in self.groups)


def collect_files(
    root: Path, minimum_size: int, skipped: list[tuple[Path, str]]
) -> list[Candidate]:
    """Walk ``root`` and return every regular file of at least ``minimum_size``.

    Directories and files we cannot stat or descend into are recorded in
    ``skipped`` rather than raising.
    """
    candidates: list[Candidate] = []
    seen_inodes: set[tuple[int, int]] = set()

    def on_error(error: OSError) -> None:
        skipped.append((Path(error.filename or root), error.strerror or str(error)))

    walker = os.walk(root, onerror=on_error, followlinks=False)
    for directory, _subdirectories, filenames in walker:
        for filename in filenames:
            path = Path(directory) / filename
            try:
                info = path.lstat()
            except OSError as error:
                skipped.append((path, error.strerror or str(error)))
                continue
            if not stat.S_ISREG(info.st_mode):
                continue  # symlink, socket, device: nothing to compare
            if info.st_size < minimum_size:
                continue
            if info.st_nlink > 1:
                identity = (info.st_dev, info.st_ino)
                if identity in seen_inodes:
                    continue
                seen_inodes.add(identity)
            candidates.append(Candidate(path, info.st_size))
    return candidates


def hash_file(path: Path, limit: int | None = None) -> str:
    """Hash a file's content, or its first ``limit`` bytes if given."""
    digest = hashlib.new(HASH_NAME)
    remaining = limit if limit is not None else -1
    with path.open("rb") as handle:
        while remaining != 0:
            size = READ_CHUNK_BYTES if remaining < 0 else min(READ_CHUNK_BYTES, remaining)
            chunk = handle.read(size)
            if not chunk:
                break
            digest.update(chunk)
            if remaining > 0:
                remaining -= len(chunk)
    return digest.hexdigest()


def group_by_hash(
    candidates: Sequence[Candidate],
    limit: int | None,
    skipped: list[tuple[Path, str]],
) -> Iterator[list[Candidate]]:
    """Yield the sub-groups of ``candidates`` whose hashes agree.

    ``limit`` is passed to :func:`hash_file`, so passing ``PREFIX_BYTES`` gives a
    cheap pre-filter and passing ``None`` compares whole files. Files that cannot
    be read are recorded in ``skipped`` and dropped.
    """
    buckets: dict[str, list[Candidate]] = defaultdict(list)
    for candidate in candidates:
        try:
            buckets[hash_file(candidate.path, limit)].append(candidate)
        except OSError as error:
            skipped.append((candidate.path, error.strerror or str(error)))
    for bucket in buckets.values():
        if len(bucket) > 1:
            yield bucket


def find_duplicates(root: Path, minimum_size: int = 1) -> ScanResult:
    """Scan ``root`` and return its duplicate groups, ordered by wasted space."""
    result = ScanResult()
    candidates = collect_files(root, minimum_size, result.skipped)
    result.files_examined = len(candidates)

    by_size: dict[int, list[Candidate]] = defaultdict(list)
    for candidate in candidates:
        by_size[candidate.size].append(candidate)

    for size, same_size in by_size.items():
        if len(same_size) < 2:
            continue
        for prefix_group in group_by_hash(same_size, PREFIX_BYTES, result.skipped):
            if size <= PREFIX_BYTES:
                # The prefix covered the whole file, so this group is final.
                identical: Iterator[list[Candidate]] = iter([prefix_group])
            else:
                identical = group_by_hash(prefix_group, None, result.skipped)
            for group in identical:
                result.groups.append(
                    DuplicateGroup(size, sorted(candidate.path for candidate in group))
                )

    result.groups.sort(key=lambda group: (group.wasted, group.size), reverse=True)
    return result


def format_size(size: int) -> str:
    """Render a byte count in the largest unit that keeps it readable."""
    value = float(size)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if abs(value) < 1024 or unit == "TiB":
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024
    raise AssertionError("unreachable")


def report(result: ScanResult, stream: TextIO) -> None:
    for group in result.groups:
        print(
            f"{len(group.paths)} copies of {format_size(group.size)}, "
            f"{format_size(group.wasted)} recoverable:",
            file=stream,
        )
        for path in group.paths:
            print(f"    {path}", file=stream)
        print(file=stream)

    print(f"examined {result.files_examined} file(s)", file=stream)
    print(
        f"found {len(result.groups)} duplicate group(s), "
        f"{format_size(result.total_wasted)} recoverable "
        f"({result.total_wasted} bytes)",
        file=stream,
    )
    if result.skipped:
        print(f"skipped {len(result.skipped)} unreadable path(s)", file=stream)


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("root", type=Path, help="directory to scan, recursively")
    parser.add_argument(
        "--min-size",
        type=int,
        default=1,
        metavar="BYTES",
        help="ignore files smaller than this (default: 1, which skips empty files)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="list every skipped path and why it was skipped",
    )
    args = parser.parse_args(argv)
    if args.min_size < 0:
        parser.error("--min-size must not be negative")
    return args


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.root.is_dir():
        print(f"error: {args.root} is not a directory", file=sys.stderr)
        return 2

    result = find_duplicates(args.root, args.min_size)
    report(result, sys.stdout)
    if args.verbose:
        for path, reason in result.skipped:
            print(f"skipped {path}: {reason}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
