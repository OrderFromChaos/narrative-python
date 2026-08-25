"""Serialise a Reconciliation as the JSON report, and write it.

One entry of `findings`, and one of `files`:

    {
      "kind": "region_mismatch",
      "resource_id": "r-3",
      "sku": "nat",
      "monthly_cents": 9600,
      "team": "network-eng",
      "billed_region": "north-atlantic-1",
      "scanned_region": "sp2",
      "above_grace": false,
      "sources": [
        "east.billing.csv",
        "east.scan.json"
      ]
    }
    {
      "path": "west.scan.json",
      "format": "scan",
      "status": "failed",
      "accepted": 0,
      "rejected": 0,
      "problems": [
        "unreadable: Expecting value: line 1 column 1 (char 0)"
      ]
    }

Two runs over one input must write byte-identical files, so no object is sorted by key on the way
out and every one keeps the order this module writes. generated_at, input_dir and the wording
inside problems are the only values a second run, or a second implementation, may differ on.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

from reconcile.vocabulary import FileOutcome, Finding, FindingKind, Reconciliation


DEFAULT_REPORT_PATH = Path('report.json')


def buildReport(
    generated_at: str,
    input_dir: str,
    reconciliation: Reconciliation,
    exit_code: int,
) -> dict[str, object]:
    """Construct the report document.

    Args:
        generated_at: the start time of the run, not the time of this call.
        input_dir: the path exactly as the command line gave it, so a report compares across
            machines only on its other keys.
    """
    rules = reconciliation.rules
    totals = reconciliation.totals
    return {
        'generated_at': generated_at,
        'input_dir': input_dir,
        'rules': {
            'ignored_skus': sorted(rules.ignored_skus),
            'region_aliases': {alias: rules.region_aliases[alias] for alias in sorted(rules.region_aliases)},
            'grace_cents': rules.grace_cents,
        },
        'totals': {
            'billing_lines': totals.billing_lines,
            'scanned_resources': totals.scanned_resources,
            'ignored_billing': totals.ignored_billing,
            'ignored_scanned': totals.ignored_scanned,
            'matched': totals.matched,
            'findings': totals.findings,
            'above_grace': totals.above_grace,
            'by_kind': {kind.value: totals.by_kind[kind] for kind in FindingKind},
        },
        'findings': [_describeFinding(finding) for finding in reconciliation.findings],
        'files': [_describeFileOutcome(outcome) for outcome in reconciliation.file_outcomes],
        'exit_code': exit_code,
    }


def _describeFinding(finding: Finding) -> dict[str, object]:
    # a value the finding does not carry is null, never an empty string and never an absent key
    return {
        'kind': finding.kind.value,
        'resource_id': finding.resource_id,
        'sku': finding.sku,
        'monthly_cents': finding.monthly_cents,
        'team': finding.team,
        'billed_region': finding.billed_region,
        'scanned_region': finding.scanned_region,
        'above_grace': finding.above_grace,
        'sources': list(finding.sources),
    }


def _describeFileOutcome(outcome: FileOutcome) -> dict[str, object]:
    return {
        'path': outcome.path,
        'format': outcome.inventory_format.value,
        'status': outcome.status.value,
        'accepted': outcome.accepted,
        'rejected': outcome.rejected,
        'problems': list(outcome.problems),
    }


def writeReport(report_path: Path, report: Mapping[str, object]) -> None:
    """Write the document as UTF-8 with LF endings and a trailing newline."""
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8', newline='\n')
