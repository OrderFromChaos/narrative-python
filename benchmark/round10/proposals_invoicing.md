# Proposed rules from the invoicing review (R10-rating9)

Four proposals, all for **Sentence form** in `SKILL.md`, **Comments**. Reply with the numbers you
approve and any edits.

## 1. No intensifiers

> Drop a word that only stresses: `exactly`, `always`, `precisely`, `simply`. Keep it when the
> sentence means something else without it: `exactly two decimal places`.

**From:** item 6, `None exactly when kind is CANCEL` → drop "exactly". Absolutes were 19× more
frequent in Claude's comments than in human Python (round 10 keyness).

**Not lintable:** `exactly two decimal places` is a correct use, so a check would need `noqa` often.

## 2. The domain term over its definition

> Name a case by its term when the code has one: `None when malformed`, not `None when a malformed
> line names no customer as a string`.

**Where:** extends the existing bullet "trade terms over paraphrase".

**From:** item 7.

## 3. No clipped terms

> Write the full term when a short form is ambiguous: `timezone`, not `zone`.

**From:** item 10: "a customer could be in many other kinds of date based zones".

## 4. Placement of a comment on an argument

> A comment on an argument goes above the call that passes it: above `pendulum.parse(raw_at,
> tz=None)`, not below the `try` block.

**Where:** extends the existing placement bullet, which already says "inside `try:`, above the
call it concerns".

**From:** item 16. This is the second placement miss next to a `try` (R10-rating6 item 4), so the
existing bullet did not prevent it.
