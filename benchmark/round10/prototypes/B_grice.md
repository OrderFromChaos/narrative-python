## Comments

Four tests, from Grice's maxims of conversation. Delete a comment that fails any of them.

Reader: a professional developer. Read domain expertise (math, statistics, a vendor's protocol) from
`CLAUDE.md`. If `CLAUDE.md` doesn't state it, ask once per session, one question per domain, and
offer to save the answers there. Never write a basic explainer. (R10-audience, R10-audience-how)

### Relation: information the code can't carry

Prefer a name or a type: `over_quota: ByteCount`, `total_cents`, `rollingMeanSignedError`.
(R10-Q25, R10-Q27, R10-Q16)

Valid topics:
- outside constraints: vendor, API or library behaviour (R10-Q34, R10-Q10)
  - `# vendor closes idle sockets at 60 s`
- business case behind an architecture choice (R10-business-case, R10-Q14)
  - `# finance signs off each team's bill separately, so one file per team`
- labels for long blocks: `# parse data` (R8-block-comments, R10-Q03)
- rules a developer must enforce, capitals scaled to the cost of breaking them (R10-Q36)

Irrelevant:
- what the next line or a single call does (R10-Q01, R10-Q06, R10-Q39)
- standard library or language behaviour: `<=`, case sensitivity, `bisect_left()` (R10-Q19, R10-Q21, R10-Q26)
- why the file follows this style guide (R9-02, R10-Q01)
- risks far outside the task's scale (R10-Q13)
- illustrations of a decision just discussed in the session (R10-Q21)
- decision ids such as `(Q08)` (R7-D04-comments, lint)

### Quality: true now, and checkable

Required:
- assumptions and uncertainty, stated as such: `# vendor documents no encoding, UTF-8 assumed` (R10-Q38, R10-Q19)
- known weaknesses (R10-candor, R10-Q05, R6-12)
  - `FIXME:` incorrect behaviour, or behaviour that breaks soon after deploy
  - `TODO:` tech debt, future improvement
- data history with a date: `# databases written before 2025/04/03 lack the account_id column` (R10-Q23)

Forbidden:
- reassurance that a weakness is fine; `deliberately`, `on purpose` (R10-candor, R10-Q20, lint)
- changelog: an earlier state of the code, or a fixed bug with nothing left of it (R10-Q04, R10-Q08, lint)
- guarantees about other modules. Put them in the module docstring or `architecture.md`. (R10-Q24, R10-Q11)
- future needs nobody has documented or planned (R10-Q15)

### Quantity: no more than the reader needs

- explain in proportion to the idea's difficulty for the reader: `# signed error` on a rolling mean,
  more on a novel method (R10-Q16)
- one step of reason (R10-Q16, R10-seed-2)
- no alternatives that were never in the code (`rather than`, `instead of`), outside architecture
  discussion (R10-Q07, R10-rather-than)

### Manner: plain, terse English

- one line: lowercase start, no period. Several lines: sentences. (R10-Q26, R10-Q35)
- drop articles where nothing is lost (R10-seed-10)
- possessives and noun compounds over relative clauses: `the archive's collections`, `in read order` (R10-seed-1, R10-seed-9, R10-Q32)
- trade terms over paraphrase: `has no side effects`. Modifiers before the noun: `JSONL logs`. (R10-seed-3, R10-seed-4)
- contractions; imperative; no `we` (R10-Q28, R10-Q29)
- callables as `name()`; no article before an identifier (R10-Q30, R10-Q35)
- names the reader can resolve from the comment's position (R10-Q22, R10-Q21)
- no agent verbs on code or abstract nouns: `finds`, `knows`, `keeps its`, `costs` (R10-Q31, R10-Q39, R10-seed-6)
- no `is what`, no `its own` (R10-Q40, R10-Q41)
- the general case: `records are separated by blank lines`, not `two records` (R10-Q40)
- semicolon only between connected clauses, otherwise two sentences; never a dash (R10-Q33, lint)
- end-of-line for a short note, above the line for anything longer (R10-Q34)

Items marked `lint` get a planned `checks.py` rule. (R10-lint)
