# Agent verbs in the skill's own prose

Applied to `skill/` with Q1 (b) and Q2 (a) (R10-owner-term, R10-tool-subjects).

`skill/agentverbs.py`, run over the prose sentences of `SKILL.md`, `tooling.md` and
`architecture.md` (code blocks and tables left out): 162 hits in 128 sentences. 9 are parse errors
and 4 are literal. The rest are below with a rewrite, plus 5 that the check misses.

Most rewrites take one of three forms: an imperative (`Log the generic fact once at the raise site`),
a plain verb such as `has`, `contains` or `is in`, or the passive.

## Two questions first

**Q1. `owner` and `owns`.** `architecture.md` uses ownership as a term: "a missing owner", "no
module owns it", "the program owns the config", and the `Owns` column in `tooling.md`. The check
flags `owns`.
- (a) Keep `owner` as the architecture term and silence those lines.
- (b) Replace it everywhere: `Find where the values belong`, `it belongs to no one module`.

The rewrites below use (b).

**Q2. Named tools as subjects.** `mypy catches a new member`, `pylint still flags a mixedCase
local`, `the formatter keeps the explosion`. A program does print output, but `catches`, `flags`,
`keeps` and `sees` all give it a mind.
- (a) Rewrite all of these as pass and fail: `a mixedCase local still fails pylint`.
- (b) Allow a named tool as the subject of `reports` and `flags`, and rewrite the rest.

The rewrites below use (a).

## Left as they are

Parse errors. In each, the real subject is a person, or the sentence was split inside a backtick
span:
- SKILL.md:169 `A reader who has never opened the module must understand the name.`
- SKILL.md:203 `Could someone change this value safely knowing only what the program does`
- SKILL.md:219 `a body that only iterates takes Iterable` (`iterate` read as `reiterate`)
- SKILL.md:439 `Every attribute declared in __init__.`
- SKILL.md:494 `The reader needs every shape the module can emit`
- SKILL.md:630 `only where a reader of this file needs the name`
- SKILL.md:657 `Comments are not thinking traces.`
- SKILL.md:778 the examples of the `NAR017` paragraph
- architecture.md:17 and :173: the subject is `the person making the change` and `a reader`

Literal. A formatter does rewrite code, and a program does compute:
- SKILL.md:356 `the fields the program actually computes on`
- SKILL.md:491 `A module that computes records`
- architecture.md:312 `the formatter rewrites it`
- tooling.md:91 `ruff format collapses a 4-arg signature`

## SKILL.md

1. **:8** `Every rule states its own reason, so read the rule and not the id after it.`
   → `The reason for each rule is in its text, so read the rule and not the id after it.`
2. **:32** `State held in a dict[str, Any] needs a cast() or a key lookup at every use to pass mypy --strict; typed attributes need neither.`
   → `State in a dict[str, Any] passes mypy --strict only with a cast() or a key lookup at every use. Typed attributes pass with neither.`
3. **:93** `Statement length does not decide it, and no threshold on it works.`
   → `It does not depend on statement length, and no threshold on length works.`
4. **:113** `so a function may carry as many as it needs` → `so a function may take any number of them`.
   `which documents them as optional anyway` → `and they read as optional in the signature anyway`
5. **:133** `If extraction would need 5+ parameters` → `If an extracted function would take 5+ parameters`
6. **:134** `Find what owns the values. That owner is a class when the program could hold two of it, and a module otherwise.`
   → `Find where the values belong. That owner is a class when two of it can exist at once, and a module otherwise.` (Q1)
7. **:139** `even when the shared version needs a parameter` → `even when the shared version takes an extra parameter`
8. **:145** `only where the type checker keeps its narrowing` → `only where the type checker's narrowing survives the merge`
9. **:149** `If it names a path, its type is Path, not str.` → `A value that is a path has type Path, not str.`
10. **:152** `This describes the formatter rather than adding a rule` → `This is how the formatter behaves, not a further rule`
11. **:247** `One measure: how many things it names, below the outermost. Car names none. dict[…] names five, and above four the annotation wants a name.`
    → `One measure: how many names it contains, below the outermost. Car contains none. dict[…] contains five, and above four, give the annotation a name.`
    (The check misses `Car names` and `the annotation wants`.)
12. **:253** `One number catches both.` → `One number covers both.`
13. **:303** `The match is the only form where mypy catches a new member.`
    → `Only a match fails mypy when a new member goes unhandled.` (Q2)
14. **:323** `A parsed record states only what its input carried. Where one input format carries a field`
    → `A parsed record contains only what its input contained. Where one input format has a field`
