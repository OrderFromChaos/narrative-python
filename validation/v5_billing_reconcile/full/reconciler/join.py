"""Match billing lines to scanned resources on resource_id, and report what fails to match.

Each resource_id matches at most one line on each side. A record whose sku is ignored by the rules
takes part in no match and appears in no finding, and a resource_id that both sides state twice
keeps the last record read.

A finding carries the fields the side that produced it had: a billed_not_found finding names a cost
and no team, and a found_not_billed finding names a team and no cost.
"""

from __future__ import annotations

from collections.abc import Iterable

from reconciler.logs import LOG
from reconciler.vocabulary import (
    Finding,
    FindingKind,
    InventoryFormat,
    InventoryRecord,
    ReconcileRules,
    ResourceId,
)


def findMismatches(records: Iterable[InventoryRecord], reconcile_rules: ReconcileRules) -> tuple[Finding, ...]:
    """Join the two sides of the inventory and report every record that fails to match.

    Returns:
        The billed_not_found findings sorted by (-monthly_cents, resource_id), then the
        found_not_billed findings sorted by (team, resource_id), then the region_mismatch findings
        sorted by resource_id.
    """
    joinable = [record for record in records if record.sku not in reconcile_rules.ignored_skus]
    billed = _indexByResourceId(record for record in joinable if record.origin is InventoryFormat.BILLING_CSV)
    scanned = _indexByResourceId(record for record in joinable if record.origin is InventoryFormat.SCAN_JSON)

    billed_not_found = []
    for resource_id in sorted(billed.keys() - scanned.keys()):
        billing_line = billed[resource_id]
        billed_not_found.append(
            Finding(
                kind=FindingKind.BILLED_NOT_FOUND,
                resource_id=resource_id,
                sku=billing_line.sku,
                monthly_cents=billing_line.monthly_cents,
                team=None,
                billed_region=billing_line.region,
                scanned_region=None,
            ),
        )

    found_not_billed = []
    for resource_id in sorted(scanned.keys() - billed.keys()):
        scanned_resource = scanned[resource_id]
        found_not_billed.append(
            Finding(
                kind=FindingKind.FOUND_NOT_BILLED,
                resource_id=resource_id,
                sku=scanned_resource.sku,
                monthly_cents=None,
                team=scanned_resource.team,
                billed_region=None,
                scanned_region=scanned_resource.region,
            ),
        )

    region_mismatch = []
    # A region the file does not name is already canonical and stands for itself.
    aliases = reconcile_rules.region_aliases
    for resource_id in sorted(billed.keys() & scanned.keys()):
        billing_line = billed[resource_id]
        scanned_resource = scanned[resource_id]
        billed_canonical = aliases.get(billing_line.region, billing_line.region)
        scanned_canonical = aliases.get(scanned_resource.region, scanned_resource.region)
        if billed_canonical == scanned_canonical:
            continue
        region_mismatch.append(
            Finding(
                kind=FindingKind.REGION_MISMATCH,
                resource_id=resource_id,
                sku=billing_line.sku,
                monthly_cents=billing_line.monthly_cents,
                team=scanned_resource.team,
                billed_region=billing_line.region,
                scanned_region=scanned_resource.region,
            ),
        )

    billed_not_found.sort(key=lambda finding: (-(finding.monthly_cents or 0), finding.resource_id))
    found_not_billed.sort(key=lambda finding: (finding.team or '', finding.resource_id))
    findings = tuple(billed_not_found + found_not_billed + region_mismatch)
    return findings


def _indexByResourceId(records: Iterable[InventoryRecord]) -> dict[ResourceId, InventoryRecord]:
    indexed: dict[ResourceId, InventoryRecord] = {}
    for record in records:
        if record.resource_id in indexed:
            LOG.debug('join.duplicate_resource', extra={'resource': record.resource_id, 'origin': record.origin.value})
        indexed[record.resource_id] = record
    return indexed
