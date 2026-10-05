# Round 10 — comments

Forced choices on `#` comments and their sentence form. Every question is built from a comment Claude
wrote. The resulting rules are `skill/SKILL.md`, **Comments**, and cover docstring prose too
(R10-docstrings); R9-10's rules on what a docstring body contains are unchanged.

| file | contents |
|---|---|
| `harvest.py` | the extractor. It writes `corpus.jsonl` |
| `corpus.jsonl` | one record per comment block, with its source, arm, length and placement |
| `classes.jsonl` | the taxonomy code and verdict of each prose block, from a classifier agent |
| `edits/` | the Python diff of every edit run, against the copy it started from |
| `seeds.md` | comment pairs the user rewrote by hand |
| `questions.md`, `key.md` | the questions, and what each one probes |
| `prototypes/` | three layouts of the rules put to the user. C was chosen (R10-structure) and matches `SKILL.md` |
| `rating.md`, `rating_key.md` | a blind sample of new-skill, old-skill and no-skill comments, and its sources |

## Sources

| source | what | blocks of prose |
|---|---|---|
| `fresh` | every Python file in the validation arms, `experiment/length`, `benchmark/round3` and the tooling, as it stands | 246 |
| `history` | blocks a later commit added to a tooling file that already existed | 24 |
| `edit` | comments and docstrings an edit run added | 10 |

The edit runs reuse the change requests in `validation/harness/changes/`:
- C1–C4 ran on v5 `base` and v6 `base` without the skill, and on v5 `full` with it. C5 ran on each
  arm's own C1 output. Each run is one agent that saw only its own copy and the request.
- Each C1–C4 agent then received one reviewer reversal of a decision it had reported, such as "compare
  skus case-sensitively" or "put the parser back in `billing_csv.py`". The reversal diff is against
  the agent's own pre-reversal copy. Those runs are named `<arm><change>_R`.
- `COMMON.md` asks every run to report what it changed, which may prime changelog voice. It stays,
  because that is the setting the comments are written in.

## Length

Prose blocks only, in words.

| arm | blocks | median | p90 | max |
|---|---|---|---|---|
| `base` (no guidance) | 32 | 6 | 20 | 26 |
| `doc` (V1/V2 style doc) | 22 | 22 | 36 | 37 |
| `skill` | 53 | 18 | 33 | 56 |
| `full` | 42 | 18 | 32 | 37 |
| `narrative` (`experiment/length`) | 27 | 31 | 42 | 45 |
| `round3` | 32 | 20 | 39 | 77 |
| `tooling` | 30 | 28 | 49 | 73 |
| `history` | 24 | 31–42 per commit | | 73 |

**Guidance makes comments longer and more frequent.** Unguided arms write about 0.4 comments per 100
lines at a median of 6 words; guided arms write 1.0–1.3 at 18. Most guided blocks take the shape
"X, so Y" or "X because Y", and the reason clause is where the length is. The skill's rule that a
comment states *why* (R9-02, the rule those arms ran under) asks for exactly that clause.

## Where changelog voice comes from

**Generated code has almost none.** The classifier marks 7 fresh blocks F2a. Two are in round 3
arms: `now lives inside that function` (copied across three variants) and `removes the lock the
threaded version needed`. The other five are in tooling Claude edited across sessions, such as
`` NOT `-q`: ... so a failing file scored zero `` (`validation/prepare_blind.py:85`) and
`... read as a clean arm for three rounds` (`validation/score_arms.py:69`).

**One-shot edits hold none.** The 15 change runs add 10 `#` blocks and none says "now", "no longer" or
"used to". What they add instead is data history, which is legitimate:
`a database written before account_id existed has the table without the column`.

The 12 reversals add no `#` block at all. Where a reversal made a comment false, the agent deleted
it: v6 `base` C1 dropped `str.splitlines() is not used: ...` along with the code it explained.

**Reversals leak the reversed decision without a changelog word (F2b).** After a reviewer reversed
one of its decisions, the agent rewrote the docstring around it, and the new text argues with the old
decision:
- `The comparison is exact and case-sensitive, so Compute-Std and compute-std differ.`
- `Every reported value except account_id goes into the key`
- `ignored_skus, by contrast, matches exactly`

Each one answers the reviewer, not a reader who never saw the review.

**Literal changelog wording (F2a) comes from long sessions.** Every instance with "now", "is not any
more" or "the old X" is in `history`: tooling that Claude edited across many turns with the user.
- `` `raises` was a trigger and is not any more. `` (`7dfdb3e:skill/checks.py:370`)
- `The floor is now 3.11 so tomllib is available` (`skill/verify.py:150`, still in the tree)
- `demanding them is what made the old raises trigger cost 61 lines in a 124-line module`
  (`7dfdb3e:skill/checks.py:331`)

## Taxonomy

| code | name |
|---|---|
| F1 | restates the code |
| F2a | literal changelog: a previous state of the code, or the act of changing it |
| F2b | conversation residue: text that answers a decision just discussed or reversed |
| F3 | justifies style-guide compliance |
| F4 | leaked citation |
| F5 | over-long: more than one idea, or more words than the claim needs |
| F6 | hedged, chatty or rhetorical |
| F7 | non-local claim that nothing checks |
| F8 | argues with an alternative that is not in the file |
| F9 | instruction aimed at a maintainer |
| F10 | oversells: reassures or argues the code is fine where a weakness exists (R10-candor) |
| K1 | block label |
| K2 | a reason the code cannot show: outside constraint, library quirk, data history |
| K4 | field, unit or nullability annotation |
| K5 | test-case annotation |
| K6 | tool directive with prose |
| K7 | TODO / FIXME, and any admitted weakness. Claude writes these about 12 times less often than human developers. |

