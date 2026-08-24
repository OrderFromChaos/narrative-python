"""The command-line tool.

This module owns argument parsing, the order of the steps, and the exit code.
Everything it does is available to a caller through `audit.audit_directory`,
`store.FindingStore` and `report`, so a program can skip this module.

Exit codes:

* ``0`` — the audit ran, and no banned package was found.
* ``1`` — the audit ran, and at least one banned package was found.
* ``2`` — the audit could not run: a missing directory, or an unreadable
  policy file.

A manifest that fails to parse does not change the exit code by itself. It
appears in the outcome table with a ``failed`` status, and in the JSON report.
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from collections.abc import Sequence
from pathlib import Path

from .audit import audit_directory
from .models import AuditResult
from .policy import PolicyError, load_policy
from .report import build_report, render_summary, write_report
from .store import FindingStore, StoreSummary

__all__ = ["EXIT_BANNED", "EXIT_OK", "EXIT_USAGE", "build_parser", "main"]

EXIT_OK = 0
EXIT_BANNED = 1
EXIT_USAGE = 2

DEFAULT_POLICY_NAME = "policy.json"
DEFAULT_DATABASE = Path("manifest-audit.sqlite3")
DEFAULT_REPORT = Path("manifest-audit-report.json")


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    parser = argparse.ArgumentParser(
        prog="manifest_audit",
        description=(
            "Audit the dependency manifests in a directory against a policy. "
            "Reads requirements.lock and packages.json files."
        ),
    )
    parser.add_argument(
        "directory",
        type=Path,
        help="the directory that holds the manifests",
    )
    parser.add_argument(
        "-p",
        "--policy",
        type=Path,
        default=None,
        help=f"the policy file (default: {DEFAULT_POLICY_NAME} in the directory)",
    )
    parser.add_argument(
        "-d",
        "--database",
        type=Path,
        default=DEFAULT_DATABASE,
        help=f"the SQLite file for findings (default: {DEFAULT_DATABASE})",
    )
    parser.add_argument(
        "-r",
        "--report",
        type=Path,
        default=DEFAULT_REPORT,
        help=f"the JSON report file (default: {DEFAULT_REPORT})",
    )
    parser.add_argument(
        "--no-store",
        action="store_true",
        help="do not write to the database",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="print only the closing summary line",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command-line tool, and return the exit code."""
    args = build_parser().parse_args(argv)
    directory: Path = args.directory
    policy_path: Path = args.policy or directory / DEFAULT_POLICY_NAME
    report_path: Path = args.report

    if not directory.is_dir():
        return _fail(f"{directory}: no such directory")

    try:
        policy = load_policy(policy_path)
    except PolicyError as error:
        return _fail(str(error))

    try:
        result = audit_directory(
            directory, policy, exclude=[policy_path, report_path, args.database]
        )
    except NotADirectoryError:
        return _fail(f"{directory}: no such directory")
    except OSError as error:
        return _fail(f"{directory}: cannot read directory: {error.strerror}")

    store_summary: StoreSummary | None = None
    if not args.no_store:
        try:
            store_summary = _store(result, args.database)
        except sqlite3.Error as error:
            return _fail(f"{args.database}: cannot write findings: {error}")

    report = build_report(result, policy=policy, store=store_summary)
    try:
        write_report(report, report_path)
    except OSError as error:
        return _fail(f"{report_path}: cannot write report: {error.strerror}")

    _print_summary(result, store_summary, quiet=args.quiet)
    print(f"Report written to {report_path}.")
    return EXIT_BANNED if result.has_banned else EXIT_OK


def _store(result: AuditResult, database: Path) -> StoreSummary:
    read_manifests = [outcome.path for outcome in result.outcomes if outcome.ok]
    with FindingStore(database) as store:
        return store.record(result.findings, read_manifests=read_manifests)


def _print_summary(
    result: AuditResult, store_summary: StoreSummary | None, *, quiet: bool
) -> None:
    text = render_summary(result, store=store_summary)
    if quiet:
        print(text.rsplit("\n\n", 1)[-1])
    else:
        print(text)


def _fail(message: str) -> int:
    print(f"manifest_audit: {message}", file=sys.stderr)
    return EXIT_USAGE
