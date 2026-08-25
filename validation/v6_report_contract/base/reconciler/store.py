"""The SQLite store: one row per distinct finding, across every run.

The store answers "have we seen this before?", so a re-run over unchanged
inputs must not double-insert. The key is a fingerprint of the finding's whole
content, which makes the answer follow the finding rather than the run: a
second run over the same inputs touches the same rows and only moves their
``last_seen_at`` forward. A finding whose cost or region has changed is a
different finding and gets its own row, which is what leaves a history behind.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path

from .models import Finding

DEFAULT_DB_NAME = 'reconcile.db'
"""The database written when ``--db`` is not given."""

_SCHEMA = """
CREATE TABLE IF NOT EXISTS finding (
    fingerprint     TEXT PRIMARY KEY,
    kind            TEXT NOT NULL,
    resource_id     TEXT NOT NULL,
    sku             TEXT NOT NULL,
    monthly_cents   INTEGER,
    team            TEXT,
    billed_region   TEXT,
    scanned_region  TEXT,
    above_grace     INTEGER NOT NULL,
    sources         TEXT NOT NULL,
    first_seen_at   TEXT NOT NULL,
    last_seen_at    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS finding_by_resource ON finding (resource_id);
"""

_UPSERT = """
INSERT INTO finding (
    fingerprint, kind, resource_id, sku, monthly_cents, team,
    billed_region, scanned_region, above_grace, sources, first_seen_at, last_seen_at
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT (fingerprint) DO UPDATE SET last_seen_at = excluded.last_seen_at
"""


@dataclass(frozen=True, slots=True)
class StoreOutcome:
    """How much of a run was new to the store."""

    inserted: int
    seen_again: int


def fingerprint(finding: Finding) -> str:
    """Return the dedup key for a finding.

    Every reported value goes into the key, in a form that cannot be confused
    across fields, so two findings share a key only when they are the same
    mismatch of the same resource with the same numbers behind it.
    """
    payload = json.dumps(
        [
            finding.kind.value,
            finding.resource_id,
            finding.sku,
            finding.monthly_cents,
            finding.team,
            finding.billed_region,
            finding.scanned_region,
            finding.above_grace,
            list(finding.sources),
        ],
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()


def record_findings(db_path: Path, findings: list[Finding], observed_at: str) -> StoreOutcome:
    """Write every finding to the store, creating the database if it is absent.

    Args:
        db_path: The database file.
        findings: The run's findings, in any order.
        observed_at: The run's start time, stored as both ``first_seen_at`` and
            ``last_seen_at`` on a row the store has not held before.

    Returns:
        How many rows were new and how many the store already held.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    rows = [
        (
            fingerprint(finding),
            finding.kind.value,
            finding.resource_id,
            finding.sku,
            finding.monthly_cents,
            finding.team,
            finding.billed_region,
            finding.scanned_region,
            int(finding.above_grace),
            json.dumps(list(finding.sources), ensure_ascii=False),
            observed_at,
            observed_at,
        )
        for finding in findings
    ]

    with closing(sqlite3.connect(db_path)) as connection, connection:
        connection.executescript(_SCHEMA)
        before = _row_count(connection)
        connection.executemany(_UPSERT, rows)
        inserted = _row_count(connection) - before

    return StoreOutcome(inserted=inserted, seen_again=len(rows) - inserted)


def _row_count(connection: sqlite3.Connection) -> int:
    return int(connection.execute('SELECT count(*) FROM finding').fetchone()[0])
