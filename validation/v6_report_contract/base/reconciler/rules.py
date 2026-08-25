"""The rules file: how it is read, how it is checked, and what it decides.

The rules answer three questions for the join, so they are kept together with
the two lookups that use them rather than being passed around as a bare dict.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any

from .errors import ReconcileError

RULES_BASENAME = 'reconcile.json'
"""The name the rules file has inside the input directory by default."""


@dataclass(frozen=True, slots=True)
class Rules:
    """A validated rules file.

    Built only by :func:`load_rules`, so every instance already satisfies the
    type checks the task states: strings throughout, and a grace of zero or
    more cents.
    """

    ignored_skus: frozenset[str]
    region_aliases: Mapping[str, str]
    grace_cents: int

    def is_ignored(self, sku: str) -> bool:
        """Report whether a record carrying this sku is dropped before the join."""
        return sku in self.ignored_skus

    def canonical_region(self, region: str) -> str:
        """Resolve a region name through the alias table, one hop only.

        With ``a`` mapped to ``b`` and ``b`` mapped to ``c``, this maps ``a`` to
        ``b`` and stops, so ``a`` and ``c`` do not compare equal. A name the
        table does not mention resolves to itself.
        """
        return self.region_aliases.get(region, region)


def load_rules(path: Path) -> Rules:
    """Read and validate the rules file at ``path``.

    Raises:
        ReconcileError: The file is unreadable, is not a JSON object, omits one
            of the three mandatory keys, or holds a value of the wrong type.
    """
    try:
        raw_text = path.read_text(encoding='utf-8')
    except OSError as error:
        raise ReconcileError(f'cannot read rules file {path}: {error}') from error
    except UnicodeDecodeError as error:
        raise ReconcileError(f'rules file {path} is not valid UTF-8') from error

    try:
        document = json.loads(raw_text)
    except json.JSONDecodeError as error:
        raise ReconcileError(f'rules file {path} is not valid JSON: {error}') from error

    if not isinstance(document, dict):
        raise ReconcileError(f'rules file {path} must hold a JSON object at the top level')

    return Rules(
        ignored_skus=frozenset(_read_string_list(document, 'ignored_skus', path)),
        region_aliases=MappingProxyType(dict(_read_string_map(document, 'region_aliases', path))),
        grace_cents=_read_non_negative_int(document, 'grace_cents', path),
    )


def _require(document: dict[str, Any], key: str, path: Path) -> Any:
    if key not in document:
        raise ReconcileError(f'rules file {path} omits the mandatory key {key!r}')
    return document[key]


def _read_string_list(document: dict[str, Any], key: str, path: Path) -> list[str]:
    value = _require(document, key, path)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ReconcileError(f'rules file {path}: {key!r} must be a list of strings')
    return value


def _read_string_map(document: dict[str, Any], key: str, path: Path) -> dict[str, str]:
    value = _require(document, key, path)
    # JSON object keys are always strings, so only the values can be wrong.
    if not isinstance(value, dict) or not all(isinstance(item, str) for item in value.values()):
        raise ReconcileError(f'rules file {path}: {key!r} must map strings to strings')
    return value


def _read_non_negative_int(document: dict[str, Any], key: str, path: Path) -> int:
    value = _require(document, key, path)
    # bool is a subclass of int, and `true` in the rules file is a type error.
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ReconcileError(f'rules file {path}: {key!r} must be an integer of zero or more')
    return value
