"""Record findings in a SQLite file, so a re-run over unchanged inputs adds no row.

    SELECT kind, resource_id, monthly_cents, team, first_seen_at FROM finding
    ('billed_not_found', 'nic-501', 300, None, '2026-08-25T01:53:13+00:00')
    ('found_not_billed', 'gpu-401', None, 'research', '2026-08-25T01:53:13+00:00')

Rows are keyed on the sha256 of the fields of the finding, so an unchanged finding inserts once
however often the program runs. `first_seen_at` is a UTC timestamp in seconds, written by the run
that first recorded the finding, and no later run replaces it.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from collections.abc import Iterable
from contextlib import closing
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path

from reconcile.join import Finding


LOG = logging.getLogger(__name__)


def recordFindings(database_path: Path, findings: Iterable[Finding]) -> int:
    """Insert every finding that the table does not already hold.

    Returns:
        The number of rows this call added, which is 0 on a re-run over unchanged inputs.
    """
    CREATE_FINDING = (
        'CREATE TABLE IF NOT EXISTS finding ('
        ' finding_key TEXT PRIMARY KEY,'
        ' kind TEXT NOT NULL,'
        ' resource_id TEXT NOT NULL,'
        ' sku TEXT NOT NULL,'
        ' monthly_cents INTEGER,'
        ' team TEXT,'
        ' billed_region TEXT,'
        ' scanned_region TEXT,'
        ' first_seen_at TEXT NOT NULL)'
    )
    INSERT_FINDING = (
        'INSERT OR IGNORE INTO finding'
        ' (finding_key, kind, resource_id, sku, monthly_cents, team, billed_region, scanned_region,'
        ' first_seen_at)'
        ' VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)'
    )

    first_seen_at = datetime.now(UTC).isoformat(timespec='seconds')
    rows = [buildFindingRow(finding, first_seen_at) for finding in findings]

    database_path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(database_path)) as connection:
        connection.execute(CREATE_FINDING)
        cursor = connection.executemany(INSERT_FINDING, rows)
        connection.commit()
        added = cursor.rowcount

    LOG.info('store.recorded', extra={'database': str(database_path), 'findings': len(rows), 'added': added})
    return added


def buildFindingRow(finding: Finding, first_seen_at: str) -> FindingRow:
    return (
        computeFindingKey(finding),
        finding.kind.value,
        finding.resource_id,
        finding.sku,
        finding.monthly_cents,
        finding.team,
        finding.billed_region,
        finding.scanned_region,
        first_seen_at,
    )


def computeFindingKey(finding: Finding) -> str:
    # SQLite holds two NULLs to be distinct, so a UNIQUE index over the nullable columns would let
    # a re-run insert a second row. The digest covers the nulls and the primary key rejects it.
    fields: list[object] = [
        finding.kind.value,
        finding.resource_id,
        finding.sku,
        finding.monthly_cents,
        finding.team,
        finding.billed_region,
        finding.scanned_region,
    ]
    return sha256(json.dumps(fields).encode('utf-8')).hexdigest()


### vocabulary #########################################################################

# One row of the finding table, in column order. The DB-API takes a sequence per row and no
# dataclass form, so the shape is named here rather than given a type of its own.
FindingRow = tuple[str, str, str, str, int | None, str | None, str | None, str | None, str]
