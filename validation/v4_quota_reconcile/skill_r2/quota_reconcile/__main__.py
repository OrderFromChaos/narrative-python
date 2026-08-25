"""Reconcile what a fleet of hosts reports it is storing against the quota each team is allowed.

Usage:
    $ python3 -m quota_reconcile fixture
    $ python3 -m quota_reconcile fixture --quotas fixture/quotas.json --database overages.db --verbose

    WARNING reports.rejected funcName=readReportDirectory lineno=42 module=reports rejected=1 total=4
    TEAM                      USED     QUOTA   OVERAGE
    platform                550.0G    500.0G     50.0G
    search                    1.2T      2.0T         -

Exit codes:
    0  every team is within its quota, and every report was read
    1  a team is over quota, or a report was rejected
    2  the arguments, the input directory or the quota file were unusable

Modules:
    sizes        a size with a unit letter, to and from a count of bytes
    entries      the UsageEntry record that both report formats parse into
    usage_text   the `*.usage` reader
    usage_json   the `*.usage.json` reader
    quotas       the quota file, to a QuotaPolicy
    reports      one directory of reports, to a per-file ReportOutcome
    reconcile    outcomes and a policy, to a Reconciliation
    store        the overages of a Reconciliation, to SQLite
    render       a Reconciliation, to a table and to a JSON document
"""

from __future__ import annotations

import argparse
import logging
import sys
from dataclasses import dataclass
from pathlib import Path

from quota_reconcile.quotas import QuotaFileError
from quota_reconcile.reconcile import Reconciliation, reconcileDirectory
from quota_reconcile.render import buildJsonReport, formatReconciliationTable
from quota_reconcile.reports import rejectedReport
from quota_reconcile.store import recordOverages


DEFAULT_QUOTA_FILENAME = 'quotas.json'
DEFAULT_DATABASE_PATH = Path('quota_overages.db')
DEFAULT_JSON_REPORT_PATH = Path('quota_report.json')
EXIT_SUCCESS = 0
EXIT_FINDINGS = 1
EXIT_UNUSABLE = 2

LOG = logging.getLogger('quota_reconcile')


def main() -> int:
    arguments = parseArguments()
    configureLogging(arguments.verbose)

    reconciliation = runReconciliation(arguments)
    if reconciliation is None:
        return EXIT_UNUSABLE

    recordOverages(arguments.database_path, reconciliation.teams)
    arguments.json_report_path.write_text(buildJsonReport(reconciliation), encoding='utf-8')
    print(formatReconciliationTable(reconciliation))

    rejected = [outcome for outcome in reconciliation.outcomes if rejectedReport(outcome.status)]
    if reconciliation.selectTeamsOverQuota() or rejected:
        return EXIT_FINDINGS
    return EXIT_SUCCESS


def parseArguments() -> Arguments:
    parser = argparse.ArgumentParser(prog='python3 -m quota_reconcile')
    parser.add_argument('reports_dir', type=Path, help='the directory holding the usage reports')
    parser.add_argument(
        '--quotas',
        type=Path,
        default=None,
        help=f'the quota file (default: {DEFAULT_QUOTA_FILENAME} inside the input directory)',
    )
    parser.add_argument('--database', type=Path, default=DEFAULT_DATABASE_PATH, help='the SQLite file of overages')
    parser.add_argument('--json', type=Path, default=DEFAULT_JSON_REPORT_PATH, help='where to write the JSON report')
    parser.add_argument('--verbose', action='store_true', help='log every rejected line and entry')
    parsed = parser.parse_args()

    return Arguments(
        reports_dir=parsed.reports_dir,
        quota_json_path=parsed.quotas,
        database_path=parsed.database,
        json_report_path=parsed.json,
        verbose=parsed.verbose,
    )


def configureLogging(verbose: bool) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(FieldFormatter())
    logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO, handlers=[handler])


def runReconciliation(arguments: Arguments) -> Reconciliation | None:
    # None: an input was unusable, and this call has logged which one
    quota_json_path = arguments.quota_json_path or arguments.reports_dir / DEFAULT_QUOTA_FILENAME
    if not arguments.reports_dir.is_dir():
        LOG.error('reports.directory.absent', extra={'reports_dir': str(arguments.reports_dir)})
        return None
    if not quota_json_path.is_file():
        LOG.error('quota.file.absent', extra={'quota_file': str(quota_json_path)})
        return None

    try:
        return reconcileDirectory(arguments.reports_dir, quota_json_path)
    except QuotaFileError:
        LOG.error('run.abandoned', extra={'reason': 'the quota file states no usable policy'})
        return None
    except OSError as exc:
        LOG.error('run.abandoned', extra={'reason': str(exc)})
        return None


### vocabulary #########################################################################


@dataclass(frozen=True)
class Arguments:
    reports_dir: Path
    quota_json_path: Path | None
    database_path: Path
    json_report_path: Path
    verbose: bool


_STANDARD = frozenset(logging.LogRecord('', 0, '', 0, '', None, None).__dict__) | {'message', 'asctime'}
_LOCATION = ('module', 'lineno', 'funcName')


class FieldFormatter(logging.Formatter):
    """Render the `extra` fields of a record, which the standard formatter of logging discards."""

    def format(self, record: logging.LogRecord) -> str:
        extra = {k: v for k, v in record.__dict__.items() if k not in _STANDARD}
        located = {key: getattr(record, key) for key in _LOCATION}
        fields = ' '.join(f'{k}={v}' for k, v in sorted({**located, **extra}.items()))
        return f'{record.levelname} {record.getMessage()} {fields}'


if __name__ == '__main__':
    sys.exit(main())
