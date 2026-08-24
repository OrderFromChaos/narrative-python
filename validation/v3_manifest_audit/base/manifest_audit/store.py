"""The SQLite store for findings.

A finding is identified by its manifest, package name, version and kind. That
identity is a unique index, and writes go through ``INSERT ... ON CONFLICT``,
so a second run over an unchanged manifest updates the ``last_seen`` column
instead of inserting a second row.

A finding that a manifest no longer produces is deleted after the write, but
only for the manifests that were read in this run. Findings from a manifest
that failed to parse stay in the table, because a failed read is not evidence
that the finding is gone.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable
from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from types import TracebackType

from .models import Finding

__all__ = ["FindingStore", "StoreSummary"]

SCHEMA_VERSION = 1

_SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS findings (
    id         INTEGER PRIMARY KEY,
    manifest   TEXT NOT NULL,
    package    TEXT NOT NULL,
    version    TEXT NOT NULL,
    kind       TEXT NOT NULL,
    source     TEXT,
    detail     TEXT NOT NULL,
    location   TEXT NOT NULL,
    first_seen TEXT NOT NULL,
    last_seen  TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS findings_identity
    ON findings (manifest, package, version, kind);

CREATE INDEX IF NOT EXISTS findings_by_kind ON findings (kind);
"""

_UPSERT = """
INSERT INTO findings
    (manifest, package, version, kind, source, detail, location, first_seen, last_seen)
VALUES
    (:manifest, :package, :version, :kind, :source, :detail, :location, :seen, :seen)
ON CONFLICT (manifest, package, version, kind) DO UPDATE SET
    source    = excluded.source,
    detail    = excluded.detail,
    location  = excluded.location,
    last_seen = excluded.last_seen
"""


@dataclass(frozen=True, slots=True)
class StoreSummary:
    """What one write did to the table."""

    seen: int
    inserted: int
    updated: int
    pruned: int
    total_rows: int


class FindingStore(AbstractContextManager["FindingStore"]):
    """A SQLite database of findings.

    Use it as a context manager, or call `close` when finished. Pass
    ``":memory:"`` as the path for a store that leaves nothing behind.
    """

    def __init__(self, path: Path | str) -> None:
        self.path = str(path)
        self._connection = sqlite3.connect(self.path)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA journal_mode = WAL")
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._create_schema()

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    def close(self) -> None:
        self._connection.close()

    def record(
        self,
        findings: Iterable[Finding],
        *,
        read_manifests: Iterable[str] = (),
        seen_at: str | None = None,
    ) -> StoreSummary:
        """Write findings, then delete the stale ones.

        Args:
            findings: The findings from this run.
            read_manifests: The manifests that were read without error. Old
                findings for these manifests that this run did not produce are
                deleted.
            seen_at: The timestamp to write. It defaults to now, in UTC.

        Returns:
            Counts for the run, for the report.
        """
        stamp = seen_at or _now()
        rows = [self._row(finding, stamp) for finding in findings]

        with self._connection:
            before = self._count()
            self._connection.executemany(_UPSERT, rows)
            after = self._count()
            pruned = self._prune(read_manifests, stamp)
            total = self._count()

        inserted = after - before
        return StoreSummary(
            seen=len(rows),
            inserted=inserted,
            updated=len(rows) - inserted,
            pruned=pruned,
            total_rows=total,
        )

    def findings_for(self, manifest: str) -> list[sqlite3.Row]:
        """Return every stored finding for one manifest, oldest first."""
        cursor = self._connection.execute(
            "SELECT * FROM findings WHERE manifest = ? ORDER BY id", (manifest,)
        )
        return cursor.fetchall()

    def count(self) -> int:
        """Return the number of stored findings."""
        return self._count()

    def _prune(self, read_manifests: Iterable[str], stamp: str) -> int:
        pruned = 0
        for manifest in read_manifests:
            cursor = self._connection.execute(
                "DELETE FROM findings WHERE manifest = ? AND last_seen <> ?",
                (manifest, stamp),
            )
            pruned += cursor.rowcount
        return pruned

    def _count(self) -> int:
        row = self._connection.execute("SELECT COUNT(*) AS n FROM findings").fetchone()
        return int(row["n"])

    def _create_schema(self) -> None:
        with self._connection:
            self._connection.executescript(_SCHEMA)
            row = self._connection.execute(
                "SELECT version FROM schema_version LIMIT 1"
            ).fetchone()
            if row is None:
                self._connection.execute(
                    "INSERT INTO schema_version (version) VALUES (?)", (SCHEMA_VERSION,)
                )
            elif int(row["version"]) != SCHEMA_VERSION:
                raise sqlite3.DatabaseError(
                    f"{self.path}: database uses schema version {row['version']}, "
                    f"but this tool needs version {SCHEMA_VERSION}"
                )

    @staticmethod
    def _row(finding: Finding, stamp: str) -> dict[str, object]:
        return {
            "manifest": finding.manifest,
            "package": finding.package,
            "version": finding.version,
            "kind": finding.kind.value,
            "source": finding.source,
            "detail": finding.detail,
            "location": finding.location,
            "seen": stamp,
        }


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds")
