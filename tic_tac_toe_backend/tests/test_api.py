import os
from fastapi.testclient import TestClient
from dotenv import load_dotenv

# Ensure env is loaded for tests
load_dotenv()

# Force in-memory DB for tests to avoid filesystem side-effects
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
# Allow local origins for any CORS preflight in tests (not strictly needed for TestClient)
os.environ["CORS_ORIGINS"] = "http://localhost:3000"

from src.api.main import app  # noqa: E402

client = TestClient(app)


def test_health():
    resp = client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict)
    assert data.get("message") == "Healthy"


def test_start_game_and_get_state():
    # Start game
    resp = client.post("/games")
    assert resp.status_code == 200
    created = resp.json()
    assert "game_id" in created
    assert "state" in created
    game_id = created["game_id"]
    state = created["state"]
    assert state["current_player"] == "X"
    assert state["winner"] is None
    assert state["is_draw"] is False
    assert state["board"] == [""] * 9

    # Fetch same game
    resp2 = client.get(f"/games/{game_id}")
    assert resp2.status_code == 200
    fetched = resp2.json()
    assert fetched["game_id"] == game_id
    assert fetched["state"]["board"] == [""] * 9


def test_make_move_and_invalid_move_flow():
    # Start a new game
    created = client.post("/games").json()
    game_id = created["game_id"]

    # Valid first move by X at index 0
    m1 = client.post(f"/games/{game_id}/moves", json={"index": 0, "player": "X"})
    assert m1.status_code == 200
    s1 = m1.json()["state"]
    assert s1["board"][0] == "X"
    assert s1["current_player"] == "O"
    assert s1["winner"] is None
    assert s1["is_draw"] is False
    assert len(s1["history"]) == 1

    # Invalid move: X tries again (wrong turn)
    bad = client.post(f"/games/{game_id}/moves", json={"index": 1, "player": "X"})
    assert bad.status_code == 400
    assert "turn" in bad.json()["detail"]

    # Invalid move: O tries an occupied cell
    bad2 = client.post(f"/games/{game_id}/moves", json={"index": 0, "player": "O"})
    assert bad2.status_code == 400
    assert "occupied" in bad2.json()["detail"]

    # Invalid move: out of range index
    bad3 = client.post(f"/games/{game_id}/moves", json={"index": 9, "player": "O"})
    assert bad3.status_code in (400, 422)


def test_finished_game_history_and_listing():
    # Create a game and play a winning sequence for X: indices 0,3,1,4,2 => X wins top row
    created = client.post("/games").json()
    game_id = created["game_id"]

    seq = [
        (0, "X"),
        (3, "O"),
        (1, "X"),
        (4, "O"),
        (2, "X"),
    ]
    last_state = None
    for idx, player in seq:
        r = client.post(f"/games/{game_id}/moves", json={"index": idx, "player": player})
        assert r.status_code == 200
        last_state = r.json()["state"]

    assert last_state is not None
    assert last_state["winner"] == "X"
    assert last_state["is_draw"] is False
    assert len(last_state["history"]) == 5

    # Fetch game and ensure history present
    g = client.get(f"/games/{game_id}")
    assert g.status_code == 200
    gdata = g.json()
    assert gdata["game_id"] == game_id
    assert gdata["state"]["winner"] == "X"
    assert len(gdata["state"]["history"]) == 5

    # List finished games should include this game
    lst = client.get("/games")
    assert lst.status_code == 200
    arr = lst.json()["games"]
    assert any(item["game_id"] == game_id for item in arr)
