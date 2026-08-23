"""Run the poll loop for as long as the service is up."""

from __future__ import annotations

import sqlite3

from collector.poller import pollRound
from collector.store import pruneOldReadings
from collector.vocabulary import DeviceEntry, EpochSeconds, RoundReport


RETENTION_S = 3600.0


def pollForever(
    connection: sqlite3.Connection,
    devices: tuple[DeviceEntry, ...],
    replies: dict[str, bytes],
    rounds: int,
) -> tuple[RoundReport, ...]:
    """Poll every device once per round, pruning what has aged out, and report each round."""
    reports = []
    for number in range(rounds):
        observed_at = EpochSeconds(float(number))
        reports.append(pollRound(connection, devices, replies, observed_at))
        pruneOldReadings(connection, EpochSeconds(observed_at - RETENTION_S))

    return tuple(reports)
