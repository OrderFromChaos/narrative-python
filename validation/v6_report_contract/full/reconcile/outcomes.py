"""Construct the FileOutcome that a reader reports for one file of the input directory.

    {"path": "edge.billing.csv", "format": "billing", "status": "partial", "accepted": 4,
     "rejected": 1, "problems": ["row 6: resource_id min-galena-3357 already appeared"]}

A file the reader opened counts one problem per rejected record, so `rejected` is the length of
`problems`. A file that failed as a whole counts zero of each and states one problem, and a file of
an unknown format was never opened and states none.
"""

from __future__ import annotations

from collections.abc import Sequence

from reconcile.vocabulary import FileOutcome, FileStatus, InventoryFormat


def describeReadFile(
    path_name: str,
    inventory_format: InventoryFormat,
    accepted: int,
    problems: Sequence[str],
) -> FileOutcome:
    """Describe a file the reader opened: partial once it rejected a record, and ok otherwise.

    Args:
        problems: one string per rejected record, which is what the outcome counts as rejected.
    """
    status = FileStatus.PARTIAL if problems else FileStatus.OK
    return FileOutcome(path_name, inventory_format, status, accepted, len(problems), tuple(problems))


def describeFailedFile(path_name: str, inventory_format: InventoryFormat, problem: str) -> FileOutcome:
    return FileOutcome(path_name, inventory_format, FileStatus.FAILED, 0, 0, (problem,))


def describeSkippedFile(path_name: str) -> FileOutcome:
    return FileOutcome(path_name, InventoryFormat.UNKNOWN, FileStatus.SKIPPED, 0, 0, ())
