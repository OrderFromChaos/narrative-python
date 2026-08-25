# Change C5 — a fourth inventory format

> Read `COMMON.md` first. It states the database and unchanged-behaviour rules that apply to
> every change request.
>
> **This change starts from the program as C1 left it.** The tool already reads three formats.

A third finance system exports charges. Read it alongside the three formats the tool already
handles.

## The format

Files named `*.charges.psv`. Pipe-separated, with a header row:

    # exported by charges-svc
    resource_id|sku|monthly_cents|region
    i-0001|compute-gpu|250000|us-east-1
    i-0002|object-store|1200|us-west-2

The header row is required, and a file whose header is not those four names in that order is
malformed. A line whose first non-whitespace character is `#` is a comment, and may appear before or
after the header. A blank line holds nothing.

The four fields are the same four the other cost formats carry, and they are **valid under the same
rules**: the same emptiness checks, the same integer check on `monthly_cents`, the same rejection
messages.

Like the other cost exports, this format **carries a cost and names no owning team.**

## What must be true afterwards

- A `*.charges.psv` file in the input directory is read and its records take part in the join
  exactly as the other cost formats do.
- A malformed `*.charges.psv` is reported per-file, and does not stop the other files.
- A line that fails a field rule is rejected and counted, with the same message the other cost
  formats produce for that failure.
- A directory holding no `.charges.psv` behaves exactly as it did before, in the sense `COMMON.md`
  defines.

Do not change the three formats that already work.
