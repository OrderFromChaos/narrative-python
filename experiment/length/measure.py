"""Split each program in the length experiment into logic, docstring, comment and blank lines.

"Longer" is not one thing. A style that adds documentation and whitespace costs a reader little. A
style that adds branches and helpers costs a reader a lot. This separates the two.

Reads `<task>/base.py` and `<task>/narrative.py` under this directory, prints a per-file table and
an arm total, and writes `RESULTS.json`.

Usage:
    $ python3 measure.py
"""

import ast
import json
import sys
from pathlib import Path


def classifyLines(source: str) -> dict[str, int]:
    """Split a module's lines into logic, docstring, comment and blank.

    Docstring lines are attributed by walking the AST for string-expression statements, so a
    multi-line docstring counts every line it spans rather than one.

    Args:
        source: Full text of the module.

    Returns:
        Counts keyed by category, plus the total.
    """
    lines = source.splitlines()
    docstring_lines: set[int] = set()

    tree = ast.parse(source)
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        if not node.body:
            continue

        first = node.body[0]
        is_docstring = (
            isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str)
        )

        if is_docstring:
            docstring_lines.update(range(first.lineno, (first.end_lineno or first.lineno) + 1))

    counts = {'code': 0, 'docstring': 0, 'comment': 0, 'blank': 0}
    for number, text in enumerate(lines, start=1):
        stripped = text.strip()
        if number in docstring_lines:
            counts['docstring'] += 1
        elif not stripped:
            counts['blank'] += 1
        elif stripped.startswith('#'):
            counts['comment'] += 1
        else:
            counts['code'] += 1

    counts['total'] = len(lines)
    return counts


def main() -> int:
    """Print a per-file breakdown and an arm-level summary as JSON."""
    root = Path(__file__).resolve().parent
    results: dict[str, dict[str, int]] = {}

    for task_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        for arm in ('base', 'narrative'):
            candidate = task_dir / f'{arm}.py'
            if candidate.exists():
                results[f'{task_dir.name}/{arm}'] = classifyLines(candidate.read_text())

    header = f'{"file":22} {"total":>6} {"code":>6} {"docstr":>7} {"comment":>8} {"blank":>6}'
    print(header)
    for name, counts in results.items():
        print(
            f'{name:22} {counts["total"]:>6} {counts["code"]:>6} '
            f'{counts["docstring"]:>7} {counts["comment"]:>8} {counts["blank"]:>6}',
        )

    for arm in ('base', 'narrative'):
        rows = [v for k, v in results.items() if k.endswith(arm)]
        if not rows:
            continue
        totals = {k: sum(r[k] for r in rows) for k in ('total', 'code', 'docstring', 'comment', 'blank')}
        print(
            f'\n{arm:22} {totals["total"]:>6} {totals["code"]:>6} '
            f'{totals["docstring"]:>7} {totals["comment"]:>8} {totals["blank"]:>6}',
        )

    (root / 'RESULTS.json').write_text(json.dumps(results, indent=2) + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