15. **:325** `because the program then reports a fact that the file does not contain`
    → `because the output then contains a fact that the file does not`
16. **:328** `A lockfile of name==version lines declares no source.` → `A lockfile of name==version lines has no source.`
17. **:336** `because a linter cannot see whether a model is used once at a gate or on every request`
    → `because whether a model is used once at a gate or on every request is not visible to a linter`
18. **:346** `only when a field holds a mutable value` → `only when a field's value is mutable`
19. **:353** `That rule is about what holds the record, not about what type a field may have.`
    → `That rule is about the type of the record itself, not about what type a field may have.`
20. **:370** `information the database and Python both already know`
    → `information already guaranteed by the database schema and the Python types`
21. **:374** `The module that needs the exception declares it, with a file-level # ruff: noqa: TID251.`
    → `Declare the exception in the module that uses the ORM, with a file-level # ruff: noqa: TID251.`
22. **:375** `a glob that drifts from the tree it describes` → `a glob that drifts from the tree it matches`
23. **:389** `the rote diffing the top principle forbids` → `the rote diffing banned by the top principle`
24. **:397** `The raise site records the generic fact once, however you factor that.`
    → `Log the generic fact once at the raise site, however you factor that.`
25. **:402** `The handle site records what it meant here, but in a degrade-and-report loop it logs the aggregate, not the item.`
    → `At the handle site, log what the failure meant there, but in a degrade-and-report loop log the aggregate, not the item.`
26. **:404** `and --verbose still shows every item` → `and every item still appears under --verbose`
27. **:419** `A half-valid config means the program does not know what it was asked to do, so`
    → `With a half-valid config, what the program was asked to do is unknown, so`
28. **:443** `Anything runnable shows how to run it.` → `Anything runnable has a usage example.`
29. **:448** `a docstring that says unassigned where the code says unattributed sends a reader to grep`
    → `unassigned in a docstring where the code has unattributed sends a reader to grep`
30. **:501** `from a sentence that says the table has columns` → `from a sentence about the table having columns`
31. **:505** `This generalises R3a-11, which said the same thing for file moves and path manipulation.`
    → `R3a-11 is the same rule for file moves and path manipulation.`
32. **:564** `It explains a language feature. Such a field holds None restates what optional means.`
    → `It is a language feature, explained. Such a field holds None repeats the meaning of optional.`
33. **:574** `Prose cannot carry that without becoming longer than the key.`
    → `In prose, the same information is longer than the key.`
34. **:575** `The summary line names what the code produces, by its real name.` → `In the summary line, call what the code produces by its real name.`
    `which paraphrases a type that already has a name` → `a paraphrase of a type that already has a name`
    (The check misses `The summary line names`.)
35. **:578** `The sentence after it explaining why stopping is right is not functionality.`
    → `A following sentence on why stopping is right is not functionality.`
36. **:580** `a # comment at the line that needs it` → `a # comment at the line it concerns`
37. **:586** `a provenance that the annotation cannot carry — … host is null when the report that gave the entry named none`
    → `a provenance absent from the annotation — … host is null when the entry's report has no host`
    (The example itself had an agent verb.)
38. **:598** `Below both, # comments carry the contract.` → `Below both, the contract goes in # comments.`
39. **:606** `The docstring carries a summary and a Raises: section. It carries Args: and Returns: only where they say something the signature cannot.`
    → `The docstring has a summary and a Raises: section. It has Args: and Returns: only where they give a fact absent from the signature.`
40. **:607** `the one part of a contract that no annotation carries` → `the one part of a contract absent from every annotation`
41. **:616** `A main() whose module docstring already lists the exit codes does not list them again.`
    → `When the exit codes are already in the module docstring, leave them out of the docstring of main().`
42. **:619** `A docstring must not assert anything the code does not do, and must not state a consequence it already implied.`
    → `Write nothing in a docstring that the code does not do, and no consequence that an earlier sentence already implies.`
43. **:622** `A docstring says what the code does. It does not say why the code is shaped the way this style guide requires.`
    → `Write in a docstring what the code does, not why the code is shaped the way this style guide requires.`
    `so this is a class and not a module argues with the style guide` → `… is an argument with the style guide`
44. **:627** `A docstring describes its own file.` → `A docstring is about its file alone.`
45. **:639** `It marks a known correctness problem parked in an orphaned section`
    → `It is a note on a known correctness problem parked in an orphaned section`
46. **:644** `The check would rather call an orphan live than let a running FIXME through.`
    → `Calling an orphan live is the safer error than letting a running FIXME through.` (The check misses it.)
47. **:647** `because its callers sit in files that this per-file checker never sees`
    → `because its callers are in files outside this per-file check`
