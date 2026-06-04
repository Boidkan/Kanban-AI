import sqlite3
from pathlib import Path

from backend.db import (
    BoardNotFoundError,
    create_user_with_board,
    deserialize_board,
    get_board_for_user,
    initialize_database,
    serialize_board,
    update_board_for_user,
)


LEGACY_EXAMPLE_BOARD = {
    "columns": [
        {"id": "col-backlog", "title": "Backlog", "cardIds": ["card-1", "card-2"]},
        {"id": "col-discovery", "title": "Discovery", "cardIds": ["card-3"]},
        {"id": "col-progress", "title": "In Progress", "cardIds": ["card-4"]},
        {"id": "col-review", "title": "Review", "cardIds": []},
        {"id": "col-done", "title": "Done", "cardIds": []},
    ],
    "cards": {
        "card-1": {"id": "card-1", "title": "Example task", "details": "Seed card 1"},
        "card-2": {"id": "card-2", "title": "Example task", "details": "Seed card 2"},
        "card-3": {"id": "card-3", "title": "Example task", "details": "Seed card 3"},
        "card-4": {"id": "card-4", "title": "Example task", "details": "Seed card 4"},
    },
}


def test_initialize_database_creates_schema_and_default_records(tmp_path: Path) -> None:
    db_path = tmp_path / "data" / "app.db"

    initialize_database(db_path=db_path)

    assert db_path.exists()

    with sqlite3.connect(db_path) as conn:
        users = conn.execute("SELECT username FROM users").fetchall()
        boards = conn.execute("SELECT user_id, board_json FROM boards").fetchall()

    assert users == [("user",)]
    assert len(boards) == 1
    assert deserialize_board(boards[0][1])["columns"]


def test_initialize_database_is_idempotent(tmp_path: Path) -> None:
    db_path = tmp_path / "data" / "app.db"

    initialize_database(db_path=db_path)
    initialize_database(db_path=db_path)

    with sqlite3.connect(db_path) as conn:
        user_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        board_count = conn.execute("SELECT COUNT(*) FROM boards").fetchone()[0]

    assert user_count == 1
    assert board_count == 1


def test_board_payload_round_trip() -> None:
    board = {
        "columns": [{"id": "col-a", "title": "A", "cardIds": ["card-1"]}],
        "cards": {"card-1": {"id": "card-1", "title": "Task", "details": "Detail"}},
    }

    serialized = serialize_board(board)
    restored = deserialize_board(serialized)

    assert restored == board


def test_repository_create_read_update_board(tmp_path: Path) -> None:
    db_path = tmp_path / "data" / "app.db"
    board = {
        "columns": [{"id": "col-a", "title": "A", "cardIds": ["card-1"]}],
        "cards": {"card-1": {"id": "card-1", "title": "Task", "details": "Detail"}},
    }

    create_user_with_board(db_path=db_path, username="alice", board=board)
    loaded_board, version = get_board_for_user(db_path=db_path, username="alice")

    assert loaded_board == board
    assert version == 1

    updated = {
        "columns": [{"id": "col-a", "title": "Updated", "cardIds": ["card-1"]}],
        "cards": {"card-1": {"id": "card-1", "title": "Task", "details": "Detail"}},
    }
    next_version = update_board_for_user(
        db_path=db_path, username="alice", board=updated
    )
    reloaded, reloaded_version = get_board_for_user(db_path=db_path, username="alice")

    assert next_version == 2
    assert reloaded_version == 2
    assert reloaded["columns"][0]["title"] == "Updated"


def test_repository_raises_for_missing_board_state(tmp_path: Path) -> None:
    db_path = tmp_path / "data" / "app.db"
    initialize_database(db_path=db_path)

    with sqlite3.connect(db_path) as conn:
        conn.execute("INSERT OR IGNORE INTO users (username) VALUES (?)", ("orphan",))
        orphan_id = conn.execute(
            "SELECT id FROM users WHERE username = ?",
            ("orphan",),
        ).fetchone()[0]
        conn.execute("DELETE FROM boards WHERE user_id = ?", (orphan_id,))
        conn.commit()

    try:
        get_board_for_user(db_path=db_path, username="orphan")
        assert False, "Expected BoardNotFoundError for orphan user."
    except BoardNotFoundError:
        pass


def test_initialize_database_migrates_legacy_example_seed(tmp_path: Path) -> None:
    db_path = tmp_path / "data" / "app.db"
    initialize_database(db_path=db_path, default_board=LEGACY_EXAMPLE_BOARD)
    initialize_database(db_path=db_path)

    board, version = get_board_for_user(db_path=db_path, username="user")

    assert version == 1
    assert board["cards"]["card-1"]["title"] == "Part 1 - Detailed planning"
    assert board["cards"]["card-10"]["title"] == "Part 10 - Sidebar AI chat"
