"""Audit the dependency manifests of a repository against a policy.

The package reads two manifest formats, checks each package against a policy of banned names,
minimum versions and allowed sources, records the findings in SQLite and reports them.

Another program calls the audit directly:

    >>> from pathlib import Path
    >>> from manifest_audit import runAudit
    >>> run = runAudit(Path('fixture'), Path('fixture/policy.json'), Path('audit.db'))

Run the command line tool with `python3 -m manifest_audit <input-dir>`. See `__main__.py` for its
arguments and its exit codes.
"""

from __future__ import annotations

from manifest_audit.audit import AuditRun, ManifestOutcome, everyFinding, runAudit
from manifest_audit.manifest import ManifestError, ManifestFormat, Package
from manifest_audit.policy import Finding, FindingKind, Policy, PolicyError, loadPolicy
from manifest_audit.report import summaryTable, writeReport


__all__ = [
    'AuditRun',
    'Finding',
    'FindingKind',
    'ManifestError',
    'ManifestFormat',
    'ManifestOutcome',
    'Package',
    'Policy',
    'PolicyError',
    'everyFinding',
    'loadPolicy',
    'runAudit',
    'summaryTable',
    'writeReport',
]
