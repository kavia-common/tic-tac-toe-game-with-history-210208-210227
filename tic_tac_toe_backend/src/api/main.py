from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.db import init_db

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
