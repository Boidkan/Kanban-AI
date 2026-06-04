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