48. **:670** `Not in the function that relies on it: an index lookup doesn't sort its own input.`
    → `Not in the function that depends on it: an index lookup doesn't sort its input.` (`own` is `NAR018` in code.)
49. **:723** `or nowhere if that function states the order itself` → `or nowhere if the order is already plain in that function`
50. **:744** `If a clause names an internal check, structure or attribute, cut it unless the reader needs it to act.`
    → `Cut a clause about an internal check, structure or attribute unless the reader needs it to act.`
51. **:778** `NAR017, from agentverbs.py, the seventh check verify.py runs, flags an agent verb on a subject that cannot act:`
    → `NAR017 is an agent verb on a subject that cannot act:` … then `It comes from agentverbs.py, the seventh check in verify.py.`
52. **:781** `It parses the sentence, so it also flags some noun compounds and participles.`
    → `The check parses each sentence, and some noun compounds and participles are flagged by mistake.`
53. **:824** `and the location that finds the call site` → `and the location of the call site`
54. **:831** `the default for anything that describes a deployment` → `the default for any deployment setting`
55. **:903** `After a passing run it lists every comment and docstring summary` → `A passing run ends with a list of every comment and docstring summary`
56. **:912** `tooling.md explains what each layer owns and documents the gotchas.`
    → `The job of each layer and the gotchas are in tooling.md.`

## tooling.md

57. **:35** `The snippet states it because it is a deliberate decision, not an oversight.`
    → `It is in the snippet because it is a decision, not an oversight.`
58. **:45** `global XYZ is a warning sign at the top of a function that says "this has side effects on module state".`
    → `global XYZ at the top of a function is a warning sign: the function has side effects on module state.`
59. **:64** `Verified that ruff check --select ALL and pylint --enable=all both report the undeclared mutation nowhere. Each tool does report other things about the file, such as … Neither reports the mutation.`
    → `Verified: neither ruff check --select ALL nor pylint --enable=all has a finding for the undeclared mutation. Both have findings for other things in the file, such as a missing docstring and a non-conforming function name.` (Q2)
60. **:91** `unless it carries a magic trailing comma. With the comma the formatter keeps the explosion exactly; without it the formatter joins the signature.`
    → `unless it ends with a magic trailing comma. With the comma, the exploded form survives formatting. Without it, the signature is joined onto one line.`
61. **:102** `The formatter rejects multiline-quotes = 'single'. It warns and enforces double.`
    → `multiline-quotes = 'single' conflicts with the formatter: ruff prints a warning, and the formatter writes double quotes regardless.`
62. **:103** `the style avoids """ for data strings anyway` → `the style uses no """ for data strings anyway`
63. **:123** `NAR011 checks this, and it agrees with ruff format on every form tested`
    → `NAR011 checks this, with the same result as ruff format on every form tested`
64. **:140** `A constant moved inside a function needs two escapes.` → `Moving a constant inside a function takes two escapes.`
65. **:149** `so pylint still flags a mixedCase local, a mixedCase argument and a mixedCase attribute`
    → `so a mixedCase local, a mixedCase argument and a mixedCase attribute still fail pylint` (Q2)
66. **:152** `Ruff stops flagging mixedCase locals once the config ignores N806, but pylint still catches them`
    → `With N806 ignored, mixedCase locals pass ruff but still fail pylint` (Q2)
67. **:172** `The loss needs a specific shape:` → `The loss happens only in a specific shape:`
68. **:180** `Merge only where the checker keeps its narrowing; where it does not, narrowing wins`
    → `Merge only where the narrowing survives the merge. Where it does not, narrowing wins`
69. **the split table** `| Layer | Owns |` → `| Layer | Job |` (Q1)

## architecture.md

70. **:8** `Every rule states its own reason.` → `The reason for each rule is in its text.`
71. **:22** `Measure what an edit must know, not how many files it touches.`
    → `Measure how much the person making an edit must know, not how many files the edit touches.`
72. **:32** `free when the field belongs to the thing it describes` → `free when the field belongs to the thing it is about`
73. **:42** `This one rule decides four questions that look unrelated:`
    → `Four questions that look unrelated have their answer in this one rule:`
74. **:44** `what the callee can derive from what it already has` → `what the callee can compute from its arguments and imports`
75. **:48** `Any module may catch it, so no module owns it.` → `Any module may catch it, so it belongs to no one module.` (Q1)
76. **:58** `The modules then hold functions and constants, and the glossary holds every type they pass between them. A module that holds only types needs no ### vocabulary divider`
    → `The modules then contain functions and constants, and the glossary contains every type passed between them. A module of types alone takes no ### vocabulary divider`
