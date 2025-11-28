# Backend Testing (pytest)

This backend uses pytest for tests.

## Install dependencies
Use the provided requirements.txt (pytest and httpx are included):

pip install -r requirements.txt

## Run tests
Always in non-interactive mode (CI example):

pytest -q

or with coverage:

pytest -q --cov=src --cov-report=term-missing

## Notes
- Tests isolate database state by setting DB_PATH to a temporary file using monkeypatch.
- No writes are made to the real ./data/tictactoe.db.
- FastAPI TestClient is created per-test to ensure isolation.
