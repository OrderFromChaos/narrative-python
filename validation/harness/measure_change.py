"""Measure what one change cost, by diffing a changed copy of an arm against the pristine arm.

    $ python3 measure_change.py validation/v5_billing_reconcile/full /tmp/.../full_C2

    files_touched  3
    files_added    0
    lines_added    41
    lines_removed  6
    churn          47

Only Python files count. A fixture, a database and a report are outputs of a run, not of the change,
so they are excluded. `git diff --no-index` does the comparison, so a file the change created shows
up as an addition rather than as a missing file.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


EXCLUDED_DIRECTORIES = frozenset({'__pycache__', 'fixture', '.git'})
EXIT_SUCCESS = 0
EXIT_UNUSABLE = 2


def main() -> int:
    """Print the cost of one change, and write it as JSON when asked.

    Returns:
        0 when the diff ran, 2 when either directory is missing.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('pristine', type=Path)
    parser.add_argument('changed', type=Path)
    parser.add_argument('--json', type=Path, help='also write the numbers here')
    arguments = parser.parse_args()

    for directory in (arguments.pristine, arguments.changed):
        if not directory.is_dir():
            print(f'not a directory: {directory}', file=sys.stderr)
            return EXIT_UNUSABLE

    cost = measureChange(arguments.pristine, arguments.changed)
    for field, value in cost.asDict().items():
        print(f'{field:<14} {value}')

    if arguments.json:
        arguments.json.write_text(json.dumps(cost.asDict(), indent=2) + '\n')

    return EXIT_SUCCESS


def measureChange(pristine: Path, changed: Path) -> ChangeCost:
    """Diff two copies of one package and total what moved.

    `git diff --no-index` exits 1 when it finds a difference, which is the expected case here, so
    the return code carries no error meaning and is ignored.
    """
    completed = subprocess.run(
        ['git', 'diff', '--no-index', '--numstat', str(pristine), str(changed)],
        capture_output=True,
        text=True,
        check=False,
    )

    touched: list[str] = []
    added_files = lines_added = lines_removed = 0
    for line in completed.stdout.splitlines():
        added_text, removed_text, path_text = line.split('\t', 2)
        if not countableFile(resultingPath(path_text)):
            continue

        touched.append(path_text)
        lines_added += int(added_text) if added_text != '-' else 0
        lines_removed += int(removed_text) if removed_text != '-' else 0
        if createdFile(path_text):
            added_files += 1

    return ChangeCost(
        files_touched=len(touched),
        files_added=added_files,
        lines_added=lines_added,
        lines_removed=lines_removed,
    )


def resultingPath(path_text: str) -> str:
    """Return the path a numstat line names after the change.

        prefix/{pristine => changed}/mod.py   ->  prefix/changed/mod.py
        /{dev/null => tmp/pkg/new.py}         ->  /tmp/pkg/new.py

    git compresses a path whose two sides share a prefix and a suffix, so the raw text ends in `}`
    for a created file and would fail a plain suffix test.
    """
    return re.sub(r'\{[^{}]*? => ([^{}]*?)\}', r'\1', path_text)


def createdFile(path_text: str) -> bool:
    # git names the absent side `/dev/null`, which is the only reliable marker: a modified file's
    # compressed path also contains ` => `.
    return 'dev/null => ' in path_text


def countableFile(path_text: str) -> bool:
    # A run writes a database and a JSON report beside the package. Those are outputs of running it,
    # not of changing it, and counting them would reward an arm that happens to write fewer files.
    if not path_text.endswith('.py'):
        return False
    return not any(part in EXCLUDED_DIRECTORIES for part in Path(path_text).parts)


### vocabulary #########################################################################


@dataclass(frozen=True)
class ChangeCost:
    """What one change cost, in files and in lines."""

    files_touched: int
    files_added: int
    lines_added: int
    lines_removed: int

    def asDict(self) -> dict[str, int]:
        return {
            'files_touched': self.files_touched,
            'files_added': self.files_added,
            'lines_added': self.lines_added,
            'lines_removed': self.lines_removed,
            'churn': self.lines_added + self.lines_removed,
        }


if __name__ == '__main__':
    sys.exit(main())
