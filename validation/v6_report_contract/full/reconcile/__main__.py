"""Match what a cloud bill charges for against what an asset scan found, and report every mismatch.

Usage:
    $ python3 -m reconcile fixture
    $ python3 -m reconcile fixture --report build/report.json --database build/reconcile.db
    $ python3 -m reconcile fixture --rules rules/production.json --verbose

Exit codes:
    0  every billing line above the grace has a scanned resource
    1  at least one does not
    2  the rules file or the input directory was unusable, so nothing was reconciled

The findings go to a JSON report, to SQLite, and to a table on stdout. Log records go to stderr.

Modules, in reading order:
    reconciler   reads the rules and the directory, then joins the two sides
    rules        the rules file, and the ReconcileRules it states
    inventory    the walk of the input directory, and the outcome of each file
    billing_csv  the finance export
    scan_json    the asset scanner document
    outcomes     the FileOutcome a reader reports for one file
    join         the match, the three kinds of finding, and the totals
    store        the SQLite table of findings
    report       the JSON report
    table        the table on stdout
    logs         the logger, and the formatter that prints its fields
    vocabulary   the records the modules pass between them
"""

from __future__ import annotations

import sys
from argparse import ArgumentParser
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from reconcile.logs import LOG, configureLogging
from reconcile.reconciler import reconcileDirectory
from reconcile.report import DEFAULT_REPORT_PATH, buildReport, writeReport
from reconcile.store import DEFAULT_DATABASE_PATH, FindingStore
from reconcile.table import formatSummary
from reconcile.vocabulary import InputDirectoryError, RulesError


EXIT_SUCCESS = 0
EXIT_ABOVE_GRACE = 1
EXIT_UNUSABLE = 2


def main() -> int:
    arguments = parseArguments(sys.argv[1:])
    configureLogging(verbose=arguments.verbose)
    generated_at = datetime.now(UTC).isoformat(timespec='seconds')

    # a half-read rules file or a missing directory leaves nothing to reconcile, so neither the
    # report nor the database is written
    try:
        reconciliation = reconcileDirectory(arguments.input_dir, rules_path=arguments.rules_path)
    except (RulesError, InputDirectoryError) as exc:
        LOG.error('run.abandoned', extra={'reason': str(exc)})
        return EXIT_UNUSABLE

    exit_code = EXIT_ABOVE_GRACE if reconciliation.totals.above_grace else EXIT_SUCCESS
    with FindingStore(arguments.database_path) as findings_store:
        findings_store.recordFindings(arguments.input_dir, reconciliation.findings)
    report = buildReport(generated_at, str(arguments.input_dir), reconciliation, exit_code)
    writeReport(arguments.report_path, report)
    print(formatSummary(reconciliation))
    return exit_code


def parseArguments(argv: Sequence[str]) -> Arguments:
    parser = ArgumentParser(prog='reconcile', description='Reconcile a cloud bill against an asset scan.')
    parser.add_argument('input_dir', type=Path, help='directory holding the *.billing.csv and *.scan.json files')
    parser.add_argument('--rules', type=Path, default=None, help='rules file (default: INPUT_DIR/reconcile.json)')
    parser.add_argument('--report', type=Path, default=DEFAULT_REPORT_PATH, help='where to write the JSON report')
    parser.add_argument('--database', type=Path, default=DEFAULT_DATABASE_PATH, help='SQLite file of findings')
    parser.add_argument('--verbose', action='store_true', help='log every rejected record, not the tally alone')
    parsed = parser.parse_args(argv)

    return Arguments(
        input_dir=parsed.input_dir,
        rules_path=parsed.rules,
        report_path=parsed.report,
        database_path=parsed.database,
        verbose=parsed.verbose,
    )


### vocabulary #########################################################################


@dataclass(frozen=True)
class Arguments:
    input_dir: Path
    rules_path: Path | None
    report_path: Path
    database_path: Path
    verbose: bool


if __name__ == '__main__':
    sys.exit(main())
