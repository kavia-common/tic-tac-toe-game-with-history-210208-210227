# Tic Tac Toe Backend (FastAPI)

This service provides REST endpoints for starting a game, making moves, and listing finished games with history.

Endpoints:
- GET /: Health check
- POST /games: Start a new game, returns { game_id, state }
- POST /games/{game_id}/moves: Apply a move with payload { index, player }, returns updated { game_id, state }
- GET /games/{game_id}: Get current game state and history
- GET /games: List recent finished games

Run locally:
- Install deps: pip install -r requirements.txt
- Start: uvicorn src.api.main:app --reload --port 3001

CORS:
- Enabled for http://localhost:3000 to support the React frontend.

Notes:
- Uses an in-memory storage adapter for demo purposes; can be swapped for a database later.
