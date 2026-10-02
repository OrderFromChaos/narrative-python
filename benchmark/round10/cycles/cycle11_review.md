# Comments for review

Every `#` comment block, numbered, with 8 lines before and 10 after. The comment lines are marked `>>`. Pragmas and `###` dividers are left out.

## Run 1 (package pgn_replay): 17 comments

`scratchpad/cycle11/p6_W_1/pgn_replay`

### 1. __main__.py:99

```python
     91     global LOG
     92     handler = logging.StreamHandler()
     93     handler.setFormatter(FieldFormatter())
     94     LOG.addHandler(handler)
     95     LOG.setLevel(logging.DEBUG if verbose else logging.WARNING)
     96 
     97 
     98 def readPgnText(pgn_path: Path) -> str | None:
>>   99     # read as UTF-8; the PGN standard specifies ISO 8859-1, identical to UTF-8 on ASCII
    100     try:
    101         return pgn_path.read_text(encoding='utf-8')
    102     except UnicodeDecodeError as exc:
    103         LOG.error('file.not_utf8', extra={'file': pgn_path.name, 'reason': exc.reason})
    104     except OSError as exc:
    105         LOG.error('file.unreadable', extra={'file': pgn_path.name, 'reason': exc.strerror})
    106     return None
    107 
    108 
    109 def logFileTally(file_replay: FileReplay) -> None:
```

### 2. fen.py:125

```python
    117 
    118 def _checkSquareName(raw_square: str) -> str:
    119     if len(raw_square) != 2 or raw_square[0] not in FILE_LETTERS or raw_square[1] not in '12345678':
    120         raise _rejectFen(f'en passant field {raw_square!r} is not a square')
    121     return raw_square
    122 
    123 
    124 def _parseCount(raw_count: str, field_name: str) -> int:
>>  125     # isdecimal() alone admits non-ASCII digits such as '٣'
    126     if not (raw_count.isascii() and raw_count.isdecimal()):
    127         raise _rejectFen(f'{field_name} {raw_count!r} is not a count')
    128     return int(raw_count)
    129 
    130 
    131 def _checkPlausible(position: Position) -> None:
    132     """Reject a position with a misplaced king, pawn, castling right or en passant square.
    133 
    134     Raises:
    135         FenError: a side has other than one king, a pawn is on the first or last rank, a castling
```

### 3. pgn.py:32

```python
     24 
     25 
     26 _PGN_TOKEN = re.compile(
     27     r'(?P<tag>\[\s*(?P<tag_name>\w+)\s+"(?P<tag_value>(?:[^"\\]|\\.)*)"\s*\])'
     28     r'|(?P<comment>\{[^}]*\}?|;[^\n]*)'
     29     r'|(?P<variation_start>\()'
     30     r'|(?P<variation_end>\))'
     31     r'|(?P<glyph>\$\d+)'
>>   32     r'|(?P<result>(?:1-0|0-1|1/2-1/2|\*)(?![^\s(){}]))'  # a result token ends at whitespace or a bracket
     33     r'|(?P<move_number>\d+\.+)'
     34     r'|(?P<san>[^\s(){};$]+)',
     35 )
     36 
     37 
     38 def splitPgnGames(pgn_text: str) -> tuple[PgnGame, ...]:
     39     """Split PGN text into games, in text order."""
     40     games: list[PgnGame] = []
     41     tags: dict[str, str] = {}
     42     sans: list[str] = []
```

### 4. pgn.py:52

```python
     44     for token in _PGN_TOKEN.finditer(pgn_text):
     45         kind = token.lastgroup
     46         if kind == 'tag' and sans:
     47             games.append(_buildGame(tags, sans))
     48             tags, sans = {}, []
     49 
     50         if kind == 'tag':
     51             depth = 0
>>   52             # \" and \\ in a tag value become " and \
     53             tags[token['tag_name']] = re.sub(r'\\(.)', r'\1', token['tag_value'])
     54         elif kind == 'variation_start':
     55             depth += 1
     56         elif kind == 'variation_end' and depth > 0:
     57             depth -= 1
     58         elif kind == 'result' and depth == 0 and (tags or sans):
     59             games.append(_buildGame(tags, sans))
     60             tags, sans = {}, []
     61         elif kind in ('san', 'variation_end') and depth == 0:
     62             sans.append(token[0])
```

