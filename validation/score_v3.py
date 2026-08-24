"""Score the three V3 arms with one toolchain and write the result beside them.

V3 arms are packages rather than single files, which prepare_blind.py cannot handle: it copies one
file per arm and counts one file's lines. This walks a directory instead.

Usage:
    $ python3 validation/score_v3.py
    $ python3 validation/score_v3.py --venv .lintenv

Exit codes:
    0  every arm scored
    2  an arm directory is missing, or the toolchain is not installed
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
TASK_DIR = ROOT / 'validation' / 'v3_manifest_audit'
ARMS = ('base', 'skill', 'full')
TOOLS = ('ruff', 'pylint', 'mypy', 'vermin')
EXIT_SUCCESS = 0
EXIT_MISSING = 2


def main() -> int:
    """Score every arm and write scores.json into the task directory."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--venv', type=Path, default=ROOT / '.lintenv')
    arguments = parser.parse_args()

    binaries = {tool: arguments.venv / 'bin' / tool for tool in TOOLS}
    absent = [tool for tool, path in binaries.items() if not path.is_file()]
    if absent:
        print(f'toolchain incomplete: {", ".join(absent)} not found in {arguments.venv}', file=sys.stderr)
        return EXIT_MISSING

    scores = {}
    for arm in ARMS:
        directory = TASK_DIR / arm
        if not directory.is_dir():
            print(f'missing arm: {directory}', file=sys.stderr)
            return EXIT_MISSING

        scores[arm] = scoreArm(directory, binaries)

    report = TASK_DIR / 'scores.json'
    report.write_text(json.dumps(scores, indent=2) + '\n')

    width = max(len(arm) for arm in ARMS)
    print(f'{"arm":{width}}  {"modules":>7} {"lines":>6} {"ruff":>5} {"pylint":>6} {"mypy":>5} {"checks":>6}')
    for arm, score in scores.items():
        row = ' '.join(
            f'{score[k]:>{w}}'
            for k, w in (('modules', 7), ('lines', 6), ('ruff', 5), ('pylint', 6), ('mypy', 5), ('checks', 6))
        )
        print(f'{arm:{width}}  {row}')

    print(f'\nwritten to {report.relative_to(ROOT)}')
    return EXIT_SUCCESS


def scoreArm(directory: Path, binaries: dict[str, Path]) -> dict[str, object]:
    """Run the whole toolchain over one arm and count what each tool reports.

    The arm is copied to a scratch directory with the shipped config, so a stray pyproject.toml the
    author left behind cannot change what the tools mean.

    Args:
        directory: The arm to score.
        binaries: Absolute paths to the four tools.

    Returns:
        One row of counts.
    """
    sources = sorted(p for p in directory.rglob('*.py') if '__pycache__' not in str(p))
    scratch = directory.parent / '.scratch' / directory.name
    if scratch.exists():
        shutil.rmtree(scratch)

    shutil.copytree(directory, scratch, ignore=shutil.ignore_patterns('__pycache__', '.mypy_cache'))
    shutil.copy(ROOT / 'skill' / 'pyproject-snippet.toml', scratch / 'pyproject.toml')

    ruff = str(binaries['ruff'])
    checks = [sys.executable, str(ROOT / 'skill' / 'checks.py')]
    counts = {
        'ruff': countLines(runIn(scratch, [ruff, 'check', '--no-cache', '--output-format=concise', '.'])),
        'pylint': countLines(runIn(scratch, pylintCommand(binaries['pylint'], scratch))),
        'mypy': countLines(runIn(scratch, [str(binaries['mypy']), '--strict', '--no-error-summary', '.'])),
        'checks': countLines(runIn(scratch, [*checks, '.'])),
    }
    formatted = runIn(scratch, [ruff, 'format', '--no-cache', '--check', '.'])
    floor = runIn(scratch, [str(binaries['vermin']), '--no-tips', '-t=3.11-', '.'])
    version = re.search(r'([0-9]+\.[0-9]+)', floor.split('Minimum required versions:')[-1])

    shutil.rmtree(scratch.parent, ignore_errors=True)
    result: dict[str, object] = dict(counts)
    result['modules'] = len(sources)
    result['lines'] = sum(len(p.read_text().splitlines()) for p in sources)
    result['format_clean'] = 'would be reformatted' not in formatted
    result['min_python'] = version.group(1) if version else '?'
    return result


def pylintCommand(pylint: Path, scratch: Path) -> list[str]:
    """Build the pylint call, which wants package names rather than a dot."""
    packages = [p.name for p in sorted(scratch.iterdir()) if p.is_dir() and (p / '__init__.py').exists()]
    return [str(pylint), '--rcfile=pyproject.toml', *packages]


def runIn(directory: Path, command: list[str]) -> str:
    """Run one tool in the scratch directory and return everything it printed."""
    completed = subprocess.run(command, cwd=directory, capture_output=True, text=True, check=False)
    return completed.stdout + completed.stderr


def countLines(output: str) -> int:
    """Count reported findings, which every tool here prints one per line as `path:line:`."""
    return len(re.findall(r'^\S*\.py:', output, re.M))


if __name__ == '__main__':
    sys.exit(main())
