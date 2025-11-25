"""Storage adapters for Tic Tac Toe backend.

Provides:
- InMemoryStorage: simple in-process storage for demo/testing
- DBStorage: SQLite-backed storage using Python's sqlite3

Storage is selected by src.api.main based on environment variables.
"""

from __future__ import annotations

import os
import re
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Generator, List, Optional

from pydantic import BaseModel, Field


# Models (duplicated minimal definitions to avoid circular import)
class Move(BaseModel):
    """Represents a single move in a tic tac toe game."""
    index: int = Field(..., ge=0, le=8, description="Zero-based board index (0-8)")
    player: str = Field(..., pattern="^(X|O)$", description="The player symbol making the move: 'X' or 'O'")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Timestamp when the move was made")


class GameState(BaseModel):
    """Represents the current state of a game."""
    board: List[str] = Field(default_factory=lambda: [""] * 9, description="Current board as 9 cells, values '', 'X', or 'O'")
    current_player: str = Field(default="X", description="Which player should move next: 'X' or 'O'")
    winner: Optional[str] = Field(default=None, description="Winner 'X' or 'O' if any")
    is_draw: bool = Field(default=False, description="True if the game ended in a draw")
    history: List[Move] = Field(default_factory=list, description="Ordered move history")


class GameRecord(GameState):
    """Game persisted record with identifiers and metadata."""
    game_id: str = Field(..., description="Unique game identifier")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    finished_at: Optional[datetime] = Field(default=None, description="End timestamp if game is finished")


# PUBLIC_INTERFACE
class InMemoryStorage:
    """Replaceable storage adapter; mimic a DB layer that can be swapped later."""
    def __init__(self) -> None:
        self._games: Dict[str, GameRecord] = {}

    # PUBLIC_INTERFACE
    def create_game(self, game_id: str, created_at: Optional[datetime] = None) -> GameRecord:
        """Create and persist a new game record and return it."""
        created_at = created_at or datetime.utcnow()
        record = GameRecord(game_id=game_id, created_at=created_at)
        # Normalize defaults
        record.board = [""] * 9
        record.current_player = "X"
        record.winner = None
        record.is_draw = False
        record.history = []
        self._games[game_id] = record
        return record

    # PUBLIC_INTERFACE
    def get_game(self, game_id: str) -> GameRecord:
        """Fetch a game by id or raise KeyError."""
        rec = self._games.get(game_id)
        if not rec:
            raise KeyError(game_id)
        return rec

    # PUBLIC_INTERFACE
    def save_game(self, record: GameRecord) -> None:
        """Persist an updated game record."""
        self._games[record.game_id] = record

    # PUBLIC_INTERFACE
    def list_finished(self, limit: int = 20) -> List[GameRecord]:
        """Return recently finished games, most recent first."""
        finished = [g for g in self._games.values() if g.winner or g.is_draw]
        finished.sort(key=lambda g: g.finished_at or g.created_at, reverse=True)
        return finished[:limit]


@dataclass
class _DbConfig:
    driver: str
    path: str


def _parse_database_url(url: str) -> _DbConfig:
    """Parse a DATABASE_URL like sqlite:///./tictactoe.db and return config.

    Supports:
    - sqlite:///relative/path.db
    - sqlite:////absolute/path.db
    - sqlite://:memory:
    - sqlite:///tictactoe.db (no leading ./)
    """
    if not url:
        raise ValueError("DATABASE_URL is empty")
    # Normalize and validate
    url = url.strip()
    # Accept :memory:
    if url.startswith("sqlite://") and ":memory:" in url:
        return _DbConfig(driver="sqlite", path=":memory:")
    # Accept three or more slashes after scheme; capture the rest as path
    m = re.match(r"^(?P<driver>sqlite):///{1,}(?P<path>.*)$", url)
    if not m:
        raise ValueError(f"Unsupported DATABASE_URL format: {url}")
    driver = m.group("driver")
    path = m.group("path")
    # If empty path, default to local file
    if not path:
        path = "./tictactoe.db"
    return _DbConfig(driver=driver, path=path)