### 5. replay.py:97

```python
     89 
     90 def _buildRepetitionKey(position: Position) -> _RepetitionKey:
     91     return _RepetitionKey(position.board, position.side_to_move, position.castling, position.en_passant)
     92 
     93 
     94 def _detectEnding(position: Position, occurrences: int) -> Ending | None:
     95     REPETITION_LIMIT = 3
     96     HALFMOVE_LIMIT = 100
>>   97     # with castling legal, the king's one-square step toward the rook is legal too, so mate tests skip castling
     98     if not legalMovesExceptCastling(position):
     99         return Ending.CHECKMATE if inCheck(position) else Ending.STALEMATE
    100     if occurrences >= REPETITION_LIMIT:
    101         return Ending.THREEFOLD_REPETITION
    102     if position.halfmove_clock >= HALFMOVE_LIMIT:
    103         return Ending.FIFTY_MOVE_RULE
    104     return None
    105 
    106 
    107 def _buildReplayedGame(
```

### 6. rules.py:29

```python
     21 _PROMOTION_KINDS = (PieceKind.KNIGHT, PieceKind.BISHOP, PieceKind.ROOK, PieceKind.QUEEN)
     22 
     23 
     24 def legalMovesExceptCastling(position: Position) -> list[Move]:
     25     return [move for move in pseudoLegalMoves(position) if not kingExposed(position, move)]
     26 
     27 
     28 def pseudoLegalMoves(position: Position) -> Iterator[Move]:
>>   29     # moves that may leave the mover's king in check
     30     for origin in ALL_SQUARES:
     31         piece = position.board[origin]
     32         if piece is not None and piece.color is position.side_to_move:
     33             yield from _generatePieceMoves(position, origin, piece.kind)
     34 
     35 
     36 def _generatePieceMoves(position: Position, origin: Square, kind: PieceKind) -> Iterable[Move]:
     37     match kind:
     38         case PieceKind.PAWN:
     39             return _generatePawnMoves(position, origin)
```

### 7. rules.py:106

```python
     98     """Generate the moves of a bishop, a rook or a queen, along each of directions up to a piece."""
     99     for direction in directions:
    100         for target in _traceRay(position, origin, direction):
    101             if _enterable(position, target):
    102                 yield Move(kind, origin, target, None)
    103 
    104 
    105 def _traceRay(position: Position, origin: Square, direction: tuple[int, int]) -> Iterator[Square]:
>>  106     # the squares along a direction, up to and including the first occupied one
    107     file_step, rank_step = direction
    108     square = shiftSquare(origin, file_step, rank_step)
    109     while square is not None:
    110         yield square
    111         if position.board[square] is not None:
    112             return
    113         square = shiftSquare(square, file_step, rank_step)
    114 
    115 
    116 def _enterable(position: Position, target: Square) -> bool:
```

### 8. rules.py:121

```python
    113         square = shiftSquare(square, file_step, rank_step)
    114 
    115 
    116 def _enterable(position: Position, target: Square) -> bool:
    117     return position.board[target] is None or _capturable(position, target)
    118 
    119 
    120 def _capturable(position: Position, target: Square) -> bool:
>>  121     # a FEN can leave the side not to move in check; capturing its king would leave a board without one
    122     occupant = position.board[target]
    123     return occupant is not None and occupant.color is not position.side_to_move and occupant.kind is not PieceKind.KING
    124 
    125 
    126 def kingExposed(position: Position, move: Move) -> bool:
    127     after = _movePieces(position, move)
    128     mover = position.side_to_move
    129     return attackedBy(after, locateKing(after, mover), invertColor(mover))
    130 
    131 
```

### 9. rules.py:160

