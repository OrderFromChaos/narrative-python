# Proposed rule: a DB-API row is a `NamedTuple`

From R10-Q10, verbatim: "Also I would use a NamedTuple instead of this...". The same point is in
R10-seed-17: "(except I would say this should probably be a NamedTuple...)".

## Measured

Python 3.11.13, the project floor. Script: a six-field row, `?` placeholders, an in-memory database.

| input | `executemany` | `execute` |
|---|---|---|
| `class FindingRow(NamedTuple)` rows | accepted | accepted |
| `@dataclass` rows | `ProgrammingError: parameters are of unsupported type` | same |

- Positional `?` placeholders bind a `NamedTuple` by position. With named `:path` placeholders, a
  `NamedTuple` binds on 3.11, gives a `DeprecationWarning` on 3.12, and raises `ProgrammingError` on
  3.14. `row._asdict()` binds named placeholders on all three.
- `checks.py` gives 0 NAR005 findings on the `NamedTuple` module: the class, its six `str`/`int`/`float`
  fields, and `storeFindings(connection, rows: list[FindingRow])`. The whole module passes
  `verify.py`: ruff, ruff format, pylint, mypy --strict, checks.py, vermin 3.11.
- `list[tuple[str, int, str, str, float, int]]` as a parameter gives NAR005, 7 things, remedy "a dataclass".
- The bare alias `FindingRow = tuple[...]` also gives 0 NAR005 findings, with or without `# noqa`.
  NAR005 checks parameters, returns and annotated assignments, not the value of a plain assignment.
  The current text's "suppress the finding" applies only where the raw tuple is written in a signature.
- `FindingRow.__mro__` is `(FindingRow, tuple, object)`. `NamedTuple` is not a base class, so the
  class syntax does not conflict with "Composition over inheritance, always".

## SKILL.md, Types, the DB-API paragraph

**Before:**

> **The DB-API is the standing exception.** `sqlite3.executemany` takes a sequence per row, so
> `list[tuple[str, str, float, float, int, int]]` names seven things and has no dataclass form —
> passing one raises `ProgrammingError: parameters are of unsupported type`. Give the row shape a
> named alias so it reads, and suppress the finding with that reason. (`R8-D27`)

**After:**

> **The DB-API is the standing exception.** `sqlite3.executemany` takes a sequence per row and
> raises `ProgrammingError: parameters are of unsupported type` on a dataclass. Instead, use a
> `NamedTuple` for rows: it is a tuple, so `executemany` takes it, and its fields have names. Use
> `?` placeholders, and say why in a comment. (`R8-D27`, `R10-namedtuple-rows`)
>
> ```python
> # sqlite3.Cursor.executemany does not support dataclasses, so NamedTuple is used instead
> class FindingRow(NamedTuple):
>     path: str
>     line: int
>     code: str
>     detail: str
>
>
> def storeFindings(connection: sqlite3.Connection, rows: list[FindingRow]) -> None:
>     connection.executemany('INSERT INTO findings VALUES (?, ?, ?, ?)', rows)
>     connection.commit()
> ```

The comment is your wording, with one change: `sqlite3.cursor` becomes `sqlite3.Cursor`, the real
class name. The decision note keeps your words exactly.

## Decision record

```json
{"id": "R10-namedtuple-rows", "dimension": "types.annotation_complexity", "round": "10",
 "kind": "gap", "options": ["a bare tuple alias, NAR005 suppressed", "a NamedTuple"],
 "choice": "a NamedTuple", "strength": "strong", "condition": "a row passed to the DB-API",
 "note": "Verbatim (R10-Q10): 'Also I would use a NamedTuple instead of this...' ... <measurements above>",
 "date": "2026-10-02"}
```

No `supersedes` field. R8-D27 records two failures of NAR005, and SKILL.md cites it for the counting
rule too. The new decision replaces only the remedy for the DB-API row. With
`"supersedes": ["R8-D27"]`, `verify_docs.py` would reject every citation of R8-D27 in `skill/`,
including the citation on the counting rule.

## Tool text

- `skill/tooling.md` and `README.md` do not mention the DB-API exception. No change.
- `checks.py`: the NAR005 remedy for `list[tuple[...]]` says "a dataclass". `checks.py` cannot tell a
  DB row from other tuples. Two choices:
  - **leave it**: SKILL.md states the exception, as it does now.
  - **widen the message** when the outermost name is `tuple`, or a `list` of `tuple`, to
    "a dataclass, or a NamedTuple for a DB-API row".
