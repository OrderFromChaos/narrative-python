"""The importable entry point: read, join, and hand back the result.

This is what another program calls to run a reconciliation without running the
command-line tool. It reads the input directory and writes nothing at all;
the report file, the database and the printed table are separate steps that the
caller asks for, so an importer can take the findings and do something else
with them entirely.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from .errors import ReconcileError
from .inventory import read_inventory
from .join import join_inventory
from .models import FileOutcome, Finding, Totals
from .rules import RULES_BASENAME, Rules, load_rules


@dataclass(frozen=True, slots=True)
class ReconcileResult:
    """Everything one run produced, ready for either output.

    ``input_dir`` is the path exactly as the caller gave it, not a resolved or
    absolute form, so that a report can be compared across machines.
    """

    generated_at: str
    input_dir: str
    rules: Rules
    totals: Totals
    findings: list[Finding]
    files: list[FileOutcome]

    @property
    def exit_code(self) -> int:
        """``1`` when any ``billed_not_found`` finding is above the grace, else ``0``.

        A finding at or below the grace is still reported. An unreadable input
        file does not by itself change this, though it can manufacture
        ``billed_not_found`` findings, and those do.
        """
        return 1 if self.totals.above_grace else 0


def reconcile(input_dir: str | Path, rules_path: str | Path | None = None) -> ReconcileResult:
    """Reconcile a bill against an asset scan.

    Args:
        input_dir: The directory holding the ``*.billing.csv`` and
            ``*.scan.json`` files. A directory holding neither is not an error:
            the result is empty and the exit code is ``0``.
        rules_path: The rules file. Defaults to ``reconcile.json`` inside
            ``input_dir``, and may name a path outside it.

    Returns:
        The findings in report order, one outcome per file considered, and the
        totals that describe them.

    Raises:
        ReconcileError: The input directory or the rules file was unusable, so
            nothing was reconciled.
    """
    generated_at = datetime.now(UTC).isoformat(timespec='seconds')

    directory = Path(input_dir)
    if not directory.is_dir():
        raise ReconcileError(f'input directory {directory} does not exist or is not a directory')

    resolved_rules = Path(rules_path) if rules_path is not None else directory / RULES_BASENAME
    rules = load_rules(resolved_rules)

    inventory = read_inventory(directory, resolved_rules)
    joined = join_inventory(inventory, rules)

    return ReconcileResult(
        generated_at=generated_at,
        input_dir=str(input_dir),
        rules=rules,
        totals=joined.totals,
        findings=joined.findings,
        files=inventory.files,
    )
