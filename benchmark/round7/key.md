# Round 7 — key

Do not read before answering `questions.md`.

`type` column: **control** = the answer is already in `SKILL.md`, used to check that the multi-file
format discriminates at all. **gap** = the doc is silent, this is the point of the exercise.
**provocation** = a position the doc does not contemplate and that I argue is better; per the
"push back hard" ruling these are deliberate arguments, not neutral probes.

## Block M — the measure

| Q | Dimension | Type | Doc / corpus prior | Expected |
|---|---|---|---|---|
| M01 | `evolution.change_cost_metric` | gap | `R2b-P0` sets the principle for one file: 0% of reader effort on rote diffing. It never says which of two readers wins — the one adding a feature, or the one following one | — |
| M02 | `evolution.abstraction_exchange_rate` | gap | `R2b-E1`/`E2` price an extracted function. `R2b-E3` prices a parameter at 5. `NAR005` prices a named type at depth 2. None of the three is priced against the others | — |

M01 is the architectural `R2b-P0`. Every later block trades in whatever it returns, and the stage-2
change-request scoring is its direct operationalisation. If it comes back "depends", the condition is
the most valuable single line in the round.

M02 fixes the exchange rate. If a file is cheaper than a threaded parameter, block B leans one way
and block C the other; if the order reverses, so do they.

## Block A — which module imports which

| Q | Dimension | Type | Doc / corpus prior | Expected |
|---|---|---|---|---|
| A01 | `architecture.dependency_direction` | gap | Doc silent on module arrows. Corpus single-file, so config is a module global in reach of everything | B |
| A02 | `architecture.cycle_breaking` | **provocation** | Doc silent. `from __future__ import annotations` is mandatory, which makes A cheap and therefore reflexive. A cycle is a wrong cut, not an import problem | B |
| A03 | `architecture.resource_lifetime_owner` | gap | `Q10`: all executable code in `main()`, which argues the entry point owns the connection. Never asked once the loop is in another module | — |
| A04 | `architecture.error_hierarchy_home` | gap | `Q20`: custom exceptions subclass `RuntimeError`. `c_typed_attrs.py` keeps the whole hierarchy in one `### vocabulary` — in one file, where there was no alternative | — |
| A05 | `architecture.shared_wire_constants` | gap | `c_typed_attrs.py` argues this in a comment: two participants speaking one protocol, "a copy inside each is a copy that can drift" | A |
| A06 | `architecture.dispatch_registry` | **provocation** | `R4-03`: keep the exhaustive `match`, it is the only form where a new member fails the type check. A is the standard plugin answer and it inverts the arrows | B |
| A07 | `state.config_propagation` | gap | `R3a-02`/`R2-06` fix where config *comes from*. `R3a-12` fixes where a constant *lives*. Nothing fixes how it *travels* | — |
| A08 | `errors.fail_fast_vs_degrade` | control | `Q24`: process the whole batch, collect failures, log a summary, exit nonzero. Never abort on the first bad item | A |

## Block B — where the cuts go

| Q | Dimension | Type | Doc / corpus prior | Expected |
|---|---|---|---|---|
| B01 | `modules.split_threshold_upper` | **provocation** | The whole file layout — `main()` first, workflow in call order, `### vocabulary` last — presumes one file. Corpus 5/5 single-file, up to 758 lines. C is the "split only on a second consumer" position | A |
| B02 | `modules.split_axis` | gap | Doc silent. `R2b-P0` weakly favours whichever puts the two things that change together in one file | — |
| B03 | `modules.split_threshold_lower` | gap | Doc silent. `R3a-12`'s test — could someone change this knowing only what the program *does* — is the nearest analogue, applied to a module | — |
| B04 | `deps.shared_utils_module` | gap | Doc silent. `R2b-E1`/`E2` — extract on foreseen reuse, not on nameability — is the in-function version of the same test | C |
| B05 | `package.init_contents` | **provocation** | **Not blind** — `R7-M01`'s answer already leans façade, for a *deep* package hiding an 800-line device. B05 asks the *top-level library* package, which is a different claim: not "hide a big implementation" but "flatten the import path a consumer writes". B is the packaging-guide default. Empty means one import path per name and no re-export layer to diff against | B, against the doc-silent prior of A |
| B06 | `imports.module_vs_name` | gap | `R3a-08`: import the class, keep the verb qualified (`struct.unpack`, `json.loads`). `store.insertReading` is that rule applied to a first-party module | — |
| B07 | `modules.vocabulary_placement` | gap | **Reframed.** As first written it asked package-glossary against per-module `### vocabulary`, which `R7-A02` and `R7-A04-revised` had already settled — a crossing type goes central. It now asks the only part still open: does a type used by exactly **one** module go central too. The two round-7 rules disagree here. `R7-A04-revised` centralised errors because anything *might* cross, which argues A. `R7-A05-property` argues B, since a frame header is a property of the parser | — |
| B08 | `modules.internal_visibility` | gap | Doc silent. Nothing in the corpus uses a leading underscore or `__all__`. The style has no privacy convention at all | — |
| B09 | `architecture.main_module_home` | gap | Doc silent. `NAR009` demands a usage example from a runnable module, which is easier to place honestly in B | — |
| B10 | `docs.internal_module_docstring` | control | `R5-02` / `NAR009`: every module opens with a docstring; only a runnable one needs the usage example | A |

