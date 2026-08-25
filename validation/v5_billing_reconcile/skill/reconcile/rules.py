"""Read the rules file, and construct the ReconcileRules that the join applies.

    {
      "ignored_skus": ["support-plan"],
      "region_aliases": {"us-east-1": "use1", "eu-west-1": "euw1"},
      "grace_cents": 500
    }

An alias names one region twice, and both names resolve to the short one, so `us-east-1` and
`use1` compare equal. `grace_cents` is a monthly cost at or below which a finding is recorded and
ignored by the exit code. The first malformed field stops the read.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from reconcile.inventory import Cents, RegionName, Sku


LOG = logging.getLogger(__name__)


def readReconcileRules(rules_path: Path) -> ReconcileRules:
    """Construct the ReconcileRules that `rules_path` states.

    Raises:
        RulesError: the file is absent, is not JSON, or holds a field of the wrong shape.
    """
    if not rules_path.is_file():
        raise rejectRules(rules_path, 'no such file')

    try:
        document: object = json.loads(rules_path.read_text(encoding='utf-8'))
    except OSError as exc:
        raise rejectRules(rules_path, f'unreadable: {exc}') from exc
    except json.JSONDecodeError as exc:
        raise rejectRules(rules_path, f'not JSON: {exc}') from exc
    if not isinstance(document, dict):
        raise rejectRules(rules_path, 'the top level is not an object')

    # An alias resolves in both directions, so the short name maps to itself.
    aliases: dict[RegionName, RegionName] = {}
    for long_name, short_name in extractStringMapping(document, 'region_aliases', rules_path).items():
        aliases[RegionName(long_name)] = RegionName(short_name)
        aliases[RegionName(short_name)] = RegionName(short_name)

    ignored_skus = frozenset(Sku(sku) for sku in extractStringList(document, 'ignored_skus', rules_path))
    grace_cents = Cents(extractInteger(document, 'grace_cents', rules_path))
    return ReconcileRules(ignored_skus=ignored_skus, region_aliases=aliases, grace_cents=grace_cents)


def extractStringList(document: Mapping[str, object], key: str, rules_path: Path) -> list[str]:
    value = document.get(key)
    if not isinstance(value, list):
        raise rejectRules(rules_path, f'{key} is not a list')
    for item in value:
        if not isinstance(item, str):
            raise rejectRules(rules_path, f'{key} holds a {type(item).__name__}, and every item must be a string')
    return value


def extractStringMapping(document: Mapping[str, object], key: str, rules_path: Path) -> dict[str, str]:
    value = document.get(key)
    if not isinstance(value, dict):
        raise rejectRules(rules_path, f'{key} is not an object')
    for name, alias in value.items():
        if not isinstance(name, str) or not isinstance(alias, str):
            raise rejectRules(rules_path, f'{key} holds a non-string name or value')
    return value


def extractInteger(document: Mapping[str, object], key: str, rules_path: Path) -> int:
    value = document.get(key)
    if not isinstance(value, int) or isinstance(value, bool):  # a bool is an int in Python
        raise rejectRules(rules_path, f'{key} is not an integer')
    return value


def rejectRules(rules_path: Path, reason: str) -> RulesError:
    # The program cannot know what it was asked to reconcile, so this is an error and not a tally.
    LOG.error('rules.rejected', extra={'rules': str(rules_path), 'reason': reason})
    return RulesError(f'{rules_path}: {reason}')


### vocabulary #########################################################################


class RulesError(RuntimeError):
    """The rules file does not state a usable set of rules."""


@dataclass(frozen=True)
class ReconcileRules:
    """What the rules file states.

    A region that the file names in no alias resolves to itself.
    """

    ignored_skus: frozenset[Sku]
    region_aliases: Mapping[RegionName, RegionName]
    grace_cents: Cents

    def resolveRegion(self, region: RegionName) -> RegionName:
        return self.region_aliases.get(region, region)
