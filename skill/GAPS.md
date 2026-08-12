# Reported gaps — from agents writing code against the skill

Raised by the validation `skill` arms, which were asked to report where SKILL.md was ambiguous,
contradictory or unfollowable. Not yet acted on: fixing them before the blind rating would mean
rating a skill that did not produce the code under review.

## From V1 (log triage)

1. **"Log at the raise site *and* the handle site" does not scale to per-item validation.** A
   parser with six raise sites gets six log calls or a helper. The agent wrote
   `rejectLine(reason) -> MalformedLineError` that logs once and returns the exception
   (`raise rejectLine(...) from exc`). The skill gives no hint that log-and-return-the-exception
   is acceptable. It also collides with degrade-and-report: a file with 10k bad lines emits 20k log
   lines. **No level guidance either** — the agent chose DEBUG at raise, WARNING at handle.

2. **The `global` rule is undefined for objects you configure rather than rebind.**
   `LOG.addHandler(...)` mutates module state, so R2b-G1 arguably requires `global LOG` — but
   `addHandler` is not in `checks.py`'s `MUTATING_METHODS`, so NAR001 never fires, and a bare
   `global LOG` with no rebinding reads oddly. Does the rule cover mutation via a domain method, or
   only container mutation?

3. **`Enum` conflicts with needing an ordering.** `LogLevel` must be comparable for `--min-level`,
   but `Literal` and `StrEnum` are banned, `case _` is banned, and a module-level
   `LEVEL_ORDER = (LogLevel.DEBUG, ...)` is forbidden by the constant-referencing-an-Enum-member
   rule. The agent used an exhaustive `match` returning `logging.DEBUG`…, which works but is a
   function call per comparison where a mapping is natural.

4. **"A dataclass, never a dict of parsed fields" versus genuinely arbitrary fields.** The task
   specifies *arbitrary* extra fields; there is no dataclass for them. The agent flattened
   leftovers to a JSON string, losing structure. A `Mapping[str, object]` field would violate Q02
   as written. The skill has no rule for a schemaless remainder, which is the common case in log
   tooling.

5. **NAR008 fights grouped guard clauses.** Grouped short guards are meant to stay grouped, but any
   guard that reaches 3 lines — which it does the moment log-then-raise applies — forces a blank
   line after it. The two rules pull opposite ways and the skill does not say which wins.

6. **`SIM103` quietly overrides guard-clauses-over-nesting.** Three symmetric `if ...: return False`
   guards get flagged; ruff demands the last become `return <negated condition>`, which is less
   symmetric than the parallel guards Q06 implies. `SIM114` is documented as disabled for exactly
   this class of problem; `SIM103` has the same character and is not mentioned.

## Fixed already

7. `COM812` and `N803` config contradictions — see decision `V-01`. Both were real; both fixed and
   regression-checked against the six benchmark files.
