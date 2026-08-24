"""Report Narrative style violations that ruff, pylint and mypy do not implement.

Each rule is one check. NAR001 and NAR006 cover module state. NAR002 covers class attributes.
NAR003 covers layout. NAR004 and NAR009 cover documentation. NAR005 covers annotation
complexity. NAR007 covers boolean grouping. NAR010 covers FIXME reachability.

See tooling.md for what the other tools own.

Usage:
    $ python3 checks.py src/
    $ python3 checks.py src/loader.py src/report.py
    $ python3 checks.py src/ --select NAR001 --select NAR006

Exit codes:
    0  nothing found
    1  at least one finding
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from dataclasses import dataclass
from pathlib import Path


### The ten rules that no off-the-shelf tool implements. Everything else is ruff, pylint or mypy;
### see tooling.md for the split and for the evidence that each of those actually fires.
### Stdlib only, so this runs anywhere python3 does.

MAX_BODY_LINES_WITHOUT_DOCSTRING = 20
MAX_ARGS_ON_ONE_LINE = 3
MAX_ANNOTATION_THINGS = 4

RULES = {
    'NAR001': 'module-level object mutated in a function without a `global` declaration',
    'NAR006': 'assignment shadows a module-level name -- add `global`, or rename the local',
    'NAR002': 'hasattr(self, ...) -- attributes must not be conditionally defined',
    'NAR003': f'def signature with more than {MAX_ARGS_ON_ONE_LINE} POSITIONAL args on one line',
    'NAR004': 'docstring missing or without Raises: on a function that takes >3 parameters or runs long',
    'NAR005': f'annotation naming more than {MAX_ANNOTATION_THINGS} things: give it a name',
    'NAR007': '`and` inside `or` without parentheses -- do not make the reader apply precedence',
    'NAR009': 'module docstring missing, or runnable module without a usage example',
    'NAR010': 'FIXME in reachable code -- a merge blocker, not a danger sign',
    'NAR000': 'file could not be read or parsed',
}

### Withdrawn codes. A code stays here so that a document naming it still resolves, while `--select`
### and the findings never offer it.

RETIRED = {
    'NAR008': 'withdrawn: blank lines inside a function are review judgement',
}


TYPE_FACTORY_CALLS = frozenset({'NewType', 'TypeVar', 'ParamSpec', 'TypeVarTuple', 'NamedTuple', 'TypedDict'})


def main() -> int:
    """Check every file named on the command line and print the findings.

    Returns:
        1 if anything was found, 0 otherwise, so this can gate a commit.
    """
    parser = argparse.ArgumentParser(description='Style checks that ruff, pylint and mypy do not implement.')
    parser.add_argument('paths', nargs='+', type=Path)
    parser.add_argument('--select', action='append', choices=sorted(RULES), help='only report these rules')
    args = parser.parse_args()

    targets: list[Path] = []
    for target in args.paths:
        targets.extend(sorted(discoverPython(target)) if target.is_dir() else [target])

    findings: list[Finding] = []
    for checked_file in targets:
        findings.extend(checkFile(checked_file))
    if args.select:
        findings = [f for f in findings if f.code in args.select]

    for finding in sorted(findings, key=lambda f: (str(f.checked_file), f.line)):
        print(f'{finding} -- {RULES.get(finding.code, "")}')

    if targets:
        # A file already reported as unreadable must not be re-read here just to size the report.
        scanned = 0
        for checked_file in targets:
            try:
                scanned += len(checked_file.read_text(encoding='utf-8').splitlines())
            except (OSError, UnicodeDecodeError):
                continue

        rate = len(findings) / max(scanned, 1) * 100
        print(f'\n{len(findings)} findings over {len(targets)} files ({rate:.2f} per 100 lines)')

    return 1 if findings else 0


def bindsAType(value: ast.expr) -> bool:
    # `ScanId = NewType('ScanId', int)` and `Outcome = Literal['a', 'b']` are module-level Assign
    # nodes, but they declare types. Reading one inside a function is not touching global state.
    if isinstance(value, ast.Call) and isinstance(value.func, ast.Name):
        return value.func.id in TYPE_FACTORY_CALLS
    if isinstance(value, ast.Subscript):
        return True
    return isinstance(value, ast.BinOp) and isinstance(value.op, ast.BitOr)


def moduleLevelVariables(tree: ast.Module) -> set[str]:
    # Only plain module-level assignments count. Imports, defs, classes and type aliases are
    # referred to freely; the rule is about *variables* whose value a function depends on.
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Assign) and not bindsAType(node.value):
            for target in node.targets:
                names.update(n.id for n in ast.walk(target) if isinstance(n, ast.Name))
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)

    return names


### Python already forces `global` in order to REBIND a module name -- omit it and you silently get
### a local instead. What Python does not force, and what no linter catches, is in-place MUTATION:
### CONFIG.clear(), CONFIG['k'] = v and CONFIG.field = v all change module state with no declaration
### and no error. That silent case is what this rule exists for. Read-only access is not flagged.
# fmt: off
MUTATING_METHODS = frozenset({
    'append', 'extend', 'insert', 'remove', 'pop', 'clear', 'sort', 'reverse',
    'update', 'setdefault', 'popitem', 'add', 'discard',
    '__setitem__', '__delitem__', '__iadd__',
})
# Configuration calls mutate module state just as container methods do -- `LOG.addHandler(...)`
# changes what every later caller of LOG does. The marker tracks side effects, not containers.
# Deliberately excludes 'write' and 'load'. `LOG_PATH.write_text(...)` writes a file and mutates
# no module state, because a Path is a value. Including it made the flagship check fire on the
# documented pattern, with no way to silence it but a `global` that lied about a side effect.
MUTATING_PREFIXES = (
    'set', 'add', 'remove', 'register', 'unregister', 'reset', 'delete', 'insert',
    'enable', 'disable', 'configure', 'install', 'attach', 'detach',
    'bind', 'unbind', 'truncate', 'flush', 'commit', 'rollback', 'execute', 'close',
)
# fmt: on


def mutatesByName(method: str) -> bool:
    """Decide whether a method name reads as a mutation.

    Exact names first, then a prefix sweep for the configuration verbs. This is a heuristic and
    cannot be otherwise: an arbitrary domain method may mutate without saying so in its name.
    NAR001 therefore under-reports rather than crying wolf.
    """
    if method in MUTATING_METHODS:
        return True
    return any(
        method.startswith(prefix) and (len(method) == len(prefix) or not method[len(prefix)].islower())
        for prefix in MUTATING_PREFIXES
    )


def mutatedModuleNames(func: ast.FunctionDef | ast.AsyncFunctionDef, module_vars: set[str]) -> set[str]:
    """Find module-level names this function changes in place.

    Detects mutating method calls, augmented assignment, `del`, and assignment through a subscript
    or attribute. A plain `NAME = x` rebind is excluded: Python already refuses to rebind a module
    name without `global`, so that case cannot go undeclared.

    Args:
        module_vars: Names bound by a plain assignment at module level.

    Returns:
        The subset of module_vars this function mutates.
    """
    mutated: set[str] = set()

    def rootName(node: ast.expr) -> str | None:
        while isinstance(node, (ast.Attribute, ast.Subscript)):
            node = node.value
        return node.id if isinstance(node, ast.Name) else None

    for node in ast.walk(func):
        target: ast.expr | None = None
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if mutatesByName(node.func.attr):
                target = node.func.value
        elif isinstance(node, ast.AugAssign):
            target = node.target
        elif isinstance(node, ast.Delete):
            for item in node.targets:
                name = rootName(item)
                if name in module_vars and isinstance(item, (ast.Subscript, ast.Attribute)):
                    mutated.add(name)

            continue
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for item in targets:
                # Plain `NAME = x` is a rebind, which Python already polices; only `NAME[k] = x`
                # and `NAME.attr = x` slip through without a declaration.
                if isinstance(item, (ast.Subscript, ast.Attribute)):
                    name = rootName(item)
                    if name in module_vars:
                        mutated.add(name)

            continue

        if target is not None:
            name = rootName(target)
            if name in module_vars:
                mutated.add(name)

    return mutated


def namesUsedInAnnotations(func: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    annotations: list[ast.expr] = [a.annotation for a in ast.walk(func.args) if isinstance(a, ast.arg) and a.annotation]
    if func.returns:
        annotations.append(func.returns)
    annotations.extend(n.annotation for n in ast.walk(func) if isinstance(n, ast.AnnAssign) and n.annotation)

    used: set[str] = set()
    for annotation in annotations:
        used.update(n.id for n in ast.walk(annotation) if isinstance(n, ast.Name))
    return used


def locallyBoundNames(func: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    bound = {a.arg for a in func.args.args + func.args.kwonlyargs + func.args.posonlyargs}
    if func.args.vararg:
        bound.add(func.args.vararg.arg)
    if func.args.kwarg:
        bound.add(func.args.kwarg.arg)

    for node in ast.walk(func):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            bound.add(node.id)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            bound.update(a.asname or a.name.split('.')[0] for a in node.names)
        # Kept as two branches deliberately. Merging them, even with explicit parentheses, widens
        # `node` back to a union so mypy sees `node.name` as `str | None`. Type narrowing beats
        # brevity here.
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node is not func:
            bound.add(node.name)
        elif isinstance(node, ast.ExceptHandler) and node.name:
            bound.add(node.name)

    return bound


def checkGlobalDeclarations(tree: ast.Module, checked_file: Path) -> list[Finding]:
    """Flag undeclared writes to module state.

    NAR001 is in-place mutation with no `global`, which neither ruff nor pylint reports at any
    setting. NAR006 is a bare assignment that shadows a module-level name, so the module value
    silently never changes.

    Reads are not flagged (R2b-G1): `global` marks a side effect, not a dependency.
    """
    module_vars = moduleLevelVariables(tree)
    findings: list[Finding] = []

    for func in ast.walk(tree):
        if not isinstance(func, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue

        declared: set[str] = set()
        for node in ast.walk(func):
            if isinstance(node, (ast.Global, ast.Nonlocal)):
                declared.update(node.names)

        # A name assigned anywhere in the function is a local, so mutating it is not touching
        # module state -- that case is NAR006's, not this one's.
        shadowed = locallyBoundNames(func) - declared
        mutated = sorted(mutatedModuleNames(func, module_vars) - declared - shadowed)
        if mutated:
            detail = f'{func.name} mutates {", ".join(mutated)}'
            findings.append(Finding(checked_file, func.lineno, 'NAR001', detail))

        # A bare `NAME = x` with no `global` silently creates a local that shadows module state.
        # Python accepts it; the module value never changes. Almost always a bug.
        rebound = {n.id for n in ast.walk(func) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)}
        shadowing = sorted((rebound & module_vars) - declared)
        if shadowing:
            detail = f'{func.name} assigns {", ".join(shadowing)} without `global`'
            findings.append(Finding(checked_file, func.lineno, 'NAR006', detail))

    return findings


def checkHasattrSelf(tree: ast.Module, checked_file: Path) -> list[Finding]:
    findings: list[Finding] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
            continue
        if node.func.id != 'hasattr' or not node.args:
            continue
        first = node.args[0]
        if isinstance(first, ast.Name) and first.id == 'self':
            findings.append(Finding(checked_file, node.lineno, 'NAR002', 'declare the attribute in __init__ instead'))

    return findings


def checkArgsPerLine(tree: ast.Module, checked_file: Path) -> list[Finding]:
    """Flag `def` signatures that keep more than three arguments on one line.

    Scoped to signatures, not calls (R2b-B1): applying it to calls costs about 19% more lines,
    because exploding an inner call forces the enclosing call to explode with it.

    The formatter cannot do this. `ruff format` leaves a four-argument signature alone while it
    fits in 120 columns, and COM812 only fires once a construct has already been split.

    Only positional parameters count. Keyword-only parameters — anything after `*` — do not, so a
    function may carry as many of those as it needs. That is also the escape hatch: marking the
    optional parameters keyword-only both documents them and stops them counting.
    """
    findings: list[Finding] = []

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue

        args = node.args
        positional = args.posonlyargs + args.args
        count = len(positional) - (1 if args.args and args.args[0].arg in ('self', 'cls') else 0)
        end_line = max((a.lineno for a in positional + args.kwonlyargs), default=node.lineno)

        if count > MAX_ARGS_ON_ONE_LINE and end_line == node.lineno:
            detail = f'def {node.name} has {count} positional args on one line'
            findings.append(Finding(checked_file, node.lineno, 'NAR003', detail))

    return findings


def missingSections(node: ast.FunctionDef | ast.AsyncFunctionDef, docstring: str, checked_file: Path) -> list[Finding]:
    """Report a function that the docstring trigger caught and whose docstring omits `Raises:`.

    A docstring that exists is not a docstring that carries the contract, so the trigger and the
    section check are two separate tests over the same function.
    """
    args = node.args
    every_arg = args.posonlyargs + args.args + args.kwonlyargs
    arity = len(every_arg) - (1 if args.args and args.args[0].arg in ('self', 'cls') else 0)
    body_end = max((getattr(n, 'end_lineno', None) or 0) for n in ast.walk(node))
    body_lines = body_end - node.body[0].lineno + 1

    if arity <= MAX_ARGS_ON_ONE_LINE and body_lines <= MAX_BODY_LINES_WITHOUT_DOCSTRING:
        return []

    # Raises: only. An exception is the one part of the contract that no annotation carries, so
    # Args: and Returns: are left to review: demanding them produces text that restates the
    # signature.
    if not any(isinstance(n, ast.Raise) for n in ast.walk(node)) or 'Raises:' in docstring:
        return []

    return [Finding(checked_file, node.lineno, 'NAR004', f'{node.name}: docstring omits Raises:')]


def checkDocstringThreshold(tree: ast.Module, checked_file: Path) -> list[Finding]:
    """Require a docstring wherever the contract is complex, not merely where the body is long.

    Two triggers: the function takes more than three parameters, or its body exceeds the line
    threshold. A `raise` is not a trigger, because the style routes raise sites through a reject*()
    helper and every two-line guard that calls one contains a `raise`.

    Keyword-only parameters count here, unlike NAR003, because every parameter is part of the
    contract even when the caller may omit it.

    A pure line threshold would be gameable in the wrong direction: splitting a 21-line function
    into two 12-line ones deletes the obligation without simplifying either contract.
    """
    findings: list[Finding] = []

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        docstring = ast.get_docstring(node)
        if docstring is not None:
            findings.extend(missingSections(node, docstring, checked_file))
            continue

        body_start = node.body[0].lineno
        body_end = max((getattr(n, 'end_lineno', None) or 0) for n in ast.walk(node))
        body_lines = body_end - body_start + 1

        args = node.args
        every_arg = args.posonlyargs + args.args + args.kwonlyargs
        arity = len(every_arg) - (1 if args.args and args.args[0].arg in ('self', 'cls') else 0)

        reasons = []
        if body_lines > MAX_BODY_LINES_WITHOUT_DOCSTRING:
            reasons.append(f'{body_lines} body lines')
        if arity > MAX_ARGS_ON_ONE_LINE:
            reasons.append(f'{arity} parameters')

        if reasons:
            findings.append(Finding(checked_file, node.lineno, 'NAR004', f'{node.name}: {", ".join(reasons)}'))

    return findings


def annotationThings(node: ast.expr) -> int:
    """Count every name an annotation carries, except the outermost one.

    What makes an annotation impossible to say out loud is how many things it names, at any nesting.
    Counting names rather than depth or width catches both
    `Callable[[Callable[[Job], Result]], Callable[[Job], Result]]`, which is deep and narrow, and
    `tuple[dict[str, str], list[str]]`, which is wide and shallow.

    The outermost name is free because it is the thing being described. `Car` costs 0, and
    `dict[str, list[tuple[float, float]]]` costs 5.
    """
    names = [n for n in ast.walk(node) if isinstance(n, (ast.Name, ast.Attribute, ast.Constant))]
    return max(0, len(names) - 1)


def checkAnnotationComplexity(tree: ast.Module, checked_file: Path) -> list[Finding]:
    """Flag an annotation too complex to say out loud.

    The measure is how many things the annotation names below its outermost name, at any nesting.
    That catches `dict[str, list[tuple[float, float]]]`, which is deep and narrow, and
    `tuple[a, b, c, d, e, f, g, h, i, j]`, which is one level deep and still unnameable.

    The type decides the remedy. A callable becomes a Protocol, and anything else becomes a
    dataclass.

    Returns:
        One finding per annotation over the threshold, each naming its own remedy.
    """
    findings: list[Finding] = []
    for node in ast.walk(tree):
        annotations: list[ast.expr] = []
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            annotations = [a.annotation for a in ast.walk(node.args) if isinstance(a, ast.arg) and a.annotation]
            if node.returns:
                annotations.append(node.returns)
        elif isinstance(node, ast.AnnAssign):
            annotations = [node.annotation]

        for annotation in annotations:
            count = annotationThings(annotation)
            if count <= MAX_ANNOTATION_THINGS:
                continue

            rendered = ast.unparse(annotation)
            # The trigger says the thing is too complex to name in conversation. The type says what
            # to replace it with: a callable becomes a Protocol, anything else becomes a dataclass.
            remedy = 'a Protocol' if 'Callable' in rendered else 'a dataclass'
            detail = f'{count} things: {rendered} -> {remedy}'
            findings.append(Finding(checked_file, annotation.lineno, 'NAR005', detail))

    return findings


def checkBoolOpParens(tree: ast.Module, source: str, checked_file: Path) -> list[Finding]:
    """Flag an `and` group inside an `or` that is not parenthesised.

    `A and B or C and D` is correct, because `and` binds tighter — but recovering that costs the
    reader a precedence lookup, which is the rote parsing the style exists to remove. Merging
    branches that share a body is encouraged; doing it by precedence is not.

    The AST does not record parentheses, so this reads the source. Both sides must be checked: a
    trailing `)` alone is ambiguous, because the last operand of a parenthesised multi-line
    expression is also followed by `)` without being grouped itself.
    """
    lines = source.splitlines()
    findings: list[Finding] = []

    def charBefore(row: int, column: int) -> str:
        while row >= 1:
            head = lines[row - 1][:column].rstrip()
            if head:
                return head[-1]
            row, column = row - 1, len(lines[row - 2]) if row >= 2 else 0

        return ''

    def charAfter(row: int, column: int) -> str:
        while row <= len(lines):
            tail = lines[row - 1][column:].lstrip()
            if tail:
                return tail[0]
            row, column = row + 1, 0

        return ''

    for node in ast.walk(tree):
        if not isinstance(node, ast.BoolOp) or not isinstance(node.op, ast.Or):
            continue

        for operand in node.values:
            if not isinstance(operand, ast.BoolOp) or not isinstance(operand.op, ast.And):
                continue

            opens = charBefore(operand.lineno, operand.col_offset) == '('
            closes = charAfter(operand.end_lineno or operand.lineno, operand.end_col_offset or 0) == ')'
            if not (opens and closes):
                detail = f'`{ast.unparse(operand)}` needs its own parentheses'
                findings.append(Finding(checked_file, operand.lineno, 'NAR007', detail))

    return findings


def calleeName(node: ast.stmt) -> str | None:
    if not isinstance(node, ast.Expr) or not isinstance(node.value, ast.Call):
        return None

    func = node.value.func
    if isinstance(func, ast.Attribute):
        return func.attr
    return func.id if isinstance(func, ast.Name) else None


def checkModuleDocstring(tree: ast.Module, checked_file: Path) -> list[Finding]:
    """Require a module docstring, and a usage example on anything runnable.

    The docstring is the first thing a reader meets, before `main()`. A module that can be executed
    has to show how — semantics vary per program, and a reader should not have to reconstruct the
    invocation from `argparse` calls further down.

    Returns:
        One finding for a missing docstring, or one for a runnable module whose docstring shows no
        example invocation.
    """
    runnable = any(isinstance(node, ast.If) and '__main__' in ast.unparse(node.test) for node in tree.body)

    docstring = ast.get_docstring(tree)
    if docstring is None:
        # A package marker has nothing to describe (R7-B01-init), and a module holding one function
        # is described by that function (R7-B10-scope). The second def is where a module starts
        # being ABOUT something rather than doing one thing. A runnable module is never exempt: it
        # still owes the usage example below.
        definitions = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        exempt = (checked_file.name == '__init__.py' and not tree.body) or (len(definitions) == 1 and not runnable)
        if exempt:
            return []

        return [Finding(checked_file, 1, 'NAR009', 'module has no docstring')]

    if not runnable:
        return []

    shows_usage = any(line.lstrip().startswith(('$', '>>>', 'python3 ', 'python ')) for line in docstring.splitlines())
    if not shows_usage:
        return [Finding(checked_file, 1, 'NAR009', 'runnable module: docstring shows no example invocation')]

    return []


# fmt: off
SKIPPED_DIRECTORIES = frozenset({
    '.venv', 'venv', '.lintenv', '.git', '.tox', 'build', 'dist',
    '__pycache__', 'node_modules', '.mypy_cache', '.ruff_cache',
})
# fmt: on


def discoverPython(root: Path) -> list[Path]:
    """Find every Python file under a directory, skipping the trees no linter should read.

    Ruff already excludes a virtual environment. Without the same exclusion here, `checks.py .`
    reports findings from installed third-party code.

    Returns:
        Every `.py` file outside a skipped directory.
    """
    return [found for found in root.rglob('*.py') if not SKIPPED_DIRECTORIES & set(found.parts)]


def calledNames(node: ast.AST) -> set[str]:
    called: set[str] = set()
    for inner in ast.walk(node):
        if not isinstance(inner, ast.Call):
            continue

        target = inner.func
        if isinstance(target, ast.Name):
            called.add(target.id)
        elif isinstance(target, ast.Attribute):
            called.add(target.attr)

    return called


def reachableFunctions(tree: ast.Module) -> set[str]:
    """Find every function reachable from module level or from `main`.

    Names are matched without scope analysis, so a method and a function that share a name are one
    node. That over-approximates reachability, which is the safe direction: NAR010 would rather
    call an orphan reachable than let a live FIXME through.

    A module with no `main` and no `__main__` block is a library module. Its callers live in files
    this checker never sees, so every function in it counts as reachable.
    """
    defined = {node.name: node for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}

    # A module with no entry point is a library module: its callers are in other files, which this
    # per-file checker cannot see. Seeding only from a local `main` would make every function in
    # such a module look orphaned, which lets a live marker in running code pass the gate.
    entry = {name for name in defined if name == 'main'}
    runnable = any(isinstance(node, ast.If) and '__main__' in ast.unparse(node.test) for node in tree.body)
    if not entry and not runnable:
        return set(defined)

    frontier = set(entry)
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            frontier |= calledNames(node) & set(defined)

    reachable: set[str] = set()
    while frontier:
        name = frontier.pop()
        if name in reachable:
            continue

        reachable.add(name)
        frontier |= calledNames(defined[name]) & set(defined)

    return reachable


def enclosingFunction(tree: ast.Module, line: int) -> str | None:
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.lineno <= line <= (node.end_lineno or node.lineno):
            return node.name

    return None


def checkFixmeReachability(tree: ast.Module, source: str, checked_file: Path) -> list[Finding]:
    """Flag a FIXME sitting in code that runs.

    The two markers mean different things. A TODO is deferred work and never blocks. A FIXME is
    either a merge blocker, or a known correctness problem parked in code nothing calls, left as a
    danger sign for whoever next considers wiring it into the hot loop.

    Only the first kind is a defect, and reachability is what separates them.

    Returns:
        One finding per FIXME inside a function reachable from an entry point.
    """
    reachable = reachableFunctions(tree)
    findings: list[Finding] = []

    for number, text in enumerate(source.splitlines(), start=1):
        if 'FIXME' not in text or not text.lstrip().startswith('#'):
            continue

        owner = enclosingFunction(tree, number)
        if owner is None or owner in reachable:
            where = f'in {owner}' if owner else 'at module level'
            findings.append(Finding(checked_file, number, 'NAR010', f'FIXME {where}, which runs'))

    return findings


def suppressedLines(source: str) -> dict[int, set[str]]:
    """Map each line carrying a `# noqa: NARxxx` comment to the codes it silences.

    Every check here is a heuristic over syntax, so each one can be wrong. Without a suppression
    the only way to clear a false positive is to change correct code into incorrect code.

    Returns:
        Line number to the set of codes suppressed on that line, or `{'ALL'}` for a bare `# noqa`.
    """
    suppressed: dict[int, set[str]] = {}
    for number, text in enumerate(source.splitlines(), start=1):
        found = re.search(r'#\s*noqa(?::\s*(?P<codes>[A-Z0-9, ]+))?', text)
        if not found:
            continue

        codes = found.group('codes')
        suppressed[number] = {c.strip() for c in codes.split(',') if c.strip()} if codes else {'ALL'}

    return suppressed


def checkFile(checked_file: Path) -> list[Finding]:
    """Run every check against one file.

    An unreadable file is reported like any other finding rather than aborting the run: a linter
    invoked over a directory must not stop at the first bad path (Q24).

    Returns:
        Every finding for this file, or a single NAR000 if it could not be read or parsed.
    """
    try:
        source = checked_file.read_text(encoding='utf-8')
    except OSError as exc:
        return [Finding(checked_file, 0, 'NAR000', f'unreadable: {exc.strerror}')]
    except UnicodeDecodeError as exc:
        return [Finding(checked_file, 0, 'NAR000', f'not UTF-8: {exc.reason}')]

    try:
        tree = ast.parse(source, filename=str(checked_file))
    except SyntaxError as exc:
        return [Finding(checked_file, exc.lineno or 0, 'NAR000', f'syntax error: {exc.msg}')]

    suppressed = suppressedLines(source)
    findings = [
        *checkGlobalDeclarations(tree, checked_file),
        *checkHasattrSelf(tree, checked_file),
        *checkArgsPerLine(tree, checked_file),
        *checkDocstringThreshold(tree, checked_file),
        *checkAnnotationComplexity(tree, checked_file),
        *checkBoolOpParens(tree, source, checked_file),
        *checkModuleDocstring(tree, checked_file),
        *checkFixmeReachability(tree, source, checked_file),
    ]

    return [f for f in findings if not (suppressed.get(f.line, set()) & {f.code, 'ALL'})]


### vocabulary #########################################################################


@dataclass(frozen=True)
class Finding:
    checked_file: Path
    line: int
    code: str
    detail: str

    def __str__(self) -> str:
        return f'{self.checked_file}:{self.line}: {self.code} {self.detail}'


if __name__ == '__main__':
    sys.exit(main())
