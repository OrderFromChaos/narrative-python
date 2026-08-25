"""The command-line tool: parse the arguments, run once, write the outputs.

Nothing here decides anything about the reconciliation. It chooses where the
outputs go and turns a failure into an exit code, and that is the whole job.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from .errors import ReconcileError
from .models import FileStatus
from .pipeline import ReconcileResult, reconcile
from .report import build_report, write_report
from .store import DEFAULT_DB_NAME, record_findings
from .summary import print_summary

DEFAULT_REPORT_NAME = 'report.json'
"""The report written when ``--report`` is not given."""

CONFIG_ERROR = 2
"""The exit code for an unusable rules file or input directory."""

_log = logging.getLogger('reconciler')


def main(argv: list[str] | None = None) -> int:
    """Run one reconciliation and return the process exit code.

    Returns:
        ``0`` when no ``billed_not_found`` finding is above the grace, ``1``
        when one is, and ``2`` when the rules file or the input directory was
        unusable. Exit code ``2`` writes no report and no database.
    """
    arguments = _parse_arguments(argv)
    logging.basicConfig(
        level=logging.INFO if arguments.verbose else logging.WARNING,
        format='%(levelname)s: %(message)s',
        stream=sys.stderr,
    )

    try:
        result = reconcile(arguments.input_dir, arguments.rules)
    except ReconcileError as error:
        _log.error('%s', error)
        return CONFIG_ERROR

    _log_files(result)
    write_report(arguments.report, build_report(result))
    _log.info('wrote the report to %s', arguments.report)

    stored = record_findings(arguments.database, result.findings, result.generated_at)
    _log.info(
        'stored %d new finding(s) in %s, %d already held',
        stored.inserted,
        arguments.database,
        stored.seen_again,
    )

    print_summary(result)
    return result.exit_code


def _parse_arguments(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog='reconciler',
        description=(
            'Match what a cloud bill charges for against what an asset scan found, '
            'and report every mismatch.'
        ),
    )
    parser.add_argument(
        'input_dir',
        help='directory holding the *.billing.csv and *.scan.json files to reconcile',
    )
    parser.add_argument(
        '--rules',
        type=Path,
        default=None,
        metavar='PATH',
        help='rules file to apply (default: reconcile.json inside the input directory)',
    )
    parser.add_argument(
        '--report',
        type=Path,
        default=Path(DEFAULT_REPORT_NAME),
        metavar='PATH',
        help=f'where to write the JSON report (default: {DEFAULT_REPORT_NAME})',
    )
    parser.add_argument(
        '--db',
        dest='database',
        type=Path,
        default=Path(DEFAULT_DB_NAME),
        metavar='PATH',
        help=f'SQLite database to record the findings in (default: {DEFAULT_DB_NAME})',
    )
    parser.add_argument(
        '-v',
        '--verbose',
        action='store_true',
        help='also log what was read and where the outputs went',
    )
    return parser.parse_args(argv)


def _log_files(result: ReconcileResult) -> None:
    """Warn about every file that was not read in full.

    A file that fails does not change the exit code, so without this the run
    can report a clean-looking zero over an input it never managed to read.
    """
    for outcome in result.files:
        if outcome.status is FileStatus.FAILED:
            _log.warning('%s failed and contributed nothing', outcome.path)
        elif outcome.status is FileStatus.PARTIAL:
            _log.warning('%s: %d record(s) rejected', outcome.path, outcome.rejected)
        elif outcome.status is FileStatus.SKIPPED:
            _log.info('%s is neither a billing nor a scan file, skipped', outcome.path)
