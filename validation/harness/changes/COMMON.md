# Rules that apply to every change request

Read this before the change request itself. Where the two disagree, the change request wins.

## An existing database must keep working

The store writes a SQLite file, and a user upgrading to your change already has one from an earlier
run. **A change that adds or alters a column must bring an existing database forward.** A run
against a database written before your change must succeed and must keep the rows already in it.

`CREATE TABLE IF NOT EXISTS` does not do this: it leaves an existing table alone, so the next insert
fails with `sqlite3.OperationalError: table <name> has no column named <new>`. Handle it however you
judge best.

**Verify it by construction**, not by reasoning: create a database with the pre-change code, run the
post-change code against that same file, and confirm both that the run succeeds and that a row
written before the change is still there.

If your change alters no column, this section does not apply and costs you nothing.

## What "existing behaviour is unchanged" means

It means **behaviour**, not bytes. Specifically:

- No finding that the program reported before your change is added, removed, or given a different
  kind, resource, or cost.
- No exit code changes for input that does not exercise your change.
- No file that was read before is now rejected, and none that was rejected is now read.

It does **not** mean byte-identical output. A change that adds a category legitimately adds that
category to a count, a column, or a JSON key, including where the count is zero. **Do not contort
the design to keep an output byte-identical** — state the output deltas your change causes and move
on.

Where a message enumerates what the program accepts, updating that enumeration is correct and is not
a behaviour change.

## Scope

Implement what the change request asks for and what this file requires. Do not take on adjacent
improvements you notice along the way. If you find a defect outside the change, **report it and
leave it**.

## Finishing

The program must run, and the change must be exercised by the fixture where the change request says
so. Report which files you changed, roughly how many lines each, what you added versus edited, and
anything you had to decide for yourself.
