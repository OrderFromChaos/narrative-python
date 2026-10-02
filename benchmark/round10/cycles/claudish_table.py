"""Recompute the Claudish feature table, per 100 comment blocks, for human code and recent cycles.

Usage:
    $ python3 claudish_table.py 7     # cycles 7 and later
"""

import io
import re
import statistics
import sys
import sysconfig
import tokenize
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]
SITE = next((REPO / '.lintenv/lib').glob('python3*/site-packages'))
PRAGMA = re.compile(r'#\s*(?:noqa|type:|pylint:|pragma|fmt:|ruff:|mypy:)|#!|#\s*-\*-')
DIVIDER = re.compile(r'^#\s*[-=#~*]{4,}')

FEATURES = [
    ('`, not` contrast', r',\s+not\s+\w'),
    ('dash (` -- ` or `—`)', r'\s--\s|—'),
    ('absolutes: every, never, whole, exactly', r'\b(?:every|never|whole|exactly)\b'),
    ('`the one` / `one place`', r'\bthe one\b|\bone place\b'),
    ('deliberately, on purpose, by design', r'\b(?:deliberately|on purpose|by design)\b'),
    ('`rather than` / `instead of`', r'\b(?:rather than|instead of)\b'),
    ('`, so` joining clauses', r',\s+so\s+(?!that\b)\w'),
    ('semicolon', r';\s'),
    (
        'agentive verb: finds, knows, wants, sees, asks, decides, owns',
        r'\b(?:finds|knows|wants|sees|asks|decides|owns)\b',
    ),
    ('container verb: holds, carries, lives, keeps, names, states', r'\b(?:holds|carries|lives|keeps|names|states)\b'),
    ('intensifier: genuine, real, actually, really, truly', r'\b(?:genuine|genuinely|real|actually|really|truly)\b'),
    ('article before a backticked identifier', r'\b(?:the|a|an)\s+`'),
    ('`because`', r'\bbecause\b'),
    ('passive (`is`/`are`/`was`/`be` + `-ed`)', r'\b(?:is|are|was|were|be|been)\s+\w+ed\b'),
    ('changelog: now, no longer, used to, the old', r'\b(?:now|no longer|used to|the old)\b'),
    ('hedge: usually, likely, probably, might, seems', r'\b(?:usually|likely|probably|might|seems)\b'),
    ('first person: we, our, us, I', r'\b(?:[Ww]e|[Oo]ur|[Uu]s|I)\b'),
    ('TODO, NOTE, FIXME, XXX, HACK', r'\b(?:TODO|NOTE|FIXME|XXX|HACK)\b'),
    ('possessive `own`', r"\b(?:its|their|\w+'s) own\b"),
]
CASE_SENSITIVE = {'TODO, NOTE, FIXME, XXX, HACK', 'first person: we, our, us, I'}


def main() -> None:
    human = humanBlocks()
    recent = recentBlocks()
    print('| feature | human | Claude, this skill |\n|---|---|---|')
    print(f'| blocks | {len(human):,} | {len(recent)} |')
    lengths = [sorted(len(b.split()) for b in s) for s in (human, recent)]
    print(f'| median words | {statistics.median(lengths[0])} | {statistics.median(lengths[1])} |')
    print(f'| p90 words | {lengths[0][int(len(lengths[0]) * 0.9)]} | {lengths[1][int(len(lengths[1]) * 0.9)]} |')
    multi = [sum(sentenceCount(b) > 1 for b in s) / len(s) * 100 for s in (human, recent)]
    print(f'| blocks of more than one sentence | {multi[0]:.0f}% | {multi[1]:.0f}% |')
    for label, pattern in FEATURES:
        rx = re.compile(pattern) if label in CASE_SENSITIVE else re.compile(pattern, re.IGNORECASE)
        rates = [sum(bool(rx.search(b)) for b in s) / len(s) * 100 for s in (human, recent)]
        counts = sum(bool(rx.search(b)) for b in recent)
        print(f'| {label} | {rates[0]:.1f} | {rates[1]:.1f} ({counts}) |')


def sentenceCount(block: str) -> int:
    return len([s for s in re.split(r'(?<=[.!?])\s+(?=[A-Z`])', block.strip()) if s])


def commentBlocks(source: str) -> list[str]:
    blocks: list[list[str]] = []
    last_line = -2
    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        if token.type != tokenize.COMMENT or PRAGMA.match(token.string) or DIVIDER.match(token.string):
            continue
        text = token.string.lstrip('#').strip()
        if not text:
            continue
        full_line = token.line[: token.start[1]].strip() == ''
        if full_line and blocks and last_line == token.start[0] - 1 and blocks[-1][0] == 'full':
            blocks[-1].append(text)
        else:
            blocks.append(['full' if full_line else 'eol', text])
        last_line = token.start[0] if full_line else -2
    return [' '.join(b[1:]) for b in blocks]


def humanBlocks() -> list[str]:
    stdlib = Path(sysconfig.get_paths()['stdlib'])
    skipped = {'encodings', 'idlelib', 'site-packages', 'test', 'tests'}
    files = [p for p in stdlib.rglob('*.py') if not skipped & set(p.relative_to(stdlib).parts)]
    for package in ('mypy', 'pylint', 'astroid'):
        files += list((SITE / package).rglob('*.py'))
    blocks: list[str] = []
    for path in files:
        try:
            blocks += commentBlocks(path.read_text(encoding='utf-8'))
        except (UnicodeDecodeError, SyntaxError, tokenize.TokenError, IndentationError):
            continue
    return blocks


def recentBlocks() -> list[str]:
    blocks: list[str] = []
    for path in sorted((REPO / 'benchmark/round10/cycles').glob('cycle*_review.md')):
        if int(path.name.removeprefix('cycle').split('_')[0]) < int(sys.argv[1]):
            continue
        for item in re.split(r'\n### ', path.read_text())[1:]:
            code = re.search(r'```python\n(.*?)```', item, re.S)
            if code:
                marked = [line[8:] for line in code.group(1).splitlines() if line.startswith('>>')]
                text = ' '.join(line.split('#', 1)[1].strip() for line in marked if '#' in line)
                if text:
                    blocks.append(text)
    return blocks


main()
