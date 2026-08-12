import argparse
import ast
import sys
from pathlib import Path

### The four rules that no off-the-shelf tool implements. Everything else is ruff, pylint or mypy;
### see tooling.md for the split and for the evidence that each of those actually fires.
### Stdlib only, so this runs anywhere python3 does.

MAX_BODY_LINES_WITHOUT_DOCSTRING = 20
MAX_ARGS_ON_ONE_LINE = 3
MAX_ANNOTATION_DEPTH = 2

RULES = {
    'NAR001': 'module-level object mutated in a function without a `global` declaration',
    'NAR006': 'assignment shadows a module-level name -- add `global`, or rename the local',
    'NAR002': 'hasattr(self, ...) -- attributes must not be conditionally defined',
    'NAR003': f'more than {MAX_ARGS_ON_ONE_LINE} arguments on one line -- put each on its own line',
    'NAR004': f'function body over {MAX_BODY_LINES_WITHOUT_DOCSTRING} lines without a docstring',
    'NAR005': f'annotation nested deeper than {MAX_ANNOTATION_DEPTH} -- promote it to a dataclass',
}


class Finding:
    def __init__(self, path: Path, line: int, code: str, detail: str) -> None:
        self.path = path
        self.line = line
        self.code = code
        self.detail = detail

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
    if isinstance(value, ast.BinOp) and isinstance(value.op, ast.BitOr):
        return True
    return False


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
MUTATING_METHODS = frozenset(
    {
        'append',
        'extend',
        'insert',
        'remove',
        'pop',
        'clear',
        'sort',
        'reverse',
        'update',
        'setdefault',
        'popitem',
        'add',
        'discard',
        '__setitem__',
        '__delitem__',
        '__iadd__',
    }
)


def mutatedModuleNames(func: ast.FunctionDef | ast.AsyncFunctionDef, module_vars: set[str]) -> set[str]:
    mutated: set[str] = set()

    def rootName(node: ast.expr) -> str | None:
        while isinstance(node, (ast.Attribute, ast.Subscript)):
            node = node.value
        return node.id if isinstance(node, ast.Name) else None

    for node in ast.walk(func):
        target: ast.expr | None = None
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in MUTATING_METHODS:
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
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node is not func:
            bound.add(node.name)
        elif isinstance(node, ast.ExceptHandler) and node.name:
            bound.add(node.name)
    return bound


def checkGlobalDeclarations(tree: ast.Module, path: Path) -> list[Finding]:
    module_vars = moduleLevelVariables(tree)
    findings: list[Finding] = []

    for func in ast.walk(tree):
        if not isinstance(func, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue

        declared: set[str] = set()
        for node in ast.walk(func):
            if isinstance(node, ast.Global):
                declared.update(node.names)
            elif isinstance(node, ast.Nonlocal):
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


def checkArgsPerLine(tree: ast.Module, source: str, path: Path) -> list[Finding]:
    # The formatter will happily leave a 4-argument signature on one line if it fits in 120
    # columns, and COM812 only fires once a construct is already split. This is the gap.
    lines = source.splitlines()
    findings: list[Finding] = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            args = node.args
            count = len(args.posonlyargs) + len(args.args) + len(args.kwonlyargs)
            count -= 1 if args.args and args.args[0].arg in ('self', 'cls') else 0
            end_line = max((a.lineno for a in args.posonlyargs + args.args + args.kwonlyargs), default=node.lineno)
            label = f'def {node.name}'
        elif isinstance(node, ast.Call):
            count = len(node.args) + len(node.keywords)
            positions = [a.lineno for a in node.args] + [k.value.lineno for k in node.keywords]
            end_line = max(positions, default=node.lineno)
            label = 'call'
        else:
            continue

        if count > MAX_ARGS_ON_ONE_LINE and end_line == node.lineno:
            findings.append(Finding(path, node.lineno, 'NAR003', f'{label} has {count} args on one line'))

    del lines
    return findings


def checkDocstringThreshold(tree: ast.Module, path: Path) -> list[Finding]:
    findings: list[Finding] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if ast.get_docstring(node) is not None:
            continue

        body_start = node.body[0].lineno
        body_end = max((getattr(n, 'end_lineno', None) or 0) for n in ast.walk(node))
        body_lines = body_end - body_start + 1
        if body_lines > MAX_BODY_LINES_WITHOUT_DOCSTRING:
            findings.append(Finding(path, node.lineno, 'NAR004', f'{node.name} is {body_lines} body lines'))
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


def checkFile(path: Path) -> list[Finding]:
    source = path.read_text(encoding='utf-8')
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        return [Finding(path, exc.lineno or 0, 'NAR000', f'syntax error: {exc.msg}')]

    return [
        *checkGlobalDeclarations(tree, path),
        *checkHasattrSelf(tree, path),
        *checkArgsPerLine(tree, source, path),
        *checkDocstringThreshold(tree, path),
        *checkAnnotationDepth(tree, path),
    ]


def main() -> int:
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
        rate = len(findings) / max(sum(len(p.read_text().splitlines()) for p in targets), 1) * 100
        print(f'\n{len(findings)} findings over {len(targets)} files ({rate:.2f} per 100 lines)')
    return 1 if findings else 0


if __name__ == '__main__':
    sys.exit(main())
