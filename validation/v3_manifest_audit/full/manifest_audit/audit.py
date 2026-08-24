"""Audit every manifest in a directory against a policy, and keep every finding.

This is the importable entry point. A program that does not want the command-line tool calls
`auditDirectory` and reads the report it returns:

    from pathlib import Path

    from manifest_audit import auditDirectory, everyFinding

    report = auditDirectory(Path('fixture'), Path('fixture/policy.json'), Path('audit.db'))
    stale = [found for found in everyFinding(report.outcomes) if found.violation is Violation.BELOW_MINIMUM]

One coordinator calls the stages in turn and holds what each one produced. The stages do not call
each other.

A malformed manifest does not stop the others: its outcome carries the reason and the run continues.
A malformed policy does stop the program, because a policy that only half parsed would audit
something the operator did not ask for.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from manifest_audit import manifests, policies
from manifest_audit.errors import ManifestError, rejectManifest
from manifest_audit.logs import LOG
from manifest_audit.store import FindingStore
from manifest_audit.vocabulary import AuditReport, DeclaredPackage, Finding, ManifestOutcome, Policy


def auditDirectory(manifest_directory: Path, policy_path: Path, database: Path) -> AuditReport:
    """Read every manifest in a directory, check it against the policy, and store the findings.

    Args:
        manifest_directory: Directory holding the manifests. Every file in it is read.
        policy_path: The `policy.json` that the packages must satisfy.
        database: SQLite file for the findings. It is created when it is absent.

    Returns:
        One outcome per manifest, and the number of findings this run added to the database.

    Raises:
        ManifestError: `manifest_directory` is not a directory.
        PolicyError: The policy file is missing or malformed.
        StoreError: The database refused the write.
    """
    if not manifest_directory.is_dir():
        raise rejectManifest(manifest_directory, 'not a directory')

    policy = policies.policyIn(policy_path)

    # The policy usually sits beside the manifests it governs, and it is a `.json` file, so without
    # this it would be read as a manifest and reported as one that declares no packages.
    policy_file = policy_path.resolve()
    to_audit = [path for path in manifests.pathsIn(manifest_directory) if path.resolve() != policy_file]

    outcomes = [_auditManifest(manifest, policy) for manifest in to_audit]
    findings = everyFinding(outcomes)

    # The tally, not the item. Each rejected manifest already logged itself at DEBUG, and the
    # number an operator acts on is how many of them failed.
    failed = [outcome for outcome in outcomes if outcome.error is not None]
    if failed:
        LOG.warning('audit.manifests_failed', extra={'failed': len(failed), 'total': len(outcomes)})

    # The database is a handle, so it opens for the one write that needs it and closes after.
    with FindingStore(database) as store:
        stored = store.storeFindings(findings)

    LOG.info('audit.finished', extra={'manifests': len(outcomes), 'findings': len(findings), 'stored': stored})

    return AuditReport(manifest_directory=manifest_directory, outcomes=tuple(outcomes), findings_stored=stored)


def everyFinding(outcomes: Iterable[ManifestOutcome]) -> tuple[Finding, ...]:
    # Every finding hangs off the manifest it came from, so a flat view has to be built. This is the
    # one place that builds it, and both the coordinator above and the report module call it.
    findings: list[Finding] = []
    for outcome in outcomes:
        findings.extend(outcome.findings)

    return tuple(findings)


def _auditManifest(manifest: Path, policy: Policy) -> ManifestOutcome:
    try:
        packages = manifests.packagesIn(manifest)
    except ManifestError as exc:
        return ManifestOutcome(manifest, None, 0, (), str(exc))

    findings: list[Finding] = []
    for package in packages:
        findings.extend(_findingsFor(package, policy, manifest))

    return ManifestOutcome(
        manifest=manifest,
        manifest_format=manifests.formatOf(manifest),
        packages_read=len(packages),
        findings=tuple(findings),
        error=None,
    )


def _findingsFor(package: DeclaredPackage, policy: Policy, manifest: Path) -> list[Finding]:
    findings = []
    for violation in policies.violationsFor(package, policy):
        finding = Finding(
            manifest=manifest,
            package=package.name,
            version=package.version,
            violation=violation,
            detail=policies.detailFor(violation, package, policy),
        )
        findings.append(finding)

    return findings