## Block C — the abstraction budget

| Q | Dimension | Type | Doc / corpus prior | Expected |
|---|---|---|---|---|
| C01 | `abstraction.seam_trigger` | control | `R2-01`: `Protocol` for a seam with more than one real implementation, never `ABC`. `R2-02`: tests use real dependencies | B |
| C02 | `architecture.inject_vs_import` | **provocation** | `R2-01` taken to its conclusion: if one implementation does not earn a `Protocol`, it may not earn an object either. `R3-P2-rank` favours a class owning typed state, but that was state, not a query surface | B |
| C03 | `abstraction.indirection_depth` | gap | Doc silent. `R2b-E3` (5+ params means a missing dataclass) is the only pressure, and it pushes toward B | B |
| C04 | `architecture.flag_drilling` | gap | Doc silent. `R5-06` makes keyword-only params free of `NAR003`, so A costs nothing the linter can see | B |
| C05 | `architecture.dependency_bundle` | gap | `R2b-E3`: 5+ parameters is a missing state dataclass. `NAR003`: >3 positional go one per line. Both point at B; neither was asked at module scale | — |
| C06 | `architecture.pure_core_io_shell` | **provocation** | Ranked **third** in round 3 (P1), where the program was small enough that the plan record read as ceremony. Re-probed at four rules and three effects | B |
| C07 | `architecture.pure_core_io_shell` | gap | The same axis at a size where it plausibly does not pay. Paired with C06 deliberately: the gap between them is the threshold | — |
| C08 | `testing.dependencies` | control | `R2-02` / `Q16`: real socket, real temp SQLite, real temp directory. A double is a last resort and gets recorded as a known gap | A |

## Block D — third-party code

| Q | Dimension | Type | Doc / corpus prior | Expected |
|---|---|---|---|---|
| D01 | `deps.third_party_containment` | **provocation** | `Q17`/`R6-03`/`R6-07` ban the ORM on anti-ceremony grounds, which argues A. The layering instinct argues B. The doc has never said whether a raw handle may cross a boundary | A |
| D02 | `deps.stdlib_vs_dependency` | gap | `R6-04` pins the toolchain; `R2-06` chose `python-decouple` over `os.environ`, so the doc is not stdlib-absolutist. The threshold is unstated | — |
| D03 | `deps.wrapping_policy` | gap | Doc silent. This is `abstraction.wrapper_modules` with a real motive attached, so it should be read against C02 and D01 | — |
| D04 | `deps.ban_scope` | gap | `R6-07`: the ban is lifted under `maintenance/`, `scripts/`, `migrations/`, by directory glob. Whether that is the mechanism or an accident of ruff's config surface is unasked | — |
| D05 | `deps.vendoring` | gap | Doc silent. `README.md` boasts that `checks.py` imports only stdlib, which is C-flavoured; `requirements-lock.txt` is A-flavoured | — |
| D06 | `deps.version_policy` | gap | `R6-04` pins exact versions and states why: an unpinned install can change what the config means. That reasoning is about a *tool*, not about a *library with consumers* | C |

## Block E — service, library, repository

