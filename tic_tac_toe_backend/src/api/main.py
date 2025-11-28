from typing import List, Optional
from uuid import uuid4
import json

from fastapi import FastAPI, HTTPException, Path
from fastapi.middleware.cors import CORSMiddleware

from src.db import init_db
from src.models import create_game, add_move, finalize_game, get_game, list_games
from src.schemas import (
    StartGameResponse,
    MoveRequest,
    MoveResponse,
    GameDetailResponse,
    GameHistoryResponse,
    HistoryItem,
)
from src.services.game_logic import (
    empty_board,
    next_player_from_board,
    detect_winner,
    is_draw,
    apply_move,
)

app = FastAPI(
    title="Tic Tac Toe Backend",
    description="API for a simple Tic Tac Toe game with SQLite persistence.",
    version="0.1.0",
    openapi_tags=[
        {"name": "health", "description": "Health and status endpoints"},
        {"name": "games", "description": "Game lifecycle and history"},
    ],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    """Initialize the database schema on application startup."""
    init_db()


@app.get("/", tags=["health"], summary="Health Check")
def health_check():
    """Simple health check endpoint."""
    return {"message": "Healthy"}


# PUBLIC_INTERFACE
@app.post(
    "/games/start",
    response_model=StartGameResponse,
    tags=["games"],
    summary="Start a new game",
    description="Create a new Tic Tac Toe game and return its initial state.",
)
def start_game() -> StartGameResponse:
    """Start a new game and return initial state with board, current player, and status."""
    game_id = str(uuid4())
    create_game(game_id)
    board = empty_board()
    current_player = next_player_from_board(board)
    return StartGameResponse(
        gameId=game_id,
        board=board,
        currentPlayer=current_player,
        status="in_progress",
        winner=None,
    )


def _build_board_from_moves(moves: List[dict]) -> List[Optional[str]]:
    board: List[Optional[str]] = [None] * 9
    for mv in moves:
        pos = mv["position"]
        player = mv["player"]
        if 0 <= pos <= 8:
            board[pos] = player
    return board


# PUBLIC_INTERFACE
@app.post(
    "/games/{gameId}/move",
    response_model=MoveResponse,
    tags=["games"],
    summary="Make a move",
    description="Apply a move for the current player. Validates turn order and cell availability.",
)
def make_move(
    move: MoveRequest,
    gameId: str = Path(..., description="The ID of the game"),
) -> MoveResponse:
    """Apply a move to a game, update persistence, and return updated state."""
    game = get_game(gameId)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    moves = game.get("moves", [])
    board = _build_board_from_moves(moves)
    winner = detect_winner(board)
    if winner is not None or is_draw(board):
        raise HTTPException(status_code=400, detail="Game is already finished")

    current_player = next_player_from_board(board)

    # Validate and apply move
    try:
        new_board = apply_move(board, move.position, current_player)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Persist new move
    move_number = len(moves) + 1
    add_move(gameId, move_number, current_player, move.position)

    # Determine status and possibly finalize
    winner = detect_winner(new_board)
    if winner:
        finalize_game(gameId, winner, json.dumps(new_board))
        return MoveResponse(
            gameId=gameId,
            board=new_board,
            currentPlayer=None,
            status="won",
            winner=winner,
        )
    elif is_draw(new_board):
        finalize_game(gameId, "draw", json.dumps(new_board))
        return MoveResponse(
            gameId=gameId,
            board=new_board,
            currentPlayer=None,
            status="draw",
            winner=None,
        )
    else:
        # Game continues
        next_player = next_player_from_board(new_board)
        return MoveResponse(
            gameId=gameId,
            board=new_board,
            currentPlayer=next_player,
            status="in_progress",
            winner=None,
        )


# PUBLIC_INTERFACE
@app.get(
    "/games/{gameId}",
    response_model=GameDetailResponse,
    tags=["games"],
    summary="Get game state",
    description="Fetch current board, status, next player, winner (if any), and full move history.",
)
def get_game_state(
    gameId: str = Path(..., description="The ID of the game"),
) -> GameDetailResponse:
    """Return the detailed game state and move history for the given game."""
    game = get_game(gameId)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    moves = game.get("moves", [])
    board = _build_board_from_moves(moves)
    winner = detect_winner(board)
    if winner:
        status = "won"
        current_player: Optional[str] = None
    elif is_draw(board):
        status = "draw"
        current_player = None
    else:
        status = "in_progress"
        current_player = next_player_from_board(board)

    move_records = [
        {"moveNumber": m["move_number"], "player": m["player"], "position": m["position"]}
        for m in moves
    ]

    return GameDetailResponse(
        gameId=gameId,
        board=board,
        currentPlayer=current_player,
        status=status,  # type: ignore[arg-type]
        winner=winner,
        moves=move_records,  # type: ignore[arg-type]
    )


# PUBLIC_INTERFACE
@app.get(
    "/games/history",
    response_model=GameHistoryResponse,
    tags=["games"],
    summary="List game history",
    description="List recent games with status and winner.",
)
def games_history() -> GameHistoryResponse:
    """List recent games with summarized status and winner."""
    games = list_games(limit=50, offset=0)
    items: List[HistoryItem] = []
    for g in games:
        # Determine status from result/finished_at
        if g["result"] == "draw":
            status = "draw"
            winner = None
        elif g["result"] in ("X", "O"):
            status = "won"
            winner = g["result"]
        else:
            status = "in_progress"
            winner = None
        items.append(
            HistoryItem(
                gameId=g["id"],
                status=status,  # type: ignore[arg-type]
                winner=winner,  # type: ignore[arg-type]
                finishedAt=g["finished_at"],
            )
        )
    return GameHistoryResponse(items=items)
