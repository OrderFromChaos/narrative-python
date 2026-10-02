# Task P6 — chess game replayer

Replay chess games from PGN files move by move, stop each game at its first illegal move, and report
how every game ends.

Use no chess library: the standard library and `pendulum` only.

## Inputs

An input directory of `*.pgn` files, read in basename order. A file has one or more games. A game is
a block of tag pairs, `[Name "value"]` one per line, followed by movetext:

```
[Event "Club night"]
[White "Ada"]
[Black "Grace"]
[Result "1-0"]

1. e4 e5 2. Bc4 {the bishop eyes f7} Nc6 3. Qh5 Nf6 (3... g6) 4. Qxf7# $1 1-0
```

- A game starts from the standard position, or from the position in its `FEN` tag when it also has
  `[SetUp "1"]`.
- Movetext has move numbers (`1.`, `3...`), moves in standard algebraic notation (SAN), comments in
  braces, variations in parentheses (which may nest), numeric annotation glyphs (`$1`), and ends with
  a result token: `1-0`, `0-1`, `1/2-1/2` or `*`.
- Comments, variations and glyphs are skipped; only the main line is replayed.
- A SAN move may end in `+`, `#`, `!`, `?` or a combination; these suffixes are ignored.

## What it does

1. **Replay** each move of the main line. A move is **illegal** when its SAN does not parse, when
   no piece can make it, when more than one piece can and the SAN has no file or rank to tell them apart, or when it
   leaves the mover's king in check. The game stops at its first illegal move.
2. **The chess rules that matter here:**
   - Castling is illegal when the king or that rook has moved, when that rook has been captured, when
     a square between them is occupied, or when the king is in check, passes through an attacked
     square or lands on one.
   - En passant is legal only on the move right after the opponent's two-square pawn step.
   - A piece pinned to its king does not count when deciding whether a SAN move must include a
     file or rank to identify the piece: with knights on b1 and e2 and the e2 knight pinned, `Nc3` is
     the b1 knight.
   - A pawn reaching the last rank promotes to the piece named in the SAN (`a8=N`); a promotion
     without `=` and a piece is illegal.
3. **Ending.** After each legal move, the game ends as:
   - **checkmate** or **stalemate**;
   - **threefold repetition** when the same position occurs for the third time. Two positions are
     the same when the pieces, the side to move, the castling rights and the en passant square are
     the same. The en passant square counts only when an en passant capture onto it is legal, here
     and in the FEN field;
   - **fifty-move rule** when the halfmove clock reaches 100.
   A game that ends this way and has further moves is reported at the ending; the moves after it are
   not replayed. A game whose moves run out first is **in progress**.
4. **Result.** Checkmate gives `1-0` or `0-1`; stalemate, threefold repetition and the fifty-move rule
   give `1/2-1/2`; an illegal move or a game in progress gives `*`. A game whose `Result` tag differs
   from this result has a **result mismatch**, except when the game is in progress.

## The outputs

`games.json`, written with `json.dumps(report, indent=2) + '\n'`:

```json
{
  "input_dir": "fixture",
  "games": [
    {"file": "openings.pgn", "game": 1, "white": "Ada", "black": "Grace", "plies": 7,
     "fen": "r1bqkb1r/pppp1Qpp/2n2n2/4p3/2B1P3/8/PPPP1PPP/RNB1K1NR b KQkq - 0 4",
     "ending": "checkmate", "result": "1-0", "declared": "1-0", "illegal": null}
  ],
  "totals": {"games": 1, "illegal": 0, "mismatches": 0}
}
```

`games` is in file order, then game order. `game` counts from 1 within its file. `plies` is the
number of legal moves replayed. `fen` is the position after the last legal move, in Forsyth–Edwards
Notation with all six fields. `ending` is one of `checkmate`, `stalemate`, `threefold repetition`,
`fifty-move rule`, `in progress` or `illegal move`. `illegal` is `null`, or
`{"ply": 9, "san": "O-O-O", "reason": "..."}` where `ply` counts from 1. A missing `White` or `Black`
tag is `"?"`. `input_dir` is the argument as typed.

A summary on stdout: one line per game, then the totals.

Exit codes: 0 when no game has an illegal move or a result mismatch, 1 otherwise, 2 when the input
directory is missing or has no `*.pgn` file.

The replay must also be importable: another program calls one function with PGN text and gets the
replayed games back.

## What is left to you

The package and module layout, the `reason` wording, the summary layout, logging, and any behaviour
this specification does not fix.

## The fixture

`fixture/` has three PGN files. Its cases: a checkmate, a stalemate, castling through an attacked
square, en passant one move too late and in time, a pinned knight that makes disambiguation
unnecessary, an underpromotion with capture, a repetition that becomes threefold only once the
castling rights match, the fifty-move rule from a FEN start, comments, nested variations and
glyphs, a SAN that does not parse, and a declared result that is wrong.
