# Round 9 — the skill read as an artifact, and V4

Rounds 1 to 8 asked what the rules should be. This round asks a different question: **what is it
like to read the shipped skill, and what does the code it produces read like to its owner?**

The input was not a benchmark. It was the V3 output, read by the author, who reported four defects
in the skill text and asked one question about the numbers.

## The question about the numbers

V3 scored `base` at 12 modules / 1433 lines and `full` at 13 / 1012. The author expected a styled
program to be *longer*, not 421 lines shorter, and asked whether `base` was catching edge cases that
`full` dropped.

**It was, and the brevity was not the cause.** Split by line kind, `full` carries 13 *more* docstring
lines and 31 *more* comment lines than `base`. The whole delta is executable code: `base` has 457
more lines of it. Of those 457, roughly 150 are capability `full` lacks, 110 are features the task
never asked for, 110 are boilerplate (`__all__` in 12 modules costs 51 lines against `full`'s 17 in
one), 60 are error ceremony, and 15 are dead.

The capability gap is real and every item is a silent false negative. Running `full`'s code against
`base`'s fixture: `base` finds 2 banned packages and exits 1; `full` finds none and **exits 0** on a
directory holding three of them. Causes: no PEP 503 name folding, so `LeftPad` misses banned
`leftpad`; a mandatory `source` field that discards a whole file when one entry omits it; a version
comparator that scores `v2.0.0` below every minimum because `re.match(r'\d+', 'v2')` fails and the
part becomes 0; a fabricated `_ASSUMED_SOURCE = 'pypi'` on every lockfile package; and an uncaught
`write_text` whose traceback exits 1 with no banned package present.

**Only the fabricated source is the skill's fault**, and it became `R9-01`. The rest are domain
defects and are recorded here so the number is not read as a style result.

## The four defects in the skill text

Isolated by the arm split, which is a natural experiment: a behaviour in both guided arms comes from
`SKILL.md`, one only in `full` comes from `architecture.md`.

| defect | cause | decision |
|---|---|---|
| the skill narrates its own development history | accumulated | `R9-06` |
| docstrings argue with the style guide, and claim things about other modules | `architecture.md`'s `Keep the reason. The reason is the comment.` | `R9-02` |
| `packagesIn`, `policyIn`, `pathsIn`; bare `path: Path` | `R7-naming-result` + `Q11` | `R9-03`, `R9-04` |
| `Args:`/`Returns:` restate the signature | `SKILL.md` contradicting itself at lines 423 and 434 | `R9-05` |

Two of these are the skill contradicting its own evidence base:

- **`R7-naming-result` inverted the answer it recorded.** The shipped rule said "Verbosity is the
  symptom." The decision quotes the answer as *"cutoffFor is not clear enough to make it obvious
  what it is doing if you saw it without context in another part of the codebase … I prefer verbose
  function names generally speaking."* The requirement was always that the name stand alone.
- **`architecture.md`'s comment rule lost the principle it came from.** `R7-D04-comments` records:
  *"the point of comments is to be valuable to future devs who do not have the context window."*
  The shipped rule kept the citation ban and dropped that.

Density confirms the attribution: 25 style-guide justifications in `full`'s 1012 lines against 7 in
`skill`'s 811, and `*In(` appears 5 times in `full` and **0** in `skill` or `base`.

## What was cut, and where it went

Archaeology as a fraction of content lines before the cut: ~20% of `SKILL.md`, ~17% of
`architecture.md`, ~55% of `tooling.md`, ~95% of `GAPS.md`.

The rule applied was **keep the fact, cut the history**. A measurement stays where it *is* the rule
("a body of 8 lines or under takes no internal blanks"); it goes where it only defends a rule
against an objection nobody raised.

Nothing was destroyed. Verified before cutting: the `NAR008` precision/recall figures are in
`round8/README.md` and `round8/nar008_golden.md`, every `GAPS.md` entry is in `round4/`, and
`SIM103`'s reason is in `pyproject-snippet.toml`. `GAPS.md` moved to `benchmark/GAPS.md` rather than
being deleted, because three round writeups cite it.

`verify_docs.py:112-118` already encoded the boundary this needs. `statesCurrentRules()` is true for
`skill/` and `README.md` and false for a round writeup, "because a round records what was decided
then". That is exactly the line round 9 draws.

## Three stale statements found in the shipped tools

Cutting the archaeology from `checks.py` exposed text its own code had stopped implementing:

1. `RULES['NAR004']` described the trigger as "a function that raises, takes >3 parameters, or runs
   long". `R8-D18-resolved` dropped the raise trigger.
2. `checkDocstringThreshold`'s docstring listed the same three triggers against two in its body.
3. `checkAnnotationComplexity`'s docstring still described the depth-over-2 / width-over-3 rule that
   `R8-D27-resolved` replaced with counting names.

All three are the failure `verify_docs.py` exists to catch and cannot: it resolves citations and
parses code blocks, not prose against behaviour.

A fourth defect was in `verify_docs.py` itself. Its citation regex ended `(?:-[a-z]+)?`, so an id
whose last segment starts with a capital was cut short at that segment: `R8-B06-Q11` matched only as
far as its `B06` and reported as unknown. Worse, `R7-D04-comments-scope` matched only as far as
`R7-D04-comments` and resolved silently to a *different decision*. Widening the tail to
`(?:-[A-Za-z0-9]+)*` moved the distinct-citation count from 166 to 171 with no new failures.
`R8-B06-Q11` was also a strong decision that had never reached `skill/`; it ships now.

## V4

`validation/v4_quota_reconcile/` is a fresh held-out task, written so that the five new rules have
something to bite on: two report formats carrying different fields, and a size grammar with units so
the parse-or-guess failure has an analogue. Three arms, same context split as V3, no arm saw V3.

`RATING.md` in that directory holds the result. The short version: every defect count fell, the two
residuals are named, and `R9-01` is the weakest test in the round because its worked example in
`SKILL.md` is drawn from a structurally identical problem.

The sharpest single result is that `base` — with no guidance, on a task sharing no domain with the
one that produced the rule — invented `UNATTRIBUTED_TEAM`, gave it `default_quota` and reported it
as a team over quota. That is `R9-01`'s failure mode, reproduced independently. Both guided arms
avoided it, and `skill` generalised the rule to a case nobody wrote down.

## Counter-argument, stated fairly

**This round had one reader, not four agents.** Round 8's method was adversarial and blind. Round 9
is one person reading one program's output and reporting what annoyed them. That finds real defects
— every one here reproduced under measurement — but it has no claim to coverage.

**Four of the five rules were written after seeing the failure they fix.** V4 is the held-out test
and it is one task with one agent per arm. V3 and V4 agreeing is two points, not a trend.

**The prose rewrite is unmeasured.** Cutting 52 instances of the `X, not Y` sentence frame and
restating four circular rules is a judgement about readability with no instrument behind it. The
defect counts test the rules; nothing tests whether the document reads better.

**`skill` and `full` still tie at zero.** Both guided arms score clean on every tool in both rounds,
so nothing mechanical separates them, and the case for `architecture.md` rests on the rating and on
the count of questions the `skill` arm had to invent answers to — 9 on V3, 18 on V4, of which
`architecture.md` answers 10.
