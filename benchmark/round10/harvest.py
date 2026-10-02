"""Collect the comments of the corpus into `corpus.jsonl`, one record per comment block.

A block is one end-of-line comment, or a run of whole-line comments on consecutive lines at one
column. Pragmas, dividers and shebangs each get a separate `kind`, so a reader can filter them out.

Sources:
    fresh    every Python file in the generated arms and the tooling, as it stands
    history  comment blocks a later commit added to an existing tooling file
    edit     comments and docstrings an edit run added, diffed against its pristine copy

Usage:
    $ python3 benchmark/round10/harvest.py
    $ python3 benchmark/round10/harvest.py --edits /path/to/edits

An edit directory has `pristine/<arm>/` and one `<arm>_<change>/` per run.
"""

from __future__ import annotations

import argparse
import ast
import io
import json
import re
import statistics
import subprocess
import sys
import tokenize
from collections.abc import Iterator
from dataclasses import dataclass, field, replace
from enum import Enum
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
CORPUS_PATH = Path(__file__).resolve().parent / 'corpus.jsonl'
FRESH_PATHS = ('validation', 'experiment/length', 'benchmark/round3', 'skill', 'verify_docs.py')
HISTORY_PATHSPECS = (
    ':(glob)skill/*.py',
    'verify_docs.py',
    ':(glob)validation/*.py',
    ':(glob)validation/harness/**/*.py',
    ':(glob)experiment/length/*.py',
)
SKIPPED_PARTS = frozenset({'blind', 'fixture', 'run', '__pycache__', '.mypy_cache', '.ruff_cache', '.lintenv'})
EXIT_SUCCESS = 0
EXIT_UNUSABLE = 2


