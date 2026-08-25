"""One call that reads a directory and returns the findings.

This is the entry point for a program that imports the package. It runs the
same steps as the command-line tool, but it writes nothing and prints nothing:
storing the findings and writing the report stay with the caller.

    from pathlib import Path
    from reconcile import reconcile_directory

    result = reconcile_directory(Path("fixture"))
    for finding in result.actionable:
        ...
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from .join import reconcile
from .loader import load_inventory
from .model import Reconciliation
from .rules import Rules, default_rules_path, load_rules


def reconcile_directory(
    input_dir: Path, rules_path: Path | None = None
) -> Reconciliation:
    """Read `input_dir`, join the two sides, and return every mismatch.

    `rules_path` defaults to `reconcile.json` inside the input directory. If
    that file is absent, the run uses the default rules: no ignored sku, no
    region alias, and no grace amount.

    Raises `NotADirectoryError` if the input directory is absent, and
    `RulesError` if a rules file exists but cannot be used.
    """
    rules, rules_file = _rules_for(input_dir, rules_path)
    inventory = load_inventory(input_dir, rules_file)
    joined = reconcile(inventory.billing, inventory.scanned, rules)

    return Reconciliation(
        input_dir=str(input_dir),
        generated_at=datetime.now(UTC).isoformat(timespec="seconds"),
        rules=rules,
        findings=joined.findings,
        stats=joined.stats,
        outcomes=inventory.outcomes,
    )


def _rules_for(
    input_dir: Path, rules_path: Path | None
) -> tuple[Rules, Path | None]:
    if rules_path is not None:
        return load_rules(rules_path), rules_path

    found = default_rules_path(input_dir)
    if found.is_file():
        return load_rules(found), found
    return Rules(), None
