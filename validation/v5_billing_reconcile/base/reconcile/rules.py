"""The `reconcile.json` rules file.

The file holds three keys:

    ignored_skus    a resource with one of these skus takes part in no join
    region_aliases  a long region name mapped to its short name
    grace_cents     a billed_not_found finding at or below this cost is
                    recorded but does not set the exit code

Every key is optional. An absent key takes the default in `Rules`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

RULES_FILENAME = "reconcile.json"


class RulesError(Exception):
    """The rules file exists but cannot be used."""


@dataclass(frozen=True)
class Rules:
    """Normalised rules.

    Skus and region names are compared in lower case. The raw text stays in the
    records, so the report shows what the input files said.
    """

    ignored_skus: frozenset[str] = frozenset()
    region_aliases: dict[str, str] = field(default_factory=dict)
    grace_cents: int = 0
    source: str | None = None

    def is_ignored(self, sku: str) -> bool:
        return sku.strip().lower() in self.ignored_skus

    def canonical_region(self, region: str) -> str:
        """Resolve a region name to the name that all of its aliases share.

        The mapping in the file goes one way, from the long name to the short
        one. Following it to its end makes both directions compare equal:
        `us-east-1` and `use1` both resolve to `use1`.
        """
        current = region.strip().lower()
        seen: set[str] = set()
        while current in self.region_aliases and current not in seen:
            seen.add(current)
            current = self.region_aliases[current]
        return current

    def same_region(self, left: str, right: str) -> bool:
        return self.canonical_region(left) == self.canonical_region(right)

    def as_dict(self) -> dict[str, Any]:
        return {
            "ignored_skus": sorted(self.ignored_skus),
            "region_aliases": dict(self.region_aliases),
            "grace_cents": self.grace_cents,
            "source": self.source,
        }


def default_rules_path(input_dir: Path) -> Path:
    return input_dir / RULES_FILENAME


def load_rules(path: Path) -> Rules:
    """Read and validate a rules file.

    Raises `RulesError` if the file is not readable, is not JSON, or holds a
    value of the wrong type. The rules decide which findings exist, so a broken
    rules file stops the run instead of being skipped.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as error:
        raise RulesError(f"cannot read rules file {path}: {error}") from error

    try:
        raw = json.loads(text)
    except json.JSONDecodeError as error:
        raise RulesError(f"rules file {path} is not valid JSON: {error}") from error

    if not isinstance(raw, dict):
        raise RulesError(f"rules file {path} must hold a JSON object")

    return Rules(
        ignored_skus=_read_sku_list(raw.get("ignored_skus", []), path),
        region_aliases=_read_alias_map(raw.get("region_aliases", {}), path),
        grace_cents=_read_grace(raw.get("grace_cents", 0), path),
        source=str(path),
    )


def _read_sku_list(value: Any, path: Path) -> frozenset[str]:
    if not isinstance(value, list):
        raise RulesError(f"rules file {path}: ignored_skus must be a list")
    skus = set()
    for item in value:
        if not isinstance(item, str):
            raise RulesError(f"rules file {path}: ignored_skus must hold strings")
        skus.add(item.strip().lower())
    return frozenset(skus)


def _read_alias_map(value: Any, path: Path) -> dict[str, str]:
    if not isinstance(value, dict):
        raise RulesError(f"rules file {path}: region_aliases must be an object")
    aliases: dict[str, str] = {}
    for name, alias in value.items():
        if not isinstance(alias, str):
            raise RulesError(
                f"rules file {path}: region_aliases[{name!r}] must be a string"
            )
        aliases[str(name).strip().lower()] = alias.strip().lower()
    return aliases


def _read_grace(value: Any, path: Path) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise RulesError(f"rules file {path}: grace_cents must be a whole number")
    if value < 0:
        raise RulesError(f"rules file {path}: grace_cents must not be negative")
    return value
