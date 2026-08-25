"""The two outputs: the summary table for a person, the JSON for a program.

Both show the same run. The table drops nothing that the JSON holds, except the
text of the per-record problems, which the table prints below the file rows.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from .model import Finding, FindingKind, Reconciliation
from .store import StoreStats


def render(result: Reconciliation) -> str:
    """Build the summary table for the terminal."""
    blocks = [
        _findings_block(result),
        _files_block(result),
        _summary_block(result),
    ]
    return "\n\n".join(block for block in blocks if block)


def build_report(
    result: Reconciliation, store: StoreStats | None = None
) -> dict[str, Any]:
    """Build the JSON report as a dictionary."""
    report: dict[str, Any] = {
        "generated_at": result.generated_at,
        "input_dir": result.input_dir,
        "rules": result.rules.as_dict(),
        "totals": {
            **result.stats.as_dict(),
            "findings": len(result.findings),
            "above_grace": len(result.actionable),
            "by_kind": {
                kind.value: len(result.of_kind(kind)) for kind in FindingKind
            },
        },
        "findings": [finding.as_dict() for finding in result.findings],
        "files": [outcome.as_dict() for outcome in result.outcomes],
        "exit_code": result.exit_code,
    }
    if store is not None:
        report["store"] = store.as_dict()
    return report


def write_report(
    path: Path, result: Reconciliation, store: StoreStats | None = None
) -> None:
    """Write the JSON report to `path`."""
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(build_report(result, store), indent=2, sort_keys=False)
    path.write_text(text + "\n", encoding="utf-8")


def _findings_block(result: Reconciliation) -> str:
    if not result.findings:
        return "FINDINGS\n  none"

    rows = [
        [
            finding.kind.value,
            finding.resource_id,
            finding.sku,
            finding.team or "-",
            _money(finding.monthly_cents),
            finding.billed_region or "-",
            finding.scanned_region or "-",
            _grace(finding),
        ]
        for finding in result.findings
    ]
    table = _table(
        ["kind", "resource", "sku", "team", "monthly", "billed", "scanned", "grace"],
        rows,
        aligns="llllrlll",
    )
    return "FINDINGS\n" + table


def _files_block(result: Reconciliation) -> str:
    if not result.outcomes:
        return "FILES\n  the input directory holds no files"

    rows = [
        [
            outcome.path,
            outcome.kind,
            outcome.status,
            str(outcome.records),
            str(len(outcome.problems)) if outcome.problems else "-",
        ]
        for outcome in result.outcomes
    ]
    lines = [
        "FILES",
        _table(
            ["file", "format", "status", "records", "problems"],
            rows,
            aligns="lllrr",
        ),
    ]
    for outcome in result.outcomes:
        for problem in outcome.problems:
            lines.append(f"  {outcome.path}: {problem}")
    return "\n".join(lines)


def _summary_block(result: Reconciliation) -> str:
    stats = result.stats
    by_kind = ", ".join(
        f"{kind.value} {len(result.of_kind(kind))}" for kind in FindingKind
    )
    statuses: dict[str, int] = {}
    for outcome in result.outcomes:
        statuses[outcome.status] = statuses.get(outcome.status, 0) + 1
    files = ", ".join(f"{count} {status}" for status, count in sorted(statuses.items()))

    lines = [
        "SUMMARY",
        f"  billing lines     {stats.billing_lines} "
        f"({stats.ignored_billing} ignored)",
        f"  scanned resources {stats.scanned_resources} "
        f"({stats.ignored_scanned} ignored)",
        f"  matched           {stats.matched}",
        f"  findings          {len(result.findings)} ({by_kind})",
        f"  above grace       {len(result.actionable)} "
        f"(grace {_money(result.rules.grace_cents)})",
        f"  files             {files or 'none'}",
    ]
    return "\n".join(lines)


def _grace(finding: Finding) -> str:
    if finding.kind is not FindingKind.BILLED_NOT_FOUND:
        return "-"
    return "over" if finding.above_grace else "within"


def _money(cents: int | None) -> str:
    if cents is None:
        return "-"
    sign = "-" if cents < 0 else ""
    return f"{sign}${abs(cents) // 100:,}.{abs(cents) % 100:02d}"


def _table(
    headers: Sequence[str], rows: Sequence[Sequence[str]], aligns: str
) -> str:
    """Lay out fixed-width columns. `aligns` holds one `l` or `r` per column."""
    widths = [
        max(len(str(row[index])) for row in [headers, *rows])
        for index in range(len(headers))
    ]

    def line(cells: Sequence[str]) -> str:
        parts = [
            str(cell).rjust(width) if aligns[index] == "r" else str(cell).ljust(width)
            for index, (cell, width) in enumerate(zip(cells, widths))
        ]
        return "  " + "  ".join(parts).rstrip()

    rule = "  " + "  ".join("-" * width for width in widths)
    return "\n".join([line(headers), rule, *(line(row) for row in rows)])
