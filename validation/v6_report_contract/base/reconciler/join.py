"""The join: which findings exist, what each one carries, and their order.

Every record on one side matches at most one record on the other, and the
records that fail to match are the point of the report. A matched pair that
agrees produces nothing at all.
"""

from __future__ import annotations

from dataclasses import dataclass

from .inventory import Inventory
from .models import BillingLine, Finding, FindingKind, ScannedResource, Totals
from .rules import Rules


@dataclass(frozen=True, slots=True)
class JoinResult:
    """The findings, in report order, and the counts that describe them."""

    findings: list[Finding]
    totals: Totals


def join_inventory(inventory: Inventory, rules: Rules) -> JoinResult:
    """Match billing lines to scanned resources and collect every mismatch.

    The sku filter is applied per side before the join. When the two sides
    disagree on sku and only one of them is ignored, the ignored side drops and
    the other survives unmatched, which is itself a finding. A sku disagreement
    between two records that both survive is not a finding: the three kinds are
    the whole list.
    """
    billed = {
        line.resource_id: line for line in inventory.billing if not rules.is_ignored(line.sku)
    }
    scanned = {
        resource.resource_id: resource
        for resource in inventory.scanned
        if not rules.is_ignored(resource.sku)
    }

    matched_ids = billed.keys() & scanned.keys()
    findings = [
        *_billed_not_found(
            [line for resource_id, line in billed.items() if resource_id not in matched_ids],
            rules,
        ),
        *_found_not_billed(
            [
                resource
                for resource_id, resource in scanned.items()
                if resource_id not in matched_ids
            ]
        ),
        *_region_mismatches(
            [(billed[resource_id], scanned[resource_id]) for resource_id in matched_ids], rules
        ),
    ]

    totals = Totals(
        billing_lines=len(inventory.billing),
        scanned_resources=len(inventory.scanned),
        ignored_billing=len(inventory.billing) - len(billed),
        ignored_scanned=len(inventory.scanned) - len(scanned),
        matched=len(matched_ids),
        findings=len(findings),
        above_grace=sum(1 for finding in findings if finding.above_grace),
        by_kind={
            kind: sum(1 for finding in findings if finding.kind is kind) for kind in FindingKind
        },
    )
    return JoinResult(findings=findings, totals=totals)


def _billed_not_found(lines: list[BillingLine], rules: Rules) -> list[Finding]:
    """Build the findings for billing lines with no scanned resource.

    Ranked by cost, largest first, because these are what the bill is paying
    for and nothing is running. A line at or below the grace stays in the
    ranked list; it only loses its say over the exit code.
    """
    findings = [
        Finding(
            kind=FindingKind.BILLED_NOT_FOUND,
            resource_id=line.resource_id,
            sku=line.sku,
            monthly_cents=line.monthly_cents,
            team=None,
            billed_region=line.region,
            scanned_region=None,
            above_grace=line.monthly_cents > rules.grace_cents,
            sources=(line.source,),
        )
        for line in lines
    ]
    return sorted(findings, key=lambda finding: (-finding.monthly_cents, finding.resource_id))


def _found_not_billed(resources: list[ScannedResource]) -> list[Finding]:
    """Build the findings for scanned resources with no billing line.

    These have no cost to rank by, so they are ordered by ``resource_id``.
    """
    findings = [
        Finding(
            kind=FindingKind.FOUND_NOT_BILLED,
            resource_id=resource.resource_id,
            sku=resource.sku,
            monthly_cents=None,
            team=resource.team,
            billed_region=None,
            scanned_region=resource.region,
            above_grace=False,
            sources=(resource.source,),
        )
        for resource in resources
    ]
    return sorted(findings, key=lambda finding: finding.resource_id)


def _region_mismatches(
    pairs: list[tuple[BillingLine, ScannedResource]], rules: Rules
) -> list[Finding]:
    """Build the findings for matched pairs whose regions differ.

    The comparison runs on the aliased forms, so ``us-east-1`` and ``use1`` are
    the same region when the rules say so. The finding reports the raw strings
    the two files wrote, and states the billing side's sku when the two
    disagree.
    """
    findings = [
        Finding(
            kind=FindingKind.REGION_MISMATCH,
            resource_id=line.resource_id,
            sku=line.sku,
            monthly_cents=line.monthly_cents,
            team=resource.team,
            billed_region=line.region,
            scanned_region=resource.region,
            above_grace=False,
            sources=tuple(sorted({line.source, resource.source})),
        )
        for line, resource in pairs
        if rules.canonical_region(line.region) != rules.canonical_region(resource.region)
    ]
    return sorted(findings, key=lambda finding: finding.resource_id)
