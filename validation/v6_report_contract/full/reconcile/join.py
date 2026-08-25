"""Match billing lines to scanned resources on resource_id, and construct the Reconciliation.

Each side drops its own records of an ignored sku before the match, so two sides that disagree on
the sku leave the surviving side unmatched and that is a finding. A sku disagreement between two
matched records is not.

An alias resolves one hop on each side and the two results are compared exactly: with `a` mapped to
`b` and `b` mapped to `c`, `a` and `c` differ. Case and whitespace are never folded.

Findings run billed_not_found first, by (-monthly_cents, resource_id), then found_not_billed by
resource_id, then region_mismatch by resource_id.
"""

from __future__ import annotations

from collections.abc import Mapping

from reconcile.vocabulary import (
    BillingLine,
    Cents,
    Finding,
    FindingKind,
    Inventory,
    ReconcileRules,
    Reconciliation,
    ReconciliationTotals,
    RegionName,
    ResourceId,
    ScannedResource,
)


def joinInventory(inventory: Inventory, rules: ReconcileRules) -> Reconciliation:
    """Apply the rules to what the readers accepted, and rank every mismatch they leave."""
    billed_by_id = {line.resource_id: line for line in inventory.billing_lines if line.sku not in rules.ignored_skus}
    scanned_by_id = {
        resource.resource_id: resource
        for resource in inventory.scanned_resources
        if resource.sku not in rules.ignored_skus
    }
    matched_ids = set(billed_by_id) & set(scanned_by_id)

    findings = (
        _rankBilledNotFound(billed_by_id, matched_ids, rules.grace_cents)
        + _listFoundNotBilled(scanned_by_id, matched_ids)
        + _listRegionMismatches(billed_by_id, scanned_by_id, matched_ids, rules.region_aliases)
    )

    totals = ReconciliationTotals(
        billing_lines=len(inventory.billing_lines),
        scanned_resources=len(inventory.scanned_resources),
        ignored_billing=sum(1 for line in inventory.billing_lines if line.sku in rules.ignored_skus),
        ignored_scanned=sum(1 for resource in inventory.scanned_resources if resource.sku in rules.ignored_skus),
        matched=len(matched_ids),
        findings=len(findings),
        above_grace=sum(1 for finding in findings if finding.above_grace),
        by_kind={kind: sum(1 for finding in findings if finding.kind is kind) for kind in FindingKind},
    )
    return Reconciliation(rules, totals, tuple(findings), inventory.file_outcomes)


def _rankBilledNotFound(
    billed_by_id: Mapping[ResourceId, BillingLine],
    matched_ids: set[ResourceId],
    grace_cents: Cents,
) -> list[Finding]:
    """List a finding per billing line with no scanned resource, dearest first.

    Returns:
        The findings sorted by (-monthly_cents, resource_id). One at or below the grace keeps its
        place in the ranking and reports above_grace false.
    """
    unmatched = [line for resource_id, line in billed_by_id.items() if resource_id not in matched_ids]
    unmatched.sort(key=lambda line: (-line.monthly_cents, line.resource_id))
    return [
        Finding(
            kind=FindingKind.BILLED_NOT_FOUND,
            resource_id=line.resource_id,
            sku=line.sku,
            monthly_cents=line.monthly_cents,
            billed_region=line.region,
            above_grace=line.monthly_cents > grace_cents,
            sources=(line.source,),
        )
        for line in unmatched
    ]


def _listFoundNotBilled(
    scanned_by_id: Mapping[ResourceId, ScannedResource],
    matched_ids: set[ResourceId],
) -> list[Finding]:
    """List a finding per scanned resource with no billing line, by resource_id ascending."""
    unmatched = [resource for resource_id, resource in scanned_by_id.items() if resource_id not in matched_ids]
    unmatched.sort(key=lambda resource: resource.resource_id)
    return [
        Finding(
            kind=FindingKind.FOUND_NOT_BILLED,
            resource_id=resource.resource_id,
            sku=resource.sku,
            team=resource.team,
            scanned_region=resource.region,
            above_grace=False,
            sources=(resource.source,),
        )
        for resource in unmatched
    ]


def _listRegionMismatches(
    billed_by_id: Mapping[ResourceId, BillingLine],
    scanned_by_id: Mapping[ResourceId, ScannedResource],
    matched_ids: set[ResourceId],
    region_aliases: Mapping[RegionName, RegionName],
) -> list[Finding]:
    """List a finding per matched pair whose regions differ once aliased, by resource_id ascending.

    Returns:
        The findings, each stating the raw regions rather than the aliased ones, and the sku of the
        billing side where the two sides disagree on it.
    """
    mismatched: list[Finding] = []
    for resource_id in sorted(matched_ids):
        line = billed_by_id[resource_id]
        resource = scanned_by_id[resource_id]
        if region_aliases.get(line.region, line.region) == region_aliases.get(resource.region, resource.region):
            continue
        mismatched.append(
            Finding(
                kind=FindingKind.REGION_MISMATCH,
                resource_id=resource_id,
                sku=line.sku,
                monthly_cents=line.monthly_cents,
                team=resource.team,
                billed_region=line.region,
                scanned_region=resource.region,
                above_grace=False,
                sources=tuple(sorted({line.source, resource.source})),
            ),
        )
    return mismatched
