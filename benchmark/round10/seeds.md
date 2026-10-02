# Round 10 seed pairs

Pairs the user wrote by hand: a comment as Claude wrote it, and the user's rewrite. They are
recorded in `decisions.jsonl` as `R10-seed-*`, weak, because they were given as examples rather
than rulings. Rows 3 onward come from answers to questions and are cited in each decision's note.

| Claude | user |
|---|---|
| `--drop clears the collections the archive carries` | `--drop clears the archive's collections` |
| `NOTE: no embedded quotes - subprocess.run() takes a list, so no shell strips them and mongorestore would receive a path that literally starts with a " character` | `NOTE: don't wrap args in quotes, subprocess.run() already handles character escapes` |
| `Reads SAMPLE_CONFIG and does not change it` | `SAMPLE_CONFIG has no side effects` |
| `Logs go to stderr as JSONL so that the report on stdout stays pipeable.` | `JSONL logs go to stderr...` |
| `` `executemany` takes one sequence per row and rejects a dataclass with `ProgrammingError: parameters are of unsupported type`, so the row shape gets a name instead. `` | `sqlite3.cursor.executemany does not support dataclasses, so NamedTuple is used instead` |
| `An outside API constraint keeps its comment.` (Claude's chat summary) | `valid comments:` then `- outside API constraints` |
| `over: ByteCount  # the bytes above the quota, and 0 when the team is within the quota` | `over_quota: ByteCount` |
| `# Amounts are in cents.` | `total_cents` |
| `in the order they were read` | `in read order` |
| `Retry once: the endpoint drops the first request after an idle period.` | `endpoint drops first request after idle time, so retry once` |
| `A blank line separates two records.` | `records are separated by blank lines` |
| `## Batch 2 — what a comment says` (Claude's header in `questions.md`) | `Batch 2 - comment content` |
| `# signed, not absolute` | `rollingMeanSignedError`, or `# signed error` |
| `databases written before account_id existed lack the column` | `databases written before 2025/04/03 lack the account_id column` |
| `a module holding one function` (Claude's comment in `skill/checks.py`) | `a module has one function` |
| `databases written before 2026/10/01 lack the account_id column, and their rows keep it NULL` | `databases written before 2026/10/01 lack the account_id column` |
| `One row per finding, in the column order of the INSERT. The DB-API takes a sequence per row and raises ProgrammingError on a dataclass, so the shape stays a tuple and the alias gives it a name.` | `DB-API doesn't allow dataclasses, so tuple` |

## Axes each pair raises

| pair | axis | block |
|---|---|---|
| 1 | possessive over a relative clause | D |
| 2 | a directive with one hop of reason, against a three-hop causal chain | C |
| 2 | a short, looser mechanism against the exact one | C |
| 2 | an instruction aimed at a maintainer | B |
| 2 | `NOTE:` prefix, and a contraction | D |
