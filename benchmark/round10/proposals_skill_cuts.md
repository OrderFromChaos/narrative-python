# Dead, duplicate and superseded clauses in SKILL.md

Applied: items 1 to 24, and item 25 as (b) (R10-other-modules). Item 26 stays as it is: `NAR010` covers a FIXME in reachable code. Item 27 is open.

`skill/SKILL.md` is 914 lines and 8,163 words. Below are 27 cuts or trims. Together they remove
about 75 lines. Each item gives the line, what is wrong with it, and the proposal. Nothing here
changes a rule. Items 25 to 27 are contradictions, which need a decision rather than a cut.

## A. Dead: no longer true

1. **:895** `Give it any path. It sorts Python files from prose and runs the right checks on each, so
   nothing has to decide a workflow at run time. There is one command, not a sequence to remember.`
   `verify.py` no longer handles prose files. It checks the `.py` files below a path.
   → `Give it any path, and every Python file below it is checked.`
2. **:870-875** `3.10 reaches end of life in October 2026.` and the bullet `datetime.UTC,
   typing.assert_never, enum.StrEnum, … are all available. No workaround is needed for any of them.`
   Both date from the move off 3.10. The bullet also lists `assert_never` and `StrEnum` as
   available, and both are banned elsewhere in the file (:297, :237).
   → Cut both. Keep the TaskGroup rule as `Supervise several long-lived tasks with
   asyncio.TaskGroup. Hand-rolled cancellation fails silently.`
3. **:883-885** `## Avoid the usual traps`: `Bare except:. Mutable default arguments. See wtfpython
   for the rest.` ruff already fails both (`E722`, `B006`), and an agent cannot act on "see
   wtfpython". → Cut the section.
4. **:593-594** `Seven cuts with no counterweight would drive every docstring to a bare summary
   line. That list is the counterweight, and it is what every surviving sentence in the measured
   package sits on.` This comments on the list rather than giving a rule, and the count is wrong:
   the lists above it have eight items. → Cut.
5. **:345-350** `… and its cost is already recorded.` This points to a decision record that the
   skill does not ship with. → End the sentence at `the schemaless remainder below.`

## B. Duplicates: another line already says it

6. **:148** `A value that is a path has type Path, not str. (R3a-10)` R10-path-type at :223 states
   this more fully. → Cut it, and add R3a-10 to the citation at :225.
7. **:273-274** `The type then decides the fix. A callable becomes a Protocol. Anything else — any
   kind of iterable — becomes a dataclass.` This repeats :248 word for word, and it sits after the
   DB-API exception, where it is out of place. → Cut.
8. **:295** `When you omit case _, mypy catches a new variant.` The code comment above it and :302
   both say this. It also has a tool as a mind-verb subject, which R10-tool-subjects rules out.
   → Cut the sentence. Keep the rest of the paragraph.
9. **:92** `It does not depend on statement length, and no threshold on length works.` This repeats
   the fifth bullet below it (`length is not the trigger, in either direction`).
   → Keep `No tool checks this.` and cut the rest.
10. **:332-333** `This bites hardest where one shared record serves two formats, which is what
    architecture.md asks for. The fix is the optional field, not a second record type.` The first
    bullet (:322) already makes the field optional on the shared record. → Cut.
11. **:352-353** `A dataclass, never a dict of parsed fields. (Q02) That rule is about the type of
    the record itself … A mapping-typed field is fine.` :318 already requires a frozen dataclass,
    and :355 already prescribes the `Mapping` field. → Cut, and move Q02 to the citation at :320.
12. **:504** `R3a-11 is the same rule for file moves and path manipulation.` :632-634 states
    R3a-11 as its own bullet. → Cut. Also cut the last sentence of :632-634 (`That is one case of
    the general rule above: show the thing rather than describe it.`).
13. **:621-624** `Write in a docstring what the code does, not why the code is shaped the way this
    style guide requires. …` The **Comments** rules cover docstring prose (R10-docstrings), and its
    Never list already has `why the file follows this style guide (R9-02)`. → Cut the bullet. If
    you want to keep the example, move `so this is a class and not a module` into the Never bullet.
14. **:797-798** `Decide by the reader, not by the line count of either formatter. JSONL logging
    belongs in an importable library that every program shares, and then it costs one import.`
    :794 and the bullet at :800 already say both things. → Cut.
