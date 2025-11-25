from datetime import datetime
from typing import List, Optional, Dict
from uuid import uuid4
import os

from fastapi import FastAPI, HTTPException, Path, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load environment variables from a .env file if present
load_dotenv()

# ----------------------------
# Models
# ----------------------------

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


# Request and Response Models

# PUBLIC_INTERFACE
class CreateGameResponse(BaseModel):
    """Response returned when starting a new game."""
    game_id: str = Field(..., description="Newly created game identifier")
    state: GameState = Field(..., description="Initial state of the game")

# PUBLIC_INTERFACE
class MakeMoveRequest(BaseModel):
    """Request payload to make a move on a specific game."""
    index: int = Field(..., ge=0, le=8, description="Zero-based board index (0-8)")
    player: str = Field(..., pattern="^(X|O)$", description="Player symbol attempting the move")

# PUBLIC_INTERFACE
class MakeMoveResponse(BaseModel):
    """Response returned after applying a move, including updated state."""
    game_id: str = Field(..., description="Game identifier")
    state: GameState = Field(..., description="Updated state after the move")

# PUBLIC_INTERFACE
class GetGameResponse(BaseModel):
    """Response containing the current game state and full history."""
    game_id: str = Field(..., description="Game identifier")
    state: GameState = Field(..., description="Current state including full history")

# PUBLIC_INTERFACE
class FinishedGameSummary(BaseModel):
    """Summary for a finished game used in listings."""
    game_id: str = Field(..., description="Game identifier")
    winner: Optional[str] = Field(default=None, description="Winner 'X' or 'O', or null if draw")
    is_draw: bool = Field(..., description="True if the game ended in a draw")
    finished_at: datetime = Field(..., description="Timestamp when the game finished")

# PUBLIC_INTERFACE
class ListGamesResponse(BaseModel):
    """Response listing recently finished games."""
    games: List[FinishedGameSummary] = Field(..., description="List of finished games (recent first)")


# ----------------------------
# Storage selection (env-driven)
# ----------------------------
from src.api.storage import InMemoryStorage, DBStorage  # local adapters

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./tictactoe.db")
USE_DB = bool(DATABASE_URL)

if USE_DB:
    storage = DBStorage(DATABASE_URL)
else:
    storage = InMemoryStorage()

# ----------------------------
# Game logic
# ----------------------------

WIN_LINES = [
    (0, 1, 2), (3, 4, 5), (6, 7, 8),  # rows
    (0, 3, 6), (1, 4, 7), (2, 5, 8),  # cols
    (0, 4, 8), (2, 4, 6),             # diagonals
]

def check_winner(board: List[str]) -> Optional[str]:
    """Return 'X' or 'O' if a winning line exists, else None."""
    for a, b, c in WIN_LINES:
        if board[a] and board[a] == board[b] and board[b] == board[c]:
            return board[a]
    return None


def is_draw(board: List[str]) -> bool:
    """Return True if the board is full and no winner."""
    return all(cell in ("X", "O") for cell in board) and check_winner(board) is None


def assert_valid_move(record: GameRecord, index: int, player: str) -> None:
    """Validate move against current game state; raise HTTPException on invalid."""
    if record.winner or record.is_draw:
        raise HTTPException(status_code=400, detail="Game already finished.")
    if player != record.current_player:
        raise HTTPException(status_code=400, detail=f"It is not {player}'s turn.")
    if not (0 <= index <= 8):
        raise HTTPException(status_code=422, detail="Index must be between 0 and 8.")
    if record.board[index] != "":
        raise HTTPException(status_code=400, detail="Cell already occupied.")


def apply_move(record: GameRecord, index: int, player: str) -> GameRecord:
    """Apply a move to the record, update board, winner/draw, current player, and history."""
    assert_valid_move(record, index, player)

    # Update board
    record.board[index] = player

    # Append to history
    record.history.append(Move(index=index, player=player, timestamp=datetime.utcnow()))

    # Check winner or draw
    winner = check_winner(record.board)
    if winner:
        record.winner = winner
        record.is_draw = False
        record.finished_at = datetime.utcnow()
    else:
        record.is_draw = is_draw(record.board)
        if record.is_draw:
            record.finished_at = datetime.utcnow()

    # Toggle player if not finished
    if not (record.winner or record.is_draw):
        record.current_player = "O" if record.current_player == "X" else "X"

    return record


# ----------------------------
# FastAPI Application
# ----------------------------

