# Python style preference benchmark

Instrument for deriving a `narrative` skill family from measured taste rather than guesses.

Target is **"the best possible way to write code with infinite time and effort"**, not how the
author currently writes. The existing corpus, an unpublished Python project, is contrast material
only — it contradicts the written style doc on six of its own rules.

## Layout

```
round1/questions.md      24 forced-choice snippets, blind
round1/key.md            what each probes; do not read before answering
round2b/                 side-by-side comparisons that settled specific rules
round3/p1_scan_ingest/   three architectures for one batch-ingest CLI
round3/p2_device_driver/ three ways to hold state in one instrument driver
round4/                  five comparisons that settled the reported gaps
round5/                  two measured rule revisions: NAR005 depth, NAR008 data literals
round7/questions.md      41 forced-choice architecture snippets, blind
round7/key.md            what each probes; do not read before answering
round8/                  red team: 35 defects from four fresh-context agents, plus the NAR008 measurement
validation/              two held-out tasks for the blind skill-vs-doc comparison
decisions.jsonl          the evidence base, one answer per line
```

Rounds 2 and 6 have no directory. Both ran in conversation against the code in front of them, and
their answers are in `decisions.jsonl` under `R2-*` and `R6-*`. A round earns a directory when it
produces material a later reader must see to judge the answer.

## Protocol

1. **Round 1** — 24 snippets, delivered as terminal prompts. Four are controls whose answer is
   already in the style doc. If a control does not reproduce the doc, stop: the instrument is
   broken and nothing else in the run is trustworthy.

2. **Round 2** — adaptive follow-ups, generated only where Round 1 returned "depends",
   contradicted the corpus, or implied an unasked question. Testing gets its own block here: the
   corpus has zero tests, so there is no prior at all.

3. **Round 3** — read the two programs in an editor, rank the variants, then for each problem name
   *three things you would change in your top pick and one thing you would steal from each of the
   others*. The annotations are the highest-signal data in the exercise. The ranking alone only
   produces preferences. The annotations produce rules.

4. **Round 4** — five side-by-side comparisons, each built from a real program, that settled the
   gaps the validation agents reported. Prose descriptions of these gaps produced no decision. Real
   code produced one in a single pass every time.

5. **Round 5** — rules revised from what writing real programs against the skill exposed.

6. **Round 6** — twelve decisions taken against the shipped toolchain: the ORM ban scope, version
   pinning, three checker thresholds, and `TODO` against `FIXME`. No directory; the code under
   discussion was the skill itself.

7. **Round 7** — architecture. Forty-one forced choices about which module imports which, where one file
   becomes several, and what a third-party dependency may touch. The program kinds are a
   long-running service, an importable library and a monorepo. The one-shot CLI is deliberately
   absent: it is the shape rounds 1 to 6 already cover, and the shape that hides every question this
   round asks. Stage 2 builds real multi-module programs only where stage 1 leaves an answer open.

8. **Round 8** — red team. Four agents with no access to the design conversation: one built a
   multi-module service against the skill, one read it hostilely for contradictions, one installed it
   from the README on a simulated fresh machine, and one reviewed a program with eight planted
   defects. 35 defects recorded as `R8-D01` to `R8-D35`. Separately, twelve functions were stripped
   of every internal blank line and marked up by hand, which measured `NAR008` at 42% precision and
   22% recall and removed it.

## decisions.jsonl schema

One object per line. Every rule in `skill/SKILL.md` must cite an `id` from this file. A rule
with no `id` and no linter behind it does not ship.

| field | type | notes |
|---|---|---|
| `id` | str | `Q07`, `R2-03`, `R3-P1-rank`, `R5-06`, `V-03` |
| `dimension` | str | dotted, e.g. `errors.chaining` |
| `round` | str | `1`, `2`, `2b`, `3`, `3a`, `4`, `5`, `6`, `7`, `8`, `validation` |
| `kind` | str | `control` \| `gap` \| `provocation` \| `derived` |
| `options` | list[str] | short labels in the order presented |
| `choice` | str | chosen label, or `depends` |
| `strength` | str \| null | `strong` \| `weak` — how hard the rule should be pushed. Null only when the question itself was rejected and no choice was made (`Q16`) |
| `condition` | str \| null | set when `choice` is `depends` or the rule is contextual |
| `note` | str \| null | verbatim user reasoning, where given |
| `date` | str | ISO date |
| `supersedes` | list[str] | optional. Ids this decision replaces. `verify_docs.py` fails any document that states current rules and cites a superseded id |

## Validation

Two tasks in `validation/`, never used in elicitation. Each generated three ways — no guidance /
the pre-existing style doc pasted as context / the finished skill — then shuffled blind for a 1-5
rating plus violation marking, and scored with `ruff` + `pylint` + `mypy` + `checks.py`.

If the skill does not beat doc-as-context, it has not earned its context budget and should be cut
back to a shorter rule list. That outcome is a real possible result of this benchmark, not a
failure mode to design around.
