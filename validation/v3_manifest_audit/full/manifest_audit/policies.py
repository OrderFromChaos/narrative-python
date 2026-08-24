"""Read the policy file, and say which rules a declared package breaks.

Whether a package is banned is a property of the policy, so the check lives beside the parser that
built it. The program holds exactly one policy, so this is a module and not a class.

The policy file is the configuration, not the batch. A half-valid policy means the program does not
know what it was asked to check, so the gate raises on the first bad entry instead of degrading. A
malformed manifest is the opposite case and is reported per file.

Every field of the policy file is optional. An absent `allowed_sources` allows every source, because
an empty allow-list that rejected everything would make a partial policy fail every package.
"""

from __future__ import annotations

import json
from pathlib import Path

from manifest_audit import versions
from manifest_audit.errors import rejectPolicy
from manifest_audit.vocabulary import DeclaredPackage, PackageName, Policy, SourceName, VersionText, Violation


def policyIn(path: Path) -> Policy:
    """Parse the policy file into a frozen record, once, at this gate.

    Nothing downstream validates the policy again.

    Args:
        path: The `policy.json` to read.

    Returns:
        The parsed policy.

    Raises:
        PolicyError: The file is missing, unreadable, not JSON, or a field has the wrong shape.
    """
    if not path.is_file():
        raise rejectPolicy(path, 'no such file')

    try:
        document = json.loads(path.read_text(encoding='utf-8'))
    except OSError as exc:
        raise rejectPolicy(path, f'unreadable: {exc.strerror}') from exc
    except json.JSONDecodeError as exc:
        raise rejectPolicy(path, f'not JSON: {exc.msg} at line {exc.lineno}') from exc

    if not isinstance(document, dict):
        raise rejectPolicy(path, f'the top level is {type(document).__name__}, not an object')

    banned = _stringList(document.get('banned', []), 'banned', path)
    sources = _stringList(document.get('allowed_sources', []), 'allowed_sources', path)
    minimums = _stringMap(document.get('minimum_versions', {}), 'minimum_versions', path)

    return Policy(
        banned=frozenset(PackageName(name) for name in banned),
        minimum_versions={PackageName(name): VersionText(floor) for name, floor in minimums.items()},
        allowed_sources=frozenset(SourceName(name) for name in sources),
    )


def violationsFor(package: DeclaredPackage, policy: Policy) -> tuple[Violation, ...]:
    # One package can break several rules, and each one is a separate finding: a banned package that
    # is also stale must not hide the stale version once the ban is lifted.
    broken = []

    if package.name in policy.banned:
        broken.append(Violation.BANNED)

    minimum = policy.minimum_versions.get(package.name)
    if minimum is not None and versions.belowMinimum(package.version, minimum):
        broken.append(Violation.BELOW_MINIMUM)

    if policy.allowed_sources and package.source not in policy.allowed_sources:
        broken.append(Violation.DISALLOWED_SOURCE)

    return tuple(broken)


def detailFor(violation: Violation, package: DeclaredPackage, policy: Policy) -> str:
    # No `case _`. A fourth member of Violation then fails the type check here, which is where the
    # operator-facing wording for it has to be written anyway.
    match violation:
        case Violation.BANNED:
            return 'the policy bans this package'
        case Violation.BELOW_MINIMUM:
            return f'below the minimum {policy.minimum_versions[package.name]}'
        case Violation.DISALLOWED_SOURCE:
            allowed = ', '.join(sorted(policy.allowed_sources))
            return f'source {package.source} is not one of {allowed}'


def _stringList(value: object, field: str, path: Path) -> list[str]:
    if not isinstance(value, list):
        raise rejectPolicy(path, f'{field} is {type(value).__name__}, not a list')

    return [_requireString(item, field, path) for item in value]


def _stringMap(value: object, field: str, path: Path) -> dict[str, str]:
    if not isinstance(value, dict):
        raise rejectPolicy(path, f'{field} is {type(value).__name__}, not an object')

    return {_requireString(k, field, path): _requireString(v, field, path) for k, v in value.items()}


def _requireString(value: object, field: str, path: Path) -> str:
    if not isinstance(value, str):
        raise rejectPolicy(path, f'{field} holds {type(value).__name__}, not a string')

    return value
