"""Ask every device for a reading, and record what came back."""

from __future__ import annotations

import sqlite3

from collector.protocol import parseFrame
from collector.store import insertReading, readingSeen
from collector.vocabulary import CollectorError, DeviceEntry, EpochSeconds, PollOutcome, RoundReport


def pollRound(
        connection: sqlite3.Connection,
        devices: tuple[DeviceEntry, ...],
        replies: dict[str, bytes],
        observed_at: EpochSeconds,
    ) -> RoundReport:
    """Poll every device once. One unreachable device does not stop the others (Q24)."""
    outcomes = tuple(pollOne(connection, device, replies, observed_at) for device in devices)
    return RoundReport(outcomes)


def pollOne(
        connection: sqlite3.Connection,
        device: DeviceEntry,
        replies: dict[str, bytes],
        observed_at: EpochSeconds,
    ) -> PollOutcome:
    """Poll one device and write what it said, returning the outcome either way."""
    try:
        reading = parseFrame(replies[device.device_id], device.device_id, observed_at)
    except CollectorError as exc:
        return PollOutcome(device.device_id, None, str(exc))

    if readingSeen(connection, reading.device_id, reading.observed_at):
        return PollOutcome(device.device_id, reading, 'duplicate')

    insertReading(connection, reading)
    return PollOutcome(device.device_id, reading, None)
