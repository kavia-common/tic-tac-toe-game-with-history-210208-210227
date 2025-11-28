# Run backend locally

Create .env (see .env.example). PORT defaults to 3001 if your process manager uses it.

Suggested command:
uvicorn src.api.main:app --host 0.0.0.0 --port ${PORT:-3001} --reload
