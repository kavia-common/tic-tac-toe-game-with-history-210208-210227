from __future__ import annotations

from typing import List, Literal, Optional
from pydantic import BaseModel, Field, field_validator


Player = Literal["X", "O"]
Cell = Optional[Literal["X", "O"]]
GameStatus = Literal["in_progress", "won", "draw"]


# PUBLIC_INTERFACE
class StartGameResponse(BaseModel):
    """Response model for starting a new game."""
    gameId: str = Field(..., description="Unique game identifier")
    board: List[Cell] = Field(..., min_length=9, max_length=9, description="Board as 9-length list with 'X', 'O' or null")
    currentPlayer: Player = Field(..., description="Which player moves next")
    status: GameStatus = Field(..., description="Game status: in_progress | won | draw")
    winner: Optional[Player] = Field(None, description="Winner player when status is 'won'")


# PUBLIC_INTERFACE
class MoveRequest(BaseModel):
    """Request model for making a move."""
    position: int = Field(..., ge=0, le=8, description="Board index 0..8")

    @field_validator("position")
    @classmethod
    def _check_range(cls, v: int) -> int:
        if not (0 <= v <= 8):
            raise ValueError("position must be in range 0..8")
        return v


# PUBLIC_INTERFACE
class MoveResponse(BaseModel):
    """Response model after a move is applied."""
    gameId: str
    board: List[Cell]
    currentPlayer: Optional[Player]
    status: GameStatus
    winner: Optional[Player] = None


class MoveRecord(BaseModel):
    """Single move record as returned by GET /games/{gameId}."""
    moveNumber: int
    player: Player
    position: int


# PUBLIC_INTERFACE
class GameDetailResponse(BaseModel):
    """Detailed game state including move history."""
    gameId: str
    board: List[Cell]
    currentPlayer: Optional[Player]
    status: GameStatus
    winner: Optional[Player] = None
    moves: List[MoveRecord]


class HistoryItem(BaseModel):
    """Single item in the history listing."""
    gameId: str
    status: GameStatus
    winner: Optional[Player] = None
    finishedAt: Optional[str] = None


# PUBLIC_INTERFACE
class GameHistoryResponse(BaseModel):
    """Response for listing recent games."""
    items: List[HistoryItem]
