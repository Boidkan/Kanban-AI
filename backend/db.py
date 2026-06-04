from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

DEFAULT_DB_PATH = Path("backend/data/app.db")

SCHEMA_SQL = """
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT NOT NULL UNIQUE,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS boards (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL UNIQUE,
  board_json TEXT NOT NULL,
  version INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
"""


class UserNotFoundError(Exception):
    pass


class BoardNotFoundError(Exception):
    pass


def is_legacy_example_board(board: dict[str, Any]) -> bool:
    cards = board.get("cards")
    if not isinstance(cards, dict):
        return False
    return any(
        isinstance(card, dict) and card.get("title") == "Example task"
        for card in cards.values()
    )


def default_board_payload() -> dict[str, Any]:
    return {
        "columns": [
            {"id": "col-backlog", "title": "Backlog", "cardIds": ["card-1", "card-2"]},
            {"id": "col-discovery", "title": "Discovery", "cardIds": ["card-3", "card-4"]},
            {"id": "col-progress", "title": "In Progress", "cardIds": ["card-5", "card-6"]},
            {"id": "col-review", "title": "Review", "cardIds": ["card-7", "card-8"]},
            {"id": "col-done", "title": "Done", "cardIds": ["card-9", "card-10"]},
        ],
        "cards": {
            "card-1": {
                "id": "card-1",
                "title": "Part 1 - Detailed planning",
                "details": "Finalize checklist plan and get user sign-off before execution.",
            },
            "card-2": {
                "id": "card-2",
                "title": "Part 2 - Scaffold Docker + FastAPI",
                "details": "Prepare container, backend skeleton, and cross-platform run scripts.",
            },
            "card-3": {
                "id": "card-3",
                "title": "Part 3 - Serve static frontend",
                "details": "Build Next.js assets and serve the Kanban app at root path.",
            },
            "card-4": {
                "id": "card-4",
                "title": "Part 4 - Fake sign-in flow",
                "details": "Gate board access with MVP credentials and add logout behavior.",
            },
            "card-5": {
                "id": "card-5",
                "title": "Part 5 - Database modeling",
                "details": "Document SQLite schema and JSON board storage strategy.",
            },
            "card-6": {
                "id": "card-6",
                "title": "Part 6 - Backend board APIs",
                "details": "Implement read/write routes with validation and DB auto-bootstrap.",
            },
            "card-7": {
                "id": "card-7",
                "title": "Part 7 - Frontend API integration",
                "details": "Wire Kanban interactions to backend persistence with loading states.",
            },
            "card-8": {
                "id": "card-8",
                "title": "Part 8 - AI connectivity",
                "details": "Verify OpenAI connectivity with deterministic 2+2 check endpoint.",
            },
            "card-9": {
                "id": "card-9",
                "title": "Part 9 - Structured AI updates",
                "details": "Return validated assistant response plus optional board update payload.",
            },
            "card-10": {
                "id": "card-10",
                "title": "Part 10 - Sidebar AI chat",
                "details": "Ship chat sidebar and refresh board automatically on AI updates.",
            },
        },
    }


def serialize_board(board: dict[str, Any]) -> str:
    return json.dumps(board, separators=(",", ":"), sort_keys=True)


def deserialize_board(payload: str) -> dict[str, Any]:
    data = json.loads(payload)
    if not isinstance(data, dict):
        raise ValueError("Board payload must deserialize to an object.")
    return data


def initialize_database(
    db_path: Path = DEFAULT_DB_PATH,
    default_username: str = "user",
    default_board: dict[str, Any] | None = None,
) -> None:
    board = default_board if default_board is not None else default_board_payload()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(db_path) as conn:
        conn.executescript(SCHEMA_SQL)
        conn.execute(
            "INSERT OR IGNORE INTO users (username) VALUES (?)",
            (default_username,),
        )
        user_row = conn.execute(
            "SELECT id FROM users WHERE username = ?",
            (default_username,),
        ).fetchone()
        if user_row is None:
            raise RuntimeError("Failed to resolve default user during DB initialization.")

        default_board_json = serialize_board(board)
        conn.execute(
            """
            INSERT OR IGNORE INTO boards (user_id, board_json)
            VALUES (?, ?)
            """,
            (user_row[0], default_board_json),
        )
        existing_board_row = conn.execute(
            "SELECT board_json FROM boards WHERE user_id = ?",
            (user_row[0],),
        ).fetchone()
        if existing_board_row is not None:
            existing_board = deserialize_board(existing_board_row[0])
            if is_legacy_example_board(existing_board):
                conn.execute(
                    """
                    UPDATE boards
                    SET board_json = ?, version = 1, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                    """,
                    (default_board_json, user_row[0]),
                )
        conn.commit()


def create_user_with_board(
    db_path: Path = DEFAULT_DB_PATH,
    username: str = "user",
    board: dict[str, Any] | None = None,
) -> None:
    payload = board if board is not None else default_board_payload()
    initialize_database(db_path=db_path)

    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT OR IGNORE INTO users (username) VALUES (?)",
            (username,),
        )
        user_row = conn.execute(
            "SELECT id FROM users WHERE username = ?",
            (username,),
        ).fetchone()
        if user_row is None:
            raise RuntimeError(f"Failed to create or resolve user '{username}'.")

        conn.execute(
            "INSERT OR IGNORE INTO boards (user_id, board_json) VALUES (?, ?)",
            (user_row[0], serialize_board(payload)),
        )
        conn.commit()


def get_board_for_user(
    db_path: Path = DEFAULT_DB_PATH,
    username: str = "user",
) -> tuple[dict[str, Any], int]:
    initialize_database(db_path=db_path)

    with sqlite3.connect(db_path) as conn:
        user_row = conn.execute(
            "SELECT id FROM users WHERE username = ?",
            (username,),
        ).fetchone()
        if user_row is None:
            raise UserNotFoundError(f"User '{username}' does not exist.")

        board_row = conn.execute(
            "SELECT board_json, version FROM boards WHERE user_id = ?",
            (user_row[0],),
        ).fetchone()
        if board_row is None:
            raise BoardNotFoundError(f"No board exists for user '{username}'.")

    return deserialize_board(board_row[0]), int(board_row[1])


def update_board_for_user(
    board: dict[str, Any],
    db_path: Path = DEFAULT_DB_PATH,
    username: str = "user",
) -> int:
    initialize_database(db_path=db_path)

    with sqlite3.connect(db_path) as conn:
        user_row = conn.execute(
            "SELECT id FROM users WHERE username = ?",
            (username,),
        ).fetchone()
        if user_row is None:
            raise UserNotFoundError(f"User '{username}' does not exist.")

        board_row = conn.execute(
            "SELECT version FROM boards WHERE user_id = ?",
            (user_row[0],),
        ).fetchone()
        if board_row is None:
            raise BoardNotFoundError(f"No board exists for user '{username}'.")

        next_version = int(board_row[0]) + 1
        conn.execute(
            """
            UPDATE boards
            SET board_json = ?, version = ?, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
            """,
            (serialize_board(board), next_version, user_row[0]),
        )
        conn.commit()

    return next_version
