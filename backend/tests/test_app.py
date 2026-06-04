import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

from backend.db import initialize_database
from backend.main import create_app


def test_health_endpoint() -> None:
    client = TestClient(create_app(Path("/tmp/does-not-exist")))
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "message": "Hello from FastAPI"}


def test_serves_frontend_index_and_asset(tmp_path: Path) -> None:
    static_dir = tmp_path / "frontend-out"
    static_dir.mkdir()
    (static_dir / "index.html").write_text(
        "<html><body><h1>Kanban Studio</h1></body></html>", encoding="utf-8"
    )
    (static_dir / "app.js").write_text("console.log('ok')", encoding="utf-8")

    client = TestClient(create_app(static_dir))
    response = client.get("/")
    assert response.status_code == 200
    assert "Kanban Studio" in response.text

    asset_response = client.get("/app.js")
    assert asset_response.status_code == 200
    assert "console.log('ok')" in asset_response.text


def test_frontend_route_falls_back_to_index_for_unknown_path(tmp_path: Path) -> None:
    static_dir = tmp_path / "frontend-out"
    static_dir.mkdir()
    (static_dir / "index.html").write_text(
        "<html><body><h1>Kanban Studio</h1></body></html>", encoding="utf-8"
    )

    client = TestClient(create_app(static_dir))
    response = client.get("/some/client-side/path")
    assert response.status_code == 200
    assert "Kanban Studio" in response.text


def test_get_board_route_returns_seeded_board(tmp_path: Path) -> None:
    db_path = tmp_path / "data" / "app.db"
    static_dir = tmp_path / "frontend-out"
    static_dir.mkdir()
    (static_dir / "index.html").write_text("<html>ok</html>", encoding="utf-8")

    client = TestClient(create_app(frontend_dir=static_dir, db_path=db_path))
    response = client.get("/api/board/user")

    assert response.status_code == 200
    payload = response.json()
    assert payload["username"] == "user"
    assert payload["version"] == 1
    assert "columns" in payload["board"]
    assert "cards" in payload["board"]


def test_put_board_route_updates_board_and_version(tmp_path: Path) -> None:
    db_path = tmp_path / "data" / "app.db"
    static_dir = tmp_path / "frontend-out"
    static_dir.mkdir()
    (static_dir / "index.html").write_text("<html>ok</html>", encoding="utf-8")

    client = TestClient(create_app(frontend_dir=static_dir, db_path=db_path))
    original = client.get("/api/board/user").json()["board"]
    original["columns"][0]["title"] = "Updated by API test"

    update_response = client.put("/api/board/user", json={"board": original})
    assert update_response.status_code == 200
    assert update_response.json()["version"] == 2
    assert update_response.json()["board"]["columns"][0]["title"] == "Updated by API test"


def test_board_route_validation_failure_returns_422(tmp_path: Path) -> None:
    db_path = tmp_path / "data" / "app.db"
    static_dir = tmp_path / "frontend-out"
    static_dir.mkdir()
    (static_dir / "index.html").write_text("<html>ok</html>", encoding="utf-8")

    client = TestClient(create_app(frontend_dir=static_dir, db_path=db_path))
    response = client.put("/api/board/user", json={"board": {"columns": []}})

    assert response.status_code == 422


def test_board_route_returns_404_for_missing_board_state(tmp_path: Path) -> None:
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

    static_dir = tmp_path / "frontend-out"
    static_dir.mkdir()
    (static_dir / "index.html").write_text("<html>ok</html>", encoding="utf-8")
    client = TestClient(create_app(frontend_dir=static_dir, db_path=db_path))

    response = client.get("/api/board/orphan")
    assert response.status_code == 404


