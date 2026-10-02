# Proposed rules from the pruner review (R10-rating10)

Two proposals and one observation. Reply with the numbers you approve and any edits.

## 1. A hard comment means the code needs rewriting

**Where:** `SKILL.md`, **Comments**, step 2 ("Guarantee it in code"), next to the footgun rule.

> If explaining how the code works takes more than one plain clause, rewrite the code instead:
> name the step, or use the obvious construct. A `dict` filled with `setdefault()` and sliced by
> insertion order becomes an explicit loop that counts periods.

**From:**

| rating | comment | your verdict |
|---|---|---|
| R10-rating10, 14 | `a period ranks by its newest snapshot, and newest-first input inserts periods in that order` | "This is a rather strange function in general, not exactly clear what it does. Why .setdefault?" |
| R10-rating3, 10 | `list before reading rules: a missing input_dir would otherwise report as a missing rules file` | "maybe this is trying to explain counterintuitive internals of a function, in which case the function itself should just be changed" |

## 2. A fact about one function's use of a type goes with that function

**Where:** `SKILL.md`, **Comments**, Never list, beside "guarantees about other modules".

> how one function uses a type, written on the type: `member order is the order plan.json lists a
> snapshot's rules` belongs to the function that writes plan.json, or nowhere if that function
> states the order itself.

**From:** item 9: "that is a property of `_describePolicy` in this case".

## Observation: agent verbs still slip through

Two of the four faulted comments use agent verbs on abstract subjects, which the written rule
already bans: `policy files … name one policy` (item 3) and `a period ranks` (item 14). `NAR016`
lints only `hold` and `carry`. Linting `name`/`names` or `rank`/`ranks` would also flag correct
uses (`--rules names another path` is the spec's own wording), so I propose no change here. Item 3
also fails the existing Fence test: the dict is built from a dataclass, so no "layout" difference
can reach `json.dumps()`, and dropping `sort_keys` would break nothing.
