import importlib
from src.db import init_db

def test_create_and_list_games_isolated_db(temp_db_path):
    # Import models fresh (ensures using temp DB env)
    from src import models
    importlib.reload(models)
    init_db()

    g = models.create_game("g1")
    assert g["id"] == "g1"
    assert g["started_at"] is not None
    assert g["finished_at"] is None
    assert g["result"] is None

    games = models.list_games()
    assert any(x["id"] == "g1" for x in games)

def test_add_move_and_get_game(temp_db_path):
    from src import models
    importlib.reload(models)
    init_db()

    models.create_game("g2")
    m1 = models.add_move("g2", 1, "X", 0)
    assert m1["move_number"] == 1
    assert m1["player"] == "X"
    assert m1["position"] == 0

    models.add_move("g2", 2, "O", 4)
    game = models.get_game("g2")
    assert game is not None
    assert len(game["moves"]) == 2
    assert game["moves"][0]["player"] == "X"
    assert game["moves"][1]["player"] == "O"

def test_finalize_game_updates_rows(temp_db_path):
    from src import models
    importlib.reload(models)
    init_db()

    models.create_game("g3")
    updated = models.finalize_game("g3", "X", "[\"X\", null, ...]")
    assert updated["result"] == "X"
    assert updated["finished_at"] is not None