def test_ai_connectivity_returns_503_when_api_key_missing(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    static_dir = tmp_path / "frontend-out"
    static_dir.mkdir()
    (static_dir / "index.html").write_text("<html>ok</html>", encoding="utf-8")
    client = TestClient(create_app(frontend_dir=static_dir, db_path=tmp_path / "app.db"))

    response = client.post("/api/ai/connectivity")

    assert response.status_code == 503
    assert "OPENAI_API_KEY" in response.json()["detail"]


def test_ai_connectivity_returns_success_with_mocked_openai(
    monkeypatch, tmp_path: Path
) -> None:
    static_dir = tmp_path / "frontend-out"
    static_dir.mkdir()
    (static_dir / "index.html").write_text("<html>ok</html>", encoding="utf-8")

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    def fake_openai_call(prompt: str, api_key: str) -> str:
        _ = prompt, api_key
        return "4"

    monkeypatch.setattr("backend.main.call_openai_chat", fake_openai_call)
    client = TestClient(create_app(frontend_dir=static_dir, db_path=tmp_path / "app.db"))

    response = client.post("/api/ai/connectivity")

    assert response.status_code == 200
    payload = response.json()
    assert payload["model"] == "gpt-4o-mini"
    assert payload["answer"] == "4"
    assert payload["is_correct"] is True


def test_ai_board_chat_message_only_does_not_update_board(
    monkeypatch, tmp_path: Path
) -> None:
    static_dir = tmp_path / "frontend-out"
    static_dir.mkdir()
    (static_dir / "index.html").write_text("<html>ok</html>", encoding="utf-8")

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    def fake_structured_call(**kwargs):
        _ = kwargs
        return {
            "assistant_response": "No board changes needed.",
            "board_update": None,
        }

    monkeypatch.setattr(
        "backend.main.call_openai_structured_board_response",
        fake_structured_call,
    )
    client = TestClient(create_app(frontend_dir=static_dir, db_path=tmp_path / "app.db"))

    before = client.get("/api/board/user").json()
    response = client.post(
        "/api/ai/board/user",
        json={"question": "summarize", "conversation": []},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["board_updated"] is False
    assert payload["version"] == before["version"]
    assert payload["board"] == before["board"]


def test_ai_board_chat_updates_and_persists_board(monkeypatch, tmp_path: Path) -> None:
    static_dir = tmp_path / "frontend-out"
    static_dir.mkdir()
    (static_dir / "index.html").write_text("<html>ok</html>", encoding="utf-8")

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    def fake_structured_call(**kwargs):
        board = kwargs["board"]
        board["columns"][0]["title"] = "Updated by AI"
        return {
            "assistant_response": "Updated the first column title.",
            "board_update": board,
        }

    monkeypatch.setattr(
        "backend.main.call_openai_structured_board_response",
        fake_structured_call,
    )
    client = TestClient(create_app(frontend_dir=static_dir, db_path=tmp_path / "app.db"))

    response = client.post(
        "/api/ai/board/user",
        json={
            "question": "rename first column",
            "conversation": [{"role": "user", "content": "Please rename it."}],
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["board_updated"] is True
    assert payload["version"] == 2
    assert payload["board"]["columns"][0]["title"] == "Updated by AI"

    persisted = client.get("/api/board/user").json()
    assert persisted["version"] == 2
    assert persisted["board"]["columns"][0]["title"] == "Updated by AI"


def test_ai_board_chat_invalid_output_returns_502(monkeypatch, tmp_path: Path) -> None:
    static_dir = tmp_path / "frontend-out"
    static_dir.mkdir()
    (static_dir / "index.html").write_text("<html>ok</html>", encoding="utf-8")

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    def fake_structured_call(**kwargs):
        _ = kwargs
        return {"unexpected": "shape"}

    monkeypatch.setattr(
        "backend.main.call_openai_structured_board_response",
        fake_structured_call,
    )
    client = TestClient(create_app(frontend_dir=static_dir, db_path=tmp_path / "app.db"))

    response = client.post("/api/ai/board/user", json={"question": "hi"})
    assert response.status_code == 502
    assert "failed validation" in response.json()["detail"]


def test_ai_board_chat_accepts_partial_board_update(monkeypatch, tmp_path: Path) -> None:
    static_dir = tmp_path / "frontend-out"
    static_dir.mkdir()
    (static_dir / "index.html").write_text("<html>ok</html>", encoding="utf-8")

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    def fake_structured_call(**kwargs):
        board = kwargs["board"]
        moved_columns = [dict(column) for column in board["columns"]]
        first = moved_columns[0]
        first["cardIds"] = [card_id for card_id in first["cardIds"] if card_id != "card-1"]
        done_column = moved_columns[-1]
        done_column["cardIds"] = [*done_column["cardIds"], "card-1"]
        return {
            "assistant_response": "Moved card-1 to done.",
            "board_update": {"columns": moved_columns},
        }

    monkeypatch.setattr(
        "backend.main.call_openai_structured_board_response",
        fake_structured_call,
    )
    client = TestClient(create_app(frontend_dir=static_dir, db_path=tmp_path / "app.db"))

    response = client.post("/api/ai/board/user", json={"question": "move to done"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["board_updated"] is True
    assert payload["board"]["cards"]["card-1"]["id"] == "card-1"
    assert "card-1" in payload["board"]["columns"][-1]["cardIds"]
