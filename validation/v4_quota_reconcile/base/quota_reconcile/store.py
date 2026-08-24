"""Keep every overage in SQLite.

Each overage carries a fingerprint: a digest of the team, its quota, its total and its ranked
paths. The fingerprint column is unique, so a second run over unchanged reports finds the row it
wrote the first time and only moves `last_seen` forward. A run over changed reports has a
different fingerprint and therefore adds a row, which leaves the history of the overage in place.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType

from .model import Reconciliation, TeamUsage

SCHEMA_VERSION = 1

_SCHEMA = """
CREATE TABLE IF NOT EXISTS overage (
    id           INTEGER PRIMARY KEY,
    fingerprint  TEXT    NOT NULL UNIQUE,
    team         TEXT    NOT NULL,
    total_bytes  INTEGER NOT NULL,
    quota_bytes  INTEGER NOT NULL,
    over_bytes   INTEGER NOT NULL,
    input_dir    TEXT    NOT NULL,
    first_seen   TEXT    NOT NULL,
    last_seen    TEXT    NOT NULL,
    seen_count   INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS overage_path (
    overage_id  INTEGER NOT NULL REFERENCES overage(id) ON DELETE CASCADE,
    rank        INTEGER NOT NULL,
    path        TEXT    NOT NULL,
    size_bytes  INTEGER NOT NULL,
    PRIMARY KEY (overage_id, rank)
);

CREATE INDEX IF NOT EXISTS overage_team ON overage(team, last_seen);
"""


@dataclass(frozen=True, slots=True)
class StoreResult:
    """How one run changed the store."""

    inserted: tuple[str, ...] = ()
    seen_again: tuple[str, ...] = ()

    @property
    def total(self) -> int:
        return len(self.inserted) + len(self.seen_again)


class OverageStore:
    """A SQLite file that holds one row per distinct overage.

    Use it as a context manager, which commits on a clean exit and closes the connection:

        with OverageStore(Path("overages.sqlite3")) as store:
            result = store.record(reconciliation)
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(path)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._create_schema()

    def __enter__(self) -> OverageStore:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if exc is None:
            self._connection.commit()
        else:
            self._connection.rollback()
        self.close()

    def close(self) -> None:
        self._connection.close()

    def record(self, result: Reconciliation) -> StoreResult:
        """Write every overage in `result`, and report which rows are new."""
        inserted: list[str] = []
        seen_again: list[str] = []
        seen_at = result.generated_at.isoformat()

        for team in result.overages:
            fingerprint = fingerprint_of(team)
            if self._touch(fingerprint, seen_at):
                seen_again.append(team.team)
                continue
            self._insert(team, fingerprint, str(result.input_dir), seen_at)
            inserted.append(team.team)

        self._connection.commit()
        return StoreResult(inserted=tuple(inserted), seen_again=tuple(seen_again))

    def overages(self, team: str | None = None) -> list[sqlite3.Row]:
        """Return the stored overages, most recently seen first."""
        query = "SELECT * FROM overage"
        parameters: tuple[str, ...] = ()
        if team is not None:
            query += " WHERE team = ?"
            parameters = (team,)
        query += " ORDER BY last_seen DESC, over_bytes DESC"
        return list(self._connection.execute(query, parameters))

    def _create_schema(self) -> None:
        with self._connection:
            self._connection.executescript(_SCHEMA)
            self._connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")

    def _touch(self, fingerprint: str, seen_at: str) -> bool:
        """Move `last_seen` forward for a known overage. Return whether the row was there."""
        cursor = self._connection.execute(
            "UPDATE overage SET last_seen = ?, seen_count = seen_count + 1 WHERE fingerprint = ?",
            (seen_at, fingerprint),
        )
        return cursor.rowcount > 0

    def _insert(self, team: TeamUsage, fingerprint: str, input_dir: str, seen_at: str) -> None:
        cursor = self._connection.execute(
            """
            INSERT INTO overage (
                fingerprint, team, total_bytes, quota_bytes, over_bytes,
                input_dir, first_seen, last_seen, seen_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
            """,
            (
                fingerprint,
                team.team,
                team.total_bytes,
                team.quota_bytes,
                team.over_bytes,
                input_dir,
                seen_at,
                seen_at,
            ),
        )
        self._connection.executemany(
            "INSERT INTO overage_path (overage_id, rank, path, size_bytes) VALUES (?, ?, ?, ?)",
            [
                (cursor.lastrowid, rank, usage.path, usage.size_bytes)
                for rank, usage in enumerate(team.paths, start=1)
            ],
        )


def fingerprint_of(team: TeamUsage) -> str:
    """Return the key that makes one overage the same overage on a later run.

    The digest covers the team, its quota, its total and its ranked paths, so a re-run over
    unchanged reports produces the same key and no second row.
    """
    material = json.dumps(
        {
            "team": team.team,
            "quota_bytes": team.quota_bytes,
            "total_bytes": team.total_bytes,
            "paths": [[usage.path, usage.size_bytes] for usage in team.paths],
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()
