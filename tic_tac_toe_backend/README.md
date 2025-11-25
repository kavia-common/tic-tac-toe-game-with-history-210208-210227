# Tic Tac Toe Backend (FastAPI)

This service provides REST endpoints for starting a game, making moves, and listing finished games with history.

Endpoints:
- GET /: Health check
- POST /games: Start a new game, returns { game_id, state }
- POST /games/{game_id}/moves: Apply a move with payload { index, player }, returns updated { game_id, state }
- GET /games/{game_id}: Get current game state and history
- GET /games: List recent finished games

## Run locally

- Install deps: `pip install -r requirements.txt`
- Start: `uvicorn src.api.main:app --reload --port 3001`

The app will auto-generate OpenAPI docs at `/docs`.

## Configuration (.env)

This service reads environment variables using python-dotenv if a `.env` file is present.

Copy `.env.example` to `.env` and adjust as needed:

```
DATABASE_URL=sqlite:///./tictactoe.db
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

- `DATABASE_URL`: The persistence layer. Supported value: SQLite via `sqlite:///path`. Default is `sqlite:///./tictactoe.db`.
  - Examples:
    - `sqlite:///./tictactoe.db` (file in project folder)
    - `sqlite:///:memory:` (ephemeral in-memory database)
- `CORS_ORIGINS`: Comma-separated list of allowed origins for the frontend.

## Persistence

By default, if `DATABASE_URL` is set (defaults to `sqlite:///./tictactoe.db`), the backend uses a SQLite-backed adapter that creates two tables:
- `games (game_id TEXT PRIMARY KEY, board TEXT, current_player TEXT, winner TEXT NULL, is_draw INT, created_at TEXT, finished_at TEXT NULL)`
- `moves (id INTEGER PRIMARY KEY AUTOINCREMENT, game_id TEXT, move_index INT, player TEXT, timestamp TEXT)`

If you explicitly want in-memory storage (not persisted), unset `DATABASE_URL` before starting the server.

## CORS

CORS is enabled and configured via `CORS_ORIGINS` (comma-separated). If not set, cross-origin requests are disabled by default (no wildcard). For local development, set:
```
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

## Migration path

The current DB layer uses Python's built-in `sqlite3` without an ORM. To migrate to another database or introduce migrations:

1. Introduce an ORM like SQLAlchemy and define models for `games` and `moves`.
2. Add Alembic for schema migration management.
3. Replace the `DBStorage` adapter with a SQLAlchemy-backed repository, keeping the same public methods:
   - `create_game(game_id, created_at=None)`
   - `get_game(game_id)`
   - `save_game(record)`
   - `list_finished(limit=20)`
4. Update `DATABASE_URL` to the appropriate driver (e.g., `postgresql+psycopg2://...`) and configure a DB driver dependency.

This adapter pattern isolates storage so the API and game logic remain unchanged.

## Notes

- OpenAPI schema can be regenerated with: `python -m src.api.generate_openapi`
- The database file is created automatically on first run if it doesn't exist.
- For production, restrict CORS origins to known hosts.
