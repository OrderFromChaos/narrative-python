"""The command-line tool.

    python3 -m quota_reconcile <input-dir> [options]

Exit codes:

- 0: every team is within quota, and every report was read.
- 1: at least one team is over quota.
- 2: the run could not start, because of a bad argument, a missing input directory or a quota
  file that cannot be used.
- 3: every team is within quota, but at least one report was damaged.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence, TextIO

from .errors import QuotaReconcileError
from .model import Reconciliation
from .quotas import QUOTA_FILE_NAME
from .reconcile import UNATTRIBUTED_TEAM, reconcile_directory
from .report import render_outcomes, render_overage_detail, render_table, write_report
from .store import OverageStore, StoreResult

EXIT_OK = 0
EXIT_OVER_QUOTA = 1
EXIT_USAGE_ERROR = 2
EXIT_REPORT_FAILED = 3

DEFAULT_REPORT_NAME = "quota-report.json"
DEFAULT_DB_NAME = "quota-overages.sqlite3"


def main(argv: Sequence[str] | None = None) -> int:
    """Run the tool. Return the exit code rather than raising `SystemExit`."""
    parser = build_parser()
    options = parser.parse_args(argv)

    try:
        result = reconcile_directory(
            options.input_dir,
            quotas_path=options.quotas,
            unattributed_team=options.unattributed_team,
        )
    except (QuotaReconcileError, NotADirectoryError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_USAGE_ERROR

    stored = None
    if not options.no_store:
        with OverageStore(options.database) as store:
            stored = store.record(result)

    report_path = write_report(result, options.report)

    _print_summary(result, stored, report_path, options, stream=sys.stdout)

    if result.has_overage:
        return EXIT_OVER_QUOTA
    if result.failed_reports:
        return EXIT_REPORT_FAILED
    return EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    parser = argparse.ArgumentParser(
        prog="quota_reconcile",
        description="Reconcile the usage a fleet reports against the quota of each team.",
        epilog=(
            "Exit codes: 0 within quota, 1 a team is over quota, 2 the run could not start, "
            "3 within quota but a report was damaged."
        ),
    )
    parser.add_argument(
        "input_dir",
        type=Path,
        metavar="INPUT_DIR",
        help="directory that holds the *.usage and *.usage.json reports",
    )
    parser.add_argument(
        "--quotas",
        type=Path,
        default=None,
        metavar="PATH",
        help=f"quota file to use (default: {QUOTA_FILE_NAME} inside INPUT_DIR)",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path(DEFAULT_REPORT_NAME),
        metavar="PATH",
        help=f"where to write the JSON report (default: {DEFAULT_REPORT_NAME})",
    )
    parser.add_argument(
        "--database",
        type=Path,
        default=Path(DEFAULT_DB_NAME),
        metavar="PATH",
        help=f"SQLite file that keeps the overages (default: {DEFAULT_DB_NAME})",
    )
    parser.add_argument(
        "--unattributed-team",
        default=UNATTRIBUTED_TEAM,
        metavar="NAME",
        help=(
            "team that collects usage from the *.usage format, which names no team "
            f"(default: {UNATTRIBUTED_TEAM})"
        ),
    )
    parser.add_argument(
        "--no-store",
        action="store_true",
        help="skip the SQLite store, and only print the table and write the JSON report",
    )
    return parser


def _print_summary(
    result: Reconciliation,
    stored: StoreResult | None,
    report_path: Path,
    options: argparse.Namespace,
    stream: TextIO,
) -> None:
    """Print the table, the over-quota detail, the per-file outcomes and where the output went."""
    print(f"Usage under {result.input_dir}", file=stream)
    print(file=stream)
    print(render_table(result), file=stream)
    print(file=stream)
    print("* the team is not named in the quota file, so it holds the default quota", file=stream)
    print(
        f"Exempt paths held {result.exempt_entries} entries"
        f" and {result.exempt_bytes} bytes, counted toward no team.",
        file=stream,
    )
    print(file=stream)

    print("Over quota", file=stream)
    print(render_overage_detail(result), file=stream)
    print(file=stream)

    print("Reports", file=stream)
    print(render_outcomes(result.outcomes), file=stream)
    print(file=stream)

    if stored is not None:
        print(
            f"Store {options.database}: {len(stored.inserted)} new overages,"
            f" {len(stored.seen_again)} seen before.",
            file=stream,
        )
    print(f"Report written to {report_path}.", file=stream)
