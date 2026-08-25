"""The single fatal-error type shared by the package."""

from __future__ import annotations


class ReconcileError(Exception):
    """A condition that stops the run before any record is reconciled.

    The command-line tool turns this into exit code 2 and writes neither a
    report nor a database. Two situations raise it: an unusable rules file and
    an unusable input directory. Every other failure is local to one file and
    is recorded as that file's outcome instead.
    """
