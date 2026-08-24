"""The policy: what it holds, how it loads, and how it judges a package.

A policy has three rules, all of them optional:

* ``banned`` — package names that must not appear at all.
* ``minimum_versions`` — the oldest acceptable version, per package.
* ``allowed_sources`` — the sources a package may come from. An empty or
  absent list turns the source check off.

Package names are matched with `models.normalize_name`, so ``Left-Pad`` in a
manifest matches ``left_pad`` in the policy.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .models import Finding, FindingKind, Package, normalize_name
from .versions import InvalidVersion, is_below

__all__ = ["Policy", "PolicyError", "load_policy"]


class PolicyError(Exception):
    """The policy file is missing or cannot be read."""


@dataclass(frozen=True, slots=True)
class Policy:
    """The rules to judge packages against.

    Attributes are stored in normalized form. Build one with `from_dict` or
    `load_policy` rather than by hand, unless the caller has already
    normalized its names.
    """

    banned: frozenset[str] = frozenset()
    minimum_versions: dict[str, str] = field(default_factory=dict)
    allowed_sources: frozenset[str] = frozenset()
    path: str | None = None

    @property
    def checks_sources(self) -> bool:
        """An empty allow-list means every source is acceptable."""
        return bool(self.allowed_sources)

    @classmethod
    def from_dict(cls, document: Any, *, path: str | None = None) -> Policy:
        """Build a policy from a decoded JSON document.

        Raises:
            PolicyError: The document has the wrong shape.
        """
        if not isinstance(document, dict):
            raise PolicyError(f"{path or '<policy>'}: top level must be an object")

        banned = _string_list(document, "banned", path)
        allowed = _string_list(document, "allowed_sources", path)
        minimums = _string_map(document, "minimum_versions", path)
        return cls(
            banned=frozenset(normalize_name(name) for name in banned),
            minimum_versions={
                normalize_name(name): version for name, version in minimums.items()
            },
            allowed_sources=frozenset(source.strip().lower() for source in allowed),
            path=path,
        )

    def check(self, package: Package) -> list[Finding]:
        """Return every finding this package produces. An empty list is a pass."""
        findings: list[Finding] = []
        key = package.key

        if key in self.banned:
            findings.append(
                self._finding(package, FindingKind.BANNED, "the policy bans this package")
            )

        minimum = self.minimum_versions.get(key)
        if minimum is not None:
            version_finding = self._version_finding(package, minimum)
            if version_finding is not None:
                findings.append(version_finding)

        if self.checks_sources and package.source is not None:
            if package.source.strip().lower() not in self.allowed_sources:
                allowed = ", ".join(sorted(self.allowed_sources))
                findings.append(
                    self._finding(
                        package,
                        FindingKind.DISALLOWED_SOURCE,
                        f"source {package.source!r} is not one of: {allowed}",
                    )
                )

        return findings

    def check_all(self, packages: list[Package]) -> list[Finding]:
        """Return the findings for a list of packages, in the order given."""
        findings: list[Finding] = []
        for package in packages:
            findings.extend(self.check(package))
        return findings

    def to_dict(self) -> dict[str, Any]:
        """Return the policy as plain data, for the JSON report."""
        return {
            "path": self.path,
            "banned": sorted(self.banned),
            "minimum_versions": dict(sorted(self.minimum_versions.items())),
            "allowed_sources": sorted(self.allowed_sources),
        }

    def _version_finding(self, package: Package, minimum: str) -> Finding | None:
        try:
            below = is_below(package.version, minimum)
        except InvalidVersion as error:
            return self._finding(
                package,
                FindingKind.UNREADABLE_VERSION,
                f"{error}, so the minimum of {minimum} cannot be checked",
            )
        if below:
            return self._finding(
                package,
                FindingKind.BELOW_MINIMUM,
                f"version {package.version} is below the minimum of {minimum}",
            )
        return None

    @staticmethod
    def _finding(package: Package, kind: FindingKind, detail: str) -> Finding:
        return Finding(
            manifest=package.manifest,
            package=package.name,
            version=package.version,
            source=package.source,
            kind=kind,
            detail=detail,
            location=package.location,
        )


def load_policy(path: Path) -> Policy:
    """Read a policy file from disk.

    Raises:
        PolicyError: The file is missing, is not JSON, or has the wrong shape.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as error:
        raise PolicyError(f"{path}: no policy file at this path") from error
    except OSError as error:
        raise PolicyError(f"{path}: cannot open file: {error.strerror}") from error
    except UnicodeDecodeError as error:
        raise PolicyError(f"{path}: file is not UTF-8 text") from error

    try:
        document = json.loads(text)
    except json.JSONDecodeError as error:
        raise PolicyError(
            f"{path}: invalid JSON at line {error.lineno} column {error.colno}: {error.msg}"
        ) from error
    return Policy.from_dict(document, path=str(path))


def _string_list(document: dict[str, Any], key: str, path: str | None) -> list[str]:
    value = document.get(key, [])
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise PolicyError(f"{path or '<policy>'}: '{key}' must be an array of strings")
    return value


def _string_map(document: dict[str, Any], key: str, path: str | None) -> dict[str, str]:
    value = document.get(key, {})
    if not isinstance(value, dict) or not all(
        isinstance(item, str) for item in value.values()
    ):
        raise PolicyError(f"{path or '<policy>'}: '{key}' must be an object of strings")
    return value
