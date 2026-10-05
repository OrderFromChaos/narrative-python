# Proposals from rating 14 (new-rules cycle)

Source: the user's notes on `cycles/newrules_review.md`. Numbers below are the review file's.
Each proposal is a line for `skill/SKILL.md`. 1, 2, 4, 5 and 6 are applied. 3 is replaced by R10-branch-comment.

## Answers first

**#9 is not a bug.** `timestamp()` is seconds since the Unix epoch, so sorting by it orders by
instant. Tested with pendulum on America/New_York, 2028-11-05:

```
2028-11-05T00:50:00-04:00 1857012600.0
2028-11-05T01:30:00-04:00 1857015000.0
2028-11-05T01:45:00-04:00 1857015900.0
2028-11-05T01:15:00-05:00 1857017700.0
2028-11-05T01:30:00-05:00 1857018600.0
```

01:45 before the change sorts before 01:15 after it. The two 01:30 compare equal with `==`, as the
comment says. The comment never says that `timestamp()` is the instant, so the fix is not visible
from it.

**#6 is intended behaviour.** The task asks for both copies of the repeated hour to be one hourly
period. The comment reads as a warning, but the case is handled, by design, in the line below.

**#28** guards against Python 3.12.1 and later, where `Server.wait_closed()` waits for every open
connection. The package targets 3.11 and also ran on 3.14, so the guard applies to newer runtimes.

**#25.** `popitem()` on an empty `OrderedDict` raises `KeyError`. The loop is safe only because
`store()` and `applyDelta()` reject an oversized item first.

## Proposals

### 1. Expected form in a format error

Rule, under **Errors** or the docstring rules:

> An error for malformed input names the expected form: `bad --now value '2028-11-05' (expected
> "2028-11-05T08:00:00Z")`. Or show it in the docstring.

From #1.

### 2. A sample next to a regex

Rule, under **Decoding aid**:

> A regex gets a sample string it matches, and one it rejects when the boundary is not obvious:
> `# matches: search_v2, db-host. Rejects: x.y`. A developer can paste them into regex101.

From #22.

### 3. A fence says whether the case is handled

Rule, under **Fence**:

> Say whether the code below handles the case or a later change must not break it. `# by design,
> both copies of the repeated hour are one period. The key has no UTC offset`, not `# the key has
> no UTC offset. When DST ends, both copies of the repeated hour are one period`.

From #6, #9 and #17. #9 rewritten: `# sort by timestamp(), the instant. Datetimes that share a tzinfo
compare by wall clock. The two 01:30 at the end of DST compare equal`. #17 rewritten:
`# tz=None keeps TOML local times without a UTC offset. pendulum.instance() adds UTC by default`.

### 4. Check a cheap invariant instead of citing another function

Extend the **Never** item "guarantees about other modules" to other functions, and add the remedy:

> a guarantee about another function. If the code depends on it and the check is cheap, check it
> here: `while self.items and …`, not `# store() rejects an oversized item, so the cache is never
> empty`.

From #23 and #25.

### 5. Version guards name the version

Rule, under **Sentence form** or the 3.11 section:

> A guard for a runtime newer than the floor names the version: `# on 3.12.1 and later,
> wait_closed() waits for open connections`.

From #28.

### 6. Positive guards

Rule, under code style:

> Write a skip guard as the negation of what a valid entry is: `if not (name_match and
> entry.is_file() and not entry.is_symlink()):`, not `if name_match is None or
> entry.is_symlink() or not entry.is_file():`.

From the user's note on the snapshot listing.

## No rule needed

- #19: cut. It adds nothing over the code.
- #23: rename to jargon (`self.lru_items`, `self.expiry_heap`) and drop both comments. **Rename
  first** covers it.
- #29: `unbounded` → over the limit. A word choice.
- #17: `without one` → `without a UTC offset`. A word fix, covered by the rewrite in proposal 3.