15. **:495** `which is the cost the __main__.py module map already pays under R9-02` A
    cross-reference the reader does not need. → `A sample goes stale and no tool catches it. Keep
    it small, and re-paste it when the output changes.`

## C. Evidence and justification an agent cannot act on

16. **:498-502** `Measured over five modules of a working program, pasting the sample took their
    docstrings from 4, 4, 5, 7 and 12 lines to 20, 8, 7, 10 and 9. …`
    → `Expect it to cost lines. The sample buys exactness, not brevity: a reader learns the column
    order, the units and the alignment from three rows of a table and cannot learn them from a
    sentence about the table having columns.`
17. **:549-551** `Applying the tests below to a working 14-module package cut its docstring prose
    by 60%, and one module lost its body entirely.` → Cut the sentence. Keep `The summary line is
    mandatory. A body is not, and usually does not earn its place. (R9-09)`.
18. **:306-308** The speed paragraph, three lines of nanosecond measurements.
    → `Speed does not change this: the difference between the forms is below run-to-run noise.
    (R4-03)`
19. **:250-252** `Count names rather than nesting depth or argument width. Depth alone admits … One
    number covers both.` The reason for `NAR005`'s metric, which `NAR005` enforces anyway. → Cut.
20. **:276-279** `The reason is comprehension and shared vocabulary, not type safety. A Point
    dataclass does not make mypy --strict catch swapped coordinates … Expect the dataclass to give
    the thing a name, not to find a bug.` It ends on an agent verb.
    → `The reason is a shared name, not type safety: only NewType catches swapped coordinates (Q15).`
21. **:210-211** `No tool checks this, and the obvious proxy does not work: "used by exactly one
    function" flags almost every constant …` → `No tool checks this. This is review judgement.`
22. **:430-436** The `NAR001` verb list (22 verbs) and `The check under-reports rather than crying
    wolf: …`. The checker enforces the list, and the agent needs only the consequence.
    → `NAR001 also counts a call to a method whose name starts with a configuration verb, such as
    set, add, register or close. So a function that calls LOG.addHandler(...) declares global LOG
    even though it never rebinds it. (V-03)`
23. **:642-648** The `NAR010` mechanism (`walks the call graph`, `over-approximates reachability`,
    the library-module rule). → `NAR010 fails a FIXME in reachable code. Every function of a module
    with no main and no __main__ block counts as reachable. (R8-D02)`
24. **:636-648** The FIXME rule sits under **The module docstring**, and **Comments**, **Marker**
    also defines FIXME. → Move it to the Marker bullet as one line: `FIXME: incorrect behaviour, or
    behaviour that breaks soon after deploy. In reachable code it blocks the merge (NAR010). In code
    nothing calls, it warns whoever wires that code in.`

## D. Contradictions to resolve

25. **Guarantees about other modules.** The Never list (:721) says `guarantees about other modules.
    Put them in the module docstring or architecture.md`. :626 says `A docstring is about its file
    alone. Do not assert what another module does`. These conflict for the module docstring. Your
    R10-Q24 answer was "better as part of the file docstring or architecture.md". Also,
    `architecture.md` there reads as the skill's own file, not a project document.
    - (a) Module docstring allowed: soften :626 to function and class docstrings.
    - (b) Module docstring not allowed: change :721 to `Put them in the project's architecture
      document.`
26. **FIXME in running code.** The Marker bullet (`FIXME: incorrect behaviour, or behaviour that
    breaks soon after deploy`) reads as allowed anywhere. `NAR010` fails it in reachable code.
    Item 24 merges the two, and says that in reachable code a FIXME blocks the merge.
27. **ORM suppression.** :337 says a pydantic suppression names its gate in the module docstring.
    :376 says an ORM suppression `stands bare`, with no explanation. Both are `TID251`.
    - (a) Keep both: pydantic at one gate needs the gate named, an ORM off the hot path does not.
    - (b) Make both bare.

## Covered by the stance, but kept

`illustrations of a decision just discussed in the session` and `alternatives never in the code` in
the Never list both fall under **Comments are not thinking traces**. Cutting those lines in cycle 4
made the results worse, and you chose the minimal cut (R10-cleanup), so this report leaves them in.

## Not covered

`architecture.md` and `tooling.md` were not part of this pass. One duplicate is visible between
the files: `results_store: Store` appears in SKILL.md :190 and architecture.md :119.
