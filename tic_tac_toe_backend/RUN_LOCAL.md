# Run backend locally

Create .env (see .env.example). PORT defaults to 3001 if your process manager uses it.

Suggested command:
uvicorn src.api.main:app --host 0.0.0.0 --port ${PORT:-3001} --reload

## CORS
If your frontend runs on a different origin (localhost:3000 or a preview URL),
set either:
- FRONTEND_URL to that exact origin (e.g., FRONTEND_URL=http://localhost:3000),
- REACT_APP_FRONTEND_URL (same as above; this app reads either), or
- CORS_ORIGINS as a comma-separated list of allowed origins.

By default, common localhost origins are allowed. The middleware is configured as:
- allow_methods: ["*"]
- allow_headers: ["*"]
- allow_credentials: true

Ensure the origin value includes protocol + host (+ port) and no trailing slash.
