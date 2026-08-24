"""Hold the audit policy, and decide what one package violates.

The policy file is a JSON object with three optional fields:

    {"banned": ["leftpad"], "minimum_versions": {"requests": "2.31.0"}, "allowed_sources": ["pypi"]}

The policy is the configuration, not the batch. `loadPolicy` therefore raises on the first
malformed field instead of degrading: a half-read policy audits something other than what the
operator asked for.

A version comparison uses the leading integer of each dot-separated part, so `2.31.0rc1` compares
as `2.31.0`. An absent part counts as zero, so `2.31` is not below `2.31.0`.
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from manifest_audit.manifest import Package


LOG = logging.getLogger(__name__)


def loadPolicy(path: Path) -> Policy:
    """Read the policy file into a frozen record.

    Every field is optional. An absent field means the policy says nothing about it: no banned
    name, no minimum version, and every source allowed.

    Raises:
        PolicyError: the file is unreadable, is not JSON, or holds a field of the wrong shape.
    """
    try:
        text = path.read_text(encoding='utf-8')
    except OSError as exc:
        raise rejectPolicy(f'cannot read {path}: {exc}') from exc

    try:
        document = json.loads(text)
    except json.JSONDecodeError as exc:
        raise rejectPolicy(f'{path} is not valid JSON: {exc}') from exc

    if not isinstance(document, dict):
        raise rejectPolicy(f'{path} does not hold a JSON object')

    banned = stringList(document, 'banned', path)
    allowed_sources = stringList(document, 'allowed_sources', path)
    minimum_versions = stringMap(document, 'minimum_versions', path)

    return Policy(frozenset(banned), minimum_versions, frozenset(allowed_sources))


def stringList(document: Mapping[str, object], key: str, path: Path) -> tuple[str, ...]:
    """Read one list-of-strings field, or nothing when the field is absent.

    Raises:
        PolicyError: the field is present and is not a list of strings.
    """
    values = document.get(key, [])
    if not isinstance(values, list) or not all(isinstance(value, str) for value in values):
        raise rejectPolicy(f'{path}: {key!r} must be a list of strings')

    return tuple(values)


def stringMap(document: Mapping[str, object], key: str, path: Path) -> Mapping[str, str]:
    """Read one string-to-string field, or nothing when the field is absent.

    Raises:
        PolicyError: the field is present and is not an object of strings.
    """
    values = document.get(key, {})
    if not isinstance(values, dict) or not all(isinstance(value, str) for value in values.values()):
        raise rejectPolicy(f'{path}: {key!r} must be an object of name to version')

    return dict(values)


def findingsFor(package: Package, manifest: Path, policy: Policy) -> list[Finding]:
    """Report every rule the package breaks. One package can break more than one."""
    reasons: list[tuple[FindingKind, str]] = []
    if package.name in policy.banned:
        reasons.append((FindingKind.BANNED, 'the policy bans this package'))

    minimum = policy.minimum_versions.get(package.name)
    if minimum is not None and belowMinimum(package.version, minimum):
        reasons.append((FindingKind.BELOW_MINIMUM, f'the policy requires {minimum} or later'))

    # A lock file declares no source, and a rule can only judge what the manifest states.
    if package.source is not None and package.source not in policy.allowed_sources:
        reasons.append((FindingKind.DISALLOWED_SOURCE, f'the policy does not allow the source {package.source!r}'))

    return [Finding(manifest, package.name, package.version, kind, detail) for kind, detail in reasons]


def belowMinimum(version: str, minimum: str) -> bool:
    """Compare two dotted versions.

    `2.28.1` is below `2.31.0`. `2.31` is not below `2.31.0`, because the absent part counts as
    zero and the shorter version is padded to the same width.
    """
    found = versionParts(version)
    wanted = versionParts(minimum)
    width = max(len(found), len(wanted))

    return found + (0,) * (width - len(found)) < wanted + (0,) * (width - len(wanted))


def versionParts(version: str) -> tuple[int, ...]:
    """Split a version into the leading integer of each dot-separated part.

    `2.31.0` gives (2, 31, 0), `1.2.0rc1` gives (1, 2, 0), and a part with no leading digit gives 0.
    """
    LEADING_DIGITS = r'\d+'

    matches = [re.match(LEADING_DIGITS, part) for part in version.split('.')]
    return tuple(int(match.group()) if match else 0 for match in matches)


def rejectPolicy(reason: str) -> PolicyError:
    """Log one rejected policy and return the exception for the caller to raise."""
    LOG.error('policy.rejected', extra={'reason': reason})
    return PolicyError(reason)


### vocabulary #########################################################################


class FindingKind(Enum):
    BANNED = 'banned'
    BELOW_MINIMUM = 'below_minimum'
    DISALLOWED_SOURCE = 'disallowed_source'


class PolicyError(RuntimeError):
    """The policy file is unreadable, or one of its fields has the wrong shape."""


@dataclass(frozen=True)
class Policy:
    banned: frozenset[str]
    minimum_versions: Mapping[str, str]
    allowed_sources: frozenset[str]


@dataclass(frozen=True)
class Finding:
    manifest: Path
    package: str
    version: str
    kind: FindingKind
    detail: str
