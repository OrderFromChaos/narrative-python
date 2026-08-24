"""Turn a reconciliation into what a person reads and into what a machine reads.

`render_table` and `render_outcomes` build the console output. `build_report` builds the JSON
document, and `write_report` writes it to a file.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Sequence

from .model import Reconciliation, ReportOutcome, TeamUsage
from .sizes import format_size

REPORT_VERSION = 1
"""The version of the JSON report layout. It changes when a field changes meaning."""

_MAX_PATHS_IN_TABLE = 3
_TABLE_HEADERS = ("TEAM", "USAGE", "QUOTA", "USED", "OVER BY", "STATUS")


def build_report(result: Reconciliation) -> dict[str, Any]:
    """Return the JSON report as a dictionary."""
    return {
        "report_version": REPORT_VERSION,
        "generated_at": result.generated_at.isoformat(),
        "input_dir": str(result.input_dir),
        "quota_file": str(result.quota_source) if result.quota_source else None,
        "unattributed_team": result.unattributed_team,
        "summary": {
            "teams": len(result.teams),
            "teams_over_quota": len(result.overages),
            "counted_bytes": result.counted_bytes,
            "exempt_bytes": result.exempt_bytes,
            "exempt_entries": result.exempt_entries,
            "reports_read": len(result.outcomes),
            "reports_failed": len(result.failed_reports),
            "reports_partial": len(result.partial_reports),
        },
        "teams": [_team_document(team) for team in result.teams],
        "overages": [team.team for team in result.overages],
        "reports": [_outcome_document(outcome) for outcome in result.outcomes],
    }


def write_report(result: Reconciliation, path: Path) -> Path:
    """Write the JSON report to `path`, and return that path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    document = json.dumps(build_report(result), indent=2, sort_keys=False)
    path.write_text(document + "\n", encoding="utf-8")
    return path


def render_table(result: Reconciliation) -> str:
    """Return the summary table: over-quota teams first, worst overage at the top."""
    if not result.teams:
        return "No usage was counted."

    rows = [_table_row(team) for team in result.teams]
    widths = [
        max(len(header), *(len(row[column]) for row in rows))
        for column, header in enumerate(_TABLE_HEADERS)
    ]

    lines = [_join_row(_TABLE_HEADERS, widths), _join_row(["-" * width for width in widths], widths)]
    lines.extend(_join_row(row, widths) for row in rows)
    return "\n".join(lines)


def render_overage_detail(result: Reconciliation, max_paths: int = _MAX_PATHS_IN_TABLE) -> str:
    """Return the largest paths of each over-quota team, worst team first."""
    if not result.overages:
        return "Every team is within quota."

    lines: list[str] = []
    for team in result.overages:
        lines.append(
            f"{team.team}: {format_size(team.total_bytes)} of {format_size(team.quota_bytes)}"
            f", over by {format_size(team.over_bytes)}"
        )
        for rank, usage in enumerate(team.paths[:max_paths], start=1):
            hosts = f" on {usage.host_count} hosts" if usage.host_count > 1 else ""
            lines.append(f"  {rank}. {format_size(usage.size_bytes):>8}  {usage.path}{hosts}")
        remaining = len(team.paths) - max_paths
        if remaining > 0:
            lines.append(f"  ... and {remaining} more paths")
    return "\n".join(lines)


def render_outcomes(outcomes: Sequence[ReportOutcome]) -> str:
    """Return one line per report file, plus the reason for every line that was dropped."""
    if not outcomes:
        return "No usage reports were found."

    lines: list[str] = []
    for outcome in outcomes:
        lines.append(
            f"[{outcome.status:>7}] {outcome.source.name}"
            f" - {outcome.entry_count} entries, {format_size(outcome.byte_count)}"
        )
        for problem in outcome.problems:
            lines.append(f"          {problem}")
    return "\n".join(lines)


def _team_document(team: TeamUsage) -> dict[str, Any]:
    return {
        "team": team.team,
        "total_bytes": team.total_bytes,
        "quota_bytes": team.quota_bytes,
        "quota_is_default": team.quota_is_default,
        "over_bytes": team.over_bytes,
        "over_quota": team.is_over_quota,
        "usage_ratio": round(team.usage_ratio, 4) if team.quota_bytes else None,
        "paths": [
            {
                "rank": rank,
                "path": usage.path,
                "size_bytes": usage.size_bytes,
                "host_count": usage.host_count,
            }
            for rank, usage in enumerate(team.paths, start=1)
        ],
    }


def _outcome_document(outcome: ReportOutcome) -> dict[str, Any]:
    return {
        "source": str(outcome.source),
        "status": outcome.status,
        "entry_count": outcome.entry_count,
        "byte_count": outcome.byte_count,
        "problems": list(outcome.problems),
    }


def _table_row(team: TeamUsage) -> tuple[str, ...]:
    used = f"{team.usage_ratio * 100:.1f}%" if team.quota_bytes else "-"
    quota = format_size(team.quota_bytes) + ("*" if team.quota_is_default else "")
    return (
        team.team,
        format_size(team.total_bytes),
        quota,
        used,
        format_size(team.over_bytes) if team.is_over_quota else "-",
        "OVER" if team.is_over_quota else "ok",
    )


def _join_row(cells: Sequence[str], widths: Sequence[int]) -> str:
    """Left-align the team name and right-align the numbers."""
    parts = [str(cells[0]).ljust(widths[0])]
    parts.extend(str(cell).rjust(width) for cell, width in zip(cells[1:], widths[1:]))
    return "  ".join(parts).rstrip()