```python
    152             ray = tuple(_traceRay(position, square, direction))
    153             if ray and position.board[ray[-1]] in (Piece(attacker, kind), queen):
    154                 return True
    155 
    156     return False
    157 
    158 
    159 def locateKing(position: Position, color: Color) -> Square:
>>  160     # a position always has one king of each color
    161     king = Piece(color, PieceKind.KING)
    162     return next(square for square in ALL_SQUARES if position.board[square] == king)
    163 
    164 
    165 def capturing(position: Position, move: Move) -> bool:
    166     en_passant_capture = move.kind is PieceKind.PAWN and move.target == position.en_passant
    167     return position.board[move.target] is not None or en_passant_capture
    168 
    169 
    170 def describeCastlingObstacle(position: Position, right: CastlingRight) -> str | None:
```

### 10. rules.py:260

```python
    252         castling=frozenset(right for right in position.castling if not _castlingRightRevoked(right, move)),
    253         en_passant=en_passant,
    254         halfmove_clock=0 if reset_clock else position.halfmove_clock + 1,
    255         fullmove_number=position.fullmove_number + (1 if mover is Color.BLACK else 0),
    256     )
    257 
    258 
    259 def _castlingRightRevoked(right: CastlingRight, move: Move) -> bool:
>>  260     # a move from or onto the king's or the rook's home square ends the right
    261     squares = locateCastlingSquares(right)
    262     return bool({move.origin, move.target} & {squares.king_from, squares.rook_from})
    263 
    264 
    265 def normaliseEnPassant(position: Position) -> Position:
    266     target = position.en_passant
    267     if target is None:
    268         return position
    269 
    270     backward = -lookupPawnDirection(position.side_to_move)
```

### 11. rules.py:308

```python
    300         case Color.WHITE:
    301             return 1
    302         case Color.BLACK:
    303             return -1
    304 
    305 
    306 ### vocabulary #########################################################################
    307 
>>  308 _Steps = tuple[tuple[int, int], ...]  # (file step, rank step) pairs
```

### 12. squares.py:46

```python
     38     return square // BOARD_SIZE
     39 
     40 
     41 def formatSquare(square: Square) -> str:
     42     return f'{FILE_LETTERS[getFileIndex(square)]}{getRankIndex(square) + 1}'
     43 
     44 
     45 def parseSquare(square_name: str) -> Square:
>>   46     # callers pass a name that matched [a-h][1-8]
     47     return makeSquare(FILE_LETTERS.index(square_name[0]), int(square_name[1]) - 1)
```

### 13. vocabulary.py:10

```python
      2 
      3 from __future__ import annotations
      4 
      5 from dataclasses import dataclass
      6 from enum import Enum
      7 from typing import NewType
      8 
      9 
>>   10 Square = NewType('Square', int)  # a1 = 0, b1 = 1, a2 = 8, h8 = 63
     11 
     12 
     13 class Color(Enum):
     14     WHITE = 'w'
     15     BLACK = 'b'
     16 
     17 
     18 class PieceKind(Enum):
     19     PAWN = 'p'
     20     KNIGHT = 'n'
```

### 14. vocabulary.py:80

```python
     72     king_to: Square
     73     rook_from: Square
     74     rook_to: Square
     75     between: tuple[Square, ...]
     76 
     77 
     78 @dataclass(frozen=True)
     79 class Position:
>>   80     board: tuple[Piece | None, ...]  # indexed by Square
     81     side_to_move: Color
     82     castling: frozenset[CastlingRight]
     83     en_passant: Square | None  # set only when an en passant capture onto it is legal
     84     halfmove_clock: int
     85     fullmove_number: int
     86 
     87 
     88 @dataclass(frozen=True)
     89 class Move:
     90     kind: PieceKind
```

### 15. vocabulary.py:83

