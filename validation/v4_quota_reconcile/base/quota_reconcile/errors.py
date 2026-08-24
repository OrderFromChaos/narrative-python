"""Exception types raised by the quota reconciler."""

from __future__ import annotations


class QuotaReconcileError(Exception):
    """Base class for every error this package raises."""


class SizeFormatError(QuotaReconcileError):
    """A size string does not follow the `<number><unit>` grammar."""


class QuotaFileError(QuotaReconcileError):
    """The quota file is missing, unreadable, or does not hold the expected fields."""


class MalformedReportError(QuotaReconcileError):
    """A usage report is damaged badly enough that no entry can be read from it."""

    def __init__(self, source: str, reason: str) -> None:
        super().__init__(f"{source}: {reason}")
        self.source = source
        self.reason = reason
