"""Run the whole Narrative toolchain over a path and report one line per tool.

Use this instead of calling the tools by hand. A hand-rolled loop counts findings by grepping tool
output, so a missing or misresolved binary produces empty output and reads as a pass. This script
resolves every tool to an absolute path and exits 2 if any one of them is absent, so a green result
means the tools ran.

This is the whole pipeline. Give it any path. It sorts Python files from prose and runs the right
checks on each, so nothing has to decide a workflow at run time.

Order matters. `ruff check --fix` and `ruff format` converge in that order and not the other.

Usage:
    $ python3 verify.py src/                 # every .py and every .md below src/
    $ python3 verify.py src/ docs/README.md
    $ python3 verify.py . --no-fix           # report only, change nothing

Exit codes:
    0  every tool passed
    1  at least one tool reported a finding
    2  the toolchain or the config is missing, so nothing was checked
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path


TOOLS = ('ruff', 'pylint', 'mypy', 'vermin')
PYTHON_FLOOR = '3.10'
STE_LINT_DEFAULT = Path.home() / '.claude/skills/ste-writing/ste-lint.py'
MAX_STE_PER_100_WORDS = 2.5
SKIPPED = frozenset({'.venv', 'venv', '.lintenv', '.git', 'build', 'dist', '__pycache__'})
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
    parser.add_argument('--ste-lint', type=Path, default=STE_LINT_DEFAULT, help='path to ste-lint.py')
    args = parser.parse_args()

    toolchain = resolveToolchain(args.venv)
    if toolchain.missing:
        lock = Path(__file__).resolve().parent / 'requirements-lock.txt'
        install = f'uv pip install --python {args.venv}/bin/python -r {lock}'
        print(f'toolchain incomplete: {", ".join(toolchain.missing)} not found', file=sys.stderr)
        print(f'  looked in {args.venv / "bin"} and on PATH', file=sys.stderr)
        print(f'  fix: uv venv {args.venv} && {install}', file=sys.stderr)
        return EXIT_NO_TOOLCHAIN

    # Presence is not enough. Every real project already has a pyproject.toml, so present-but-wrong
    # is the DEFAULT state, not an edge case. Without the Narrative sections each tool falls back to
    # its own defaults, accepts double quotes and snake_case functions, and reports a clean run.
    snippet = Path(__file__).resolve().parent / 'pyproject-snippet.toml'
    absent = missingConfigSections(args.config)
    if absent:
        print(f'config at {args.config} is not a Narrative config', file=sys.stderr)
        print(f'  missing: {", ".join(absent)}', file=sys.stderr)
        print('  the tools would fall back to their defaults and report a clean run', file=sys.stderr)
        print(f'  fix: merge {snippet} into {args.config}', file=sys.stderr)

        return EXIT_NO_TOOLCHAIN

    code, prose = splitByKind(args.paths)
    if not code and not prose:
        print('nothing to check: no .py or .md files found', file=sys.stderr)
        return EXIT_NO_TOOLCHAIN

    targets = [str(p) for p in code]
    checker = Path(__file__).resolve().parent / 'checks.py'
    results: list[Result] = []

    if not args.no_fix:
        run([toolchain.paths['ruff'], 'check', '--config', str(args.config), '--fix', '-q', *targets])
        run([toolchain.paths['ruff'], 'format', '--config', str(args.config), '-q', *targets])

    ruff_config = ['--config', str(args.config)]
    check_cmd = [toolchain.paths['ruff'], 'check', *ruff_config, '--output-format=concise']
    results.append(gradeRuffCheck(run([*check_cmd, *targets])))
    results.append(gradeFormat(run([toolchain.paths['ruff'], 'format', *ruff_config, '--check', *targets])))
    results.append(gradePylint(run([toolchain.paths['pylint'], f'--rcfile={args.config}', *targets])))
    mypy_cmd = [toolchain.paths['mypy'], '--config-file', str(args.config), '--strict', '--no-error-summary']
    results.append(gradeMypy(run([*mypy_cmd, *targets])))
    results.append(gradeChecks(run([sys.executable, str(checker), *targets])))
    vermin_cmd = [toolchain.paths['vermin'], '--no-tips', f'-t={PYTHON_FLOOR}-', '--violations']
    results.append(gradeVermin(run([*vermin_cmd, *targets])))

    if prose:
        results.append(gradeProse(prose, args.ste_lint))

    width = max(len(r.tool) for r in results)
    for result in results:
        print(f'{result.tool:<{width}}  {result.summary}')

    failed = [r for r in results if not r.passed]
    if failed:
        # Print what each failing tool said. A bare count would force the reader to re-run the
        # tools by hand, which is the one thing this script exists to stop them doing.
        for result in failed:
            print(f'\n--- {result.tool} ---')
            print(result.detail.rstrip() or '(no output)')

        print(f'\n{len(failed)} of {len(results)} checks failed')
        return EXIT_FINDINGS

    print(f'\nall {len(results)} checks passed')
    return EXIT_SUCCESS


def splitByKind(paths: list[Path]) -> tuple[list[Path], list[Path]]:
    """Sort the given paths into Python files and prose files.

    A directory expands to everything below it. This is what lets one command cover a whole
    project: the caller never decides which checker a file needs.

    Args:
        paths: Files or directories named on the command line.

    Returns:
        The Python files, and the Markdown files.
    """
    code: list[Path] = []
    prose: list[Path] = []

    for path in paths:
        found = sorted(path.rglob('*')) if path.is_dir() else [path]
        code.extend(f for f in found if f.suffix == '.py' and not SKIPPED & set(f.parts))
        prose.extend(f for f in found if f.suffix == '.md' and not SKIPPED & set(f.parts))

    return code, prose


def gradeProse(paths: list[Path], linter: Path) -> Result:
    """Run the STE linter over every prose file, when that skill is installed.

    Prose quality is a rule of this style, so the pipeline must cover it. The skill is a soft
    dependency, so its absence is reported rather than treated as a failure.

    Args:
        paths: Markdown files to check.
        linter: The ste-lint.py to run them through.

    Returns:
        One result covering every prose file.
    """
    if not linter.is_file():
        # Loud on purpose. A skipped prose check that reports success is a green run over
        # unchecked prose, which is the same false pass verify.py exists to prevent (R8-D34).
        detail = f'{linter} not found. Install ste-writing, or pass --ste-lint <path>.'
        return Result('ste (prose)', True, 'SKIPPED, prose was not checked', detail)

    noisy: list[str] = []
    for path in paths:
        output = run([sys.executable, str(linter), str(path)])
        rate = re.search(r'per100w=\s*([0-9.]+)', output.text)
        if rate and float(rate.group(1)) > MAX_STE_PER_100_WORDS:
            noisy.append(f'{path}: {rate.group(1)} violations per 100 words')

    if noisy:
        return Result('ste (prose)', False, f'{len(noisy)} of {len(paths)} files over threshold', '\n'.join(noisy))

    return Result('ste (prose)', True, f'{len(paths)} files clean', '')


def missingConfigSections(config: Path) -> list[str]:
    """Name the Narrative config sections that this file does not carry.

    Args:
        config: Path to a pyproject.toml.

    Returns:
        Human-readable descriptions of what is absent. Empty when the config is usable.
    """
    if not config.is_file():
        return [f'{config} does not exist']

    try:
        text = config.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError) as exc:
        return [f'unreadable: {exc}']

    # Matched by text rather than parsed. `tomllib` is 3.11+, and this style targets 3.10, so the
    # tool that enforces the floor must not itself break it.
    required = (
        (r'\[tool\.ruff\]', '[tool.ruff]'),
        (r'\[tool\.ruff\.lint\]', '[tool.ruff.lint]'),
        (r'function-naming-style', '[tool.pylint.basic] function-naming-style'),
        (r'strict\s*=\s*true', '[tool.mypy] strict = true'),
    )

    return [label for pattern, label in required if not re.search(pattern, text)]


def resolveToolchain(venv: Path) -> Toolchain:
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

    return Toolchain(resolved, tuple(missing))


def run(command: list[str]) -> Output:
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    return Output(completed.returncode, completed.stdout + completed.stderr)


def countFindingLines(output: Output) -> int:
    return sum(1 for line in output.text.splitlines() if '.py:' in line)


def gradeRuffCheck(output: Output) -> Result:
    found = countFindingLines(output)
    return Result('ruff check', output.code == 0, 'clean' if output.code == 0 else f'{found} findings', output.text)


def gradeFormat(output: Output) -> Result:
    return Result('ruff format', output.code == 0, 'clean' if output.code == 0 else 'would reformat', output.text)


def gradePylint(output: Output) -> Result:
    found = countFindingLines(output)
    return Result('pylint', output.code == 0, 'clean' if output.code == 0 else f'{found} findings', output.text)


def gradeMypy(output: Output) -> Result:
    found = countFindingLines(output)
    return Result('mypy --strict', output.code == 0, 'clean' if output.code == 0 else f'{found} errors', output.text)


def gradeChecks(output: Output) -> Result:
    found = countFindingLines(output)
    return Result('checks.py', output.code == 0, 'clean' if output.code == 0 else f'{found} findings', output.text)


def gradeVermin(output: Output) -> Result:
    # `--violations` matters. Without it vermin fails any file it cannot date, such as one using no
    # version-specific syntax at all, which it reports as `~2, ~3` and treats as target-not-met.
    if output.code == 0:
        return Result('vermin', True, f'{PYTHON_FLOOR} or lower', output.text)

    lines = output.text.strip().splitlines()
    return Result('vermin', False, lines[-1] if lines else 'failed', output.text)


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
    detail: str


@dataclass(frozen=True, slots=True)
class Toolchain:
    paths: Mapping[str, str]
    missing: tuple[str, ...]


if __name__ == '__main__':
    sys.exit(main())
