# Round 1 — key

Do not read before answering `questions.md`.

`type` column: **control** = answer already stated in the style doc, used to check the instrument
works. **gap** = doc is silent, this is the point of the exercise. **provocation** = an option the
doc does not contemplate and that I think is better; per the "push back hard" ruling these are
deliberate arguments, not neutral probes.

| Q | Dimension | Type | Doc / corpus prior | Expected |
|---|---|---|---|---|
| 01 | `naming.explicit_global` | control | Doc §9 mandates `global` at top of function. Corpus: 0 opportunities, untested | B |
| 02 | `data.dataclass_over_dict` | control | Doc §11. Corpus: producer yes, consumer no | B |
| 03 | `strings.multiline_concat` | control | Doc §3.3 — parens, never `"""`, whitespace bugs | A |
| 04 | `class.attrs_in_init` | control | Doc §10. Corpus 7/7 compliant | B |
| 05 | `docs.docstring_policy` | gap | Doc silent. Corpus 0/13 docstrings, contract in `#` comments instead | — |
| 06 | `control.guard_clauses` | gap | Doc silent. Corpus 6:1 early-exit | B |
| 07 | `control.comprehension_ceiling` | gap | Corpus 0.8 comprehensions/loop, zero nested. Split is by accumulator | — |
| 08 | `logging.interpolation` | gap | Doc mandates JSONL logging; C is the form that actually produces structured fields. Corpus: 23 `print`, no logging | — |
| 09 | `naming.magic_numbers` | gap | Corpus inlines `50` 3× with a comment; doc implies named constants | — |
| 10 | `structure.main_function` | **provocation** | Corpus 5/5 inline, up to 215 lines under the guard. No `main()`, no exit code, anywhere | B |
| 11 | `naming.abbreviations` | gap | Corpus: names scale with scope — `x`/`i`/`f` in loops, 5-word names at config level. C is that policy | — |
| 12 | `naming.predicates` | gap | Corpus has zero `is_`/`has_` prefixes | — |
| 13 | `typing.param_variance` | gap | Doc silent | — |
| 14 | `typing.json_payload` | gap | Tension with the no-runtime-validation rule: C validates at the boundary | — |
| 15 | `typing.newtype_primitives` | **provocation** | "Illegal states unrepresentable" axis, user-selected | B |
| 16 | `typing.protocol_vs_abc` | gap | Doc mandates composition over inheritance; ABC is inheritance | — |
| 17 | `typing.strictness` | **provocation** | B is what `mypy --strict` forces. User was explicitly unsure | — |
| 18 | `typing.exhaustiveness` | **provocation** | `assert_never` turns a new enum variant into a type error. Corpus: 0 Enum | B |
| 19 | `errors.granularity` | gap | Corpus: 3 try blocks in 586 lines | — |
| 20 | `errors.custom_classes` | gap | Corpus: 0 custom exceptions | — |
| 21 | `errors.chaining` | gap | Corpus: 0 `raise ... from` | — |
| 22 | `errors.eafp_vs_lbyl` | gap | `dignified-python` defaults LBYL, which is the unusual position | — |
| 23 | `errors.log_site` | gap | Doc silent. Double-logging is the failure mode | — |
| 24 | `errors.fail_fast_vs_degrade` | gap | Doc silent. B is argued in-code so it is not a strawman | — |

## Confounds to watch

- **Q05** varies docstring *presence and format* together. If the answer is "docstring yes, but not
  Google-style", that is two facts — record both, and generate a Round 2 follow-up on format.
- **Q10** also varies the exit-code and the inline-config-constants habit. If B wins, follow up
  separately on whether `ALL_CAPS` config-at-top-of-guard survives the move into `main()`.
- **Q14** C does work at the boundary that A and B do not, so it is not purely a typing question —
  it is the smallest honest version of parse-don't-validate. P1 variant C tests it at scale.
- **Q19** B additionally distinguishes `SKIPPED_DUPLICATE` from `QUARANTINED`. That is inherent to
  narrow handling, but note it if B wins for the wrong reason.

## Instrument check

If any of Q01–Q04 does not come back matching the doc, stop. Either the doc no longer reflects the
preference, or the question format is not discriminating. Both invalidate the other 20 answers
until resolved.
