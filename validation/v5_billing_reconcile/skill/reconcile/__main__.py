"""Match what a cloud bill charges for against what an asset scan found, and report every mismatch.

The input directory holds one file per inventory, in either format, beside the rules file. Every
file is read, one file that does not parse stops no other, and the findings go to a table, to a
JSON report and to a SQLite file that a re-run does not double-insert.

Usage:
    $ python3 -m reconcile fixture
    $ python3 -m reconcile fixture --database billing.db --report billing.json --rules fixture/reconcile.json
    $ python3 -m reconcile fixture --verbose

The two tables go to stdout, and the log goes to stderr:

    WARNING inventory.files_rejected files=4 funcName=readInventoryDirectory lineno=87 module=run rejected=1
    INFO store.recorded added=4 database=reconcile.db findings=4 funcName=recordFindings lineno=64 module=store

Exit codes:
    0  no billed_not_found finding costs more than grace_cents
    1  a billed_not_found finding costs more than grace_cents, or an input file was rejected
    2  the input directory or the rules file is unusable, so nothing was reconciled

Modules:
    inventory    the Resource record and the names of the join
    billing_csv  read one *.billing.csv finance export
    scan_json    read one *.scan.json asset scan
    rules        read reconcile.json
    join         match the two sides, and construct one Finding per mismatch
    store        record the findings in SQLite
    report       render the table and the JSON report
    run          reconcile one directory, and the entry point another program imports
"""

from __future__ import annotations

import logging
import sys
from argparse import ArgumentParser
from dataclasses import dataclass
from pathlib import Path

from reconcile.join import aboveGrace
from reconcile.report import formatReconciliation, writeJsonReport
from reconcile.rules import RulesError
from reconcile.run import FileOutcome, InputDirectoryError, Reconciliation, reconcileDirectory


DEFAULT_DATABASE_PATH = Path('reconcile.db')
DEFAULT_REPORT_PATH = Path('reconcile_report.json')
EXIT_SUCCESS = 0
EXIT_MISMATCH = 1
EXIT_UNUSABLE = 2
STANDARD_LOG_FIELDS = frozenset(logging.LogRecord('', 0, '', 0, '', None, None).__dict__) | {'message', 'asctime'}
CALL_SITE_LOG_FIELDS = ('module', 'lineno', 'funcName')

LOG = logging.getLogger('reconcile')


def main() -> int:
    arguments = parseArguments()
    configureLogging(verbose=arguments.verbose)

    try:
        reconciliation = reconcileDirectory(
            arguments.input_dir,
            arguments.database_path,
            rules_path=arguments.rules_path,
        )
    except (InputDirectoryError, RulesError) as exc:
        # Both mean the program does not know what it was asked to reconcile.
        LOG.error('reconcile.unusable_input', extra={'reason': str(exc)})
        return EXIT_UNUSABLE

    print(formatReconciliation(reconciliation))
    writeJsonReport(arguments.report_path, reconciliation)
    return computeExitCode(reconciliation)


def parseArguments() -> Arguments:
    parser = ArgumentParser(prog='python3 -m reconcile', description='Reconcile a cloud bill against an asset scan.')
    parser.add_argument('input_dir', type=Path, help='the directory holding the inventory files and the rules file')
    parser.add_argument('--database', type=Path, default=DEFAULT_DATABASE_PATH, help='the SQLite file of findings')
    parser.add_argument('--report', type=Path, default=DEFAULT_REPORT_PATH, help='the JSON report to write')
    parser.add_argument('--rules', type=Path, default=None, help='the rules file; INPUT_DIR/reconcile.json by default')
    parser.add_argument('--verbose', action='store_true', help='log every rejected file and every dropped duplicate')
    parsed = parser.parse_args()

    return Arguments(
        input_dir=parsed.input_dir,
        database_path=parsed.database,
        report_path=parsed.report,
        rules_path=parsed.rules,
        verbose=parsed.verbose,
    )


def configureLogging(*, verbose: bool) -> None:
    global LOG
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(FieldFormatter())
    LOG.addHandler(handler)
    LOG.setLevel(logging.DEBUG if verbose else logging.INFO)


def computeExitCode(reconciliation: Reconciliation) -> int:
    over_grace = [each for each in reconciliation.findings if aboveGrace(each, reconciliation.rules.grace_cents)]
    rejected = [each for each in reconciliation.files if each.outcome is FileOutcome.REJECTED]

    # The verdict is what an operator acts on, so it is the summary record as well as the code.
    LOG.info(
        'reconcile.finished',
        extra={
            'findings': len(reconciliation.findings),
            'above_grace': len(over_grace),
            'rejected': len(rejected),
            'rows_added': reconciliation.rows_added,
        },
    )

    if over_grace or rejected:
        return EXIT_MISMATCH
    return EXIT_SUCCESS


### vocabulary #########################################################################


@dataclass(frozen=True)
class Arguments:
    """What the command line asked for.

    `rules_path` is None when the command line named no rules file, and `reconcile.run` then
    resolves the default.
    """

    input_dir: Path
    database_path: Path
    report_path: Path
    rules_path: Path | None
    verbose: bool


class FieldFormatter(logging.Formatter):
    """Render a log record as its event name, then every field of `extra` and the call site, sorted.

    The standard formatter of logging discards `extra`, where every tally of this program sits.
    """

    def format(self, record: logging.LogRecord) -> str:
        extra = {key: value for key, value in record.__dict__.items() if key not in STANDARD_LOG_FIELDS}
        located = {key: getattr(record, key) for key in CALL_SITE_LOG_FIELDS}
        fields = ' '.join(f'{key}={value}' for key, value in sorted({**located, **extra}.items()))
        return f'{record.levelname} {record.getMessage()} {fields}'


if __name__ == '__main__':
    sys.exit(main())
