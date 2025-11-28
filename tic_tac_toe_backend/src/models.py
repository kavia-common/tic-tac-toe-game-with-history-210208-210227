from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from src.db import db_session


# PUBLIC_INTERFACE
def create_game(game_id: str) -> Dict[str, Any]:
    """Create a new game row.

    Args:
        game_id: Unique identifier for the game (string).

    Returns:
        A dictionary representing the created game.
    """
    now = datetime.utcnow().isoformat()
    with db_session() as conn:
        conn.execute(
            """
            INSERT INTO games (id, started_at, finished_at, result, final_board)
            VALUES (?, ?, NULL, NULL, NULL)
            """,
            (game_id, now),
        )
        row = conn.execute(
            "SELECT id, started_at, finished_at, result, final_board FROM games WHERE id = ?",
            (game_id,),
        ).fetchone()
        return _row_to_game_dict(row)


# PUBLIC_INTERFACE
def add_move(game_id: str, move_number: int, player: str, position: int) -> Dict[str, Any]:
    """Add a move to a game.

    Args:
        game_id: ID of the game.
        move_number: Sequential move number (starting from 1).
        player: The player making the move (e.g., 'X' or 'O').
        position: Board position (0-8) in a 3x3 grid.

    Returns:
        Inserted move as a dict.
    """
    now = datetime.utcnow().isoformat()
    with db_session() as conn:
        conn.execute(
            """
            INSERT INTO moves (game_id, move_number, player, position, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (game_id, move_number, player, position, now),
        )
        row = conn.execute(
            """
            SELECT id, game_id, move_number, player, position, created_at
            FROM moves
            WHERE game_id = ? AND move_number = ?
            """,
            (game_id, move_number),
        ).fetchone()
        return _row_to_move_dict(row)


# PUBLIC_INTERFACE
def finalize_game(game_id: str, result: Optional[str], final_board: str) -> Dict[str, Any]:
    """Finalize a game by setting finished_at, result and final_board.

    Args:
        game_id: ID of the game to finalize.
        result: Outcome string (e.g., 'X', 'O', 'draw', or None).
        final_board: The final board representation (JSON/string).

    Returns:
        Updated game as a dict.
    """
    now = datetime.utcnow().isoformat()
    with db_session() as conn:
        conn.execute(
            """
            UPDATE games
            SET finished_at = ?, result = ?, final_board = ?
            WHERE id = ?
            """,
            (now, result, final_board, game_id),
        )
        row = conn.execute(
            "SELECT id, started_at, finished_at, result, final_board FROM games WHERE id = ?",
            (game_id,),
        ).fetchone()
        return _row_to_game_dict(row)


# PUBLIC_INTERFACE
def get_game(game_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve a game and its moves.

    Args:
        game_id: ID of the game.

    Returns:
        Game object with 'moves' list, or None if not found.
    """
    with db_session(readonly=True) as conn:
        game_row = conn.execute(
            "SELECT id, started_at, finished_at, result, final_board FROM games WHERE id = ?",
            (game_id,),
        ).fetchone()
        if not game_row:
            return None
        moves_rows = conn.execute(
            """
            SELECT id, game_id, move_number, player, position, created_at
            FROM moves
            WHERE game_id = ?
            ORDER BY move_number ASC
            """,
            (game_id,),
        ).fetchall()

    game = _row_to_game_dict(game_row)
    game["moves"] = [_row_to_move_dict(r) for r in moves_rows]
    return game


# PUBLIC_INTERFACE
def list_games(limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
    """List games ordered by started_at descending.

    Args:
        limit: Max number of games to return.
        offset: Pagination offset.

    Returns:
        A list of game dicts without moves to keep it light.
    """
    with db_session(readonly=True) as conn:
        rows = conn.execute(
            """
            SELECT id, started_at, finished_at, result, final_board
            FROM games
            ORDER BY datetime(started_at) DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        ).fetchall()
    return [_row_to_game_dict(r) for r in rows]


def _row_to_game_dict(row) -> Dict[str, Any]:
    """Convert a sqlite Row for games into a dict."""
    return {
        "id": row["id"],
        "started_at": row["started_at"],
        "finished_at": row["finished_at"],
        "result": row["result"],
        "final_board": row["final_board"],
    }


def _row_to_move_dict(row) -> Dict[str, Any]:
    """Convert a sqlite Row for moves into a dict."""
    return {
        "id": row["id"],
        "game_id": row["game_id"],
        "move_number": row["move_number"],
        "player": row["player"],
        "position": row["position"],
        "created_at": row["created_at"],
    }
