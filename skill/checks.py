"""Report Narrative style violations that ruff, pylint and mypy do not implement.

Each rule is one check. NAR001 and NAR006 cover module state; NAR002 covers class attributes;
NAR003, NAR008 and NAR009 cover layout; NAR004 and NAR009 cover documentation; NAR005 covers
annotation depth; NAR007 covers boolean grouping. See tooling.md for what the other tools own.

Usage:
    $ python3 checks.py src/
    $ python3 checks.py src/loader.py src/report.py
    $ python3 checks.py src/ --select NAR001 --select NAR006

Exit codes:
    0  nothing found
    1  at least one finding
"""

import argparse
import ast
import sys
from dataclasses import dataclass
from pathlib import Path


### The nine rules that no off-the-shelf tool implements. Everything else is ruff, pylint or mypy;
### see tooling.md for the split and for the evidence that each of those actually fires.
### Stdlib only, so this runs anywhere python3 does.

MAX_BODY_LINES_WITHOUT_DOCSTRING = 20
MAX_ARGS_ON_ONE_LINE = 3
MAX_ANNOTATION_DEPTH = 2
MIN_LINES_BEFORE_BLANK = 3

RULES = {
    'NAR001': 'module-level object mutated in a function without a `global` declaration',
    'NAR006': 'assignment shadows a module-level name -- add `global`, or rename the local',
    'NAR002': 'hasattr(self, ...) -- attributes must not be conditionally defined',
    'NAR003': f'def signature with more than {MAX_ARGS_ON_ONE_LINE} POSITIONAL args on one line',
    'NAR004': 'no docstring on a function that raises, takes >3 parameters, or runs long',
    'NAR005': f'annotation nested deeper than {MAX_ANNOTATION_DEPTH} -- promote it to a dataclass',
    'NAR007': '`and` inside `or` without parentheses -- do not make the reader apply precedence',
    'NAR008': f'no blank line after a statement spanning {MIN_LINES_BEFORE_BLANK}+ lines',
    'NAR009': 'module docstring missing, or runnable module without a usage example',
    'NAR000': 'file could not be read or parsed',
}


@dataclass(frozen=True)
class Finding:
    path: Path
    line: int
    code: str
    detail: str

    def __str__(self) -> str:
        return f'{self.path}:{self.line}: {self.code} {self.detail}'


TYPE_FACTORY_CALLS = frozenset({'NewType', 'TypeVar', 'ParamSpec', 'TypeVarTuple', 'NamedTuple', 'TypedDict'})


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
MUTATING_PREFIXES = (
    'set', 'add', 'remove', 'register', 'unregister', 'reset', 'delete', 'insert',
    'write', 'load', 'enable', 'disable', 'configure', 'install', 'attach', 'detach',
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
        func: The function to inspect.
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


def checkGlobalDeclarations(tree: ast.Module, path: Path) -> list[Finding]:
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
            findings.append(Finding(path, func.lineno, 'NAR001', detail))

        # A bare `NAME = x` with no `global` silently creates a local that shadows module state.
        # Python accepts it; the module value never changes. Almost always a bug.
        rebound = {n.id for n in ast.walk(func) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)}
        shadowing = sorted((rebound & module_vars) - declared)
        if shadowing:
            detail = f'{func.name} assigns {", ".join(shadowing)} without `global`'
            findings.append(Finding(path, func.lineno, 'NAR006', detail))

    return findings


def checkHasattrSelf(tree: ast.Module, path: Path) -> list[Finding]:
    findings: list[Finding] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
            continue
        if node.func.id != 'hasattr' or not node.args:
            continue
        first = node.args[0]
        if isinstance(first, ast.Name) and first.id == 'self':
            findings.append(Finding(path, node.lineno, 'NAR002', 'declare the attribute in __init__ instead'))

    return findings


def checkArgsPerLine(tree: ast.Module, path: Path) -> list[Finding]:
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
            findings.append(Finding(path, node.lineno, 'NAR003', detail))

    return findings


def checkDocstringThreshold(tree: ast.Module, path: Path) -> list[Finding]:
    """Require a docstring wherever the contract is complex, not merely where the body is long.

    A pure line threshold is gameable in the wrong direction: splitting a 21-line function into two
    12-line ones deletes the obligation, so the rule would reward fragmentation. Contract
    complexity does not shrink when you split a function — the pieces still raise, and still take
    their parameters.

    Triggers: the function raises, or takes more than three parameters, or exceeds the line
    threshold. Keyword-only parameters count here, unlike NAR003 — every parameter is part of the
    contract even when the caller may omit it.
    """
    findings: list[Finding] = []

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if ast.get_docstring(node) is not None:
            continue

        body_start = node.body[0].lineno
        body_end = max((getattr(n, 'end_lineno', None) or 0) for n in ast.walk(node))
        body_lines = body_end - body_start + 1

        args = node.args
        every_arg = args.posonlyargs + args.args + args.kwonlyargs
        arity = len(every_arg) - (1 if args.args and args.args[0].arg in ('self', 'cls') else 0)
        raises = any(isinstance(n, ast.Raise) for n in ast.walk(node))

        reasons = []
        if body_lines > MAX_BODY_LINES_WITHOUT_DOCSTRING:
            reasons.append(f'{body_lines} body lines')
        if arity > MAX_ARGS_ON_ONE_LINE:
            reasons.append(f'{arity} parameters')
        if raises:
            reasons.append('raises')

        if reasons:
            findings.append(Finding(path, node.lineno, 'NAR004', f'{node.name}: {", ".join(reasons)}'))

    return findings


def annotationDepth(node: ast.expr) -> int:
    if isinstance(node, ast.Subscript):
        inner = node.slice
        parts = inner.elts if isinstance(inner, ast.Tuple) else [inner]
        return 1 + max((annotationDepth(p) for p in parts), default=0)

    return 0