F9 was left open for the questions. R10-Q12 dropped a maintainer instruction (weakly), and R10-Q15 bans speculating about what another team will do.

### Counts

A classifier agent coded every prose block and every `history` and `edit` docstring: 434 records.
A record can carry several codes. It was told the user finds most of Claude's comments too long, so
its verdicts lean strict. Its verdicts are not decisions; the questions are.

| code | fresh | history | edit |
|---|---|---|---|
| F1 restates | 26 | 11 | 4 |
| F2a changelog | 7 | 10 | 0 |
| F2b residue | 10 | 16 | 5 |
| F3 style justification | 34 | 0 | 1 |
| F4 citation | 6 | 9 | 0 |
| F5 over-long | 69 | 39 | 4 |
| F6 hedged or chatty | 21 | 13 | 2 |
| F7 non-local | 31 | 7 | 18 |
| F8 absent alternative | 29 | 14 | 4 |
| F9 maintainer instruction | 6 | 4 | 0 |
| K1 block label | 28 | 5 | 1 |
| K2 reason the code cannot show | 152 | 29 | 34 |
| K4 annotation | 18 | 0 | 10 |
| K5 test case | 8 | 0 | 0 |

| verdict | fresh | history | edit |
|---|---|---|---|
| keep | 110 | 13 | 106 |
| trim | 90 | 47 | 14 |
| cut | 46 | 6 | 2 |

**Most fixes are trims of a real reason, not deletions.** Of the 90 fresh blocks marked trim, 74
carry a real reason (K2), and 42 of the 69 over-long blocks do too. Most of the time the comment
should exist and is written too long.

Re-run the extraction with:

    $ python3 benchmark/round10/harvest.py --edits <directory of edit runs>

## Claudish: Claude's comments against human ones

`sessions` is a fourth source, kept outside the repository because it contains the user's private code:
every comment line Claude added through Edit, Write or MultiEdit across the user's Claude Code
transcripts, 29 projects. Only tool inputs were read. The baseline is professional, almost entirely
pre-LLM Python: the CPython 3.14 standard library (without `encodings/` and `idlelib/`) and the mypy,
pylint and astroid sources.

Rates are per 100 comment blocks. `Claude #` is Python, shell and config files only. `Claude all`
adds `//` languages, mostly Java and TypeScript.

| feature | Claude # | Claude all | human | ratio |
|---|---|---|---|---|
| blocks | 2,578 | 6,305 | 22,891 | |
| median words | 24 | 31 | 9 | |
| p90 words | 83 | 101 | 29 | |
| blocks of more than one sentence | 45% | 56% | 15% | 3.1 |
| `, not` contrast | 10.7 | 10.0 | 0.4 | 24 |
| dash (` -- ` or `—`) | 23.9 | 34.4 | 1.0 | 23 |
| absolutes: every, never, whole, exactly | 31.1 | 46.5 | 1.6 | 19 |
| `the one` / `one place` | 2.2 | 2.8 | 0.1 | 18 |
| deliberately, on purpose, by design | 2.1 | 3.1 | 0.1 | 17 |
| `rather than` / `instead of` | 18.2 | 21.4 | 1.1 | 16 |
| `, so` joining clauses | 32.9 | 42.3 | 3.3 | 10 |
| semicolon | 18.5 | 27.5 | 2.5 | 7 |
| agentive verb: finds, knows, wants, sees, asks, decides, owns | 2.3 | 4.9 | 0.3 | 7 |
| container verb: holds, carries, lives, keeps, names, states | 11.3 | 13.1 | 2.0 | 6 |
| intensifier: genuine, real, actually, really, truly | 8.3 | 11.2 | 1.5 | 6 |
| article before a backticked identifier | 2.8 | 1.3 | 0.6 | 5 |
| `because` | 9.2 | 10.2 | 2.4 | 4 |
| passive (`is`/`are`/`was`/`be` + `-ed`) | 26.0 | 35.5 | 14.7 | 1.8 |
| changelog: now, no longer, used to, the old | 2.9 | 4.9 | 2.7 | 1.1 |
| hedge: usually, likely, probably, might, seems | 0.3 | 0.5 | 2.4 | 0.1 |
| first person: we, our, us, I | 2.0 | 3.6 | 22.8 | 0.1 |
| TODO, NOTE, FIXME, XXX, HACK | 0.1 | 0.1 | 3.7 | 0.03 |

The same features after round 10, per 100 comment blocks, with 95% intervals in brackets: Wilson
intervals for rates, and intervals from binomial order statistics for the word-count percentiles.
`human` is recomputed from the same sources (21,977 blocks against 22,891; first person comes out at
16.4 against 22.8, the other rows within 0.4). `Claude, no skill` is `Claude #` above, with its
interval derived from the published rate and block count, because the transcripts are private.
`this skill, cycles 7 to 13` is every `#` comment block in the review files of those cycles
(`cycles/`). `cycle 13` is ten runs of `skill/` as shipped, one per task P1 to P10. The semicolon
rows before cycle 12 predate R10-no-semicolon. `cycles/claudish_table.py` recomputes the table.

