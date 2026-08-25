"""The JSON report.

The report is a contract: two correct implementations must produce byte-
identical bytes for the same input, apart from the run time, the input path and
the wording inside ``problems``. That constrains three things this module
therefore does by hand rather than by convenience.

Key order is the document's order, top level and nested alike, so every mapping
here is built in the order it is published in and ``sort_keys`` is never used.
Sorted values are sorted where the document says so and nowhere else. The
serialisation is pinned: two-space indent, unescaped non-ASCII, one trailing
newline, LF line endings, UTF-8.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import FileOutcome, Finding
from .pipeline import ReconcileResult
from .rules import Rules


def build_report(result: ReconcileResult) -> dict[str, Any]:
    """Assemble the report document for one run."""
    return {
        'generated_at': result.generated_at,
        'input_dir': result.input_dir,
        'rules': _rules_block(result.rules),
        'totals': _totals_block(result),
        'findings': [_finding_entry(finding) for finding in result.findings],
        'files': [_file_entry(outcome) for outcome in sorted(result.files, key=_by_path)],
        'exit_code': result.exit_code,
    }


def write_report(path: Path, document: dict[str, Any]) -> None:
    """Write the report to ``path``, in the one serialisation the contract allows."""
    path.write_text(
        json.dumps(document, indent=2, ensure_ascii=False) + '\n',
        encoding='utf-8',
        newline='\n',
    )


def _by_path(outcome: FileOutcome) -> str:
    return outcome.path


def _rules_block(rules: Rules) -> dict[str, Any]:
    """Echo the rules that were applied, with both collections sorted."""
    return {
        'ignored_skus': sorted(rules.ignored_skus),
        'region_aliases': {key: rules.region_aliases[key] for key in sorted(rules.region_aliases)},
        'grace_cents': rules.grace_cents,
    }


def _totals_block(result: ReconcileResult) -> dict[str, Any]:
    totals = result.totals
    return {
        'billing_lines': totals.billing_lines,
        'scanned_resources': totals.scanned_resources,
        'ignored_billing': totals.ignored_billing,
        'ignored_scanned': totals.ignored_scanned,
        'matched': totals.matched,
        'findings': totals.findings,
        'above_grace': totals.above_grace,
        'by_kind': {kind.value: count for kind, count in totals.by_kind.items()},
    }


def _finding_entry(finding: Finding) -> dict[str, Any]:
    """Render one finding. A value it does not carry is ``null``, never omitted."""
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


def _file_entry(outcome: FileOutcome) -> dict[str, Any]:
    """Render one file outcome. ``path`` is the basename: the report travels."""
    return {
        'path': outcome.path,
        'format': outcome.file_format.value,
        'status': outcome.status.value,
        'accepted': outcome.accepted,
        'rejected': outcome.rejected,
        'problems': list(outcome.problems),
    }
