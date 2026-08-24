"""Audit every manifest in a directory against a policy, and record what the audit finds.

Another program calls `runAudit` to get the whole result without the command line tool:

    from pathlib import Path
    from manifest_audit.audit import runAudit

    run = runAudit(Path('fixture'), Path('fixture/policy.json'), Path('audit.db'))

One unusable manifest does not stop the others. It becomes an outcome that carries the reason, and
the run continues with the next file.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from manifest_audit.manifest import (
    LOCK_SUFFIX,
    PACKAGES_SUFFIX,
    ManifestContents,
    ManifestError,
    ManifestFormat,
    rejectManifest,
)
from manifest_audit.packages_json import readPackagesJson
from manifest_audit.policy import Finding, Policy, findingsFor, loadPolicy
from manifest_audit.requirements_lock import readRequirementsLock
from manifest_audit.store import openStore, recordFindings


MANIFEST_SUFFIXES = (LOCK_SUFFIX, PACKAGES_SUFFIX)

LOG = logging.getLogger(__name__)


def runAudit(input_dir: Path, policy_path: Path, database: Path) -> AuditRun:
    """Audit every manifest in a directory and record the findings.

    Args:
        input_dir: The directory that holds the manifests.
        policy_path: The policy file. It is never read as a manifest, even when it sits in
            input_dir.
        database: The SQLite file that receives the findings.

    Returns:
        One outcome per manifest, in name order, and the number of findings written.

    Raises:
        PolicyError: the policy file is unreadable or malformed, so the run cannot start.
    """
    policy = loadPolicy(policy_path)
    outcomes = [auditManifest(path, policy) for path in discoverManifests(input_dir, policy_path)]

    unreadable = [outcome for outcome in outcomes if outcome.error is not None]
    if unreadable:
        LOG.warning('audit.manifests_unreadable', extra={'unreadable': len(unreadable), 'total': len(outcomes)})

    connection = openStore(database)
    recorded = recordFindings(connection, everyFinding(outcomes))
    connection.close()

    return AuditRun(tuple(outcomes), recorded)


def discoverManifests(input_dir: Path, policy_path: Path) -> list[Path]:
    """List every manifest in the directory, in name order, without the policy file."""
    found: list[Path] = []
    for suffix in MANIFEST_SUFFIXES:
        found.extend(input_dir.glob(f'*{suffix}'))

    excluded = policy_path.resolve()
    return sorted(path for path in found if path.resolve() != excluded)


def auditManifest(path: Path, policy: Policy) -> ManifestOutcome:
    """Read one manifest and check every package in it against the policy."""
    try:
        contents = readManifest(path)
    except ManifestError as exc:
        return ManifestOutcome(path, None, 0, 0, str(exc), ())

    findings: list[Finding] = []
    for package in contents.packages:
        findings.extend(findingsFor(package, path, policy))

    return ManifestOutcome(path, contents.format, len(contents.packages), contents.skipped, None, tuple(findings))


def readManifest(path: Path) -> ManifestContents:
    """Read a manifest with the reader that its suffix selects.

    The suffix is the only signal available before the file is open, and the set of suffixes is
    open, so this is a chain of tests rather than a match over the format.

    Raises:
        ManifestError: no reader handles the suffix.
    """
    if path.suffix == LOCK_SUFFIX:
        return readRequirementsLock(path)
    if path.suffix == PACKAGES_SUFFIX:
        return readPackagesJson(path)

    raise rejectManifest(path, f'no reader handles the suffix {path.suffix!r}')


def everyFinding(manifests: Iterable[ManifestOutcome]) -> list[Finding]:
    """Flatten the findings of every manifest into one list, in manifest order."""
    findings: list[Finding] = []
    for outcome in manifests:
        findings.extend(outcome.findings)

    return findings


### vocabulary #########################################################################


@dataclass(frozen=True)
class ManifestOutcome:
    path: Path
    format: ManifestFormat | None
    packages: int
    skipped: int
    error: str | None
    findings: tuple[Finding, ...]


@dataclass(frozen=True)
class AuditRun:
    manifests: tuple[ManifestOutcome, ...]
    recorded: int
