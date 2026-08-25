"""One resource of a cloud account, however the program read it. The vocabulary of the join.

    Resource(resource_id='vm-101', sku='compute-std', region='us-east-1', monthly_cents=42000, team=None)
    Resource(resource_id='vm-101', sku='compute-std', region='use1', monthly_cents=None, team='platform')

A billing export carries a cost and no owning team, and an asset scan carries a team and no cost.
Both fields are therefore optional, and a check that reads one skips a record that does not carry
it. A record holds the region as its file spelled it, and `reconcile.rules` resolves the aliases.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import NewType


LOG = logging.getLogger(__name__)


def rejectInventory(inventory_path: Path, reason: str) -> MalformedInventoryError:
    # A single rejected file is not something an operator acts on, so the tally at the handle site
    # carries the level and this record carries the reason.
    LOG.debug('inventory.rejected', extra={'inventory': str(inventory_path), 'reason': reason})
    return MalformedInventoryError(f'{inventory_path.name}: {reason}')


### vocabulary #########################################################################

ResourceId = NewType('ResourceId', str)
Sku = NewType('Sku', str)
RegionName = NewType('RegionName', str)
TeamName = NewType('TeamName', str)
Cents = NewType('Cents', int)


class MalformedInventoryError(RuntimeError):
    """An inventory file does not hold what its format promises."""


@dataclass(frozen=True)
class Resource:
    resource_id: ResourceId
    sku: Sku
    region: RegionName
    monthly_cents: Cents | None
    team: TeamName | None
