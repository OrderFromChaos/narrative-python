# Proposal 2, reworked: what the comments have in common

## The cases

Each comment below is accurate, and each was trimmed, cut or called confusing.

| rating | comment as written | your verdict |
|---|---|---|
| R10-rating9, 7 | `None when a malformed line names no customer as a string` | `None when malformed` |
| R10-rating6, 7 | `member order is the order of the report's findings and of its by_kind object` | cut the `by_kind` clause; `member order is the report's order` |
| R10-rating4, 5 | `member order is the report's order of findings and of by_kind` | `member order matches the report's order` |
| R10-rating5, 1 | `line_num is the line on which the row just read ends` | cut: "makes reading this snippet take like twice as long" |
| R10-rating4, 3 | `adds the file's accepted records to the dict for its side` | muddled: "'for its side' doesn't make any sense" |
| R10-rating3, 12 | `line_num after each row, so a problem names the line a reader sees in an editor` | cut |

## The general problem

The comment reports the code's internal detail: which check runs, which structure is filled, which
attribute is read. The reader needs the concept that detail adds up to: malformed, report order, the
line number. The detail is what the agent saw while writing, so this is a small thinking trace inside
an otherwise valid comment.

## Two framings

### A. The conclusion, not the derivation

> State what the code means, not how it gets there: `None when malformed`, not `None when a
> malformed line names no customer as a string`. If a clause names an internal check, structure or
> attribute, cut it unless the reader needs it to act.

This generalises the Decoding aid's existing "State the intent, not the mechanism" to every comment.

### B. The level of the thing commented

> Write at the level of the thing commented. A field's note uses the record's terms (`malformed`,
> `report order`), not the parser's (`names no customer as a string`, `by_kind object`).

This is narrower: it targets field and return notes, where most of the cases above occur.

## Recommendation

A. It covers all six cases. B misses the two `line_num` comments, which sit on statements, not
fields.