def checkAnnotationDepth(tree: ast.Module, path: Path) -> list[Finding]:
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
            depth = annotationDepth(annotation)
            if depth > MAX_ANNOTATION_DEPTH:
                rendered = ast.unparse(annotation)
                findings.append(Finding(path, annotation.lineno, 'NAR005', f'depth {depth}: {rendered}'))

    return findings


def checkBoolOpParens(tree: ast.Module, source: str, path: Path) -> list[Finding]:
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
                findings.append(Finding(path, operand.lineno, 'NAR007', detail))

    return findings


def checkBlankLineBlocks(tree: ast.Module, path: Path) -> list[Finding]:
    """Flag a multi-line statement butted directly against the next statement.

    Blank lines inside a function separate logically self-contained blocks, and in this style that
    is their only meaning. The rule is deliberately conservative — it fires only after a statement
    of three or more lines, so deliberately grouped one- and two-line guards stay grouped.

    A docstring is exempt: it is not a block of logic, and the first real statement follows it
    directly.
    """
    findings: list[Finding] = []

    for parent in ast.walk(tree):
        for field in ('body', 'orelse', 'finalbody'):
            block = getattr(parent, field, None)
            if not isinstance(block, list):
                continue

            for first, second in zip(block, block[1:], strict=False):
                span = (first.end_lineno or first.lineno) - first.lineno + 1
                touching = second.lineno == (first.end_lineno or first.lineno) + 1
                is_docstring = (
                    block.index(first) == 0
                    and isinstance(first, ast.Expr)
                    and isinstance(first.value, ast.Constant)
                    and isinstance(first.value.value, str)
                )

                if span >= MIN_LINES_BEFORE_BLANK and touching and not (is_docstring or sameCallee(first, second)):
                    detail = f'{span}-line statement is followed immediately by another'
                    findings.append(Finding(path, second.lineno, 'NAR008', detail))

    return findings


def calleeName(node: ast.stmt) -> str | None:
    if not isinstance(node, ast.Expr) or not isinstance(node.value, ast.Call):
        return None

    func = node.value.func
    if isinstance(func, ast.Attribute):
        return func.attr
    return func.id if isinstance(func, ast.Name) else None


def sameCallee(first: ast.stmt, second: ast.stmt) -> bool:
    # Repeated calls to one callee are a group by construction -- a run of `parser.add_argument(...)`
    # is one block however long any single call wraps to. Splitting it would break exactly the
    # grouping this rule exists to protect.
    name = calleeName(first)
    return name is not None and name == calleeName(second)


def checkModuleDocstring(tree: ast.Module, path: Path) -> list[Finding]:
    """Require a module docstring, and a usage example on anything runnable.

    The docstring is the first thing a reader meets, before `main()`. A module that can be executed
    has to show how — semantics vary per program, and a reader should not have to reconstruct the
    invocation from `argparse` calls further down.

    Returns:
        One finding for a missing docstring, or one for a runnable module whose docstring shows no
        example invocation.
    """
    docstring = ast.get_docstring(tree)
    if docstring is None:
        return [Finding(path, 1, 'NAR009', 'module has no docstring')]

    runnable = any(isinstance(node, ast.If) and '__main__' in ast.unparse(node.test) for node in tree.body)

    if not runnable:
        return []

    shows_usage = any(line.lstrip().startswith(('$', '>>>', 'python3 ', 'python ')) for line in docstring.splitlines())
    if not shows_usage:
        return [Finding(path, 1, 'NAR009', 'runnable module: docstring shows no example invocation')]

    return []


def checkFile(path: Path) -> list[Finding]:
    """Run every check against one file.

    An unreadable file is reported like any other finding rather than aborting the run: a linter
    invoked over a directory must not stop at the first bad path (Q24).

    Returns:
        Every finding for this file, or a single NAR000 if it could not be read or parsed.
    """
    try:
        source = path.read_text(encoding='utf-8')
    except OSError as exc:
        return [Finding(path, 0, 'NAR000', f'unreadable: {exc.strerror}')]
    except UnicodeDecodeError as exc:
        return [Finding(path, 0, 'NAR000', f'not UTF-8: {exc.reason}')]

    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        return [Finding(path, exc.lineno or 0, 'NAR000', f'syntax error: {exc.msg}')]

    return [
        *checkGlobalDeclarations(tree, path),
        *checkHasattrSelf(tree, path),
        *checkArgsPerLine(tree, path),
        *checkDocstringThreshold(tree, path),
        *checkAnnotationDepth(tree, path),
        *checkBoolOpParens(tree, source, path),
        *checkBlankLineBlocks(tree, path),
        *checkModuleDocstring(tree, path),
    ]


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
        targets.extend(sorted(target.rglob('*.py')) if target.is_dir() else [target])

    findings: list[Finding] = []
    for path in targets:
        findings.extend(checkFile(path))
    if args.select:
        findings = [f for f in findings if f.code in args.select]

    for finding in sorted(findings, key=lambda f: (str(f.path), f.line)):
        print(f'{finding} -- {RULES.get(finding.code, "")}')

    if targets:
        # A file already reported as unreadable must not be re-read here just to size the report.
        scanned = 0
        for path in targets:
            try:
                scanned += len(path.read_text(encoding='utf-8').splitlines())
            except (OSError, UnicodeDecodeError):
                continue

        rate = len(findings) / max(scanned, 1) * 100
        print(f'\n{len(findings)} findings over {len(targets)} files ({rate:.2f} per 100 lines)')

    return 1 if findings else 0


if __name__ == '__main__':
    sys.exit(main())
