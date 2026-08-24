# Round 8 — red team

Round 7 wrote 70 architecture rules and put them in `skill/architecture.md`. This round attacks
them, and everything they sit on.

## Protocol

Four agents, each with **no access to this conversation** and no idea what the author concluded.
Three were given the skill files only and told that `benchmark/` is unavailable to a real user. The
method is `GAPS.md`'s, which this repository already found more productive than reviewing the text.

| agent | task | why |
|---|---|---|
| **write** | build a runnable multi-module service against the skill, log every ambiguity | reproduces the `GAPS.md` method at multi-module scale |
| **critique** | hostile read for contradictions, verify prose claims against `checks.py` and the config | text defects the writer would work around without noticing |
| **install** | follow `README.md` literally on a simulated fresh machine | the path every real user walks first |
| **review** | review a planted-defect program against the skill | the skill's *second* advertised purpose, never tested |

The review agent was scored: eight violations were planted deliberately and two more were
incidental, and the ground truth was written down before the agent ran.

## Results

**35 defects.** All are in `decisions.jsonl` as `R8-D01` to `R8-D35`.

### The one every agent found

`architecture.md:118` says an application package's `__init__.py` is empty. `NAR009` rejects a module
with no docstring. The exemption exists, under the heading **"not shipped. Do not follow these
yet."** (`R8-D01`)

**All four agents hit it, unprompted, none of them warned.** It is the most likely defect to meet on
anyone's first program, because every package has an `__init__.py`. One agent named the failure mode
exactly: the reader hits the error, scrolls, finds the pending section describing that exemption, and
applies it — the pending section reads as the resolution because the body offers none.

### Three bugs that were already shipping

Round 7 did not cause these. They were found because someone finally ran the toolchain against its
own documentation.

**`ruff check --fix` erases `NAR005` findings, and it is step one of the pipeline.** (`R8-D03`)
`UP` is selected, so `Optional[X]` becomes `X | None`. `annotationDepth` handles `ast.Subscript` and
`ast.List`, and a union is an `ast.BinOp`, so it scores depth 0. Measured: one finding before, zero
after, same annotation. `SKILL.md` calls that order "the order that converges". It converges by
deleting the evidence. Round 5 measured `NAR005` depth at length and never met this form.

**`NAR010` is inert in every module except the entry point.** (`R8-D02`) `SKILL.md` promises it
over-approximates — "would rather call an orphan live than let a running `FIXME` through". It seeds
the frontier only from a function named `main` in the same module. **Following `architecture.md`'s
own instruction to put `main` in `__main__.py` is what disables it.** It fails in the direction the
document promises it will not.

**`NAR001` fires on the logging pattern `SKILL.md` prints.** (`R8-D04`) A `configureLogging` written
straight from the documented example fails the gate, and the rule that explains why lives only in
`GAPS.md` and a code comment.

### The review path works

The planted-defect program scored **10 of 10, with zero false positives.**

Every architectural violation was caught with the right rule quoted: a per-vendor constant in a
generic module, an exception defined where it is raised, a `Protocol` over the only implementation, a
raw handle crossing modules, a `utils.py` grab-bag, missing underscores, a registering decorator,
symbol-imports from first-party modules, a threaded unused flag, and a discarded computed value.

It obeyed the instruction not to invent rules: a genuine missing `commit()` went in a separate
"not covered by the style" list rather than being dressed up as a style violation. It also found
roughly twenty real violations that were never planted.

**This is the strongest evidence in the round that the architecture rules are usable**, and it is
worth weighing against the 35 defects: the rules are hard to *follow* in places and easy to *apply*.

### What the agents could not decide

Undefined terms cost more than contradictions did. "Boundary" is used in four incompatible senses and
never defined (`R8-D11`) — the scope of `frozen=True` swings with which sense a reader picks. "A
coherent concern" has its only calibration in a citation that does not resolve (`R8-D12`). The
criterion for "below" is stated only as a consequence (`R8-D13`).

`R8-D21` is the root cause of two others, and it was written in this session: `SKILL.md:11` says
"This document governs one file" and no document then says that it still governs each file's
internals once a program spans several.

## What held up

Reported so the fixes do not damage what works.

- **`tooling.md` is the only file with no defect found**, by the agent whose job was finding them.
- Every version pin is honest: `README.md`'s table, `requirements-lock.txt` and the installed venv
  agree exactly on all four tools.
- `verify.py` behaves as documented in every tested branch — exit 0 clean, exit 1 with each failing
  tool's own output, exit 2 on a missing toolchain or config, `--no-fix` leaving files untouched, and
  the STE linter degrading to "skipped" without a traceback.
- The exhaustive-`match` rule works end to end: adding an enum member produces exactly the promised
  `Missing return statement`.
- The 3.10 floor is enforced consistently across `verify.py`, the config and `vermin`.
- `checks.py` runs standalone on any `python3` with no venv, as claimed.
- One agent called the DEBUG-per-item / WARNING-per-tally split "the best rule in the document" and
  said it produced measurably better logs than its own instinct.

## Counter-argument, stated fairly

**Three of the four agents were given a task the skill does not target.** The skill is written for
this author's Python. Two agents built services from a cold start with no domain context, which is
the hardest possible case and not the common one. Defect counts from that setting overstate what a
user who already knows the house style would hit.

**The 35 are not equally weighted and the list does not say so.** `R8-D01` will bite everyone;
`R8-D25` is an edge case one agent met once. Ordering them by severity was not attempted.

**No agent was asked to weigh cost against benefit.** They were told to find defects, and they did.
None was asked whether the rules made the code better, which is the question the validation arms
exist to answer and which remains unanswered from round 7.

**The review score is one program with a known answer key.** Ten of ten is a real result, and the
agent knew it was reviewing, was told a house style applied, and had every rule in front of it. That
is not the same as noticing a violation unprompted in a large diff.

## The whitespace measurement

Separate from the defect list, and the round's other substantive result. `nar008_golden.md` records
it. Twelve functions were stripped of every internal blank line and marked up by hand; `NAR008` was
then run against the marked-up version.

23 blank lines wanted, 12 findings raised, 5 in common. **Precision 42%, recall 22%.** The check is
wrong more often than right in both directions, and the line-count proxy carries almost no signal.
`R8-NAR008` supersedes `R6-10` and removes the check. `R8-NAR008-rule` records what the markup
encodes instead.
