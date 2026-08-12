# T3 — duplicate file finder

Find duplicate files under a directory tree by content. Group files by size first, then compare by
hash only within groups of equal size. Report groups of duplicates, largest wasted space first,
with the total recoverable bytes. Accept the root directory and an optional minimum file size.
Skip unreadable files without aborting and report how many were skipped.

Single file. Python 3.10+. Standard library only. No test suite.
