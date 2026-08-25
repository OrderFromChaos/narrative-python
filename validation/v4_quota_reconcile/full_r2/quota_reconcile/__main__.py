"""Reconcile what a fleet of hosts reports it is storing against the quota each team is allowed.

Modules in reading order: `scan` walks the input directory, `usage_text` and `usage_json` parse the
two report formats, `sizes` converts a unit suffix to bytes, `quotas` reads the quota file,
`reconcile` totals and ranks, `store` records the overages, `report` renders, `common` holds the
types they pass between them, and `logs` holds the logger.

Usage:
    $ python3 -m quota_reconcile fixture
    WARNING scan.rejected funcName=readReports lineno=40 module=scan rejected=1 total=4
    TEAM                  USED     QUOTA   OVERAGE
    search                2.3T      2.0T    307.2G
    archive              12.0G    100.0G         -

    $ python3 -m quota_reconcile fixture --quotas /etc/quotas.json --database overages.db --verbose

Exit codes:
    0  every report read, and every team within its quota
    1  at least one team is over quota
    2  the input directory, the quota file or the arguments were unusable
    3  every team within its quota, but at least one report was rejected
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from quota_reconcile import logs, reconcile, report, store
from quota_reconcile.common import QuotaConfigError, Reconciliation
from quota_reconcile.logs import LOG


DEFAULT_QUOTA_NAME = 'quotas.json'
DEFAULT_DATABASE_PATH = Path('quota_overages.db')
DEFAULT_REPORT_PATH = Path('quota_report.json')
EXIT_WITHIN_QUOTA = 0
EXIT_OVER_QUOTA = 1
EXIT_UNUSABLE_INPUT = 2
EXIT_REPORT_REJECTED = 3


def main() -> int:
    """Reconcile the reports of one input directory, then record, render and write the result."""
    arguments = parseArguments()
    logs.configureLogging(verbose=arguments.verbose)

    input_dir: Path = arguments.input_dir
    quota_json_path: Path = arguments.quotas or input_dir / DEFAULT_QUOTA_NAME
    if not input_dir.is_dir():
        return rejectInput('input.not_a_directory', input_dir)
    if not quota_json_path.is_file():
        return rejectInput('quotas.absent', quota_json_path)

    try:
        reconciliation = reconcile.reconcileUsage(input_dir, quota_json_path)
    except QuotaConfigError:
        return EXIT_UNUSABLE_INPUT

    results_store = store.Store(arguments.database)
    try:
        recorded = results_store.recordOverages(reconciliation.teams)
    finally:
        results_store.close()

    report.writeJsonReport(reconciliation, arguments.json_report)
    LOG.info('run.complete', extra={'recorded': recorded, 'report': str(arguments.json_report)})
    print(report.formatTable(reconciliation))
    return chooseExitCode(reconciliation)


def parseArguments() -> argparse.Namespace:
    DESCRIPTION = 'Reconcile what a fleet of hosts reports it is storing against the quota each team is allowed.'
    parser = argparse.ArgumentParser(prog='python3 -m quota_reconcile', description=DESCRIPTION)
    parser.add_argument('input_dir', type=Path, help='the directory holding the usage reports')
    parser.add_argument('--quotas', type=Path, help=f'the quota file, by default INPUT_DIR/{DEFAULT_QUOTA_NAME}')
    parser.add_argument('--database', type=Path, default=DEFAULT_DATABASE_PATH, help='where to record the overages')
    parser.add_argument('--json-report', type=Path, default=DEFAULT_REPORT_PATH, help='the JSON report to write')
    parser.add_argument('--verbose', action='store_true', help='log every rejected line and entry')
    return parser.parse_args()


def rejectInput(event: str, path: Path) -> int:
    LOG.error(event, extra={'path': str(path)})
    return EXIT_UNUSABLE_INPUT


def chooseExitCode(reconciliation: Reconciliation) -> int:
    if any(usage.overage for usage in reconciliation.teams):
        return EXIT_OVER_QUOTA
    if any(outcome.error is not None for outcome in reconciliation.outcomes):
        return EXIT_REPORT_REJECTED
    return EXIT_WITHIN_QUOTA


if __name__ == '__main__':
    sys.exit(main())