| feature | Claude, no skill | human | this skill, cycles 7 to 13 | cycle 13 |
|---|---|---|---|---|
| blocks | 2,578 | 21,977 | 185 | 84 |
| median words | 24 | 9 [9, 9] | 11 [10, 11] | 11 [10, 11] |
| p90 words | 83 | 29 [28, 29] | 17 [15, 20] | 17 [15, 20] |
| blocks of more than one sentence (%) | 45.0 [43.1, 46.9] | 14.8 [14.3, 15.3] | 4.3 [2.2, 8.3] | 8.3 [4.1, 16.2] |
| `, not` contrast | 10.7 [9.6, 12.0] | 0.4 [0.4, 0.5] | 0.5 [0.1, 3.0] | 1.2 [0.2, 6.4] |
| dash (` -- ` or `—`) | 23.9 [22.3, 25.6] | 1.0 [0.8, 1.1] | 0.0 [0.0, 2.0] | 0.0 [0.0, 4.4] |
| absolutes: every, never, whole, exactly | 31.1 [29.4, 32.9] | 1.5 [1.4, 1.7] | 7.0 [4.2, 11.7] | 6.0 [2.6, 13.2] |
| `the one` / `one place` | 2.2 [1.7, 2.9] | 0.1 [0.1, 0.2] | 0.5 [0.1, 3.0] | 1.2 [0.2, 6.4] |
| deliberately, on purpose, by design | 2.1 [1.6, 2.7] | 0.1 [0.0, 0.1] | 0.0 [0.0, 2.0] | 0.0 [0.0, 4.4] |
| `rather than` / `instead of` | 18.2 [16.8, 19.7] | 1.1 [0.9, 1.2] | 0.0 [0.0, 2.0] | 0.0 [0.0, 4.4] |
| `, so` joining clauses | 32.9 [31.1, 34.7] | 2.9 [2.7, 3.1] | 14.6 [10.2, 20.4] | 14.3 [8.4, 23.3] |
| semicolon | 18.5 [17.1, 20.0] | 2.3 [2.1, 2.5] | 3.2 [1.5, 6.9] | 0.0 [0.0, 4.4] |
| agentive verb: finds, knows, wants, sees, asks, decides, owns | 2.3 [1.8, 2.9] | 0.3 [0.2, 0.4] | 0.0 [0.0, 2.0] | 0.0 [0.0, 4.4] |
| container verb: holds, carries, lives, keeps, names, states | 11.3 [10.1, 12.6] | 1.8 [1.7, 2.0] | 1.6 [0.6, 4.7] | 0.0 [0.0, 4.4] |
| intensifier: genuine, real, actually, really, truly | 8.3 [7.3, 9.4] | 1.4 [1.3, 1.6] | 0.5 [0.1, 3.0] | 0.0 [0.0, 4.4] |
| article before a backticked identifier | 2.8 [2.2, 3.5] | 0.5 [0.4, 0.6] | 0.0 [0.0, 2.0] | 0.0 [0.0, 4.4] |
| `because` | 9.2 [8.1, 10.4] | 2.3 [2.1, 2.5] | 0.5 [0.1, 3.0] | 1.2 [0.2, 6.4] |
| passive (`is`/`are`/`was`/`be` + `-ed`) | 26.0 [24.3, 27.7] | 12.5 [12.0, 12.9] | 4.9 [2.6, 9.0] | 8.3 [4.1, 16.2] |
| changelog: now, no longer, used to, the old | 2.9 [2.3, 3.6] | 2.4 [2.2, 2.6] | 0.5 [0.1, 3.0] | 0.0 [0.0, 4.4] |
| hedge: usually, likely, probably, might, seems | 0.3 [0.2, 0.6] | 2.0 [1.8, 2.2] | 0.0 [0.0, 2.0] | 0.0 [0.0, 4.4] |
| first person: we, our, us, I | 2.0 [1.5, 2.6] | 16.4 [15.9, 16.9] | 0.0 [0.0, 2.0] | 0.0 [0.0, 4.4] |
| TODO, NOTE, FIXME, XXX, HACK | 0.1 [0.0, 0.3] | 3.6 [3.3, 3.8] | 0.0 [0.0, 2.0] | 0.0 [0.0, 4.4] |
| possessive `own` |  | 0.2 [0.2, 0.3] | 0.5 [0.1, 3.0] | 0.0 [0.0, 4.4] |

**Words and pairs Claude overuses most**, by Dunning log-likelihood: `rather than`, `so the`,
`is the`, `is what`, `its own`, `which is`, `reads as`, `the whole`, `what makes`, `does not`,
`nothing`, `against`, `every`, `own`, `per`.

**Words and pairs Claude underuses most**: `we`, `if`, `need to`, `will`, `should`, `don't`,
`it's`, `to avoid`, `make sure`, `in case`, `note that`, `todo`, `if the`, `so we`.

What the two lists show:
- **Claude writes argument.** Its comments are full declarative sentences that assert, contrast and
  conclude: `X, not Y`, `X rather than Y`, `X, so Y`, `the one place`, `every`, `never`,
  `deliberately`.
- **Human developers write working notes.** Their comments are short fragments that state a
  condition or a purpose and talk to a colleague: `if the`, `need to`, `to avoid`, `in case`, `we`,
  `don't`, `TODO`.
