"""Output: the summary table for the terminal, and the JSON report file."""

from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .models import AuditResult
from .policy import Policy
from .store import StoreSummary

__all__ = ["REPORT_SCHEMA_VERSION", "build_report", "render_summary", "write_report"]

REPORT_SCHEMA_VERSION = 1

_NO_FINDINGS = "No findings. Every package meets the policy."


def render_summary(result: AuditResult, *, store: StoreSummary | None = None) -> str:
    """Build the text that the command-line tool prints.

    The text has a findings table, a per-manifest outcome table, and one
    closing line for each of the store and the totals.
    """
    blocks: list[str] = []

    if result.findings:
        blocks.append(
            _table(
                ["MANIFEST", "PACKAGE", "VERSION", "SOURCE", "KIND", "DETAIL"],
                [
                    [
                        Path(finding.manifest).name,
                        finding.package,
                        finding.version,
                        finding.source or "-",
                        finding.kind.value,
                        finding.detail,
                    ]
                    for finding in result.findings
                ],
            )
        )
        counts = result.counts_by_kind()
        blocks.append(
            "Findings by kind: "
            + ", ".join(f"{kind} {count}" for kind, count in counts.items())
        )
    else:
        blocks.append(_NO_FINDINGS)

    blocks.append(
        _table(
            ["MANIFEST", "FORMAT", "STATUS", "PACKAGES", "FINDINGS", "NOTE"],
            [
                [
                    Path(outcome.path).name,
                    outcome.format,
                    outcome.status.value,
                    str(outcome.package_count),
                    str(outcome.finding_count),
                    outcome.error or "",
                ]
                for outcome in result.outcomes
            ],
        )
        if result.outcomes
        else "No manifests found."
    )

    if store is not None:
        blocks.append(
            f"Store: {store.inserted} new, {store.updated} already known, "
            f"{store.pruned} cleared, {store.total_rows} rows in total."
        )

    read = len(result.outcomes) - len(result.failed_manifests)
    blocks.append(
        f"Read {read} of {_count(len(result.outcomes), 'manifest')}, "
        f"{_count(result.package_count, 'package')}, "
        f"{_count(len(result.findings), 'finding')}, "
        f"{len(result.banned_findings)} of them banned."
    )
    return "\n\n".join(blocks)


def build_report(
    result: AuditResult,
    *,
    policy: Policy | None = None,
    store: StoreSummary | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Build the JSON report as plain data."""
    report: dict[str, Any] = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "generated_at": generated_at or datetime.now(UTC).isoformat(timespec="seconds"),
        "root": result.root,
        "policy": policy.to_dict() if policy is not None else {"path": result.policy_path},
        "summary": {
            "manifests": len(result.outcomes),
            "manifests_read": len(result.outcomes) - len(result.failed_manifests),
            "manifests_failed": len(result.failed_manifests),
            "packages": result.package_count,
            "findings": len(result.findings),
            "banned_findings": len(result.banned_findings),
            "findings_by_kind": result.counts_by_kind(),
        },
        "manifests": [outcome.to_dict() for outcome in result.outcomes],
        "findings": [finding.to_dict() for finding in result.findings],
    }
    if store is not None:
        report["store"] = {
            "inserted": store.inserted,
            "updated": store.updated,
            "pruned": store.pruned,
            "total_rows": store.total_rows,
        }
    return report


def write_report(report: dict[str, Any], path: Path) -> Path:
    """Write the JSON report, and return the path it was written to.

    Raises:
        OSError: The file cannot be written.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    return path


def _count(number: int, noun: str) -> str:
    """Return ``"1 package"`` or ``"3 packages"``."""
    return f"{number} {noun}" if number == 1 else f"{number} {noun}s"


def _table(headers: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
    """Lay out a table with columns wide enough for their content."""
    widths = [len(header) for header in headers]
    for row in rows:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], len(cell))

    lines = [_line(headers, widths), _line(["-" * width for width in widths], widths)]
    lines.extend(_line(row, widths) for row in rows)
    return "\n".join(lines)


def _line(cells: Sequence[str], widths: Sequence[int]) -> str:
    padded = [cell.ljust(width) for cell, width in zip(cells, widths, strict=True)]
    return "  ".join(padded).rstrip()
