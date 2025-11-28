import os
import sqlite3
from contextlib import contextmanager
from typing import Iterator

from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

DEFAULT_DB_PATH = "./data/tictactoe.db"


def _ensure_dir_exists(path: str) -> None:
    """Ensure the directory for the DB file exists."""
    directory = os.path.dirname(path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)


def _get_db_path() -> str:
    """
    Resolve database path from environment.

    Env var:
      - DB_PATH: Optional path to sqlite database file.
    """
    db_path = os.getenv("DB_PATH", DEFAULT_DB_PATH)
    return db_path


def get_connection(readonly: bool = False) -> sqlite3.Connection:
    """
    Create and return a sqlite3 connection.

    - Ensures the database directory exists (for read-write).
    - Sets row_factory to sqlite3.Row for dict-like access.
    - Enables foreign keys.
    """
    db_path = _get_db_path()

    if readonly:
        # Use URI mode for read-only connections
        uri = f"file:{db_path}?mode=ro"
        conn = sqlite3.connect(uri, uri=True, check_same_thread=False)
    else:
        _ensure_dir_exists(db_path)
        conn = sqlite3.connect(db_path, check_same_thread=False)

    conn.row_factory = sqlite3.Row
    # Enforce foreign key constraints
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


@contextmanager
def db_session(readonly: bool = False) -> Iterator[sqlite3.Connection]:
    """
    Context manager that yields a sqlite3 connection and manages commit/rollback.

    Example:
        with db_session() as conn:
            conn.execute("INSERT ...")
    """
    conn = get_connection(readonly=readonly)
    try:
        yield conn
        if not readonly:
            conn.commit()
    except Exception:
        if not readonly:
            conn.rollback()
        raise
    finally:
        conn.close()


# PUBLIC_INTERFACE
def init_db() -> None:
    """Initialize the SQLite database schema if it does not already exist."""
    schema_games = """
    CREATE TABLE IF NOT EXISTS games (
        id TEXT PRIMARY KEY,
        started_at DATETIME NOT NULL,
        finished_at DATETIME NULL,
        result TEXT NULL,
        final_board TEXT
    );
    """

    schema_moves = """
    CREATE TABLE IF NOT EXISTS moves (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        game_id TEXT NOT NULL,
        move_number INTEGER NOT NULL,
        player TEXT NOT NULL,
        position INTEGER NOT NULL,
        created_at DATETIME NOT NULL,
        FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE
    );
    """

    with db_session() as conn:
        conn.execute(schema_games)
        conn.execute(schema_moves)

        # Helpful index for listing and joins
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_moves_game_id ON moves (game_id);"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_games_started_at ON games (started_at DESC);"
        )
