"""Audit the dependency manifests of a repository against a policy.

Every file in the input directory is read as a manifest. A `.lock` file holds one `name==version`
per line. A `.json` file holds a packages document. The policy names banned packages, minimum
versions and allowed sources. A manifest that does not parse is reported and does not stop the rest.

Every finding goes into SQLite, keyed on the manifest, the package, the version and the violation,
so a second audit of an unchanged manifest adds no rows.

Reading order:
    audit.py                the coordinator, and the entry point another program imports
    manifests.py            find the files, and dispatch on the format each one declares
    requirements_lock.py    the `name==version` text format
    packages_json.py        the packages document format
    policies.py             read the policy, and name the rules a package breaks
    versions.py             order two version strings
    store.py                the SQLite database of findings
    reports.py              the summary table and the JSON report
    errors.py               the failure types, and the one place each one is recorded
    logs.py                 the shared logger and its formatter
    vocabulary.py           every type that the modules above pass between them

Usage:
    $ python3 -m manifest_audit fixture
    $ python3 -m manifest_audit fixture --policy fixture/policy.json --database audit.db
    $ python3 -m manifest_audit fixture --report audit.json --verbose

Exit codes:
    0  no banned package was found
    1  at least one banned package was found
    2  the directory, the policy or the database was unusable
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from manifest_audit import audit, reports
from manifest_audit.errors import ManifestError, PolicyError, StoreError
from manifest_audit.logs import configureLogging
from manifest_audit.vocabulary import Violation


POLICY_NAME = 'policy.json'
DEFAULT_DATABASE = Path('manifest_audit.db')
DEFAULT_REPORT = Path('manifest_audit.json')
EXIT_SUCCESS = 0
EXIT_BANNED = 1
EXIT_UNUSABLE = 2


def main() -> int:
    """Audit one directory, print the table, write the report, and pick the exit code.

    Returns:
        1 when the audit found a banned package, 2 when it could not run, 0 otherwise.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('manifest_directory', type=Path, help='directory of manifests to audit')
    parser.add_argument('--policy', type=Path, help=f'policy file (default: <directory>/{POLICY_NAME})')
    parser.add_argument('--database', type=Path, default=DEFAULT_DATABASE, help='SQLite file for findings')
    parser.add_argument('--report', type=Path, default=DEFAULT_REPORT, help='JSON report to write')
    parser.add_argument('--verbose', action='store_true', help='log every rejected manifest')
    args = parser.parse_args()

    configureLogging(verbose=args.verbose)
    policy_path = args.policy if args.policy is not None else args.manifest_directory / POLICY_NAME

    # One arm for three types. Each was already logged in its own words where it was raised, and
    # here all three mean the same thing: the audit could not run, so nothing was checked.
    try:
        report = audit.auditDirectory(args.manifest_directory, policy_path, args.database)
    except (ManifestError, PolicyError, StoreError) as exc:
        print(exc, file=sys.stderr)
        return EXIT_UNUSABLE

    print(reports.summaryTable(report))
    reports.writeReport(report, args.report)
    print(f'report written to {args.report}')

    banned = [found for found in audit.everyFinding(report.outcomes) if found.violation is Violation.BANNED]
    if banned:
        return EXIT_BANNED

    return EXIT_SUCCESS


if __name__ == '__main__':
    sys.exit(main())
