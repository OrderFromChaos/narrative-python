"""The command-line tool.

    python3 -m reconcile <input-dir> [--rules PATH] [--db PATH] [--report PATH]

Exit codes:

    0  no billed_not_found finding above the grace amount
    1  at least one billed_not_found finding above the grace amount
    2  the run could not start: no input directory, or a broken rules file

A malformed input file does not change the exit code. It is reported in the
file table, and the findings that its absence causes are reported with the
rest.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import report as report_module
from .model import Reconciliation
from .rules import RULES_FILENAME, RulesError
from .service import reconcile_directory
from .store import StoreStats, record_findings

DEFAULT_DB = Path("reconcile.db")
DEFAULT_REPORT = Path("reconcile-report.json")

EXIT_CLEAN = 0
EXIT_FINDINGS = 1
EXIT_ERROR = 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python3 -m reconcile",
        description=(
            "Match a cloud bill against an asset scan and report every mismatch."
        ),
    )
    parser.add_argument(
        "input_dir",
        type=Path,
        help="directory that holds the *.billing.csv and *.scan.json files",
    )
    parser.add_argument(
        "--rules",
        type=Path,
        default=None,
        metavar="PATH",
        help=f"rules file (default: {RULES_FILENAME} in the input directory)",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB,
        metavar="PATH",
        help=f"SQLite store for the findings (default: {DEFAULT_DB})",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=DEFAULT_REPORT,
        metavar="PATH",
        help=f"JSON report to write (default: {DEFAULT_REPORT})",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        result = reconcile_directory(args.input_dir, args.rules)
    except NotADirectoryError as error:
        print(f"error: {error}", file=sys.stderr)
        return EXIT_ERROR
    except RulesError as error:
        print(f"error: {error}", file=sys.stderr)
        return EXIT_ERROR

    store = record_findings(args.db, result.findings, result.generated_at)
    report_module.write_report(args.report, result, store)

    print(report_module.render(result))
    print()
    print(_outputs(args.db, args.report, store))
    sys.stdout.flush()

    _warn(result)
    return EXIT_FINDINGS if result.exit_code else EXIT_CLEAN


def _outputs(db_path: Path, report_path: Path, store: StoreStats) -> str:
    return "\n".join(
        [
            "OUTPUTS",
            f"  store   {db_path} "
            f"({store.inserted} new, {store.updated} seen again, "
            f"{store.total_rows} rows)",
            f"  report  {report_path}",
        ]
    )


def _warn(result: Reconciliation) -> None:
    for outcome in result.failed_files:
        print(
            f"warning: {outcome.path} was not read: {'; '.join(outcome.problems)}",
            file=sys.stderr,
        )
    if result.rules.source is None:
        print(
            f"warning: no {RULES_FILENAME} in {result.input_dir}, "
            "the run used the default rules",
            file=sys.stderr,
        )
    for finding in result.actionable:
        print(
            f"warning: {finding.resource_id} is billed but was not found",
            file=sys.stderr,
        )
