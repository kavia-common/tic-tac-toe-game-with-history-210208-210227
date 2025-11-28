import json

def assert_board_shape(board):
    assert isinstance(board, list)
    assert len(board) == 9
    assert all(v in (None, "X", "O") for v in board)

def test_start_game_returns_initial_state(test_app):
    r = test_app.post("/games/start")
    assert r.status_code == 200
    data = r.json()
    assert "gameId" in data and isinstance(data["gameId"], str)
    assert_board_shape(data["board"])
    assert data["currentPlayer"] in ("X", "O")
    assert data["status"] == "in_progress"
    assert data.get("winner") is None

def test_make_move_updates_board_and_turn(test_app):
    # Start
    s = test_app.post("/games/start").json()
    gid = s["gameId"]
    # X plays 0
    r1 = test_app.post(f"/games/{gid}/move", json={"position": 0})
    assert r1.status_code == 200
    d1 = r1.json()
    assert d1["gameId"] == gid
    assert d1["board"][0] == "X"
    assert d1["status"] == "in_progress"
    assert d1["currentPlayer"] == "O"

    # O plays 1
    r2 = test_app.post(f"/games/{gid}/move", json={"position": 1})
    assert r2.status_code == 200
    d2 = r2.json()
    assert d2["board"][1] == "O"
    assert d2["currentPlayer"] == "X"

def test_invalid_move_cell_occupied_returns_400(test_app):
    s = test_app.post("/games/start").json()
    gid = s["gameId"]
    assert test_app.post(f"/games/{gid}/move", json={"position": 0}).status_code == 200
    r = test_app.post(f"/games/{gid}/move", json={"position": 0})
    assert r.status_code == 400
    assert "occupied" in r.json()["detail"].lower()

def test_invalid_move_game_over_returns_400(test_app):
    s = test_app.post("/games/start").json()
    gid = s["gameId"]
    # X 0, O 3, X 1, O 4, X 2 -> X wins
    seq = [0, 3, 1, 4, 2]
    for p in seq:
        resp = test_app.post(f"/games/{gid}/move", json={"position": p})
        assert resp.status_code == 200
    # Another move not allowed
    r = test_app.post(f"/games/{gid}/move", json={"position": 8})
    assert r.status_code == 400
    assert "finished" in r.json()["detail"].lower()

def test_get_game_state_with_moves_and_status(test_app):
    s = test_app.post("/games/start").json()
    gid = s["gameId"]
    test_app.post(f"/games/{gid}/move", json={"position": 0})  # X
    test_app.post(f"/games/{gid}/move", json={"position": 4})  # O
    r = test_app.get(f"/games/{gid}")
    assert r.status_code == 200
    data = r.json()
    assert data["gameId"] == gid
    assert len(data["moves"]) == 2
    assert data["status"] in ("in_progress", "won", "draw")
    assert data["currentPlayer"] in ("X", "O", None)

def test_detect_win_and_persisted_history(test_app):
    s = test_app.post("/games/start").json()
    gid = s["gameId"]
    # X:0 O:3 X:1 O:4 X:2 -> X wins
    for p in [0, 3, 1, 4, 2]:
        r = test_app.post(f"/games/{gid}/move", json={"position": p})
    last = r.json()
    assert last["status"] == "won"
    assert last["winner"] == "X"
    # History should include finished game
    rh = test_app.get("/games/history")
    assert rh.status_code == 200
    h = rh.json()
    assert "items" in h
    items = h["items"]
    assert any(it["gameId"] == gid and it["status"] == "won" and it["winner"] == "X" for it in items)

def test_detect_draw_and_persisted(test_app):
    s = test_app.post("/games/start").json()
    gid = s["gameId"]
    # Draw sequence:
    # X:0 O:1 X:2 O:4 X:3 O:5 X:7 O:6 X:8
    seq = [0,1,2,4,3,5,7,6,8]
    for p in seq:
        r = test_app.post(f"/games/{gid}/move", json={"position": p})
        assert r.status_code == 200
    last = r.json()
    assert last["status"] == "draw"
    assert last["winner"] is None
    rh = test_app.get("/games/history")
    items = rh.json()["items"]
    assert any(it["gameId"] == gid and it["status"] == "draw" for it in items)
