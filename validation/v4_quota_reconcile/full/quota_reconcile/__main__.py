"""Reconcile the storage that a fleet of hosts reports against the quota of each team.

The program reads every usage report in one directory, totals the bytes of each team, and compares
each total against the quota of that team. It prints a table, it writes a JSON report, and it records
each overage in a SQLite database. A malformed report does not stop the other reports.

The modules in reading order:
    reconcile      totals one directory of reports against one quota file
    reports        finds each report in the directory and picks the parser for it
    usage_text     reads the `.usage` format
    usage_json     reads the `.usage.json` format
    byte_size      converts a size with a unit suffix to a count of bytes
    quotas         reads the quota file
    overages       compares each total against a quota, and ranks what it finds
    store          records each overage in SQLite
    summary_table  formats the result for a terminal
    json_report    writes the result as JSON
    logs           writes the log records to standard error
    vocabulary     the records and the errors that the modules pass to each other

Usage:
    $ python3 -m quota_reconcile fixture
    $ python3 -m quota_reconcile fixture --database quota.db --report quota.json --verbose

Exit codes:
    0  every team is within its quota, and the program read every report in full
    1  a team is over its quota, or the program rejected a report or an entry
    2  the input directory, the quota file, the database or the report path is unusable
"""

from __future__ import annotations

import argparse
import sys
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path

from quota_reconcile import json_report, logs, overages, quotas, reconcile, store, summary_table
from quota_reconcile.logs import LOG
from quota_reconcile.vocabulary import QuotaFileError, ReadStatus, ReconcileResult, StoreError


DEFAULT_REPORT_PATH = Path('quota-report.json')
DEFAULT_DATABASE_PATH = Path('quota-overages.db')
EXIT_SUCCESS = 0
EXIT_FINDINGS = 1
EXIT_UNUSABLE = 2


def main() -> int:
    options = parseArguments()
    logs.configureLogging(verbose=options.verbose)
    if not options.usage_dir.is_dir():
        LOG.error('usage_dir.missing', extra={'usage_dir': str(options.usage_dir)})
        return EXIT_UNUSABLE

    try:
        result = reconcile.reconcileDirectory(options.usage_dir, options.quota_path)
    except QuotaFileError:
        LOG.error('reconcile.stopped', extra={'quota_file': str(options.quota_path)})
        return EXIT_UNUSABLE

    published = publishResult(result, options)
    if published != EXIT_SUCCESS:
        return published
    return resolveExitCode(result)


def parseArguments() -> CommandOptions:
    parser = argparse.ArgumentParser(
        prog='python3 -m quota_reconcile',
        description='Reconcile the storage that a fleet of hosts reports against the quota of each team.',
    )
    parser.add_argument('usage_dir', type=Path, help='the directory that holds the usage reports')
    parser.add_argument('--quotas', type=Path, help=f'the quota file, {quotas.QUOTA_FILENAME} in usage_dir by default')
    parser.add_argument('--database', type=Path, default=DEFAULT_DATABASE_PATH, help='the SQLite file for overages')
    parser.add_argument('--report', type=Path, default=DEFAULT_REPORT_PATH, help='the JSON report to write')
    parser.add_argument('--verbose', action='store_true', help='log every rejected entry')

    arguments = parser.parse_args()
    usage_dir: Path = arguments.usage_dir
    return CommandOptions(
        usage_dir=usage_dir,
        quota_path=arguments.quotas or usage_dir / quotas.QUOTA_FILENAME,
        database_path=arguments.database,
        report_path=arguments.report,
        verbose=arguments.verbose,
    )


def publishResult(result: ReconcileResult, options: CommandOptions) -> int:
    """Record the overages, print the table, and write the JSON report.

    Returns:
        EXIT_SUCCESS, or EXIT_UNUSABLE when the database or the report path refused the result.
    """
    try:
        with closing(store.OverageStore(options.database_path)) as overage_store:
            overage_store.recordOverages(overages.selectOverQuotaTeams(result.teams))
    except StoreError:
        LOG.error('reconcile.unrecorded', extra={'database': str(options.database_path)})
        return EXIT_UNUSABLE

    print(summary_table.formatSummaryTable(result))
    try:
        json_report.writeJsonReport(options.report_path, result)
    except OSError as exc:
        LOG.error('report.unwritable', extra={'report': str(options.report_path), 'reason': str(exc)})
        return EXIT_UNUSABLE
    return EXIT_SUCCESS


def resolveExitCode(result: ReconcileResult) -> int:
    rejected_files = sum(1 for outcome in result.outcomes if outcome.status is ReadStatus.REJECTED)
    rejected_entries = sum(outcome.rejected_lines for outcome in result.outcomes)
    if overages.selectOverQuotaTeams(result.teams) or rejected_files or rejected_entries:
        return EXIT_FINDINGS
    return EXIT_SUCCESS


### vocabulary #########################################################################


@dataclass(frozen=True)
class CommandOptions:
    usage_dir: Path
    quota_path: Path
    database_path: Path
    report_path: Path
    verbose: bool


if __name__ == '__main__':
    sys.exit(main())
