import os
import tempfile
import contextlib
import importlib

import pytest
from fastapi.testclient import TestClient


# Ensure we import app after setting DB_PATH so startup uses temp db
@contextlib.contextmanager
def _temp_db_env():
    fd, path = tempfile.mkstemp(prefix="tictactoe-test-", suffix=".db")
    os.close(fd)
    old = os.environ.get("DB_PATH")
    os.environ["DB_PATH"] = path
    try:
        yield path
    finally:
        try:
            os.remove(path)
        except FileNotFoundError:
            pass
        if old is None:
            os.environ.pop("DB_PATH", None)
        else:
            os.environ["DB_PATH"] = old


@pytest.fixture
def temp_db_path():
    with _temp_db_env() as p:
        yield p


@pytest.fixture
def test_app(temp_db_path):
    # Import after env set; reload module to ensure fresh startup hooks run per test
    from src.api import main as main_module
    importlib.reload(main_module)
    app = main_module.app
    # Use TestClient as a context manager so FastAPI startup and shutdown events run,
    # ensuring init_db() is executed with the temporary DB path.
    with TestClient(app) as client:
        yield client
