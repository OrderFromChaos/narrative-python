# Does the Narrative style make code longer?

## Why

Earlier numbers were confounded. The validation `base` arms wrote embedded test suites nobody asked
for (758 lines for V2, ~190 of them tests) while the `skill` arm was not asked for tests. That
comparison flattered the skill.

## Control

Both arms get identical task text and identical constraints: **single file, must run, no test
suite**. The only difference is whether the Narrative skill is supplied.

Length is decomposed, because "longer" is not one thing:

| measure | what it means |
|---|---|
| `code` | non-blank, non-comment, non-docstring lines — actual logic |
| `docstring` | lines inside docstrings |
| `comment` | `#` lines |
| `blank` | blank lines |

The interesting question is not total lines. It is whether the style adds **logic** or only
**documentation and whitespace**. Docstrings and blank lines are cheap to skim; more branches and
more helpers are not.
