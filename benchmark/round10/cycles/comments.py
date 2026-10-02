"""List every # comment in each cycle run's package, with the code that follows it."""

import io
import re
import sys
import tokenize
from pathlib import Path

PRAGMA = re.compile(r'#\s*(?:noqa|type:|pylint:|pragma|fmt:|ruff:)|###')
CONTEXT_LINES = 3


def commentsOf(path: Path) -> list[tuple[int, str, bool]]:
    source = path.read_text()
    found = []
    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        if token.type == tokenize.COMMENT and not PRAGMA.match(token.string):
            end_of_line = token.line[: token.start[1]].strip() != ''
            # a full-line comment directly under another continues that block
            if found and not end_of_line and not found[-1][2] and found[-1][0] + found[-1][1].count('\n') + 1 == token.start[0]:
                number, text, _ = found[-1]
                found[-1] = (number, text + '\n' + token.string, False)
                continue
            found.append((token.start[0], token.string, end_of_line))
    return found


def main() -> None:
    root = Path(sys.argv[1])
    for run in sorted(root.glob('v6_*')):
        files = sorted(p for p in run.rglob('*.py') if '.venv' not in p.parts)
        rows = [(f, *c) for f in files for c in commentsOf(f)]
        print(f'===== {run.name}: {len(rows)} comments')
        for f, number, text, end_of_line in rows:
            lines = f.read_text().splitlines()
            print(f'--- {f.relative_to(run)}:{number}{" (eol)" if end_of_line else ""}')
            if end_of_line:
                print('   ', lines[number - 1])
                continue
            print('   ', text.replace('\n', '\n    '))
            block_end = number + text.count('\n')
            for following in lines[block_end : block_end + CONTEXT_LINES]:
                print('    |', following)


main()
