"""Read the rules file into a ReconcileRules, and apply what it states.

    {
      "ignored_skus": ["support-plan"],
      "region_aliases": {"us-east-1": "use1", "us-west-2": "usw2"},
      "grace_cents": 500
    }

All three keys are required, and the first malformed key stops the read. `region_aliases` maps one
spelling of a region to the other, and a region the file does not name stands for itself.
`grace_cents` is the cost at or below which a billed_not_found finding is recorded and does not
fail the run.
"""

from __future__ import annotations

import json
from pathlib import Path

from reconciler.logs import LOG
from reconciler.vocabulary import Cents, Finding, FindingKind, ReconcileRules, RegionName, RulesFileError, Sku


def readRules(rules_path: Path) -> ReconcileRules:
    """Parse the rules file into the record the join and the report both read.

    Raises:
        RulesFileError: the file is missing, is not JSON, or states a key of the wrong shape.
    """
    REQUIRED_KEYS = ('ignored_skus', 'region_aliases', 'grace_cents')

    if not rules_path.is_file():
        raise _rejectRules(rules_path, 'no rules file at that path')

    try:
        rules_text = rules_path.read_text(encoding='utf-8')
    except UnicodeDecodeError as exc:
        raise _rejectRules(rules_path, 'the rules file is not UTF-8 text') from exc
    except OSError as exc:
        raise _rejectRules(rules_path, 'the rules file could not be read') from exc

    try:
        stated = json.loads(rules_text)
    except json.JSONDecodeError as exc:
        raise _rejectRules(rules_path, 'the rules file is not valid JSON') from exc

    # validate the shape of every key before any of them reaches a lookup
    if not isinstance(stated, dict):
        raise _rejectRules(rules_path, 'the rules file holds something other than a JSON object')
    absent = [key for key in REQUIRED_KEYS if key not in stated]
    if absent:
        raise _rejectRules(rules_path, f'the rules file states no {", no ".join(absent)}')
    ignored_skus = stated['ignored_skus']
    region_aliases = stated['region_aliases']
    grace_cents = stated['grace_cents']
    if not isinstance(ignored_skus, list) or not all(isinstance(sku, str) for sku in ignored_skus):
        raise _rejectRules(rules_path, '"ignored_skus" is not a list of strings')
    if not isinstance(region_aliases, dict) or not all(
        isinstance(alias, str) and isinstance(region, str) for alias, region in region_aliases.items()
    ):
        raise _rejectRules(rules_path, '"region_aliases" is not an object of string to string')
    if isinstance(grace_cents, bool) or not isinstance(grace_cents, int) or grace_cents < 0:
        raise _rejectRules(rules_path, '"grace_cents" is not a count of cents at or above zero')

    reconcile_rules = ReconcileRules(
        ignored_skus=frozenset(Sku(sku) for sku in ignored_skus),
        region_aliases={RegionName(alias): RegionName(region) for alias, region in region_aliases.items()},
        grace_cents=Cents(grace_cents),
    )
    return reconcile_rules


def canonicaliseRegion(region: RegionName, reconcile_rules: ReconcileRules) -> RegionName:
    # The file maps one spelling to the other and states neither direction, so a region the file
    # does not name is already canonical and stands for itself.
    return reconcile_rules.region_aliases.get(region, region)


def aboveGrace(finding: Finding, reconcile_rules: ReconcileRules) -> bool:
    # Grace answers whether a finding is worth failing the run over, and only a billing line that
    # bought nothing is. A region mismatch carries a cost too, and no cost excuses it.
    if finding.kind is not FindingKind.BILLED_NOT_FOUND:
        return False
    return finding.monthly_cents is not None and finding.monthly_cents > reconcile_rules.grace_cents


def _rejectRules(rules_path: Path, reason: str) -> RulesFileError:
    LOG.error('rules.rejected', extra={'path': str(rules_path), 'reason': reason})
    return RulesFileError(f'{rules_path}: {reason}')
