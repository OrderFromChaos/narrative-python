"""Stage a blinded, shuffled copy of every validation arm and score each arm mechanically.

Each task holds three implementations of one problem: one written with no guidance, one with the
prior style document, one with the skill. This copies them to `blind/1.py`, `blind/2.py` and
`blind/3.py` in an order derived from a salt, and redacts the strings that would name the arm.

The mapping goes to `MANIFEST.json` and the tool scores to `SCORES.json`, both separate from the
staged files, so reading a candidate cannot reveal which arm produced it.

Usage:
    $ python3 prepare_blind.py --scratch /tmp/blind-scoring
    $ python3 prepare_blind.py --scratch /tmp/blind-scoring --salt second-pass
"""

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parent.parent / 'skill'
ARMS = ('base', 'doc', 'skill')
# Anything naming the arm would unblind the rating, so it is stripped before shuffling.
TELLTALES = re.compile(
    r'\b(SKILL\.md|rules-so-far|narrative|R[0-9]a?-[0-9]+|R2b-[A-Z0-9]+|Q[0-9]{2})\b',
)


def shuffleOrder(task: str, salt: str) -> list[str]:
    """Deterministically permute the arms so the mapping is reproducible but not guessable.

    Args:
        task: Directory name of the validation task.
        salt: Any string; changing it reshuffles.

    Returns:
        The three arm names in presentation order.
    """
    digest = hashlib.sha256(f'{task}:{salt}'.encode()).digest()
    order = list(ARMS)
    for index in range(len(order) - 1, 0, -1):
        swap = digest[index] % (index + 1)
        order[index], order[swap] = order[swap], order[index]

    return order


def toolPath(lint_bin: Path | None, name: str) -> str:
    """Resolve one linter, from an explicit bin directory or from PATH.

    Args:
        lint_bin: Directory holding the linter executables, or None to use PATH.
        name: Executable name, such as `ruff`.

    Returns:
        The command to run for that tool.
    """
    return str(lint_bin / name) if lint_bin else name


def runTool(command: list[str], target: Path) -> tuple[bool, str]:
    result = subprocess.run(
        [*command, str(target)],
        capture_output=True,
        text=True,
        cwd=target.parent,
        check=False,
    )

    return result.returncode == 0, (result.stdout + result.stderr).strip()


def scoreOne(source: Path, scratch: Path, lint_bin: Path | None) -> dict[str, object]:
    """Run the whole toolchain against one candidate and count what it reports."""
    scratch.mkdir(parents=True, exist_ok=True)
    staged = scratch / source.name
    shutil.copy(source, staged)
    shutil.copy(SKILL_DIR / 'pyproject-snippet.toml', scratch / 'pyproject.toml')

    ruff = toolPath(lint_bin, 'ruff')
    # NOT `-q`: quiet suppresses the very lines this counts, so a failing file scored zero.
    ruff_cmd = [ruff, 'check', '--no-cache', '--output-format=concise']
    ruff_ok, ruff_out = runTool(ruff_cmd, staged)
    fmt_ok, _ = runTool([ruff, 'format', '--no-cache', '--check'], staged)
    pylint_cmd = [toolPath(lint_bin, 'pylint'), '--rcfile=pyproject.toml']
    pylint_ok, pylint_out = runTool(pylint_cmd, staged)
    mypy_cmd = [toolPath(lint_bin, 'mypy'), '--strict', '--no-error-summary']
    mypy_ok, mypy_out = runTool(mypy_cmd, staged)
    checks_ok, checks_out = runTool([sys.executable, str(SKILL_DIR / 'checks.py')], staged)
    _, vermin_out = runTool([toolPath(lint_bin, 'vermin'), '--no-tips', '-t=3.10-'], staged)

    version = re.search(r'([0-9]+\.[0-9]+)', vermin_out.split('Minimum required versions:')[-1])
    return {
        'lines': len(source.read_text().splitlines()),
        'ruff': 0 if ruff_ok else len(re.findall(r'^\S+\.py:', ruff_out, re.M)),
        'format_clean': fmt_ok,
        'pylint': 0 if pylint_ok else len(re.findall(r'^\S+\.py:', pylint_out, re.M)),
        'mypy': 0 if mypy_ok else len(re.findall(r'^\S+\.py:', mypy_out, re.M)),
        'checks': 0 if checks_ok else countReportedFindings(checks_out),
        'min_python': version.group(1) if version else '?',
    }


def countReportedFindings(output: str) -> int:
    found = re.search(r'(\d+) findings', output)
    return int(found.group(1)) if found else 0


def main() -> int:
    """Stage a blinded copy of each arm and score every arm mechanically.

    The scores go to a separate file from the blinded sources, so reading a candidate cannot
    reveal which arm produced it.

    Returns:
        0 always. Failures surface as missing files rather than exit codes.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('--salt', default='v1')
    parser.add_argument('--scratch', type=Path, required=True)
    parser.add_argument(
        '--lint-bin',
        type=Path,
        default=None,
        help='Directory holding ruff, pylint, mypy and vermin. Defaults to PATH.',
    )

    args = parser.parse_args()

    root = Path(__file__).resolve().parent
    manifest: dict[str, object] = {}
    scores: dict[str, object] = {}

    for task_dir in sorted(p for p in root.iterdir() if p.is_dir() and p.name.startswith('v')):
        present = [a for a in ARMS if (task_dir / f'{a}.py').exists()]
        if len(present) != len(ARMS):
            print(f'{task_dir.name}: only {present}, skipping')
            continue

        blind_dir = task_dir / 'blind'
        shutil.rmtree(blind_dir, ignore_errors=True)
        blind_dir.mkdir()

        order = shuffleOrder(task_dir.name, args.salt)
        for position, arm in enumerate(order, start=1):
            source = task_dir / f'{arm}.py'
            text = TELLTALES.sub('[redacted]', source.read_text())
            (blind_dir / f'{position}.py').write_text(text)
            manifest[f'{task_dir.name}/{position}.py'] = arm
            scores[f'{task_dir.name}/{arm}'] = scoreOne(
                source,
                args.scratch / task_dir.name / arm,
                args.lint_bin,
            )

        print(f'{task_dir.name}: staged {len(order)} candidates')

    (root / 'MANIFEST.json').write_text(json.dumps(manifest, indent=2) + '\n')
    (root / 'SCORES.json').write_text(json.dumps(scores, indent=2) + '\n')
    print(f'\nmapping -> {root / "MANIFEST.json"} (do not open before rating)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
