# Python style preference benchmark

Instrument for deriving a `narrative` skill family from measured taste rather than guesses.

Target is **"the best possible way to write code with infinite time and effort"**, not a
description of how the author currently writes. The existing corpus, an unpublished Python
project, is contrast material only — it contradicts the written style doc on six of its own rules.

## Layout

```
round1/questions.md    24 forced-choice snippets, blind
round1/key.md          what each probes; do not read before answering
round3/p1_scan_ingest/ three architectures for one batch-ingest CLI
round3/p2_device_driver/ three ways to hold state in one instrument driver
round4/                adversarial markup file (optional round)
validation/            two held-out tasks for the blind skill-vs-doc comparison
decisions.jsonl        the evidence base — every answer, one per line
```

## Protocol

1. **Round 1** — 24 snippets, delivered as terminal prompts. Four are controls whose answer is
   already in the style doc. If a control does not reproduce the doc, stop: the instrument is
   broken and nothing else in the run is trustworthy.
2. **Round 2** — adaptive follow-ups, generated only where Round 1 returned "depends",
   contradicted the corpus, or implied an unasked question. Testing gets its own block here: the
   corpus has zero tests, so there is no prior at all.
3. **Round 3** — read the two programs in an editor, rank the variants, then for each problem name
   *three things you would change in your top pick and one thing you would steal from each of the
   others*. The annotations are the highest-signal data in the exercise; the ranking alone only
   produces preferences, the annotations produce rules.
4. **Round 4** (optional) — mark up a seeded file as a PR review. Generative rather than
   forced-choice, so it catches preferences no question anticipated. Contains deliberate
   non-violations to measure false-positive rate.

## decisions.jsonl schema

One object per line. Every rule in the final `rules.md` must cite an `id` from this file; a rule
with no `id` and no linter behind it does not ship.

| field | type | notes |
|---|---|---|
| `id` | str | `Q07`, `R2-03`, `P1-rank`, `P1-note-1` |
| `dimension` | str | dotted, e.g. `errors.chaining` |
| `round` | int | 1-4 |
| `kind` | str | `control` \| `gap` \| `provocation` |
| `options` | list[str] | short labels in the order presented |
| `choice` | str | chosen label, or `depends` |
| `strength` | str | `strong` \| `weak` — how hard the rule should be pushed |
| `condition` | str \| null | set when `choice` is `depends` or the rule is contextual |
| `note` | str \| null | verbatim user reasoning, where given |
| `date` | str | ISO date |

## Validation

Two tasks in `validation/`, never used in elicitation. Each generated three ways — no guidance /
the pre-existing style doc pasted as context / the finished skill — then shuffled blind for a 1-5
rating plus violation marking, and scored with `ruff` + `pylint` + `mypy` + `checks.py`.

If the skill does not beat doc-as-context, it has not earned its context budget and should be cut
back to a shorter rule list. That outcome is a real possible result of this benchmark, not a
failure mode to design around.
