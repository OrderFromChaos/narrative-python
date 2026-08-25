"""Join billed resources to scanned resources on resource_id, and construct one Finding per mismatch.

    Finding(kind=<FindingKind.REGION_MISMATCH: 'region_mismatch'>, resource_id='db-201',
            sku='postgres-ha', monthly_cents=89000, team='payments', billed_region='eu-west-1',
            scanned_region='us-east-1')

Each side matches at most one record on the other. A resource_id that either side bills or scans
under an ignored sku takes part in no join and appears in no finding. A repeated resource_id on one
side keeps the first record.

Findings sort by (kind rank, -monthly_cents, resource_id), so the most expensive thing you pay for
and cannot find comes first. A finding that carries no cost sorts as 0.
"""

from __future__ import annotations

import logging
from collections.abc import Container, Iterable, Sequence
from dataclasses import dataclass
from enum import Enum
from itertools import chain

from reconcile.inventory import Cents, RegionName, Resource, ResourceId, Sku, TeamName
from reconcile.rules import ReconcileRules


LOG = logging.getLogger(__name__)


def joinResources(
    billed: Sequence[Resource],
    scanned: Sequence[Resource],
    rules: ReconcileRules,
) -> tuple[Finding, ...]:
    """Construct one Finding for each resource that the two sides do not agree on.

    A matched pair takes the sku and the cost of the billing line, which is what the account pays.
    """
    ignored = {resource.resource_id for resource in chain(billed, scanned) if resource.sku in rules.ignored_skus}
    billed_by_id = indexResources(billed, ignored, 'billed')
    scanned_by_id = indexResources(scanned, ignored, 'scanned')

    findings: list[Finding] = []
    for resource_id, billing in billed_by_id.items():
        scan = scanned_by_id.get(resource_id)
        if scan is None:
            findings.append(
                Finding(
                    kind=FindingKind.BILLED_NOT_FOUND,
                    resource_id=resource_id,
                    sku=billing.sku,
                    monthly_cents=billing.monthly_cents,
                    team=None,
                    billed_region=billing.region,
                    scanned_region=None,
                ),
            )
        elif rules.resolveRegion(billing.region) != rules.resolveRegion(scan.region):
            findings.append(
                Finding(
                    kind=FindingKind.REGION_MISMATCH,
                    resource_id=resource_id,
                    sku=billing.sku,
                    monthly_cents=billing.monthly_cents,
                    team=scan.team,
                    billed_region=billing.region,
                    scanned_region=scan.region,
                ),
            )

    for resource_id, scan in scanned_by_id.items():
        if resource_id not in billed_by_id:
            findings.append(
                Finding(
                    kind=FindingKind.FOUND_NOT_BILLED,
                    resource_id=resource_id,
                    sku=scan.sku,
                    monthly_cents=None,
                    team=scan.team,
                    billed_region=None,
                    scanned_region=scan.region,
                ),
            )

    return tuple(sorted(findings, key=rankFinding))


def indexResources(
    resources: Iterable[Resource],
    ignored: Container[ResourceId],
    side: str,
) -> dict[ResourceId, Resource]:
    indexed: dict[ResourceId, Resource] = {}
    dropped = 0
    for resource in resources:
        if resource.resource_id in ignored:
            continue
        if resource.resource_id in indexed:
            dropped += 1
            LOG.debug('join.duplicate', extra={'side': side, 'resource': resource.resource_id})
            continue
        indexed[resource.resource_id] = resource

    if dropped:
        LOG.warning('join.duplicates_dropped', extra={'side': side, 'dropped': dropped, 'kept': len(indexed)})

    return indexed


def rankFinding(finding: Finding) -> tuple[int, int, str]:
    return (rankFindingKind(finding.kind), -(finding.monthly_cents or 0), finding.resource_id)


def rankFindingKind(kind: FindingKind) -> int:
    match kind:
        case FindingKind.BILLED_NOT_FOUND:
            return 0
        case FindingKind.FOUND_NOT_BILLED:
            return 1
        case FindingKind.REGION_MISMATCH:
            return 2


def aboveGrace(finding: Finding, grace_cents: Cents) -> bool:
    if finding.kind is not FindingKind.BILLED_NOT_FOUND or finding.monthly_cents is None:
        return False
    return finding.monthly_cents > grace_cents


### vocabulary #########################################################################


class FindingKind(Enum):
    BILLED_NOT_FOUND = 'billed_not_found'
    FOUND_NOT_BILLED = 'found_not_billed'
    REGION_MISMATCH = 'region_mismatch'


@dataclass(frozen=True)
class Finding:
    """One resource that the billing export and the asset scan do not agree on.

    A field holds None where the side that carries it took no part in the finding: a resource that
    no scan found has no team, and a resource that no line bills for has no cost.
    """

    kind: FindingKind
    resource_id: ResourceId
    sku: Sku
    monthly_cents: Cents | None
    team: TeamName | None
    billed_region: RegionName | None
    scanned_region: RegionName | None
