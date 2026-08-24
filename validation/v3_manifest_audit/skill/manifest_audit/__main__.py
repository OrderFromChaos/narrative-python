"""Audit the dependency manifests of a directory against a policy.

The tool reads every `*.lock` and `*.json` manifest in the input directory, checks each package
against the policy, records the findings in SQLite, prints a summary and writes a JSON report. One
unusable manifest does not stop the others: it is reported as an outcome at the end.

The policy file is not read as a manifest, even when it sits in the input directory.

Usage:
    $ python3 -m manifest_audit fixture
    $ python3 -m manifest_audit fixture --policy policy.json --database audit.db
    $ python3 -m manifest_audit fixture --report audit_report.json --verbose

Exit codes:
    0  every manifest was read, and no banned package was found
    1  a banned package was found, or a manifest could not be read
    2  the input directory, the policy file or the arguments were unusable
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from manifest_audit.audit import everyFinding, runAudit
from manifest_audit.policy import FindingKind, PolicyError
from manifest_audit.report import summaryTable, writeReport


POLICY_NAME = 'policy.json'
DEFAULT_DATABASE = Path('audit.db')
DEFAULT_REPORT = Path('audit_report.json')
EXIT_SUCCESS = 0
EXIT_FINDINGS = 1
EXIT_UNUSABLE = 2
STANDARD_FIELDS = frozenset(logging.LogRecord('', 0, '', 0, '', None, None).__dict__) | {'message', 'asctime'}
LOCATION_FIELDS = ('module', 'lineno', 'funcName')

### The package logger, not `__name__`: run as `-m`, this module is called `__main__`, and a handler
### on that name would never reach the records the other modules emit.
LOG = logging.getLogger('manifest_audit')


def main() -> int:
    """Parse the arguments, run the audit, print the summary and write the report.

    Returns:
        0 when the run was clean, 1 on a banned package or an unreadable manifest, and 2 when the
        input directory or the policy file could not be used.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('input_dir', type=Path, help='the directory that holds the manifests')
    parser.add_argument('--policy', type=Path, help=f'the policy file (default: <input_dir>/{POLICY_NAME})')
    parser.add_argument('--database', type=Path, default=DEFAULT_DATABASE, help='the SQLite file for the findings')
    parser.add_argument('--report', type=Path, default=DEFAULT_REPORT, help='the JSON report to write')
    parser.add_argument('--verbose', action='store_true', help='report every skipped line and entry')
    args = parser.parse_args()

    configureLogging(verbose=args.verbose)
    if not args.input_dir.is_dir():
        LOG.error('audit.input_dir_missing', extra={'input_dir': str(args.input_dir)})
        return EXIT_UNUSABLE

    policy_path = args.policy if args.policy is not None else args.input_dir / POLICY_NAME
    try:
        run = runAudit(args.input_dir, policy_path, args.database)
    except PolicyError:
        # `rejectPolicy` already logged the reason at the raise site.
        return EXIT_UNUSABLE

    print(summaryTable(run))
    writeReport(args.report, run)

    banned = [finding for finding in everyFinding(run.manifests) if finding.kind is FindingKind.BANNED]
    unreadable = [outcome for outcome in run.manifests if outcome.error is not None]
    if banned or unreadable:
        LOG.warning('audit.failed', extra={'banned': len(banned), 'unreadable': len(unreadable)})
        return EXIT_FINDINGS

    return EXIT_SUCCESS


def configureLogging(*, verbose: bool) -> None:
    """Send every record to stderr with its structured fields spelled out."""
    global LOG

    handler = logging.StreamHandler()
    handler.setFormatter(FieldFormatter())
    LOG.addHandler(handler)
    LOG.setLevel(logging.DEBUG if verbose else logging.INFO)


### vocabulary #########################################################################


class FieldFormatter(logging.Formatter):
    """Render the event name and every `extra` field. The standard formatter discards them."""

    def format(self, record: logging.LogRecord) -> str:
        extra = {key: value for key, value in record.__dict__.items() if key not in STANDARD_FIELDS}
        located = {key: getattr(record, key) for key in LOCATION_FIELDS}
        fields = ' '.join(f'{key}={value}' for key, value in sorted({**located, **extra}.items()))
        return f'{record.levelname} {record.getMessage()} {fields}'


if __name__ == '__main__':
    sys.exit(main())
