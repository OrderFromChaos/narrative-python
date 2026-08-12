# T1 — CSV to SQLite loader

Load a CSV file into a SQLite table. The CSV has a header row. Coerce each column to int, float or
text by inspecting the values. Rows that fail coercion are skipped and reported at the end with
their line number and the reason. Accept the CSV path, the database path and the table name.
Report how many rows were loaded and how many skipped; exit nonzero if any were skipped.

Single file. Python 3.10+. Standard library only. No test suite.
