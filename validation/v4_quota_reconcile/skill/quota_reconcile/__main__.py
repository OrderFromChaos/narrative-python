"""Reconcile what a fleet of hosts reports it stores against the quota of each team.

The tool reads every usage report in the input directory, in either the `*.usage` text format or the
`*.usage.json` format. It totals the usage of each team, compares each total against the quota of
that team, records every overage in SQLite, writes a JSON report, and shows a table. One unreadable
report does not stop the reports after it, and the table names every report file and what came of
it.

Usage:
    $ python3 -m quota_reconcile fixture
    $ python3 -m quota_reconcile fixture --quotas quotas.json --report out.json --database out.db
    $ python3 -m quota_reconcile fixture --verbose

The quota file defaults to `quotas.json` inside the input directory.

Exit codes:
    0  every report was read, and every team is inside its quota
    1  a team is over quota, or a report was unreadable
    2  the input directory, the quota file, the database or the JSON report is unusable
"""

from __future__ import annotations

import argparse
import logging
import sqlite3
import sys
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path

from quota_reconcile.quotas import DEFAULT_QUOTA_FILE_NAME
from quota_reconcile.reconcile import reconcileDirectory
from quota_reconcile.store import openOverageStore, recordOverages
from quota_reconcile.summary import printSummaryTable, writeJsonReport
from quota_reconcile.vocabulary import InputDirectoryError, QuotaFileError, ReadOutcome, Reconciliation


DEFAULT_REPORT_PATH = Path('quota_report.json')
DEFAULT_DATABASE_PATH = Path('quota_overages.db')
PACKAGE_LOGGER = 'quota_reconcile'
EXIT_SUCCESS = 0
EXIT_FINDINGS = 1
EXIT_UNUSABLE = 2

LOG = logging.getLogger(PACKAGE_LOGGER)


def main() -> int:
    """Reconcile the reports, then record, write and show the result.

    The tool writes the database and the JSON report before it shows the table, so a run that cannot
    write one of them shows no table.
    """
    arguments = parseArguments()
    configureLogging(verbose=arguments.verbose)

    try:
        result = reconcileDirectory(arguments.input_dir, arguments.quota_json_path)
    except InputDirectoryError:
        LOG.exception('input.unusable')
        return EXIT_UNUSABLE
    except QuotaFileError:
        LOG.exception('quotas.unusable')
        return EXIT_UNUSABLE

    try:
        with closing(openOverageStore(arguments.database_path)) as overage_store:
            recordOverages(overage_store, result)
        writeJsonReport(result, arguments.report_json_path)
    except sqlite3.Error:
        LOG.exception('store.unusable')
        return EXIT_UNUSABLE
    except OSError:
        LOG.exception('report.unusable')
        return EXIT_UNUSABLE

    printSummaryTable(result, sys.stdout)
    return selectExitCode(result)


def parseArguments() -> Arguments:
    """Read the command line into the arguments of one run.

    Returns:
        The arguments, with the quota file put inside the input directory when the command line
        names no quota file. A bad command line stops the program inside argparse.
    """
    parser = argparse.ArgumentParser(
        prog='python3 -m quota_reconcile',
        description='Reconcile the storage usage of a fleet against the quota of each team.',
    )
    parser.add_argument('input_dir', type=Path, help='the directory that holds the usage reports')
    parser.add_argument(
        '--quotas',
        type=Path,
        default=None,
        help=f'the quota file, which defaults to {DEFAULT_QUOTA_FILE_NAME} inside the input directory',
    )
    parser.add_argument('--report', type=Path, default=DEFAULT_REPORT_PATH, help='where to write the JSON report')
    parser.add_argument('--database', type=Path, default=DEFAULT_DATABASE_PATH, help='where to record the overages')
    parser.add_argument('--verbose', action='store_true', help='log every rejected entry as well as the tallies')
    namespace = parser.parse_args()

    input_dir: Path = namespace.input_dir
    quotas: Path | None = namespace.quotas
    return Arguments(
        input_dir=input_dir,
        quota_json_path=input_dir / DEFAULT_QUOTA_FILE_NAME if quotas is None else quotas,
        report_json_path=namespace.report,
        database_path=namespace.database,
        verbose=namespace.verbose,
    )


def configureLogging(*, verbose: bool) -> None:
    global LOG
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(FieldFormatter())
    LOG.addHandler(handler)
    LOG.setLevel(logging.DEBUG if verbose else logging.INFO)


def selectExitCode(result: Reconciliation) -> int:
    unreadable = sum(1 for outcome in result.outcomes if outcome.outcome is ReadOutcome.UNREADABLE)
    if result.overages or unreadable:
        return EXIT_FINDINGS
    return EXIT_SUCCESS


### vocabulary #########################################################################


@dataclass(frozen=True)
class Arguments:
    """What the command line asked the tool to do."""

    input_dir: Path
    quota_json_path: Path
    report_json_path: Path
    database_path: Path
    verbose: bool


STANDARD_RECORD_FIELDS = frozenset(logging.LogRecord('', 0, '', 0, '', None, None).__dict__) | {'message', 'asctime'}
LOCATION_FIELDS = ('module', 'lineno', 'funcName')


class FieldFormatter(logging.Formatter):
    """Show the event name of a record, then every field of it, so that `extra` reaches the reader."""

    def format(self, record: logging.LogRecord) -> str:
        extra = {key: value for key, value in record.__dict__.items() if key not in STANDARD_RECORD_FIELDS}
        located = {key: getattr(record, key) for key in LOCATION_FIELDS}
        fields = ' '.join(f'{key}={value}' for key, value in sorted({**located, **extra}.items()))
        return f'{record.levelname} {record.getMessage()} {fields}'


if __name__ == '__main__':
    sys.exit(main())