```python
     75     between: tuple[Square, ...]
     76 
     77 
     78 @dataclass(frozen=True)
     79 class Position:
     80     board: tuple[Piece | None, ...]  # indexed by Square
     81     side_to_move: Color
     82     castling: frozenset[CastlingRight]
>>   83     en_passant: Square | None  # set only when an en passant capture onto it is legal
     84     halfmove_clock: int
     85     fullmove_number: int
     86 
     87 
     88 @dataclass(frozen=True)
     89 class Move:
     90     kind: PieceKind
     91     origin: Square
     92     target: Square
     93     promotion: PieceKind | None
```

### 16. vocabulary.py:109

```python
    101     setup: str | None
    102     fen: str | None
    103     sans: tuple[str, ...]
    104 
    105 
    106 @dataclass(frozen=True)
    107 class IllegalMove:
    108     ply: int
>>  109     san: str | None  # None when the start position is unusable and the game has no moves
    110     reason: str
    111 
    112 
    113 @dataclass(frozen=True)
    114 class ReplayedGame:
    115     white: str | None
    116     black: str | None
    117     plies: int
    118     fen: str | None  # None when the start position is unusable
    119     ending: Ending
```

### 17. vocabulary.py:118

```python
    110     reason: str
    111 
    112 
    113 @dataclass(frozen=True)
    114 class ReplayedGame:
    115     white: str | None
    116     black: str | None
    117     plies: int
>>  118     fen: str | None  # None when the start position is unusable
    119     ending: Ending
    120     result: GameResult
    121     declared: str | None
    122     illegal: IllegalMove | None
    123     result_mismatch: bool
    124 
    125 
    126 @dataclass(frozen=True)
    127 class FileReplay:
    128     file_name: str
```

## Run 2 (package pgnreplay): 3 comments

`scratchpad/cycle11/p6_W_2/pgnreplay`

### 18. geometry.py:44

```python
     36     return square // BOARD_WIDTH
     37 
     38 
     39 def parseFileLetter(file_letter: str) -> int:
     40     return FILE_LETTERS.index(file_letter)
     41 
     42 
     43 def parseSquareName(square_name: str) -> Square:
>>   44     # the caller has matched square_name against [a-h][1-8]
     45     return makeSquare(parseFileLetter(square_name[0]), int(square_name[1]) - 1)
     46 
     47 
     48 def formatSquareName(square: Square) -> str:
     49     return f'{FILE_LETTERS[fileOf(square)]}{rankOf(square) + 1}'
```

### 19. pgn.py:46

```python
     38     in_movetext = False
     39     depth = 0
     40     for token in TOKEN.finditer(pgn_text):
     41         kind = token.lastgroup
     42         if kind == 'tag':
     43             if in_movetext:
     44                 games.append(_buildGame(tags, sans))
     45                 tags, sans, in_movetext, depth = {}, [], False, 0
>>   46             # PGN escapes a quote or a backslash in a tag value with a backslash
     47             tags[token['name']] = re.sub(r'\\(.)', r'\1', token['value'])
     48         elif kind == 'result' and depth == 0:
     49             games.append(_buildGame(tags, sans))
     50             tags, sans, in_movetext = {}, [], False
     51         elif kind == 'open':
     52             depth += 1
     53             in_movetext = True
     54         elif kind == 'close':
     55             depth = max(depth - 1, 0)
     56         elif kind in ('number', 'word'):
```

### 20. rules.py:208

```python
    200         occupant = position.board[target]
    201         if (occupant is not None and _enterable(occupant, pawn.color)) or target == position.en_passant:
    202             targets.append(target)
    203 
    204     return targets
    205 
    206 
    207 def _enterable(occupant: Piece | None, mover: Color) -> bool:
>>  208     # a FEN may start with the side not to move in check; capturing that king would make inCheck() raise ValueError
    209     return occupant is None or (occupant.color is not mover and occupant.kind is not Kind.KING)
    210 
    211 
    212 def _movePieces(position: Position, move: Move) -> Board:
    213     squares = list(position.board)
    214     squares[move.origin] = None
    215     if _enPassantCapture(position, move):
    216         squares[geometry.makeSquare(geometry.fileOf(move.target), geometry.rankOf(move.origin))] = None
    217 
    218     if move.piece.kind is Kind.KING:
```