77. **:87** `and the name of the whole is what tells a reader the two conditions belong together`
    → `and from the name of the whole, a reader learns that the two conditions belong together`
78. **:103** `whatever the directory says` → `whatever the directory layout`
79. **:118** `and SKILL.md's naming rules refuse it: the name must carry its meaning to a reader who has never opened the module`
    → `which breaks SKILL.md's naming rules: the name must make sense to a reader who has never opened the module`
80. **:130** `a group that needs "and" to describe it is two groups` → `a group described only with "and" is two groups`
81. **:134** `Do not wait until a second program needs the code.` → `Do not wait for a second program to use the code.`
82. **:144** `a version comparator can name a concept cleanly` → `a version comparator can be a clean concept`
83. **:154** `A leading underscore marks any module-level name that is internal:`
    → `Prefix every internal module-level name with an underscore:`
84. **:158** `When a later change needs it elsewhere` → `When a later change uses it elsewhere`
85. **:168** `The entry point knows which modules exist and nothing about any of them.` → `The entry point has the list of modules and nothing about any of them.`
    `the one line that names it` → `the one line with its name`
86. **:171** `Its docstring says what the program is for and lists the modules in reading order.`
    → `Its docstring is the program's purpose, then the modules in reading order.`
87. **:176** `This is the one docstring that names other modules, and it is the only exception to the rule that a docstring describes its own file.`
    → `This is the one docstring with other modules' names in it, and the only exception to the rule that a docstring is about its file alone.`
88. **:178** `Every other module docstring says what that module does and stops there.`
    → `Every other module docstring is about what that module does, and nothing else.`
89. **:191** `A seam needs a Protocol once it has more than one real implementation; a thing needs a class once the program could hold two of it.`
    → `A seam earns a Protocol once it has more than one real implementation. A thing earns a class once two of it can exist at once.`
90. **:196** `One function calls them in turn and holds the intermediates.`
    → `One function calls them in turn, with the intermediates in its local variables.`
91. **:198** `by the amount of decision it holds` → `by the number of decisions in it`
92. **:201** `One module names every case of a closed set, in an exhaustive match.`
    → `Every case of a closed set is in one module, in an exhaustive match.`
93. **:215** `an idle hold can fail where the program cannot see it` → `an idle hold can fail with no sign in the program`
94. **:218** `fine for anything that never needs closing` → `fine for anything never closed`
95. **:223** `The program owns the config, so unlike every other bundle it needs no class with behaviour to hold it.`
    → `There is one config for the whole program, so unlike every other bundle it takes no class with behaviour around it.` (Q1)
96. **:227** `so the singleton rule above already permits it. That rule excludes a hardcoded default invented in a module`
    → `so the singleton rule above already allows it. Not allowed under that rule: a hardcoded default invented in a module`
97. **:229** `owes a global, which is what NAR001 catches` → `owes a global, and fails NAR001`
98. **:240** `inside the function that needs it` → `inside the function that reads it`
99. **:253** `One module names the library. Everything downstream sees a domain type.`
    → `One module imports the library. Everything downstream gets a domain type.`
100. **:262** `one frozen version fits and needs no changes` → `one frozen version fits with no changes`
101. **:263** `Adoption cannot see a package that is popular and bad.`
     → `A package can be popular and bad, and no adoption number measures that.`
102. **:265** `A library states a floor.` → `A library has a version floor.`
103. **:275** `whichever program needed it first` → `whichever program used it first`
104. **:278** `it reaches anything that can notify` → `it extends to any source with notifications`
105. **:296** `a program may name a rule it implements. … where NAR006 is its own identifier. Naming your own code is not a citation.`
     → `a program may contain the name of a rule it implements. … where NAR006 is an identifier of checks.py itself. A name from the same program is not a citation.`
106. **:302** `At the end of a long function the name says what comes out, and the reader does not scroll to the signature.`
     → `At the end of a long function, the name of the returned value is enough, and the reader does not scroll to the signature.`
107. **:303** `manufactures the rote diffing R2b-P0 forbids` → `creates the rote diffing banned by R2b-P0`
108. **:323** `Whether a bundle names a real thing.` → `Whether a bundle is a real thing.`
109. **:325** `an __all__ that names something undefined` → `an __all__ with an undefined name`

## Seen in passing, not proposed here

- **Container verbs.** The skill uses `lives` as a container verb (`it lives with the vendor`, `An
  exception type lives in the shared vocabulary`), and the check does not flag it.
- **Semicolons and dashes.** The skill's prose uses both, and the comment rules ban both. Agents
  copy the skill's prose. See SKILL.md:32 and :586.