- **Claude never hedges, never contracts and never says `we`.** Seed pair 2 adds the human features
  back: a `NOTE:` marker, a contraction, an imperative, and one clause of reason.
- **Claude almost never admits a weakness.** TODO, FIXME, XXX, `known limitation`, `workaround`,
  `untested` or `approximate` appear in 0.3% of its blocks and 3.7% of human ones. Its certainty
  claims (`always`, `never`, `cannot`, `impossible`) run at 2.7 times the human rate. The user rules
  that a known weakness is stated, as a TODO naming the fix, rather than justified (R10-candor).
- **Literal changelog wording is not the distinguishing feature.** Its rate is about the human one.
  Claude is distinguished by the contrastive argument around a change, which is F2b and F8.

Caveat: some of the session projects loaded the Narrative skill or a style instruction, so part of
the `Claude` column is guided output. The fresh-arm numbers above separate guided from unguided
writing for this repository's tasks.

## Trial: procedural against priority framing

Prototype C opens its steps with "Before writing a comment, in order:". The user asked whether that
framing makes an agent walk the four steps aloud for every comment. Two copies of the skill differed
only in that framing: `procedural` (C as accepted) and `priority` (the same items as an "Order of
preference" list). A third copy, `current`, is the skill as it stands. Each ran change requests C2 and
C4 on v5 `full`, one fresh agent per cell, with no mention of comments in the prompt.

| arm | C2 tokens, tools, time | C4 tokens, tools, time | step mentions in the agent's text |
|---|---|---|---|
| current | 116k, 21, 192 s | 111k, 21, 172 s | 0 |
| procedural | 119k, 20, 202 s | 107k, 20, 159 s | 0 |
| priority | 130k, 27, 271 s | 109k, 17, 148 s | 0 |

New `#` comments, excluding a comment all three C2 arms edited in place:

| arm | comment |
|---|---|
| current C2 | `A database written before sku_mismatch existed has no scanned_sku column.` |
| current C4 | `Last, where ALTER TABLE puts it in a database from before the column existed.` |
| current C4 | `CREATE TABLE IF NOT EXISTS leaves a table from an earlier version without the column.` |
| procedural C2 | `databases written before 2026/10/01 lack the scanned_sku column` |
| procedural C4 | `databases written before 2026/10/01 lack the account_id column` |
| priority C2 | `databases written before 2026/10/01 lack the scanned_sku column` |
| priority C4 | `databases written before 2026/10/01 lack the account_id column, and their rows keep it NULL` |

- **No arm narrated the steps.** Mentions of the step names or the R10-Q25 test in the agents' text
  and reasoning: 0 in every cell. Cost differences sit within run-to-run spread.
- **Both C arms wrote the dated data-history form** that R10-Q23 asked for, lowercase without a
  period. The `current` arm wrote undated history in sentence case, and two of its three comments
  give code an agent verb (`leaves`, `puts`).
- **The trial is small.** One agent per cell, and these change requests call for one or two
  comments each. It shows the framing costs nothing measurable. It cannot rank the two C framings,
  and the transcripts may not hold all of an agent's reasoning.

## Validation of the shipped rules

The **Comments** section went into `skill/SKILL.md` with `NAR012` to `NAR015` in `checks.py`. The
validation agents read a copy taken before `R10-skill-gaps`, so it lacked the extension of the steps
to rewording and the verb principle.

Fresh write of V6 (`validation/v6_report_contract/TASK.md`), one agent per arm:

| arm | `#` comments | per 100 lines | median words | docstring words |
|---|---|---|---|---|
| no skill (`base`) | 4 | 0.29 | 14.5 | 2,280 |
| old skill (`full`) | 7 | 0.53 | 17 | 2,225 |
| new skill | 2 | 0.18 | 10 | 1,158 |

The new skill's two comments: `read-only: NEVER write inside the input directory` and
`input_dir_argument stays a str: a Path would normalise what the command line typed`.

**Docstrings changed too, without a rule.** Per 1,000 docstring words, the new skill against the old:
`rather than` 0.0 against 1.3, `, not` 0.0 against 0.9, `, so` 2.6 against 6.3, absolutes 6.0
against 13.5, agent and container verbs 5.2 against 11.2.

**The agent-verb fault persisted in edits.** C3 on v5 `full` under the new skill wrote `its billing
lines leave the report too. A billing line names no team, so it takes the team of the scanned
resource`, and its reversal wrote `a billing line names no team, so no rule ignores it on its own
evidence`. The list of example verbs in that copy did not hold `leave`, `names`, `takes` or `ignores`,
which is the gap `R10-skill-gaps` addresses.

**Reversal residue moved into docstrings.** The C1 reversal (don't strip ledger fields) added no `#`
comment, and added `A value between tabs is taken exactly as written, with no trimming.` to a module
docstring. The skill copy these agents read applied the rules to `#` comments only; R10-docstrings extends them to docstrings.

`rating.md` is a blind sample of 15 comments from the three sources; `rating_key.md` gives each item's source.

## Blind rating

The user rated `rating.md` without the key (R10-rating):

| source | keep | trim | cut |
|---|---|---|---|
| new skill | 2 | 1 | 3 |
| old skill | 0 | 1 | 5 |
| no skill | 0 | 0 | 3 |

Two of the three cut new-skill comments came from edit runs on the copy without R10-skill-gaps, and
give code an agent verb. The third, `input_dir_argument stays a str: a Path would normalise what the
command line typed`, is a valid topic, an architecture decision, cut as too inconsequential. The
user's overall verdict: most comments at this scale restate the code.

## Kinds against lists

Two copies of the current skill differed only in the **Comments** section: `kinds` (four comment
kinds with a test each, and a never list) and `lists` (the valid and invalid topic lists). Each ran
the V6 fresh write, C1 and C3 on v5 `full`, and one reviewer reversal per edit.

| version | V6 comments | per 100 lines | median words | edit comments |
|---|---|---|---|---|
| kinds | 8 | 0.70 | 11 | 1 |
| lists | 3 | 0.27 | 13 | 3 |

The kinds V6 run wrote more comments, including `bool is an int subclass, so JSON true would pass
the int check`, close to one the user cut in the first blind rating. Both versions wrote `billing
lines name no team` in an edit, a container verb outside the rule's example list. Neither wrote a
TODO for an edge case its agent reported as unhandled. One run per cell; `rating2.md` is the blind
sample, `rating2_key.md` its sources.

Rating 2 (R10-rating2): kinds 1 keep, 1 trim, 7 cut; lists 3 keep, 3 cut. Most cut comments
restate the code in compliant style. The kinds tests gave the writing agent categories to place a
restatement in (a simple regex as a decoding aid, `bool is an int subclass` as a source fact).

## Instruction cycles

The user's direction (R10-instruction-design): a failed instruction means the instruction is not
good enough, so design better instructions before choosing between layouts. Each cycle adds short
stance paragraphs to the shipped skill, all with the restatement gate (R10-restatement-gate), and runs
the V6 fresh write twice per variant.

**Where the comments come from.** 9 of the 11 comments in the kinds and lists V6 runs repeat an item
from the agent's own report of decisions where the spec was silent or edge cases it tested: one-hop
aliases, a boolean `grace_cents`, digit-only cents, NULLs in a SQLite unique key, writing inside the
input directory. The user's word for them: thinking traces.

### Cycle 1

| variant | stance added | comments per run |
|---|---|---|
| G | the gate alone | 4, 4 |
| R | redirect: decisions go in the report, edge cases in tests, behaviour in names | 6, 1 |
| S | authorship: the lines you reasoned about feel like they need explaining | 5, 13 |
| RS | both | 3, 4 |

No variant separates from the run-to-run spread. The same comments recur whatever the stance:
`bool subclasses int` in 7 of 8 runs, `read-only: NEVER write inside the input directory` in 5,
one-hop aliases in 4.

### The judge

Five judge prompts tried to reproduce the user's keep/cut line on the 30 rated comments (R10-F02,
R10-F03): rubric 20 of 30, rubric with examples 21, predict-then-compare 19, content questions 21,
against a base rate of 21. Reader-intelligence framing moved errors between directions without
reducing them; the content questions kept every comment the user kept. The refined content-question
judge, scored before the user rated R10-rating3, reached 10 of 18 against a base rate of 11
(R10-F04). Its main error came from a clause generalised from two labels ('cut gotcha guards'),
which the user's reversal on `bool subclasses int` refuted. User ratings remain the measure.

### Cycle 2

Variants, each added after `These rules cover docstring prose too.` with the gate:

- **T**: "**Comments are not thinking traces.** While writing, you reasoned through edge cases,
  alternatives and spec gaps. That reasoning is a thinking trace: it belongs in your report to the
  user, not in the code."
- **Q**: "**A reader arrives at one line with one question.** A comment answers a question a reader
  would ask at that exact line, and sits on that line. If no reader would ask, write nothing. If a
  better name would answer it, rename instead."
- **TQ**: both. **G**: the gate alone, as control.

Measure per variant: comments per run, placement errors (a comment away from the line it concerns,
R10-locality), then a blind user rating of the distinct comments.

| variant | comments per run | placement errors per run |
|---|---|---|
| G | 7, 7 | 4, 0 |
| T | 7, 6 | 0, 0 |
| Q | 8, 4 | 0, 0 |
| TQ | 2, 4 | 1, 1 |

Comments are counted as blocks, without `###` dividers or pragmas; the same count gives cycle 1's
table. Cycle 2's G differs from cycle 1's G only in the block-label bullet (R10-block-label-size)
and wrote 7 and 7 against 4 and 4, so the spread between runs of one skill is at least 3.
TQ's 2 and 4 fall inside that spread. A placement error here is a comment at the top of a function
body or above an initialisation block when it concerns a later statement; four of the six state
the function's return contract (`# a returned str is the problem that rejects the row`).

Recurring families: `bool subclasses int` in 8 of 8 runs, `read-only: NEVER write inside the input
directory` in 6, one-hop aliases and non-ASCII digits in 4 each, enum member order and the
input_dir echoed as typed in 3 each. Ten comments from families no earlier rating settled are in
`rating4.md`, with the variants in `rating4_key.md`.

The user rated those ten (R10-rating4). Applying the verdicts of R10-rating3 and R10-rating4 to
every cycle 2 comment by family:

| variant | comments | kept or trimmed | cut |
|---|---|---|---|
| G | 14 | 7 | 7 |
| T | 13 | 13 | 0 |
| Q | 12 | 12 | 0 |
| TQ | 6 | 5 | 1 |

Each family verdict comes from one comment in one context. G_1's cuts are three return contracts at
the top of a function body and an unclear summary (`for its side`); G_2's are end-of-line notes on a
dataclass field and a NewType, and a container verb (`a value the finding does not carry`). T and Q wrote about as many comments as G and none of the cut kinds. TQ wrote fewer, and
TQ_1 left out the read-only rule the other variants wrote in 6 of 8 runs.

### Cycle 3

Two more runs each of G, T and Q with the cycle 2 skills unchanged.

| variant | comments per run | cut by family verdict | not yet rated |
|---|---|---|---|
| G | 8, 6 | 3, 0 | 2, 0 |
| T | 2, 3 | 0, 0 | 0, 0 |
| Q | 8, 4 | 0, 1 | 2, 0 |

G_3's cuts are two return contracts at the top of a function body and `JSON object keys are always
strings` (R10-rating3). Q_4's is a NewType note (`a basename, the form the report names a file by`),
the family cut in R10-rating3. The four comments not yet rated are in `rating5.md`, with the
variants in `rating5_key.md`.

The user rated them (R10-rating5): G_3 one kept, one cut; Q_3 one cut, one to replace with a rename.
Cycles 2 and 3 together, four runs per variant:

| variant | comments | cut or replaced by a rename |
|---|---|---|
| G | 28 | 11 |
| T | 18 | 0 |
| Q | 24 | 3 |

### Cycle 4

Two runs of the folded draft `prototypes/D_cleaned.md`, which drops the Reader paragraph, the Test
line and the Never list, moving their content into the thinking-trace paragraph, the gate and a
Placement list.

| run | comments | cut by family verdict | not yet rated |
|---|---|---|---|
| D_1 | 5 | 1 | 1 |
| D_2 | 10 | 5 | 1 |

D_2's cuts are two return contracts, `adds each accepted record to billing_lines or
scanned_resources`, `list before reading the rules` (R10-rating3) and `the keys of a JSON object are
always strings` (R10-rating3). Against T's 0 of 18, the user restored the tested section and dropped
only the Reader paragraph's domain question (R10-cleanup). Both runs wrote the Fence form `needs the
bool test: JSON true is a Python int` (R10-fence-consequence). The two unrated comments, an
end-of-line note on `connection.total_changes` and `each raise site logged its reason` above an
except clause that doesn't log, were hard to judge without more context.

### Cycle 5

Two V6 runs of the shipped section, with R10-fence-form, R10-footgun and R10-worked-example: 6 and 7
comments. Six of the 13 copy SKILL.md examples word for word (`isdigit() alone admits non-ASCII
digits such as '²'`, `without the bool test, JSON true passes as 1`, `read_text() would translate
newlines, …`, the last now inside the `try`), because those examples came from this task. The user
rated the set fine (R10-rating7) and asked for a task the examples were not drawn from. The worked
example in one run now matches the code: `with a->b and b->c, a resolves to b and b to c, so a
matches neither`.

### Cycle 6

Task P1, timesheet to payroll (spec, fixture and expected result in `tasks/P1/`): punches
across a daylight saving change, weeks in local time, a shift length halfway between rounding steps
(where `round()` rounds to even), and a half-cent gross pay (where `Decimal.quantize()` defaults to
half-even). None of these appears among the SKILL.md examples. Two runs of the shipped section.

Both runs computed the fixture correctly (11 shifts, 1 duplicate, 4 problems, 1740.27). The user
kept 17 of their 20 comments (R10-rating8); three reuse SKILL.md example wording where the
situation recurs. The review also produced six rules outside the comment rules, listed in
`proposals_payroll.md`: R10-raw-names, R10-path-type, R10-money-cents, R10-pendulum, R10-uv and the
container-verb check `NAR016` (R10-nar016).

### Cycle 7

Task P2, subscription invoices (spec, fixture and expected result in `tasks/P2/`): proration
over a month in each customer's time zone, where March 2028 is an hour short in US zones; a tax of
exactly half a cent; resent and out-of-order events. Two runs of the skill with the six rules from
R10-rating8. Both billed the fixture correctly (65.14, 4 problems), and both used pendulum, integer
cents with `Fraction`, `raw_` names and a `str` path only for the echoed input directory; neither
wrote a container verb. Run 1 wrote 14 comments, nine of them end-of-line notes on dataclass fields;
run 2 wrote 4. The user found most fine (R10-rating9). One placement error recurred: a comment on
the `tz=None` argument sat below the `try` block instead of above the call.

### Cycle 8

Task P3, snapshot pruner (spec, fixture and expected result in `tasks/P3/`): retention periods
in local time, an hour repeated on the night of 2028-11-05, a snapshot whose UTC date differs from
its local date, and a symbolic link with a snapshot name. Two runs of the skill with R10-conclusion,
R10-intensifiers, R10-clipped-terms and R10-argument-placement. Both produced the expected plan
(6 kept, 7 deleted, 2 problems). Both put the `tz=None` comment above the call that passes it. Of 17
comments the user faulted 4 (R10-rating10); two of the four used agent verbs the written rule bans
(`policy files … name one policy`, `a period ranks`).

### Cycle 9

Task P4, dependency license audit (`tasks/P4/`): PEP 503 names, SPDX precedence, case-insensitive
ids, an exception on its last day. Two runs of a skill copy in which `verify.py` lists every comment
and docstring summary after a passing run, and SKILL.md tells the agent to read the list against
**Sentence form** (the listing is `skill/checks.py --prose`). Both audits were correct. Agent verbs fell
from about 8 in 136 lines (cycles 7-8) to 2 in 78 (R10-prose-inventory). The two left are what the
parser-based check (`skill/agentverbs.py`, R10-agentverb-check) catches.

Review files with the code around each comment, numbered as the user rated them, are in `cycles/`;
`cycles/review.py` builds them, `cycles/comments.py` counts comment blocks, and
`cycles/claudish_table.py` recomputes the feature table of the Claudish section.

### Cycle 10

Task P5, configuration layer audit (`tasks/P5/`): version comparison where `1.9.0` sorts after
`1.10.0` as a string, `true == 1` and `25 == 25.0` in Python, arrays that replace, an environment
that skips a layer. Two runs of a skill copy in which `verify.py` runs the agent-verb check as a
seventh check and lists every comment and docstring summary after a passing run
(`agentverb/cycle10_skill.patch`). Both audits were correct (13 errors, 3 warnings), and neither run
silenced the check with `noqa`. Of 48 comment and docstring lines, one agent verb remained (`every
file the audit needs`); the check now catches that form. Each run wrote 4 comments
(`cycles/cycle10_review.md`).

### Cycle 11

Task P6, chess game replayer with no chess library (`tasks/P6/`): castling through an attacked
square, en passant one move late, a pinned knight that removes the need to disambiguate, a
threefold repetition that counts only once castling rights match, the fifty-move rule from a FEN
start. Expected results computed with python-chess. Two runs of a skill copy with `NAR018`, the
pendulum boundary rule, the agent-verb check and the comment listing
(`agentverb/cycle11_skill.patch`). Both replayed all 13 games correctly, and both checked their move
generators against published perft counts. Both found that the stalemate game started from an
illegal position (`k7/8/2Q5/…` with Black in check); the fixture now starts it from
`k7/8/8/2Q5/…`. Of 69 comment and docstring lines, two agent verbs remained, neither silenced with
`noqa` (`the Move it names`, `what a SAN without suffixes states`); the check now catches the
first. Review file: `cycles/cycle11_review.md`.

### Cycle 12

Task P7, MIDI file analyser with no MIDI library (`tasks/P7/`): running status across a meta event,
a tempo map in the first track of a format 1 file, a tempo change during a note, a retriggered
pitch, a note on placed before a same-tick note off, a hanging note, SMPTE time and a truncated
file. Expected results computed with mido. Two runs of `skill/` as shipped, with the Depth rule of
R10-depth-sentences, the semicolon ban (R10-no-semicolon), `NAR017` and the comment listing. Both
runs matched every expected value. They wrote 14 `#` comments (6 and 8). One is two sentences, and
it restates the variable-length quantity encoding from the task spec. No comment has a semicolon
or a dash, and `agentverbs.py` passed both runs with no `noqa`. The MIDI facts (velocity 0, channel
10, running status) went into module docstrings. Review file: `cycles/cycle12_review.md`. The user
kept all 14 comments, with one wording nitpick: `for time signatures on one tick`, not `of`
(R10-rating13).

### Cycle 13

Ten runs of `skill/` as shipped (after R10-pydantic and R10-orm-validation), one per task. P1 to P7
are the earlier batch tasks. Three tasks of other shapes were added:
- P8 (`tasks/P8/`): an asyncio server for a subset of the memcached text protocol, with expiry and
  LRU eviction.
- P9 (`tasks/P9/`): a terminal text-wrapping library with no command line, counting display
  columns.
- P10 (`tasks/P10/`): a change request (key signatures, a tempo range, a channel filter) against
  the cycle 12 MIDI package.

All ten matched every expected value: P8 replayed `session.txt` with no mismatch, and P9 passed all 20
fixture cases. P2 and P8 wrote no tests. Three runs wrote a file outside their own directory and
deleted it. The runs wrote 84 `#` comment blocks (P10: the 4 it added). 7 are two sentences, against
0 of 28 in cycles 10 and 11, but 4 of the 7 are the `logging.NullHandler()` example of **Depth**,
copied word for word. No comment has a semicolon, a dash or an agent verb, and no run silenced
`NAR017`. Review file: `cycles/cycle13_review.md`.


### Cleanup cycle

Three comment-heavy scripts of gtnh-determinism, written by Claude without the skill
(`seedsearch/loot-csv.py`, `seedsearch/chest-attribution.py`, `scripts/diff-chests.py`), each
cleaned up twice: with the skill before R10-cleanup-rewrite and R10-subject-verb, and with them.
All six reproduced the original's output on their own test inputs. Opening sentences of the
comment and docstring blocks: the originals had no fragment, and each arm had 2 of about 40, all
labels on fields (`chunk x and z`, `in chunks, None for no limit`). Neither arm triggered `NAR020`,
so these files do not reproduce the 15% of predicate fragments in GT5-Unofficial PR 6, a Java
cleanup. Review file: `cycles/cleanup_review.md`.

### Same-session cleanup cycle

Tasks P3, P5 and P8, each written by one agent without the skill, then cleaned up by the same agent in
the same conversation with the skill: three agents with the skill before R10-cleanup-rewrite and
R10-subject-verb, three with it. All six kept the fixture output. Opening sentences of the comment
and docstring blocks, by the classifier of the cleanup cycle:

| | blocks | clause | label | imperative | fronted | `NAR020` |
|---|---|---|---|---|---|---|
| old skill, phase 1 | 53 | 55% | 9% | 26% | 5 | 0 |
| old skill, cleaned | 66 | 38% | 8% | 50% | 3 | 0 |
| new skill, phase 1 | 72 | 57% | 21% | 17% | 4 | 0 |
| new skill, cleaned | 74 | 35% | 9% | 46% | 7 | 0 |

Read by hand, one of the cleaned "fronted" blocks has its subject cut (`# dotted, such as
'flags.search_v2.rollout'`, a trailing comment on a type alias). The rest are labels or open with a
`without X,` clause. The same-session workflow did not reproduce the fragments of GT5-Unofficial PR 6
either.

The cleanups converged on one comment form instead. Of the 44 `#` comments the cleanups added or
changed, 14 open with `without` and 15 contain `would`, and 27 (61%) have one or the other. Four of
the six runs wrote the same bool fence: `# without the bool test, JSON true passes as 1`. The rates
are 30% in cycle 13 (written with the skill) and 16% in the fresh-agent cleanup cycle. By arm: 14 of
19 old, 13 of 25 new.

Both P8 cleanups moved the connection handlers into one `asyncio.TaskGroup`, after the skill's
3.11 bullet. An unexpected exception in one handler then cancels every other connection and stops
the server. Before the cleanup, `asyncio.start_server` ran each handler as its own task, and the
exception ended that connection only.

Review file: `cycles/samesession_review.md`.

### New-rules cycle

P3, P5 and P8, each written by one agent with the skill at commit a3d2346 (R10-fence-fact,
R10-period-join, R10-we, R10-reason-order and the rule pass over the skill's own text). All three
passed their fixture and `verify.py`. They wrote 35 `#` comments: 27 full-line, 8 trailing labels on
fields. None opens with `without` or contains `would`, and none joins clauses with `, which`,
`, since` or `, so`. Twelve take the form of a fact, then a command: `is_file() follows symbolic
links. Check is_symlink() too`. Three repeat the skill's bool example nearly word for word
(`bool subclasses int. Reject it too`, `… Test it first`). Review file: `cycles/newrules_review.md`.

## Open

- Kinds against lists (R10-instruction-design): the cycles ran with kinds plus the gate and T
  (R10-stance), and lists were not retested with them.
- The developer-action half of R10-fence-consequence: what a warning such as `# order matters: a
  repeated resource_id is accepted from the first file only` should tell the reader.
- The shipped section adds lines no cycle tested in it: the Fence sentence (R10-fence-consequence),
  the return-contract bullet (R10-return-contract), the Fence form and try placement
  (R10-fence-form), the footgun rule (R10-footgun) and the worked-example rule
  (R10-worked-example). Cycle 4 ran the first two inside the folded draft; cycles 5 and 6 ran the
  shipped section. Cycle 7 ran the six rules from R10-rating8.
- R10-rating6 judged the wording of the 18 comments from the T runs; the user rated their style
  poorly overall.
- An unconfirmed generalisation in **Sentence form**: "drop articles where nothing is lost" (one
  rewrite, R10-seed-10). "One step of reason" in **Depth** is replaced (R10-depth-sentences).
- What the user keeps, from R10-rating3 to R10-rating5 and R10-F03: outside facts, rules for future
  changers, facts not visible from the comment's position, gotcha guards the reader does not already
  know (R10-audience), and a one-line summary above a dense comprehension.
- The agent-verb check (R10-agentverb-check, `NAR017`) is `skill/agentverbs.py`. It reads spaCy's
  `en_core_web_md` parse and two word lists that `agentverb/build_words.py` derives from WordNet 3.0
  (`skill/words.json`, with WordNet's license), so it needs no NLTK at run time. spaCy 3.8.16 and
  the model 3.8.0 are pinned in `skill/requirements-lock.txt`, and `verify.py` exits 2 when the lint
  venv cannot import them. Scores: on the hand-labelled lines of cycles 7 to 11 (`agentverb/gold.tsv`,
  tuned on), 29 of 32 agent verbs found and no false flags; on 40 sampled flags from the round 10
  Claude corpus, about 35 correct; on 1,500 CPython stdlib comments, 33 flagged, about two thirds
  personification humans write too ('socket knows', 'an algorithm wants'). Its misses: a plural
  subject before a relative clause (`policy files that differ … name one policy`) and a
  prepositional phrase between subject and verb (`a SAN without suffixes states`). Its false flags:
  participles after a quantifier (`one denied id`), noun compounds (`the rules file`). It skips a docstring
  line indented past the body, a pasted sample, unless it is an entry under a section header such as
  `Returns:`. Before that, in cycle 13, a sample summary line (`4/4  C minor  3 notes`) read as `C
  notes`, and the P10 run moved the key signature to the end of its summary line to clear it. It reads a
  run of whole-line comments at one column, or a docstring paragraph, as one passage. Checked line
  by line, it missed a sentence wrapped between its subject and its verb: `the mongo image` at the
  end of one line and `declares` at the start of the next, in a Python docstring from a work repo.
- The comment listing (R10-prose-inventory) is `checks.py --prose`, which `verify.py` prints after a
  passing run.
- The task specs P1 to P4 are reworded so the agent-verb check flags only its two known false
  flags in them. Earlier runs copied the old wording (`a retention policy keeps`) into docstrings.
- The cycle packages are not kept; the review files in `cycles/` have every comment with its code.
