# Run backend locally

Create .env (see .env.example). PORT defaults to 3001 if your process manager uses it.

Suggested command:
uvicorn src.api.main:app --host 0.0.0.0 --port ${PORT:-3001} --reload

## CORS
If your frontend runs on a different origin (localhost:3000 or a preview URL),
set either:
- FRONTEND_URL to that exact origin (e.g., FRONTEND_URL=http://localhost:3000), or
- CORS_ORIGINS as a comma-separated list of allowed origins.

By default, common localhost origins are allowed.