def main() -> int:
    """Harvest every source, write the corpus, and print a length summary per source and arm.

    Returns:
        0 when the corpus was written, 2 when `--edits` names no directory.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--edits', type=Path, help='directory of edit runs beside their pristine arms')
    arguments = parser.parse_args()

    if arguments.edits and not (arguments.edits / 'pristine').is_dir():
        print(f'no pristine/ under {arguments.edits}', file=sys.stderr)
        return EXIT_UNUSABLE

    blocks = [*harvestFresh(), *harvestHistory()]
    if arguments.edits:
        blocks.extend(harvestEdits(arguments.edits))

    records = countCopies(blocks)
    with CORPUS_PATH.open('w', encoding='utf-8') as corpus:
        for block, copies in records:
            corpus.write(json.dumps(block.asRecord(copies), ensure_ascii=False) + '\n')

    printSummary([block for block, _ in records])
    return EXIT_SUCCESS


def harvestFresh() -> Iterator[Block]:
    for path in sorted(pythonFiles()):
        relative = path.relative_to(REPO_ROOT)
        origin = Origin(file=str(relative), source=Source.FRESH, arm=armOf(relative))
        yield from extractBlocks(path.read_text(encoding='utf-8'), origin)


def pythonFiles() -> Iterator[Path]:
    for name in FRESH_PATHS:
        root = REPO_ROOT / name
        candidates = root.rglob('*.py') if root.is_dir() else [root]
        yield from (path for path in candidates if not SKIPPED_PARTS.intersection(path.parts))


def armOf(relative: Path) -> str:
    """Name the arm a corpus file belongs to, from where it sits.

            validation/v1_log_triage/skill.py                     ->  skill
            validation/v5_billing_reconcile/full/reconciler/x.py  ->  full
            experiment/length/t1/narrative.py                     ->  narrative
            benchmark/round3/p1_scan_ingest/a_procedural.py       ->  round3
            validation/score_arms.py                              ->  tooling

    A flat file under a validation task is a whole arm, so its stem is the arm's name.
    """
    parts = relative.parts
    if parts[0] == 'validation' and re.match(r'v\d+_', parts[1]):
        return parts[2] if len(parts) > 3 else relative.stem
    if parts[0] == 'experiment' and len(parts) == 4:
        return relative.stem
    if parts[0] == 'benchmark':
        return 'round3'
    return 'tooling'


def harvestHistory() -> Iterator[Block]:
    """Yield the blocks each commit added to a tooling file that already existed.

    A file a commit created is fresh writing, not an edit, and `harvestFresh` already reads its
    current text. The root commit has no parent to diff against and yields nothing.
    """
    commits = runGit('log', '--format=%h', '--', *HISTORY_PATHSPECS).split()
    for commit in commits:
        diff_text = runGit('diff-tree', '-p', '-U0', '--no-commit-id', '-r', commit, '--', *HISTORY_PATHSPECS)
        for file_name, change in parseAddedLines(diff_text).items():
            if change.created:
                continue

            origin = Origin(file=file_name, source=Source.HISTORY, arm=commit)
            source_text = runGit('show', f'{commit}:{file_name}')
            yield from addedBlocks(source_text, origin, change.lines)


def harvestEdits(edits_root: Path) -> Iterator[Block]:
    for run in sorted(edits_root.iterdir()):
        arm, _, change_name = run.name.partition('_')
        pristine = Path('pristine') / arm
        if not change_name or not (edits_root / pristine).is_dir():
            continue

        diff_text = runGit('diff', '--no-index', '-U0', str(pristine), run.name, cwd=edits_root)
        for file_name, change in parseAddedLines(diff_text).items():
            path = edits_root / file_name
            if path.suffix != '.py' or SKIPPED_PARTS.intersection(path.parts):
                continue

            origin = Origin(file=file_name, source=Source.EDIT, arm=run.name)
            yield from addedBlocks(path.read_text(encoding='utf-8'), origin, change.lines)


def runGit(*arguments: str, cwd: Path = REPO_ROOT) -> str:
    # `git diff --no-index` exits 1 whenever the two sides differ, which is the expected case. A
    # fixture can contain bytes that are not UTF-8, and only the Python hunks are read.
    completed = subprocess.run(
        ['git', *arguments],
        capture_output=True,
        text=True,
        errors='replace',
        check=False,
        cwd=cwd,
    )
    return completed.stdout


def parseAddedLines(diff_text: str) -> dict[str, AddedLines]:
    """Map each file a `-U0` diff touches to the line numbers it added on the new side.

            +++ b/v5base_C1/reconcile/ledger.py   ->  file v5base_C1/reconcile/ledger.py
            @@ -40,0 +41,3 @@                     ->  lines 41, 42, 43

    A file the diff created is marked, so a caller can tell an edit from fresh writing.
    """
    added: dict[str, AddedLines] = {}
    created = False
    current: AddedLines | None = None
    for line in diff_text.splitlines():
        if line.startswith('diff --git'):
            created = False
            current = None
        elif line.startswith('new file mode'):
            created = True
        elif line.startswith('+++ b/'):
            current = added.setdefault(line.removeprefix('+++ b/'), AddedLines(created=created))
        elif current and (hunk := re.match(r'@@ -\S+ \+(\d+)(?:,(\d+))? @@', line)):
            start = int(hunk[1])
            count = int(hunk[2]) if hunk[2] is not None else 1
            current.lines.update(range(start, start + count))

    return added


def addedBlocks(source_text: str, origin: Origin, added_lines: set[int]) -> Iterator[Block]:
    candidates = [*extractBlocks(source_text, origin), *extractDocstrings(source_text, origin)]
    yield from (block for block in candidates if added_lines.intersection(range(block.line, block.last_line + 1)))


def extractBlocks(source_text: str, origin: Origin) -> list[Block]:
    """Split a module's comments into blocks, merging whole-line comments that stack at one column.

    A file that does not tokenize contributes nothing, and its name goes to stderr.
    """
    blocks: list[Block] = []
    try:
        tokens = [token for token in tokenize.generate_tokens(io.StringIO(source_text).readline)]
    except (tokenize.TokenError, SyntaxError):
        print(f'not tokenizable, skipped: {origin.file}', file=sys.stderr)
        return blocks

    for token in tokens:
        if token.type != tokenize.COMMENT:
            continue

        row, column = token.start
        placement = Placement.INLINE if token.line[:column].strip() else Placement.ABOVE
        if blocks and blocks[-1].continuedBy(row, column, placement):
            blocks[-1] = replace(blocks[-1], lines=(*blocks[-1].lines, token.string), last_line=row)
            continue

        blocks.append(
            Block(
                origin=origin,
                line=row,
                last_line=row,
                column=column,
                lines=(token.string,),
                placement=placement,
                kind=classifyComment(token.string, row),
            ),
        )

    return blocks


def classifyComment(comment: str, row: int) -> Kind:
    if row == 1 and comment.startswith('#!'):
        return Kind.SHEBANG
    if re.match(r'#\s*(noqa|type:|pragma|fmt:|ruff:|pylint:|mypy:|isort:)', comment):
        return Kind.PRAGMA
    if re.search(r'[-=#~*]{4,}\s*$', comment) or not comment.strip('#').strip():
        return Kind.DIVIDER
    return Kind.PROSE


def extractDocstrings(source_text: str, origin: Origin) -> list[Block]:
    """Return one block per module, class and function docstring, spanning its source lines.

    A file that does not parse contributes nothing.
    """
    try:
        tree = ast.parse(source_text)
    except SyntaxError:
        return []

    blocks: list[Block] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue

        docstring = ast.get_docstring(node)
        if docstring is None:
            continue

        first = node.body[0]
        blocks.append(
            Block(
                origin=origin,
                line=first.lineno,
                last_line=first.end_lineno or first.lineno,
                column=first.col_offset,
                lines=(docstring,),
                placement=Placement.DOCSTRING,
                kind=Kind.DOCSTRING,
            ),
        )

    return blocks


def countCopies(blocks: list[Block]) -> list[tuple[Block, int]]:
    # The arms of one round share code, so one comment can sit in several files. The first copy
    # stands for all of them. A source counts separately, since a fresh comment can recur in an edit.
    copies: dict[CopyKey, list[Block]] = {}
    for block in blocks:
        key = CopyKey(source=block.origin.source, kind=block.kind, text=' '.join(block.text.lower().split()))
        copies.setdefault(key, []).append(block)

    return [(same[0], len(same)) for same in copies.values()]


def printSummary(blocks: list[Block]) -> None:
    print(f'{"source":8} {"arm":14} {"blocks":>6} {"median":>6} {"p90":>4} {"max":>4}')
    groups: dict[str, list[int]] = {}
    for block in blocks:
        if block.kind is not Kind.PROSE:
            continue

        arm = block.origin.arm if block.origin.source is Source.FRESH else block.origin.arm.split('_')[0]
        groups.setdefault(f'{block.origin.source.value:8} {arm:14}', []).append(block.words)

    for group, words in sorted(groups.items()):
        p90 = statistics.quantiles(words, n=10, method='inclusive')[-1] if len(words) > 1 else words[0]
        print(f'{group} {len(words):>6} {statistics.median(words):>6.0f} {p90:>4.0f} {max(words):>4}')


### vocabulary #########################################################################


class Source(Enum):
    FRESH = 'fresh'
    HISTORY = 'history'
    EDIT = 'edit'


class Kind(Enum):
    PROSE = 'prose'
    PRAGMA = 'pragma'
    DIVIDER = 'divider'
    SHEBANG = 'shebang'
    DOCSTRING = 'docstring'


class Placement(Enum):
    ABOVE = 'above'
    INLINE = 'inline'
    DOCSTRING = 'docstring'


@dataclass(frozen=True)
class Origin:
    """Where a block came from. `arm` is a commit hash for history and a run name for an edit."""

    file: str
    source: Source
    arm: str


@dataclass(frozen=True)
class CopyKey:
    source: Source
    kind: Kind
    text: str


@dataclass
class AddedLines:
    created: bool
    lines: set[int] = field(default_factory=set)


@dataclass(frozen=True)
class Block:
    origin: Origin
    line: int
    last_line: int
    column: int
    lines: tuple[str, ...]
    placement: Placement
    kind: Kind

    @property
    def text(self) -> str:
        if self.kind is Kind.DOCSTRING:
            return ' '.join(self.lines[0].split())
        return ' '.join(re.sub(r'^#+:?\s?', '', line.strip()) for line in self.lines)

    @property
    def words(self) -> int:
        return len(self.text.split())

    def continuedBy(self, row: int, column: int, placement: Placement) -> bool:
        stacked = row == self.last_line + 1 and column == self.column
        return stacked and placement is Placement.ABOVE and self.placement is Placement.ABOVE

    def asRecord(self, copies: int) -> dict[str, object]:
        return {
            'file': self.origin.file,
            'line': self.line,
            'text': self.text,
            'raw': '\n'.join(self.lines),
            'placement': self.placement.value,
            'kind': self.kind.value,
            'words': self.words,
            'sentences': len(re.findall(r'[.!?](?=\s|$)', self.text)) or 1,
            'source': self.origin.source.value,
            'arm': self.origin.arm,
            'copies': copies,
        }


if __name__ == '__main__':
    sys.exit(main())
