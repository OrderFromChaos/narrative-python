"""Write a numbered review file of every # comment in the given runs, with code around each."""

import io
import re
import sys
import tokenize
from pathlib import Path

PRAGMA = re.compile(r'#\s*(?:noqa|type:|pylint:|pragma|fmt:|ruff:)|###')
BEFORE = 8
AFTER = 10


def commentBlocks(path: Path) -> list[tuple[int, int]]:
    blocks: list[tuple[int, int]] = []
    for token in tokenize.generate_tokens(io.StringIO(path.read_text()).readline):
        if token.type != tokenize.COMMENT or PRAGMA.match(token.string):
            continue
        number = token.start[0]
        full_line = token.line[: token.start[1]].strip() == ''
        if blocks and full_line and blocks[-1][1] + 1 == number:
            blocks[-1] = (blocks[-1][0], number)
            continue
        blocks.append((number, number))
    return blocks


def main() -> None:
    output, runs = Path(sys.argv[1]), [Path(arg) for arg in sys.argv[2:]]
    out = ['# Comments for review', '',
           f'Every `#` comment block, numbered, with {BEFORE} lines before and {AFTER} after. '
           'The comment lines are marked `>>`. Pragmas and `###` dividers are left out.', '']
    count = 0
    for run in runs:
        files = sorted(p for p in run.rglob('*.py') if '.venv' not in p.parts)
        blocks = [(f, b) for f in files for b in commentBlocks(f)]
        out += [f'## {run.name}: {len(blocks)} comments', '', f'`{run}`', '']
        for path, (first, last) in blocks:
            count += 1
            lines = path.read_text().splitlines()
            start, end = max(1, first - BEFORE), min(len(lines), last + AFTER)
            out += [f'### {count}. {path.relative_to(run)}:{first}', '', '```python']
            for number in range(start, end + 1):
                mark = '>>' if first <= number <= last else '  '
                out.append(f'{mark} {number:4} {lines[number - 1]}')
            out += ['```', '']
    output.write_text('\n'.join(out))
    print(count)


main()
