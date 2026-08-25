"""Runs the command-line tool: `python3 -m reconcile <input-dir>`."""

from __future__ import annotations

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
