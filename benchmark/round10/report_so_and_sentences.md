# `, so` and single-sentence comments

Data: the 87 `#` comment blocks of cycles 7 to 11 (`cycles/`) against 21,977 human blocks from
CPython, mypy, pylint and astroid. Your verdicts come from R10-rating9 to R10-rating12.

## `, so` is not a fault

**Your verdicts.** Cycles 7 to 11 have 12 comments with `, so`. You rated 10 of them: 9 fine or
better (`source is left out of comparison and hashing, so a resent event compares equal to the
first copy`: "very good"), and 1 cut for its content (`canonical JSON, so policy files that differ
only in layout name one policy`: "premature reassurance").

**Half the gap is what the comments are for.** A comment that gives a reason is 34% of the skill's
comments and 18% of human ones. The skill writes few labels, TODOs or notes, so reasons dominate,
and `, so` comes with reasons. Human reason comments use it the same way: `int allows a leading +/-
as well as surrounding whitespace, so we ensure that isn't the case`.

**The other half is one habit.** Among reason comments only:

| connector | human | this skill |
|---|---|---|
| colon (`zoneinfo raises IsADirectoryError: …`) | 48% | 10% |
| `, so` | 16% | 40% |
| `since` | 13% | 0% |
| `because` | 12% | 0% |
| `to avoid` / `in case` | 10% | 0% |
| `otherwise` | 5% | 0% |
| `would` (counterfactual) | 6% | 33% |
| `without X, Y` | 0% | 23% |

The skill states the fact, then the consequence: `X, so Y` or `without X, Y`. Humans also state the
purpose first: `to avoid a duplicate row per run`, `in case the file is empty`. The Fence form rule
(R10-fence-form) asks for the counterfactual, so part of this is the rule working. No change
proposed: the comments are rated well, and the monotony is mild.

## Single sentences: one rule caps the depth

**What humans write in two or more sentences.** 15% of human blocks, median 29 words. Of 30 random
ones:

| kind | count | under the skill |
|---|---|---|
| an outside fact or constraint, then what the code does about it | 11 | wanted, but capped at one sentence |
| an algorithm or proof (premise, then method) | 3 | wanted for a novel method (**Depth**) |
| a function or field described in a comment | 10 | moved to docstrings, or cut |
| TODO, notes, chatter | 3 | markers only |
| history, license | 3 | banned |

The first kind is the one that matters. Two examples:

> On API level 30 and higher, Logcat will strip any number of leading newlines. [...] Work around
> this by adding a leading space, which shouldn't make any difference to the log's usability.

> The operation has completed, so no need to postpone the work. We cannot take this short cut if we
> need the NumberOfBytes, CompletionKey values returned by PostQueuedCompletionStatus().

**Your ratings asked for this kind three times:**
- `logging.NullHandler()`: "the choice to use it should be explained, along with the warning that
  it blocks stderr output as well" (R10-rating3)
- `order matters: a repeated resource_id is accepted from the first file only`: "needs to help the
  dev understand if they need to take a positive action" (R10-rating4)
- a 7-line regex: "complex enough to have a brief comment before the block" (R10-rating12)

**The cause.** **Depth** says "in proportion to the idea's difficulty for the reader, and one step
of reason". "One step of reason" is one of the two generalisations the round README lists as
unconfirmed: it came from one rewrite (R10-seed-2) and a question about reader expertise
(R10-Q16). With dashes and semicolons banned, and a one-line comment taking no period, a second step
can only fit as `, so` on the same line, or as a multi-line block, which the agents never wrote.

## Proposal

Replace the **Depth** line. Applied as R10-depth-sentences, with an example taken from R10-rating3
in place of the Logcat one:

> **Depth:** in proportion to the idea's difficulty for the reader. When the reader needs the
> consequence or the action as well as the fact, write a second sentence, as a block of full
> sentences. A one-line comment stays one clause.

```python
# logging.NullHandler() stops the last-resort handler from printing this package's warnings.
# They reach stderr only when the calling program configures logging.
LOG.addHandler(logging.NullHandler())
```
