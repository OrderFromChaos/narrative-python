# NAR003 follow-up — ">3 args goes multiline" applied to calls

Four real versions of `skill/checks.py`, same code, differing only in how the doc's
*"if any call or definition is longer than 3 args, put args on separate lines even if it doesn't
go over the 120 character limit"* rule is scoped.

Each was produced by inserting a magic trailing comma into the targeted constructs and running the
real `ruff format` with your config. This is exactly what the toolchain does, not an approximation.

| file | rule scope | lines | vs current |
|---|---|---|---|
| `current.py` | not applied to calls (what is committed today) | 318 | — |
| `defonly.py` | `def` signatures only, calls exempt | 324 | +6 |
| `col100.py` | defs, plus calls whose line exceeds 100 columns | 357 | **+39** |
| `strict.py` | defs and every call with >3 args | 378 | **+60 (+19%)** |

Open them side by side. The measurement that matters is not the line count, it is what the code
reads like.

## The same function under each regime

```python
# current.py and defonly.py -- identical here
        if isinstance(first, ast.Name) and first.id == 'self':
            findings.append(Finding(path, node.lineno, 'NAR002', 'declare the attribute in __init__ instead'))
    return findings


# col100.py and strict.py -- identical here
        if isinstance(first, ast.Name) and first.id == 'self':
            findings.append(
                Finding(
                    path,
                    node.lineno,
                    'NAR002',
                    'declare the attribute in __init__ instead',
                )
            )
    return findings
```

**Note the compounding.** One 110-column line becomes seven. It is not a 4-way split — exploding
the inner `Finding(...)` makes the outer `findings.append(...)` no longer fit either, so both
explode. Any nested call hits this.

The narrowest offender in the file is 73 columns:

```python
findings.append(Finding(path, func.lineno, 'NAR001', detail))
```

Under `strict` that also becomes seven lines.

## Recommendation

`defonly`. The rule earns its keep on signatures — a signature is a contract, it is read far more
often than it is written, and one-arg-per-line makes diffs of a changing contract clean. A call is
an expression; splitting `Finding(path, func.lineno, 'NAR001', detail)` across six lines does not
tell the reader anything the single line did not, and it pushes the surrounding logic apart.

`col100` is the compromise if you want the rule to reach calls at all: it leaves the 73-column
cases alone and only touches lines that were getting long anyway. It still costs 39 lines here.

Your doc hedges on exactly this clause — *"In general... is preferred for readability"* — where the
surrounding rules are flat imperatives. That reads like it was already a Suggestion.

---

# Separate finding: the formatter destroys packed collection literals

Not part of the NAR003 question, but found while producing these files, and it affects a pattern
your existing code uses.

```python
# written like this
MUTATING_METHODS = frozenset({
    'append', 'extend', 'insert', 'remove', 'pop', 'clear', 'sort', 'reverse',
    'update', 'setdefault', 'popitem', 'add', 'discard',
})

# ruff format makes it this -- 5 lines becomes 20, one item per line
MUTATING_METHODS = frozenset(
    {
        'append',
        'extend',
        ...
    }
)
```

Your own corpus has this pattern — a packed word-list constant in the existing corpus is
a 17-word list packed onto 2 lines. Under the formatter it becomes **19 lines**.

Tested and ruled out: **omitting the trailing comma does not help.** Both the with-comma and
without-comma versions explode identically. Once a collection literal does not fit on one line,
`ruff format` always goes one item per line.

The only escape is an explicit fence:

```python
# fmt: off
COMMON_WORDS_FOR_TAG_FILTER = [
    'the', 'of', 'to', 'how', '2', '3', 'a', 'is', 'and', 'new', 'in', 'on',
    'i', 'for', 'are', 'can', 'at',
]
# fmt: on
```

Verified to work. So the options are: accept one-item-per-line for all collections, or spend a
`# fmt: off` fence on the word-list-shaped ones where packing genuinely reads better. This is the
same category as the two blank lines between methods — a formatter fight, decided on whether the
rule is worth the friction.