| Q | Dimension | Type | Doc / corpus prior | Expected |
|---|---|---|---|---|
| E01 | `state.singleton_scope` | gap | `Q10`: all executable code in `main()`. `R2b-G1`/`NAR001`: mutation carries `global`. A satisfies both to the letter and is still the shape the doc never contemplated | B |
| E02 | `logging.logger_ownership` | gap | The doc shows `LOG = logging.getLogger('app')` at module scope in a single-file program. `R5-03` says a monorepo shares the formatter module, not the logger | — |
| E03 | `architecture.config_slicing` | gap | `R3a-02`: a config file parsed into a frozen dataclass. Which dataclass, and how many, is unasked | — |
| E04 | `architecture.clock_injection` | gap | `c_typed_attrs.py` calls `time.monotonic()` inside `parseStatus`. `R2-02` (real dependencies) weakly argues against injecting a clock; `R2-12` (property-based tests wherever there is an invariant) argues for it | — |
| E05 | `library.entry_shape` | gap | `Q10` and `R3a-03` order a file around `main()`. A library has no `main()`, so either the rule generalises to "the public entry" or it is a CLI rule wearing a general name. The doc does not say which | A |
| E06 | `monorepo.sharing_boundary` | gap | `R2b-E4`: always collapse duplicated-but-drifting code, even when the shared version needs a parameter — decided *inside one file*, where collapsing costs no import edge. `R5-03` shares a formatter module across a monorepo | A |
| E07 | `concurrency.polling_vs_events` | gap | `R2-04` makes asyncio the default for IO-bound work but never says whether the loop asks or listens. Added at the answerer's request after an unprompted preference for event-driven surfaced while answering `R7-M01`; asked against code because a preference stated in the abstract is weaker evidence than one taken against a program | B |

## Confounds to watch

- **M02** is an ordering, not a choice. If two of the three tie, say so — a tie is a real result and
  it means the two costs are interchangeable in later questions.

- **A01** — B also moves the config lookup up a level. That is inherent to reversing the arrow, not
  an added variable. But if B wins for "the lookup belongs to the caller" rather than "store must not
  import config", that is a different rule. Ask which.

- **A02** — C additionally destroys a named type, which `NAR005` and `R6-09` argue against. If C is
  attractive, the finding is about the cost of sharing a type, not about cycles. Record both.

- **A03 / E01** — both ask who owns the database handle. A03 varies *which module*, E01 varies
  *module-global against passed*. If A03 says the entry point owns it and E01 says a module global is
  fine, the answers disagree; reconcile before recording either.

- **A07 / E03** — A07 asks how config travels, E03 asks what shape it travels in. A07 option B and
  E03 option A are the same object seen twice. Consistent answers are expected; inconsistent ones
  mean one of the two was read as the other.

- **B07 is now a false dichotomy and must be reframed before it is asked.** Block A answered it from
  both sides: `R7-A02` put a shared type in a common vocabulary module, `R7-A04` kept a single-owner
  type in the module that raises it, and `R7-A02-A04-ownership` derived the reconciliation — a type
  lives with its owner and moves to a shared module only when more than one module owns it. Asking
  "one package vocabulary or one per module" now has the answer "both, by owner count". Reframe B07
  to ask what it can still settle: how many importers make a type shared, whether a type read by many
  but written by one counts, and where the shared module sits relative to its owners.

- **B04 is bruised, not broken.** `R7-A05-growth` said to start with a `common.py` and split it when
  it grows, which reads as a vote for option A. It is not, and the distinction matters: that
  `common.py` is scoped to one system's directory and holds what that system's modules genuinely
  share. B04's three helpers are unrelated — a formatter, a batcher and a checksum — and only the
  checksum is shared, with `drift_check`. The DRY reasoning in `R7-A05-growth` pulls out what is
  duplicated, and `R2-09` calls a one-line helper called once residue. Both still point at C. Ask it,
  but if A wins, establish whether it won on "a common module is fine" or on "these three belong
  together", because only the second contradicts C.

- **B01 / B03** — the same axis at opposite ends. If B01 says "one file" and B03 says "the 28-line
  module should exist", the answers are inconsistent and one of the two is being read as a different
  question. **Reconcile before recording either.**

- **B05** — C bundles three things: a re-export, a shared constant and a shared `LOG`. If C loses,
  follow up on whether it lost for the re-export or for the state. E02 covers the `LOG` half.

  **B05 is not blind, and the useful answer is the boundary rather than the winner.** `R7-M01`
  already put a façade on a deep package, to hide an 800-line device implementation from a caller.
  B05 asks the top-level library package, where nothing is being hidden and the only effect is which
  import path a consumer writes. If both come back façade, the rule is flat and `__init__.py` always
  re-exports. If B05 comes back empty, the rule has a condition — a façade is earned by the size of
  what it hides, not by being a package — and **that condition is the finding**.

- **B09** — the two options differ in where `sys.exit` sits as well as where `main` sits. `Q10` fixes
  `sys.exit(main())` as the form; neither option violates it, but note if that drove the answer.

- **C01 / C02** — deliberately adjacent. C01 is the control: given an object seam, is the `Protocol`
  earned. C02 asks whether the object exists at all. **If C01 does not reproduce `R2-01`, stop before
  trusting C02.**

