import os
import sys
import tempfile
import contextlib
from pathlib import Path
from typing import List

import pytest
from fastapi.testclient import TestClient

# Prepend absolute src path immediately upon module import to affect collection
_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_src_path = os.path.join(_root, "src")
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)


def _prepend_src_to_syspath():
    """
    Prepend absolute backend src path to sys.path so 'from src...' imports
    work regardless of pytest's pythonpath handling.
    """
    this_file = Path(__file__).resolve()
    backend_root = this_file.parents[1]
    src_path = (backend_root / "src").resolve()
    src_str = str(src_path)
    if src_str not in sys.path:
        sys.path.insert(0, src_str)


# Ensure path is set at import time (session start)
_prepend_src_to_syspath()


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


@pytest.fixture(scope="session", autouse=True)
def _session_path_setup():
    """
    Session-scoped autouse fixture to harden sys.path for all tests.
    """
    _prepend_src_to_syspath()
    yield


@pytest.fixture
def temp_db_path():
    with _temp_db_env() as p:
        yield p


def _debug_routes(app) -> List[str]:
    """
    Helper to print and return route paths and openapi paths for diagnostics.
    """
    try:
        route_paths = [getattr(r, "path", None) for r in app.router.routes]
    except Exception:
        route_paths = []
    try:
        openapi_paths = list(app.openapi().get("paths", {}).keys())
    except Exception:
        openapi_paths = []
    print("Registered routes:", route_paths)
    print("OpenAPI paths:", openapi_paths)
    return route_paths


@pytest.fixture
def test_app(temp_db_path):
    """
    Provides a FastAPI TestClient configured to use a temporary isolated DB.

    Steps:
    - Ensure sys.path includes absolute src path.
    - Set DB_PATH to temp file.
    - Explicitly call init_db() after setting DB_PATH to eliminate timing gaps.
    - Use TestClient as a context manager so FastAPI startup events still run.
    - Assert the /games/history route is present in both router and OpenAPI.
    """
    _prepend_src_to_syspath()

    # Import after env is set
    from src.db import init_db
    from src.api.main import app  # Import the concrete app instance directly

    # Explicit DB init just before client usage to avoid any race/timing gap
    init_db()

    # Diagnostics and assertions before client context
    route_paths = _debug_routes(app)
    openapi_paths = list(app.openapi().get("paths", {}).keys())
    assert "/games/history" in openapi_paths, "Expected /games/history in OpenAPI paths"
    # Router stores parameterized routes separately; ensure exact match exists
    assert "/games/history" in route_paths, (
        "Expected /games/history in router routes. "
        f"Found: {route_paths}"
    )

    # Use TestClient as a context manager so startup/shutdown events run
    with TestClient(app) as client:
        # Verify endpoint responds 200 even when no games exist
        resp = client.get("/games/history")
        print("GET /games/history status during fixture:", resp.status_code, "body:", resp.text)
        assert resp.status_code == 200, "Expected /games/history to respond 200"
        data = resp.json()
        assert "items" in data and isinstance(data["items"], list), (
            "Expected GameHistoryResponse with 'items' list"
        )
        yield client
