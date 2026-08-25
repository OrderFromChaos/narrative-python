# Change C3 — exempt a team from the reconciliation

> Read `COMMON.md` first. It states the database and unchanged-behaviour rules that apply to
> every change request.

Some teams run their own billing and must not appear in this report.

## The new rules field

`reconcile.json` gains one optional key:

```json
{
  "ignored_skus": ["support-plan"],
  "ignored_teams": ["platform-infra"],
  "region_aliases": {"us-east-1": "use1"},
  "grace_cents": 500
}
```

**`ignored_teams`** — a scanned resource whose `team` is in this list takes part in no join and
appears in no finding. It behaves exactly as `ignored_skus` does, except that it matches on the team
rather than on the sku.

The key is optional. A rules file that omits it behaves as it does today.

## Note on the asymmetry

Only one of the two formats carries a team. A billing record therefore can never be excluded by this
field on its own evidence. Decide what happens to a billing record whose matching scanned resource
was excluded by `ignored_teams`, and say what you decided and why.

## What must be true afterwards

- A scanned resource whose team is listed produces no finding of any kind.
- A rules file with no `ignored_teams` key behaves exactly as before.
- Everything else behaves exactly as it did before, in the sense `COMMON.md` defines.
