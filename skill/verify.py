"""Run the whole Narrative toolchain over a path and report one line per tool.

Use this instead of calling the tools by hand. A hand-rolled loop counts findings by grepping tool
output, so a missing or misresolved binary produces empty output and reads as a pass. This script
resolves every tool to an absolute path and exits 2 if any one of them is absent, so a green result
means the tools ran.

Order matters. `ruff check --fix` and `ruff format` converge in that order and not the other.

Usage:
    $ python3 verify.py src/
    $ python3 verify.py src/ --venv .lintenv --config pyproject.toml
    $ python3 verify.py src/ --no-fix        # report only, change nothing

Exit codes:
    0  every tool passed
    1  at least one tool reported a finding
    2  the toolchain or the config is missing, so nothing was checked
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


TOOLS = ('ruff', 'pylint', 'mypy', 'vermin')
PYTHON_FLOOR = '3.10'
EXIT_SUCCESS = 0
EXIT_FINDINGS = 1
EXIT_NO_TOOLCHAIN = 2


def main() -> int:
    """Resolve the toolchain, run every check, and print one line per tool.

    Returns:
        0 when everything passed, 1 on findings, 2 when a tool could not be found.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('paths', nargs='+', type=Path)
    parser.add_argument('--venv', type=Path, default=Path('.lintenv'))
    parser.add_argument('--config', type=Path, default=Path('pyproject.toml'))
    parser.add_argument('--no-fix', action='store_true', help='report only, do not rewrite files')
    args = parser.parse_args()

    toolchain, missing = resolveToolchain(args.venv)
    if missing:
        install = f'uv pip install --python {args.venv}/bin/python {" ".join(TOOLS)}'
        print(f'toolchain incomplete: {", ".join(missing)} not found', file=sys.stderr)
        print(f'  looked in {args.venv / "bin"} and on PATH', file=sys.stderr)
        print(f'  fix: uv venv {args.venv} && {install}', file=sys.stderr)
        return EXIT_NO_TOOLCHAIN

    # Without this file every tool silently falls back to its own defaults, which reports double
    # quotes as correct and never requires mixedCase. A wrong-config run looks like a clean one.
    if not args.config.is_file():
        snippet = Path(__file__).resolve().parent / 'pyproject-snippet.toml'
        print(f'no config at {args.config}', file=sys.stderr)
        print('  every tool would fall back to its defaults, so the result would be meaningless', file=sys.stderr)
        print(f'  fix: cp {snippet} {args.config}', file=sys.stderr)

        return EXIT_NO_TOOLCHAIN

    targets = [str(p) for p in args.paths]
    checker = Path(__file__).resolve().parent / 'checks.py'
    results: list[Result] = []

    if not args.no_fix:
        run([toolchain['ruff'], 'check', '--fix', '-q', *targets])
        run([toolchain['ruff'], 'format', '-q', *targets])

    results.append(gradeRuffCheck(run([toolchain['ruff'], 'check', '--output-format=concise', *targets])))
    results.append(gradeFormat(run([toolchain['ruff'], 'format', '--check', *targets])))
    results.append(gradePylint(run([toolchain['pylint'], f'--rcfile={args.config}', *targets])))
    results.append(gradeMypy(run([toolchain['mypy'], '--strict', '--no-error-summary', *targets])))
    results.append(gradeChecks(run([sys.executable, str(checker), *targets])))
    results.append(gradeVermin(run([toolchain['vermin'], '--no-tips', f'-t={PYTHON_FLOOR}-', *targets])))

    width = max(len(r.tool) for r in results)
    for result in results:
        print(f'{result.tool:<{width}}  {result.summary}')

    failed = [r for r in results if not r.passed]
    if failed:
        print(f'\n{len(failed)} of {len(results)} checks failed')
        return EXIT_FINDINGS

    print(f'\nall {len(results)} checks passed')
    return EXIT_SUCCESS


def resolveToolchain(venv: Path) -> tuple[dict[str, str], list[str]]:
    """Find every tool as an absolute path.

    A relative path breaks the moment anything changes directory, which is how a missing binary
    starts looking like a clean run. Prefer the venv, fall back to PATH, and report what is absent
    rather than proceeding without it.

    Args:
        venv: Directory of a virtual environment to prefer.

    Returns:
        The resolved absolute paths, and the names of any tool that could not be found.
    """
    resolved: dict[str, str] = {}
    missing: list[str] = []

    for tool in TOOLS:
        candidate = (venv / 'bin' / tool).resolve()
        if candidate.is_file():
            resolved[tool] = str(candidate)
            continue

        on_path = shutil.which(tool)
        if on_path:
            resolved[tool] = on_path
            continue

        missing.append(tool)

    return resolved, missing


def run(command: list[str]) -> Output:
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    return Output(completed.returncode, completed.stdout + completed.stderr)


def countFindingLines(output: Output) -> int:
    return sum(1 for line in output.text.splitlines() if '.py:' in line)


def gradeRuffCheck(output: Output) -> Result:
    found = countFindingLines(output)
    return Result('ruff check', output.code == 0, 'clean' if output.code == 0 else f'{found} findings')


def gradeFormat(output: Output) -> Result:
    return Result('ruff format', output.code == 0, 'clean' if output.code == 0 else 'would reformat')


def gradePylint(output: Output) -> Result:
    found = countFindingLines(output)
    return Result('pylint', output.code == 0, 'clean' if output.code == 0 else f'{found} findings')


def gradeMypy(output: Output) -> Result:
    found = countFindingLines(output)
    return Result('mypy --strict', output.code == 0, 'clean' if output.code == 0 else f'{found} errors')


def gradeChecks(output: Output) -> Result:
    found = countFindingLines(output)
    return Result('checks.py', output.code == 0, 'clean' if output.code == 0 else f'{found} findings')


def gradeVermin(output: Output) -> Result:
    if output.code == 0:
        return Result('vermin', True, f'{PYTHON_FLOOR} or lower')
    return Result('vermin', False, output.text.strip().splitlines()[-1] if output.text.strip() else 'failed')


### vocabulary #########################################################################################


@dataclass(frozen=True)
class Output:
    code: int
    text: str


@dataclass(frozen=True)
class Result:
    tool: str
    passed: bool
    summary: str


if __name__ == '__main__':
    sys.exit(main())
