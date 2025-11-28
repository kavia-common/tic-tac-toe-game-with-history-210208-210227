from __future__ import annotations

from typing import List, Optional, Tuple

Cell = Optional[str]  # 'X' | 'O' | None
Player = str          # 'X' | 'O'

WIN_LINES: Tuple[Tuple[int, int, int], ...] = (
    (0, 1, 2),
    (3, 4, 5),
    (6, 7, 8),
    (0, 3, 6),
    (1, 4, 7),
    (2, 5, 8),
    (0, 4, 8),
    (2, 4, 6),
)


# PUBLIC_INTERFACE
def empty_board() -> List[Cell]:
    """Return a fresh 3x3 board as a 9-length list of None."""
    return [None] * 9


# PUBLIC_INTERFACE
def next_player_from_board(board: List[Cell]) -> Player:
    """Compute next player by counting existing marks."""
    x = sum(1 for c in board if c == "X")
    o = sum(1 for c in board if c == "O")
    return "X" if x == o else "O"


# PUBLIC_INTERFACE
def detect_winner(board: List[Cell]) -> Optional[Player]:
    """Return 'X' or 'O' if a winner exists, otherwise None."""
    for a, b, c in WIN_LINES:
        if board[a] is not None and board[a] == board[b] == board[c]:
            return board[a]  # type: ignore[return-value]
    return None


# PUBLIC_INTERFACE
def is_draw(board: List[Cell]) -> bool:
    """True if all cells filled and no winner."""
    return all(c is not None for c in board) and detect_winner(board) is None


# PUBLIC_INTERFACE
def apply_move(board: List[Cell], position: int, player: Player) -> List[Cell]:
    """Apply a move on a copy of the board; raises ValueError if invalid."""
    if not (0 <= position <= 8):
        raise ValueError("Position out of bounds")
    if board[position] is not None:
        raise ValueError("Cell already occupied")
    new_board = list(board)
    new_board[position] = player
    return new_board
