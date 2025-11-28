# How to Run Backend Tests

1) Create virtualenv and install:
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

2) Run tests (non-interactive):
pytest -q

3) Coverage (optional):
pytest -q --cov=src --cov-report=term-missing

Tests isolate DB by setting DB_PATH to a temporary file. No writes to ./data/tictactoe.db.
