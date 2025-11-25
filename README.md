# tic-tac-toe-game-with-history-210208-210227

Fullstack Tic Tac Toe with a FastAPI backend and a React frontend.

## Quickstart (Local)

Backend:
1. cd tic_tac_toe_backend
2. Create/Edit `.env` (already added):
   ```
   DATABASE_URL=sqlite:///./tictactoe.db
   CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
   # FRONTEND_URL is optional: when set, it is automatically added to allowed CORS origins
   # FRONTEND_URL=https://your-preview-frontend.example.com
   PORT=3001
   ```
3. Install and run:
   ```
   pip install -r requirements.txt
   uvicorn src.api.main:app --reload --port ${PORT:-3001}
   ```
   Docs: http://localhost:3001/docs

Frontend:
1. cd ../tic-tac-toe-game-with-history-210208-210227/tic_tac_toe_frontend
2. Ensure `.env` contains (see .env.example for reference):
   ```
   REACT_APP_API_BASE=http://localhost:3001
   ```
3. Install and run:
   ```
   npm install
   npm start
   ```
   App: http://localhost:3000

## Persistence and configuration

- Default persistence uses SQLite at `sqlite:///./tictactoe.db`. To switch to in-memory, unset `DATABASE_URL` before starting the backend.
- CORS origins for local dev: `http://localhost:3000,http://127.0.0.1:3000`.
- The frontend reads the backend base URL from `REACT_APP_API_BASE`.