app = FastAPI(
    title="Tic Tac Toe API",
    description="REST API for playing Tic Tac Toe with simple persistence and history.",
    version="1.0.0",
    openapi_tags=[
        {"name": "health", "description": "Service health endpoints"},
        {"name": "games", "description": "Game lifecycle and move operations"},
    ],
)

# CORS with env-driven origins (strict)
# SECURITY: Do not allow wildcard origins by default. Require explicit configuration via CORS_ORIGINS.
cors_origins_env = os.getenv("CORS_ORIGINS", "")
origins = [o.strip() for o in cors_origins_env.split(",") if o.strip()]
# Provide localhost defaults for development if not explicitly configured
if not origins:
    origins = ["http://localhost:3000", "http://127.0.0.1:3000"]

# If no origins configured, set empty list to effectively disable cross-origin requests.
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["health"], summary="Health Check")
def health_check() -> Dict[str, str]:
    """Health check endpoint.

    Returns:
        Dict[str, str]: A simple message indicating the service is healthy.
    """
    return {"message": "Healthy"}


# PUBLIC_INTERFACE
@app.post("/games", response_model=CreateGameResponse, tags=["games"], summary="Start a new game", description="Creates a new Tic Tac Toe game and returns the game id and initial state.")
def start_game() -> CreateGameResponse:
    """Create a new game.

    Returns:
        CreateGameResponse: Contains the game_id and the initial state of the new game.
    """
    # Generate a game id here in the API layer for consistent behavior across adapters
    game_id = str(uuid4())
    rec = storage.create_game(game_id=game_id, created_at=datetime.utcnow())
    state = GameState(
        board=rec.board,
        current_player=rec.current_player,
        winner=rec.winner,
        is_draw=rec.is_draw,
        history=rec.history,
    )
    return CreateGameResponse(game_id=rec.game_id, state=state)


# PUBLIC_INTERFACE
@app.post(
    "/games/{game_id}/moves",
    response_model=MakeMoveResponse,
    tags=["games"],
    summary="Make a move",
    description="Apply a move by specifying the board index (0-8) and the player ('X' or 'O'). Returns updated state.",
)
def make_move(
    game_id: str = Path(..., description="The target game identifier"),
    payload: MakeMoveRequest = Body(..., description="The move to apply to the game"),
) -> MakeMoveResponse:
    """Apply a move to an existing game and return the updated state.

    Args:
        game_id (str): The target game identifier.
        payload (MakeMoveRequest): The move payload containing index and player.

    Returns:
        MakeMoveResponse: The updated game state after applying the move.
    """
    try:
        rec = storage.get_game(game_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Game not found")

    rec = apply_move(rec, payload.index, payload.player)
    storage.save_game(rec)

    state = GameState(
        board=rec.board,
        current_player=rec.current_player,
        winner=rec.winner,
        is_draw=rec.is_draw,
        history=rec.history,
    )
    return MakeMoveResponse(game_id=rec.game_id, state=state)


# PUBLIC_INTERFACE
@app.get(
    "/games/{game_id}",
    response_model=GetGameResponse,
    tags=["games"],
    summary="Get game state",
    description="Fetch the current state and full move history for a specific game.",
)
def get_game(game_id: str = Path(..., description="The game identifier")) -> GetGameResponse:
    """Fetch the current game state and history.

    Args:
        game_id (str): The game identifier.

    Returns:
        GetGameResponse: The current state including full move history.
    """
    try:
        rec = storage.get_game(game_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Game not found")

    state = GameState(
        board=rec.board,
        current_player=rec.current_player,
        winner=rec.winner,
        is_draw=rec.is_draw,
        history=rec.history,
    )
    return GetGameResponse(game_id=rec.game_id, state=state)


# PUBLIC_INTERFACE
@app.get(
    "/games",
    response_model=ListGamesResponse,
    tags=["games"],
    summary="List recent finished games",
    description="Returns a list of recently finished games (winner or draw), most recent first.",
)
def list_games() -> ListGamesResponse:
    """List finished games with basic summary metadata.

    Returns:
        ListGamesResponse: Recently finished games (winner or draw), most recent first.
    """
    records = storage.list_finished(limit=20)
    summaries = [
        FinishedGameSummary(
            game_id=r.game_id,
            winner=r.winner,
            is_draw=r.is_draw,
            finished_at=r.finished_at or r.created_at,
        )
        for r in records
    ]
    return ListGamesResponse(games=summaries)
