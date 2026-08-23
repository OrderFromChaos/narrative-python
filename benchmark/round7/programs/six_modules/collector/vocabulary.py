"""The words the collector is written in.

Every type that crosses a module boundary is declared here, and so is every type that could
(R7-B07). The modules that follow hold functions and constants only.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import NewType


DeviceId = NewType('DeviceId', str)
EpochSeconds = NewType('EpochSeconds', float)


class CollectorError(RuntimeError):
    """Anything the collector refuses to read or cannot reach."""


class CorruptFrameError(CollectorError):
    """A reply arrived, and it is not a frame this program can read."""


class UnknownDeviceError(CollectorError):
    """A reply arrived from a device the table does not list."""


@dataclass(frozen=True, slots=True)
class DeviceEntry:
    device_id: DeviceId
    site_code: str


@dataclass(frozen=True, slots=True)
class Reading:
    device_id: DeviceId
    celsius: float
    observed_at: EpochSeconds


@dataclass(frozen=True, slots=True)
class PollOutcome:
    device_id: DeviceId
    reading: Reading | None
    refusal: str | None


@dataclass(frozen=True, slots=True)
class RoundReport:
    outcomes: tuple[PollOutcome, ...]

    @property
    def read(self) -> int:
        """Return how many devices answered with a frame this program could read."""
        return sum(1 for outcome in self.outcomes if outcome.reading is not None)

    @property
    def refused(self) -> int:
        """Return how many devices did not."""
        return sum(1 for outcome in self.outcomes if outcome.refusal is not None)