- **C06 / C07** — the same dimension at two sizes, on purpose. A split answer is the **desired**
  result: it yields a threshold instead of a flat rule. A matching answer at both sizes is also
  informative and should be recorded as flat.

- **C08** — B also changes the production signature of `pollOne`, from a connection to a store
  object. That is the architecture point of the question and it is why this control sits in an
  architecture round, but it means a vote for A is a vote against the seam as well as against the
  double. If A wins, C02 should agree; if they disagree, one of them is being answered on the
  other's dimension.

- **D01 / D03** — D01 asks whether a handle may cross a boundary, D03 asks whether a library may be
  called directly. The same instinct answers both, so agreement proves little and **disagreement is
  the informative outcome**: it would mean the rule depends on which third party, not on the shape.

- **D02** — B is longer and uses `asyncio.to_thread`, so it also carries a concurrency cost that A
  does not. `R2-04` makes asyncio the default for IO-bound work, which is what forces the thread
  hop. If B loses, check whether it lost for the line count or for the thread.

- **D04** — C is not a config mechanism, it is a repository-shape answer. If C wins, that is an
  answer to E06 as well and both must be recorded.

- **E02** — the emitted record's `name` field differs between the options. Nothing else does.
  Behavioural identity is broken by exactly the thing being measured, which is legitimate and is
  stated in the question.

- **E05** — B additionally reverses the definition order, which `R2-10` constrains only at module
  *execution* level. Both options are legal under `R2-10`. If B wins, the reason matters: "a library
  has no thesis" is a different rule from "leaves first reads better".

- **E07** — **this question is not blind.** The preference for event-driven over polling was stated
  unprompted while answering `R7-M01`, before the question existed. It is asked anyway because the
  stated preference carries no condition and no cost, and the question supplies both: B drops the
  round, which is the unit `Q24`'s aggregate log record and `RoundReport` are both defined over. The
  informative answer is what replaces the round, not which option wins. Record `kind` as `derived`
  if B wins without a new boundary being named.

- **E06** — C is deliberately the worst-looking option and exists so that "a shared library" is
  chosen against a real alternative rather than by default. If C is not obviously wrong, that is a
  finding about `drift_check` being the natural owner, and the rule is about *which* module owns
  shared code, not *whether* one does.

## Instrument check

If any of **A08, B10, C01, C08** does not come back matching `SKILL.md`, stop that block. Either the
doc no longer reflects the preference at this altitude, or the multi-file sketch format is not
discriminating. Both invalidate that block's other answers until resolved.

**A control gates its own block, not the run.** Round 1 stopped everything because all 24 questions
sat at one altitude. These six blocks do not, and one broken question format need not contaminate
the rest.

**A08 is the exception worth watching.** It is the only control whose settled answer (`Q24`) was
itself decided from a snippet rather than from a program, and it is the one whose meaning could
genuinely change once the failure crosses a module boundary. Treat a mismatch there as a real
finding, and re-ask it as a stage-2 follow-up before discarding the run.

## Coverage against the scope

| requested area | questions |
|---|---|
| dependency direction between modules | A01, A02, A03, A04, A06, D01 |
| when one file becomes several | B01, B02, B03, B04 |
| what a package `__init__.py` holds | B05, B06, B09 |
| module size and cohesion thresholds | B01, B03, B04, B08 |
| where shared types live across files | A02, A04, B07, A05 |
| how far a call chain and a flag may reach | C03, C04, C05 |
| inject or import | C01, C02, E01, E03, E04 |
| third-party and dependency policy | D01, D02, D03, D04, D05, D06 |
| long-running service | A03, A07, A08, C04, E01, E02 |
| importable library | B05, B07, B08, D06, E05 |
| multi-program repository | A05, B04, D04, E06 |
| pure core / IO shell, re-probed at size | C06, C07 |

## What stage 2 would have to build

Named here so the decision to build a program is a decision, not a drift. Build a cluster only for a
dimension these answers leave open.

| trigger | cluster |
|---|---|
| A01/A02/A03 return `depends`, or B01 and B03 disagree | **layering** — one service, 450–700 lines, two variants across 3–5 modules, plus one change request scored by files touched |
| B01 or B03 returns `depends` | **split threshold** — one ~600-line program as one file, split by stage, and split by subject, plus the same program grown to ~1,400 lines |
| B04 or E06 returns `depends` | **cross-module DRY** — two programs sharing a 15-line routine: duplicated, collapsed, collapsed with a parameter one caller varies |
| D01 or D03 returns `depends` | **containment** — one service in two variants, handle-travels against handle-wrapped, with a library swap as the change request |
