# Gaps found by writing real programs against the skill

Agents wrote programs against `SKILL.md` and reported every place the skill was ambiguous,
contradictory, or impossible to follow. That report found more defects than any review of the text.

All six gaps are now closed. Each entry records what the agent hit and what the rule became.

## 1. "Log at the raise site and the handle site" did not scale

A parser with six raise sites needed six log statements or a helper. The rule also fought
degrade-and-report: a file with 10,000 bad lines produced 20,000 log records.

**Resolved (R4-02).** The raise site records the generic fact once, however you factor it. A helper
that logs and returns the exception satisfies the rule. In a degrade-and-report loop the handle
site logs the aggregate, not the item.

Measured on a 10,000-bad-line fixture: per-item handle-site logging produced 10,023 records and
3.2 MB. An item-at-DEBUG plus tally-at-WARNING split produced 24 records and 1.2 KB, and lost
nothing under `--verbose`. The level rule follows. An operator cannot act on one bad line. An
operator can act on "4,812 of 10,000 lines rejected".

## 2. The `global` rule was undefined for objects you configure

`LOG.addHandler(...)` mutates module state, but `addHandler` was not in the checker's list of
mutating methods, so `NAR001` never fired.

**Resolved (V-03).** All mutation requires the marker, because the marker tracks side effects
rather than containers. `NAR001` now matches configuration verbs by prefix as well as exact
container methods. The check under-reports rather than crying wolf: an arbitrary domain method can
mutate without saying so in its name.

## 3. `Enum` conflicted with needing an ordering

`LogLevel` had to be comparable, but the skill banned `Literal` and `StrEnum`, banned a `case _`
fallback, and appeared to ban a module-level constant naming an Enum member.

**Resolved (R4-03).** Keep the exhaustive `match`. It is the only form where adding a member fails
the type check. A dict lookup and an `IntEnum` both type-check clean and fail at runtime.

The performance objection did not survive measurement. The mapping is 15% faster per call, 119.8
against 141.7 ns, and a function-local dict is 6.4 times slower. End-to-end the spread between
forms is smaller than run-to-run noise.

The apparent placement ban was a misreading. R2-10 orders definitions. It does not ban them. A
constant naming an Enum member is legal in `### vocabulary` after that Enum.

## 4. "A dataclass, never a dict" fought genuinely schemaless input

Log lines carry arbitrary extra fields. No dataclass describes them.

**Resolved (R4-04).** Q02 chose between "dict of parsed fields" and "frozen dataclass". It decided
what holds the record, never what type a field may have. Promote the fields the program computes
on to typed attributes. Put the remainder in one `Mapping[str, object]` field.

Two traps come with that, both verified. Never splat the remainder into an output record: an
untrusted line carrying its own `source` key overwrites your provenance. A frozen dataclass with a
mapping field is not hashable, so `set(entries)` raises at runtime with no linter warning.

## 5. `NAR008` fought deliberately grouped guards

A guard that logs before raising is three lines, so `NAR008` forced a blank line and split a group
the style protects elsewhere.

**Resolved (R4-05).** The rules never actually collided. Inlining the log at the raise site caused
it. Move the log into a `reject*()` helper that logs and returns the exception, and each guard is
two lines again. The guards group, `NAR008` is silent, and the raise-site rule still holds.

The same helper resolves gap 1, which makes it a genuine pattern in this style rather than a
workaround.

## 6. `SIM103` overrode guard-clauses-over-nesting

Three symmetric `if ...: return False` guards were flagged. Ruff demanded the last one read
`return not (...)`, unlike its siblings.

**Resolved (R4-06).** The config disables `SIM103`.

The original report claimed `SIM103` "has the same character" as `SIM114`. It does not. The
`SIM114` fix is safe, so `ruff check --fix` applies it silently, which is what made it dangerous.
The `SIM103` fix is unsafe-only, so the documented command never touches it. It can only fail the
gate. The case for disabling it rests on the demand being wrong, not on autofix risk.
