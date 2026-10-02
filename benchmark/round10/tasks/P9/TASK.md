# Task P9 — terminal text wrapping

A library that measures and wraps text for a fixed-width terminal, counting display columns rather
than code points.

A library only, with no command line. Use the standard library only. Include tests.

## The functions

- `displayWidth(text: str) -> int`: the number of terminal columns the text takes.
- `wrap(text: str, width: int) -> list[str]`: the text broken into lines of at most `width` columns.

## Width

- A character whose East Asian Width is W or F takes 2 columns.
- These take 0 columns: a combining character (`unicodedata.combining` is not 0), U+200B zero width
  space, U+200D zero width joiner, U+FE00 to U+FE0F variation selectors, U+00AD soft hyphen, and an
  ANSI SGR escape sequence (`ESC [`, digits and semicolons, `m`).
- Every other printable character takes 1 column, including U+00A0 no-break space.
- Any other control character, and any other escape sequence, raises `ValueError`. Newline is
  allowed in `wrap` and raises in `displayWidth`.
- A **cluster** is a character followed by the zero-width characters after it, other than SGR
  sequences and soft hyphens. A cluster is never split, and its width is the sum of its
  characters' widths.

## Wrapping

- `\n` is a hard break. Each paragraph is wrapped separately, and an empty paragraph is an empty
  line.
- A line may break after a run of U+0020 spaces, or at a soft hyphen. U+00A0 is not a break.
- The spaces at a break are dropped. Spaces inside a line are kept as they are.
- A soft hyphen where the line breaks is shown as `-`, and that column counts toward the width. A
  soft hyphen where the line does not break is removed from the output.
- A word wider than the line breaks between clusters, as late as possible. A 2-column cluster that
  would cross the right edge moves to the next line, so that line ends one column short.
- **A style continues across a break.** When an SGR style is active at a break, the line ends with
  `ESC[0m` and the next line starts with every SGR sequence since the last reset, in order. A reset
  is `ESC[0m` or `ESC[m`.
- `width` below 2 raises `ValueError`.

## What is left to you

The package and module layout, error messages, and any behaviour this specification does not fix.

## The fixture

`fixture/cases.json` has `displayWidth` and `wrap` cases with their expected results, as JSON with
`\u` escapes. Its cases: CJK text with no spaces, a combining accent, a soft hyphen used and unused,
a no-break space, a bold style that crosses a break, hard breaks with an empty paragraph, a word
longer than the line, inner runs of spaces, a zero width space and a tab.
