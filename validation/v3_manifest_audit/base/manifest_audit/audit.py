"""The audit itself: read each manifest, judge it, collect the outcomes.

This is the importable entry point. It touches no database, writes no file and
prints nothing, so a caller can use it and then do what it likes with the
`models.AuditResult`.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from .models import (
    AuditResult,
    Finding,
    ManifestError,
    ManifestOutcome,
    ManifestStatus,
)
from .policy import Policy
from .readers import discover_manifests, format_of, read_manifest

__all__ = ["audit_directory", "audit_manifest", "audit_manifests"]


def audit_directory(
    root: Path, policy: Policy, *, exclude: Iterable[Path] = ()
) -> AuditResult:
    """Audit every manifest directly inside ``root``.

    Args:
        root: The directory that holds the manifests.
        policy: The rules to judge the packages against.
        exclude: Paths to leave out of the search, such as the policy file.

    Returns:
        The findings and the per-manifest outcomes. A manifest that cannot be
        read becomes a failed outcome; it does not stop the others.

    Raises:
        NotADirectoryError: ``root`` is not a directory.
    """
    manifests = discover_manifests(root, exclude=exclude)
    return audit_manifests(manifests, policy, root=root)


def audit_manifests(
    manifests: Iterable[Path], policy: Policy, *, root: Path | None = None
) -> AuditResult:
    """Audit a chosen list of manifests, in the order given."""
    outcomes: list[ManifestOutcome] = []
    findings: list[Finding] = []

    for path in manifests:
        outcome, manifest_findings = audit_manifest(path, policy)
        outcomes.append(outcome)
        findings.extend(manifest_findings)

    return AuditResult(
        root=str(root) if root is not None else "",
        policy_path=policy.path,
        outcomes=tuple(outcomes),
        findings=tuple(findings),
    )


def audit_manifest(path: Path, policy: Policy) -> tuple[ManifestOutcome, list[Finding]]:
    """Audit one manifest.

    Returns:
        The outcome for the manifest, and its findings. A manifest that cannot
        be read returns a failed outcome and no findings; the error text is on
        the outcome.
    """
    manifest_format = format_of(path) or "unknown"
    try:
        packages = read_manifest(path)
    except ManifestError as error:
        return (
            ManifestOutcome(
                path=str(path),
                format=manifest_format,
                status=ManifestStatus.FAILED,
                error=error.message,
            ),
            [],
        )

    findings = policy.check_all(packages)
    outcome = ManifestOutcome(
        path=str(path),
        format=manifest_format,
        status=ManifestStatus.OK,
        package_count=len(packages),
        finding_count=len(findings),
    )
    return outcome, findings
