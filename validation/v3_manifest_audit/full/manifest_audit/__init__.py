"""Audit the dependency manifests of a repository against a policy.

Another program calls `auditDirectory` and reads the report. The command-line tool is
`python3 -m manifest_audit`, and `__main__.py` lists the modules in reading order.
"""

from __future__ import annotations

from manifest_audit.audit import auditDirectory, everyFinding
from manifest_audit.errors import ManifestError, PolicyError, StoreError
from manifest_audit.vocabulary import (
    AuditReport,
    DeclaredPackage,
    Finding,
    ManifestFormat,
    ManifestOutcome,
    PackageName,
    Policy,
    SourceName,
    VersionText,
    Violation,
)


__all__ = [
    'AuditReport',
    'DeclaredPackage',
    'Finding',
    'ManifestError',
    'ManifestFormat',
    'ManifestOutcome',
    'PackageName',
    'Policy',
    'PolicyError',
    'SourceName',
    'StoreError',
    'VersionText',
    'Violation',
    'auditDirectory',
    'everyFinding',
]
