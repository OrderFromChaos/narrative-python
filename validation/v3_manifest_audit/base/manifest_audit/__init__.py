"""Audit the dependency manifests of a repository against a policy.

The package reads two manifest formats, ``requirements.lock`` and
``packages.json``, and reports the packages that break a policy: a banned
name, a version below a minimum, or a source that is not allowed.

Command line::

    python3 -m manifest_audit fixture

As a library::

    from pathlib import Path
    from manifest_audit import audit_directory, load_policy

    policy = load_policy(Path("fixture/policy.json"))
    result = audit_directory(Path("fixture"), policy)
    for finding in result.findings:
        print(finding.package, finding.kind, finding.detail)

The audit writes nothing. To keep the findings, pass them to a
`FindingStore`; to make the JSON report, use `build_report`.
"""

from __future__ import annotations

from .audit import audit_directory, audit_manifest, audit_manifests
from .models import (
    AuditResult,
    Finding,
    FindingKind,
    ManifestError,
    ManifestOutcome,
    ManifestStatus,
    Package,
)
from .policy import Policy, PolicyError, load_policy
from .readers import discover_manifests, format_of, read_manifest
from .report import build_report, render_summary, write_report
from .store import FindingStore, StoreSummary
from .versions import InvalidVersion, compare_versions, is_below

__all__ = [
    "AuditResult",
    "Finding",
    "FindingKind",
    "FindingStore",
    "InvalidVersion",
    "ManifestError",
    "ManifestOutcome",
    "ManifestStatus",
    "Package",
    "Policy",
    "PolicyError",
    "StoreSummary",
    "audit_directory",
    "audit_manifest",
    "audit_manifests",
    "build_report",
    "compare_versions",
    "discover_manifests",
    "format_of",
    "is_below",
    "load_policy",
    "read_manifest",
    "render_summary",
    "write_report",
]

__version__ = "1.0.0"
