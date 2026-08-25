"""Read the rules file, and construct the ReconcileRules that the join applies.

    {
      "ignored_skus": ["platform-support-tier"],
      "region_aliases": {"north-atlantic-1": "na1", "south-pacific-2": "sp2"},
      "grace_cents": 750
    }

All three keys are mandatory. A missing key, a value of the wrong type or a negative grace raises
RulesError rather than degrading: a half-read rules file leaves the program unable to say which
resources it was asked to reconcile.
"""

from __future__ import annotations

import json
from pathlib import Path

from reconcile.logs import LOG
from reconcile.vocabulary import Cents, ReconcileRules, RegionName, RulesError, Sku


RULES_FILENAME = 'reconcile.json'


def readReconcileRules(rules_path: Path) -> ReconcileRules:
    """Parse the rules file at rules_path.

    Raises:
        RulesError: the file is unreadable, is not a JSON object, omits one of the three keys, or
            holds a value the join cannot apply.
    """
    if not rules_path.is_file():
        raise _rejectRules(rules_path, 'no such file')
    try:
        stated = json.loads(rules_path.read_text(encoding='utf-8'))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _rejectRules(rules_path, f'unreadable: {exc}') from exc
    if not isinstance(stated, dict):
        raise _rejectRules(rules_path, 'the top level is not an object')

    # every key is mandatory, and each carries its own shape
    for key in ('ignored_skus', 'region_aliases', 'grace_cents'):
        if key not in stated:
            raise _rejectRules(rules_path, f'{key} is missing')
    rules = ReconcileRules(
        ignored_skus=_readIgnoredSkus(rules_path, stated['ignored_skus']),
        region_aliases=_readRegionAliases(rules_path, stated['region_aliases']),
        grace_cents=_readGraceCents(rules_path, stated['grace_cents']),
    )
    return rules


def _readIgnoredSkus(rules_path: Path, stated: object) -> frozenset[Sku]:
    if not isinstance(stated, list):
        raise _rejectRules(rules_path, 'ignored_skus is not a list')
    if not all(isinstance(entry, str) for entry in stated):
        raise _rejectRules(rules_path, 'ignored_skus holds a value that is not a string')
    return frozenset(Sku(entry) for entry in stated)


def _readRegionAliases(rules_path: Path, stated: object) -> dict[RegionName, RegionName]:
    if not isinstance(stated, dict):
        raise _rejectRules(rules_path, 'region_aliases is not an object')
    if not all(isinstance(alias, str) and isinstance(canonical, str) for alias, canonical in stated.items()):
        raise _rejectRules(rules_path, 'region_aliases holds a value that is not a string')
    return {RegionName(alias): RegionName(canonical) for alias, canonical in stated.items()}


def _readGraceCents(rules_path: Path, stated: object) -> Cents:
    # bool is a subclass of int, so `true` would otherwise pass as a grace of 1
    if isinstance(stated, bool) or not isinstance(stated, int):
        raise _rejectRules(rules_path, 'grace_cents is not an integer')
    if stated < 0:
        raise _rejectRules(rules_path, 'grace_cents is negative')
    return Cents(stated)


def _rejectRules(rules_path: Path, reason: str) -> RulesError:
    """Log the rejection and return the error, so a raise site stays two lines."""
    LOG.error('rules.rejected', extra={'path': str(rules_path), 'reason': reason})
    return RulesError(f'{rules_path}: {reason}')
