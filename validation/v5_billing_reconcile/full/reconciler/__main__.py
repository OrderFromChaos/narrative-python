"""Match what a cloud bill charges for against what an asset scan found, and report every mismatch.

Usage:
    $ python3 -m reconciler fixture
    $ python3 -m reconciler fixture --database findings.db --report report.json
    $ python3 -m reconciler fixture --rules other/reconcile.json --verbose

Exit codes:
    0  every billing line above the grace matched a scanned resource
    1  at least one billed_not_found finding costs more than the grace
    2  the rules file or the input directory was unusable, so nothing was reconciled

Modules, in reading order:
    rules        the rules file, and the region aliases and grace it states
    inventory    every inventory file of the input directory, whichever format each one is
    billing_csv  one `*.billing.csv` from the finance export
    scan_json    one `*.scan.json` from the asset scanner
    join         billing lines matched to scanned resources, and what fails to match
    reconcile    one reconciliation, for a caller that is not this program
    store        the SQLite file that holds every finding
    report       the table for the terminal and the JSON report
    vocabulary   the types these modules pass between them
    logs         the logger they all write to
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

from reconciler import logs, reconcile, report, rules, store
from reconciler.logs import LOG
from reconciler.vocabulary import InventoryFileError, RulesFileError


RULES_FILENAME = 'reconcile.json'
DEFAULT_DATABASE_PATH = Path('findings.db')
DEFAULT_REPORT_PATH = Path('report.json')
EXIT_SUCCESS = 0
EXIT_FINDINGS = 1
EXIT_UNUSABLE = 2


def main() -> int:
    arguments = parseArguments()
    logs.configureLogging(verbose=arguments.verbose)

    # Either failure leaves the program not knowing what to reconcile, and both log their own path.
    try:
        reconcile_rules = rules.readRules(arguments.rules_path)
        reconciliation = reconcile.reconcileDirectory(arguments.input_directory, reconcile_rules)
    except (RulesFileError, InventoryFileError):
        return EXIT_UNUSABLE

    with store.FindingStore(arguments.database_path) as findings_store:
        added_rows = findings_store.insertFindings(reconciliation.findings)
    LOG.info('run.recorded', extra={'findings': len(reconciliation.findings), 'added': added_rows})

    print(report.formatSummaryTable(reconciliation, reconcile_rules))
    report.writeJsonReport(arguments.report_path, reconciliation, reconcile_rules)

    if any(rules.aboveGrace(finding, reconcile_rules) for finding in reconciliation.findings):
        return EXIT_FINDINGS
    return EXIT_SUCCESS


def parseArguments() -> Arguments:
    parser = argparse.ArgumentParser(description='Reconcile a cloud bill against an asset scan.')
    parser.add_argument('input_directory', type=Path, help='the directory holding the inventory files')
    parser.add_argument('--rules', type=Path, default=None, help=f'the rules file (default: INPUT/{RULES_FILENAME})')
    parser.add_argument('--database', type=Path, default=DEFAULT_DATABASE_PATH, help='the SQLite file for findings')
    parser.add_argument('--report', type=Path, default=DEFAULT_REPORT_PATH, help='the JSON report to write')
    parser.add_argument('--verbose', action='store_true', help='log every rejected line, not just the tally')
    parsed = parser.parse_args()

    input_directory: Path = parsed.input_directory
    stated_rules_path: Path | None = parsed.rules
    arguments = Arguments(
        input_directory=input_directory,
        rules_path=stated_rules_path or input_directory / RULES_FILENAME,
        database_path=parsed.database,
        report_path=parsed.report,
        verbose=parsed.verbose,
    )
    return arguments


### vocabulary #########################################################################


@dataclass(frozen=True)
class Arguments:
    input_directory: Path
    rules_path: Path
    database_path: Path
    report_path: Path
    verbose: bool


if __name__ == '__main__':
    sys.exit(main())