class DBStorage:
    """SQLite-backed storage adapter using Python's sqlite3 module."""

    def __init__(self, database_url: str = "sqlite:///./tictactoe.db") -> None:
        cfg = _parse_database_url(database_url)
        if cfg.driver != "sqlite":
            raise ValueError(f"Only sqlite is supported; got {cfg.driver}")
        self._db_path = cfg.path
        # Ensure directory exists for file databases
        if self._db_path not in (":memory:",):
            db_dir = os.path.dirname(self._db_path)
            if db_dir and db_dir != ":":
                os.makedirs(db_dir, exist_ok=True)
        # Initialize schema
        self._init_db()

    @contextmanager
    def _conn(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(self._db_path, detect_types=sqlite3.PARSE_DECLTYPES)
        try:
            # return rows as tuples; convert timestamps manually with ISO
            conn.row_factory = sqlite3.Row
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self._conn() as conn:
            cur = conn.cursor()
            # games table
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS games (
                    game_id TEXT PRIMARY KEY,
                    board TEXT NOT NULL,
                    current_player TEXT NOT NULL,
                    winner TEXT,
                    is_draw INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    finished_at TEXT
                )
                """
            )
            # moves table
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS moves (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    game_id TEXT NOT NULL,
                    move_index INTEGER NOT NULL,
                    player TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (game_id) REFERENCES games (game_id) ON DELETE CASCADE
                )
                """
            )
            # index to fetch moves by game/time
            cur.execute("CREATE INDEX IF NOT EXISTS idx_moves_game_time ON moves (game_id, id)")

    # PUBLIC_INTERFACE
    def create_game(self, game_id: str, created_at: Optional[datetime] = None) -> GameRecord:
        """Create and persist a new game record and return it."""
        created_at = created_at or datetime.utcnow()
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO games (game_id, board, current_player, winner, is_draw, created_at, finished_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    game_id,
                    ",".join([""] * 9),
                    "X",
                    None,
                    0,
                    created_at.isoformat(),
                    None,
                ),
            )
        return GameRecord(
            game_id=game_id,
            board=[""] * 9,
            current_player="X",
            winner=None,
            is_draw=False,
            history=[],
            created_at=created_at,
            finished_at=None,
        )

    # PUBLIC_INTERFACE
    def get_game(self, game_id: str) -> GameRecord:
        """Fetch a game by id or raise KeyError."""
        with self._conn() as conn:
            cur = conn.execute("SELECT * FROM games WHERE game_id = ?", (game_id,))
            row = cur.fetchone()
            if not row:
                raise KeyError(game_id)
            board = row["board"].split(",") if row["board"] else [""] * 9
            # load moves
            mcur = conn.execute(
                "SELECT move_index, player, timestamp FROM moves WHERE game_id = ? ORDER BY id ASC",
                (game_id,),
            )
            history: List[Move] = []
            for mrow in mcur.fetchall():
                history.append(
                    Move(
                        index=int(mrow["move_index"]),
                        player=str(mrow["player"]),
                        timestamp=datetime.fromisoformat(str(mrow["timestamp"])),
                    )
                )
            rec = GameRecord(
                game_id=str(row["game_id"]),
                board=board,
                current_player=str(row["current_player"]),
                winner=str(row["winner"]) if row["winner"] is not None else None,
                is_draw=bool(row["is_draw"]),
                history=history,
                created_at=datetime.fromisoformat(str(row["created_at"])),
                finished_at=datetime.fromisoformat(str(row["finished_at"])) if row["finished_at"] else None,
            )
            return rec

    # PUBLIC_INTERFACE
    def save_game(self, record: GameRecord) -> None:
        """Persist an updated game record, including any new moves not yet saved.

        Strategy:
        - Rewrite board/current_player/winner/is_draw/finished_at in games table.
        - Ensure moves in DB match record.history length. We insert new moves if DB has fewer.
        """
        with self._conn() as conn:
            # Update game core fields
            conn.execute(
                """
                UPDATE games
                SET board = ?, current_player = ?, winner = ?, is_draw = ?, finished_at = ?
                WHERE game_id = ?
                """,
                (
                    ",".join(record.board),
                    record.current_player,
                    record.winner,
                    1 if record.is_draw else 0,
                    record.finished_at.isoformat() if record.finished_at else None,
                    record.game_id,
                ),
            )
            # Count existing moves
            cur = conn.execute("SELECT COUNT(*) AS c FROM moves WHERE game_id = ?", (record.game_id,))
            existing = int(cur.fetchone()["c"])
            # Insert only new moves
            for mv in record.history[existing:]:
                conn.execute(
                    """
                    INSERT INTO moves (game_id, move_index, player, timestamp)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        record.game_id,
                        mv.index,
                        mv.player,
                        mv.timestamp.isoformat(),
                    ),
                )

    # PUBLIC_INTERFACE
    def list_finished(self, limit: int = 20) -> List[GameRecord]:
        """Return recently finished games, most recent first."""
        with self._conn() as conn:
            cur = conn.execute(
                """
                SELECT * FROM games
                WHERE (winner IS NOT NULL) OR (is_draw = 1)
                ORDER BY COALESCE(finished_at, created_at) DESC
                LIMIT ?
                """,
                (limit,),
            )
            rows = cur.fetchall()
            results: List[GameRecord] = []
            for row in rows:
                board = row["board"].split(",") if row["board"] else [""] * 9
                results.append(
                    GameRecord(
                        game_id=str(row["game_id"]),
                        board=board,
                        current_player=str(row["current_player"]),
                        winner=str(row["winner"]) if row["winner"] is not None else None,
                        is_draw=bool(row["is_draw"]),
                        history=[],  # summaries need not include history
                        created_at=datetime.fromisoformat(str(row["created_at"])),
                        finished_at=datetime.fromisoformat(str(row["finished_at"])) if row["finished_at"] else None,
                    )
                )
            return results
