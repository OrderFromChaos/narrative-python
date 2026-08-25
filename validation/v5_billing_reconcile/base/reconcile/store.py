"""The SQLite store for findings.

A finding is identified by its kind and its resource id. That pair is the
primary key, so a re-run over unchanged inputs updates the row it wrote before
instead of inserting a second one.

`first_seen_at` keeps the time of the first run that found the mismatch.
`last_seen_at` moves to the time of the latest run that found it again. A row
whose `last_seen_at` is older than the latest run is a mismatch that the inputs
no longer show.
"""

from __future__ import annotations

import sqlite3
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path

from .model import Finding

SCHEMA = """
CREATE TABLE IF NOT EXISTS findings (
    kind           TEXT    NOT NULL,
    resource_id    TEXT    NOT NULL,
    sku            TEXT    NOT NULL,
    team           TEXT,
    monthly_cents  INTEGER,
    billed_region  TEXT,
    scanned_region TEXT,
    above_grace    INTEGER NOT NULL,
    sources        TEXT    NOT NULL,
    first_seen_at  TEXT    NOT NULL,
    last_seen_at   TEXT    NOT NULL,
    PRIMARY KEY (kind, resource_id)
);
"""

UPSERT = """
INSERT INTO findings (
    kind, resource_id, sku, team, monthly_cents, billed_region,
    scanned_region, above_grace, sources, first_seen_at, last_seen_at
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT (kind, resource_id) DO UPDATE SET
    sku            = excluded.sku,
    team           = excluded.team,
    monthly_cents  = excluded.monthly_cents,
    billed_region  = excluded.billed_region,
    scanned_region = excluded.scanned_region,
    above_grace    = excluded.above_grace,
    sources        = excluded.sources,
    last_seen_at   = excluded.last_seen_at;
"""


@dataclass(frozen=True)
class StoreStats:
    """What one write did to the store."""

    inserted: int = 0
    updated: int = 0
    total_rows: int = 0

    def as_dict(self) -> dict[str, int]:
        return {
            "inserted": self.inserted,
            "updated": self.updated,
            "total_rows": self.total_rows,
        }


def record_findings(
    db_path: Path, findings: list[Finding], seen_at: str
) -> StoreStats:
    """Write every finding to the store and report what changed.

    Creates the database and the table if they are absent. The write is one
    transaction: either every finding lands or none does.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(db_path)) as connection:
        connection.execute("PRAGMA foreign_keys = ON;")
        connection.executescript(SCHEMA)

        known = {
            (kind, resource_id)
            for kind, resource_id in connection.execute(
                "SELECT kind, resource_id FROM findings;"
            )
        }
        inserted = sum(
            1
            for finding in findings
            if (finding.kind.value, finding.resource_id) not in known
        )

        with connection:
            connection.executemany(
                UPSERT,
                [_row(finding, seen_at) for finding in findings],
            )
        total = connection.execute("SELECT COUNT(*) FROM findings;").fetchone()[0]

    return StoreStats(
        inserted=inserted,
        updated=len(findings) - inserted,
        total_rows=total,
    )


def read_findings(db_path: Path) -> list[dict[str, object]]:
    """Read back every stored finding, newest first.

    Present for the programs that import this package. The command-line tool
    does not use it.
    """
    if not db_path.exists():
        return []
    with closing(sqlite3.connect(db_path)) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            "SELECT * FROM findings ORDER BY last_seen_at DESC, kind, resource_id;"
        ).fetchall()
    return [dict(row) for row in rows]


def _row(finding: Finding, seen_at: str) -> tuple[object, ...]:
    return (
        finding.kind.value,
        finding.resource_id,
        finding.sku,
        finding.team,
        finding.monthly_cents,
        finding.billed_region,
        finding.scanned_region,
        int(finding.above_grace),
        ",".join(finding.sources),
        seen_at,
        seen_at,
    )
