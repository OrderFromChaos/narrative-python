"""The join between the billing lines and the scanned resources.

The two sides join on the resource id. Each record on one side matches at most
one record on the other, and the records that fail to match are the report.

A resource whose sku is in `ignored_skus` leaves the join before it starts. It
matches nothing and appears in no finding, on either side.
"""

from __future__ import annotations

from dataclasses import dataclass

from .model import (
    BillingLine,
    Finding,
    FindingKind,
    JoinStats,
    ScannedResource,
)
from .rules import Rules


@dataclass(frozen=True)
class JoinResult:
    """The findings, and the counts that produced them."""

    findings: list[Finding]
    stats: JoinStats


def reconcile(
    billing: list[BillingLine],
    scanned: list[ScannedResource],
    rules: Rules,
) -> JoinResult:
    """Join the two sides and return every mismatch.

    `billed_not_found` findings come first, the largest cost first. A finding at
    or below `grace_cents` is returned like any other, with `above_grace` false,
    so the caller can record it without acting on it.
    """
    billed = {
        line.resource_id: line for line in billing if not rules.is_ignored(line.sku)
    }
    found = {
        resource.resource_id: resource
        for resource in scanned
        if not rules.is_ignored(resource.sku)
    }

    stats = JoinStats(
        billing_lines=len(billing),
        scanned_resources=len(scanned),
        ignored_billing=len(billing) - len(billed),
        ignored_scanned=len(scanned) - len(found),
        matched=len(billed.keys() & found.keys()),
    )

    findings = (
        _billed_not_found(billed, found, rules)
        + _found_not_billed(billed, found)
        + _region_mismatch(billed, found, rules)
    )
    return JoinResult(findings=findings, stats=stats)


def _billed_not_found(
    billed: dict[str, BillingLine],
    found: dict[str, ScannedResource],
    rules: Rules,
) -> list[Finding]:
    """A billing line with no scanned resource. The bill pays for nothing."""
    lines = [line for key, line in billed.items() if key not in found]
    lines.sort(key=lambda line: (-line.monthly_cents, line.resource_id))
    return [
        Finding(
            kind=FindingKind.BILLED_NOT_FOUND,
            resource_id=line.resource_id,
            sku=line.sku,
            monthly_cents=line.monthly_cents,
            billed_region=line.region,
            above_grace=line.monthly_cents > rules.grace_cents,
            sources=(line.source,),
        )
        for line in lines
    ]


def _found_not_billed(
    billed: dict[str, BillingLine],
    found: dict[str, ScannedResource],
) -> list[Finding]:
    """A scanned resource with no billing line. The usage is unbilled."""
    resources = [
        resource for key, resource in found.items() if key not in billed
    ]
    resources.sort(key=lambda resource: resource.resource_id)
    return [
        Finding(
            kind=FindingKind.FOUND_NOT_BILLED,
            resource_id=resource.resource_id,
            sku=resource.sku,
            team=resource.team,
            scanned_region=resource.region,
            sources=(resource.source,),
        )
        for resource in resources
    ]


def _region_mismatch(
    billed: dict[str, BillingLine],
    found: dict[str, ScannedResource],
    rules: Rules,
) -> list[Finding]:
    """Both sides matched, but they disagree about the region.

    The comparison uses the canonical region name, so a long name and its alias
    are the same region.
    """
    findings = []
    for key in sorted(billed.keys() & found.keys()):
        line = billed[key]
        resource = found[key]
        if rules.same_region(line.region, resource.region):
            continue
        findings.append(
            Finding(
                kind=FindingKind.REGION_MISMATCH,
                resource_id=key,
                sku=line.sku,
                monthly_cents=line.monthly_cents,
                team=resource.team,
                billed_region=line.region,
                scanned_region=resource.region,
                sources=(line.source, resource.source),
            )
        )
    return findings
