## Comments

**Test: what information does this comment provide over the code itself?** (R10-Q25)

Reader: a professional developer. Read domain expertise (math, statistics, a vendor's protocol) from
`CLAUDE.md`. If `CLAUDE.md` doesn't state it, ask once per session, one question per domain, and
offer to save the answers there. Never write a basic explainer. (R10-audience, R10-audience-how)

These rules cover docstring prose too. (R10-docstrings)

**Comments are not thinking traces.** While writing, you reasoned through edge cases, alternatives
and spec gaps. That reasoning is a thinking trace: it belongs in your report to the user, not in
the code. (R10-stance)

**Cut a comment whose content a smart reader would get from the code below it (including variable
names), no matter how the comment is phrased or what rule category it seems to fit.**
(R10-restatement-gate)

Before writing or rewording a comment, in order:

1. **Rename first.** If the information fits in a name or a type, rename and write no comment:
   `over_quota: ByteCount`, `total_cents`, `rollingMeanSignedError`. (R10-Q25, R10-Q27, R10-Q16)
2. **Guarantee it in code.** Establish a cheap precondition, such as sorted input, upstream in the
   call flow, and write no comment. Not in the function that relies on it: an index lookup doesn't
   sort its own input. (R10-Q19)
3. **Match a kind.** Write a comment only if it is one of the four **Comment kinds**, passes that
   kind's test, and is not under **Never**. Deleting is a valid outcome of a rewrite.
4. **Set the depth and sentence form** by **Depth** and **Sentence form**.

**Comment kinds:** (R10-topic-lists, R10-fp-fn, R10-kinds)

- **Source**: a fact or requirement from outside the code. Test: it would still be true if the code
  were deleted, and a professional at the reader's level wouldn't already know it.
  (R10-Q10, R10-Q14, R10-Q23, R10-Q34, R10-Q43, R10-Q48, R10-Q51, R10-business-case)
  - `# vendor closes idle sockets at 60 s`
  - `# finance signs off each team's bill separately, so one file per team`
  - `# databases written before 2025/04/03 lack the account_id column`
  - `WARN_THRESHOLD = 1.6  # calibration spec CAL-7, section 3`
  - `# handles millions of rows`, at the top of the function
- **Fence**: code that looks unusual, where the obvious simplification silently breaks it. Test: name
  the simplification a smart, experienced developer would make, and the defect it causes: a wrong
  result, a crash, a security hole or a performance collapse. A cosmetic difference doesn't count,
  and neither does adding a feature. Say what the fact forces in the code.
  (R10-Q20, R10-Q42, R10-Q44, R10-Q45, R10-Q50, R10-Q53, R10-Q55, R10-fence-consequence)
  - `# needs both isinstance() checks; JSON true is a Python int`, not `# JSON true is a Python int`
  - `# constant-time comparison, so response timing doesn't reveal the token`
  - `# walk backwards so deleting an item doesn't shift the indexes still to visit`
  - `# migrate before load: load reads the account_id column`
  - not `# file can change between calls, so not cached`: a cache is a feature, not a simplification
- **Decoding aid**: a line a professional at the reader's level would need docs or a worked example
  to read. Test: you'd look it up. State the intent, not the mechanism. (R10-Q42, R10-Q46)
  - `SIZE_PATTERN = re.compile(...)  # number, then an optional binary unit suffix`
  - `# fsum() for accurate floating point math`
- **Marker**: no test needed. (R10-candor, R10-Q03, R10-Q05, R10-Q36, R10-Q38, R6-12, R8-block-comments)
  - `FIXME:` incorrect behaviour, or behaviour that breaks soon after deploy
  - `TODO:` tech debt, future improvement
  - a stated assumption: `# vendor documents no encoding, UTF-8 assumed`
  - a label on a block of at least 4 lines, ideally 6 or more: `# parse data` (R10-block-label-size)
  - a rule a developer must enforce, with capitals scaled to the cost of breaking it:
    `# read-only: NEVER write to the audited readings`

**Never, even when a kind's test passes:**
- what the next line or a single call does (R10-Q01, R10-Q06, R10-Q39, R10-Q47, R10-Q54)
- standard library or language behaviour the reader knows: `<=`, case sensitivity, `None` (R10-Q19, R10-Q21, R10-Q26, R10-Q49)
- why the file follows this style guide (R9-02, R10-Q01)
- decision ids such as `(Q08)` (R7-D04-comments, `NAR012`)
- changelog: an earlier state of the code, or a fixed bug with nothing left of it (R10-Q04, R10-Q08, R10-Q52, `NAR015`)
- alternatives never in the code (`rather than`, `instead of`), except in architecture discussion (R10-Q07, R10-rather-than)
- risks far outside the task's scale, and decisions too inconsequential for a later reader to reconsider (R10-Q13, R10-rating)
- future needs nobody has documented or planned (R10-Q15)
- reassurance that a weakness is fine; `deliberately`, `on purpose` (R10-candor, R10-Q20, `NAR014`)
- guarantees about other modules. Put them in the module docstring or `architecture.md`. (R10-Q24, R10-Q11)
- illustrations of a decision just discussed in the session (R10-Q21)
- a function's return contract. State it in the docstring, and only if the return type doesn't make it obvious. (R10-return-contract)

**Depth:** in proportion to the idea's difficulty for the reader, and one step of reason.
`# signed error` on a rolling mean, more on a novel method. (R10-Q16, R10-seed-2)

**Sentence form:**
- a one-line `#` comment: lowercase start, no period. Several lines, and every docstring: sentences. (R10-Q26, R10-Q35, R10-docstrings)
- terse: drop articles where nothing is lost (R10-seed-10)
- possessives and noun compounds over relative clauses: `the archive's collections`, `in read order` (R10-seed-1, R10-seed-9, R10-Q32)
- trade terms over paraphrase: `has no side effects`. Modifiers before the noun: `JSONL logs`. (R10-seed-3, R10-seed-4)
- contractions; imperative; no `we` (R10-Q28, R10-Q29)
- callables as `name()`; no article before an identifier (R10-Q30, R10-Q35)
- only names the reader can resolve from the comment's position (R10-Q22, R10-Q21)
- with code or an abstract noun as the subject, only verbs for what code literally does: `returns`,
  `raises`, `reads`, `writes`, `calls`, `skips`. Never agency or containment: `finds`, `knows`,
  `holds`, `carries`, `keeps its`, `costs`. Write `a module has one function`, not
  `a module holding one function`. These words are examples; the test is whether the subject can
  perform the verb. (R10-Q31, R10-Q39, R10-seed-1, R10-seed-6, R10-seed-15, R10-skill-gaps)
- no `is what`, no `its own` (R10-Q40, R10-Q41)
- the general case: `records are separated by blank lines`, not `two records` (R10-Q40)
- semicolon only between connected clauses, otherwise two sentences; never a dash (R10-Q33, `NAR013`)
- directly above the statement it concerns, not above its enclosing block; end-of-line for a short note (R10-Q34, R10-locality)

`NAR012` to `NAR015` flag four wording faults in comments and docstrings, and a clean run is no
evidence about the rest of these lists. Check every comment and docstring you write or touch against
them. A dash after a list-item term is allowed. `NAR015` also flags `no longer` about data; such a
sentence usually gives data an agent verb, so reword it. Silence a false positive with
`# noqa: NARxxx`. (R10-lint, R10-skill-gaps, R10-list-dash, R10-nar015-scope)
