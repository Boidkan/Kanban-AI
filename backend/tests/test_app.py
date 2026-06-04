import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

from backend.db import initialize_database
from backend.main import create_app


def _make_client(tmp_path: Path) -> TestClient:
    static_dir = tmp_path / "frontend-out"
    static_dir.mkdir(exist_ok=True)
    (static_dir / "index.html").write_text("<html>ok</html>", encoding="utf-8")
    return TestClient(create_app(frontend_dir=static_dir, db_path=tmp_path / "app.db"))


def _auth_headers(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/auth/login", json={"username": "user", "password": "password"}
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['token']}"}


def test_health_endpoint(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
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

    client = TestClient(create_app(static_dir, db_path=tmp_path / "app.db"))
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

    client = TestClient(create_app(static_dir, db_path=tmp_path / "app.db"))
    response = client.get("/some/client-side/path")
    assert response.status_code == 200
    assert "Kanban Studio" in response.text


def test_login_succeeds_with_valid_credentials(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    response = client.post(
        "/api/auth/login", json={"username": "user", "password": "password"}
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["username"] == "user"
    assert payload["token"]


def test_login_rejects_invalid_credentials(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    response = client.post(
        "/api/auth/login", json={"username": "user", "password": "wrong"}
    )
    assert response.status_code == 401


def test_login_unknown_username_and_wrong_password_share_generic_error(
    tmp_path: Path,
) -> None:
    client = _make_client(tmp_path)
    wrong_password = client.post(
        "/api/auth/login", json={"username": "user", "password": "wrong"}
    )
    unknown_user = client.post(
        "/api/auth/login", json={"username": "ghost", "password": "password"}
    )
    assert wrong_password.status_code == 401
    assert unknown_user.status_code == 401
    # Do not reveal which field was wrong.
    assert wrong_password.json()["detail"] == unknown_user.json()["detail"]


def test_seeded_user_token_authorizes_board(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    headers = _auth_headers(client)
    assert client.get("/api/board", headers=headers).status_code == 200


def test_register_creates_account_and_logs_in(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    response = client.post(
        "/api/auth/register", json={"username": "alice", "password": "supersecret"}
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["username"] == "alice"
    assert payload["token"]

    headers = {"Authorization": f"Bearer {payload['token']}"}
    board = client.get("/api/board", headers=headers)
    assert board.status_code == 200
    assert board.json()["version"] == 1


def test_register_duplicate_username_returns_409(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    # 'user' is seeded at startup.
    response = client.post(
        "/api/auth/register", json={"username": "user", "password": "supersecret"}
    )
    assert response.status_code == 409


def test_register_rejects_invalid_username_and_short_password(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    bad_username = client.post(
        "/api/auth/register", json={"username": "no spaces!", "password": "supersecret"}
    )
    too_short_username = client.post(
        "/api/auth/register", json={"username": "ab", "password": "supersecret"}
    )
    short_password = client.post(
        "/api/auth/register", json={"username": "carol", "password": "short"}
    )
    assert bad_username.status_code == 422
    assert too_short_username.status_code == 422
    assert short_password.status_code == 422


def test_registered_user_can_log_in_afterwards(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    client.post(
        "/api/auth/register", json={"username": "dave", "password": "supersecret"}
    )
    login = client.post(
        "/api/auth/login", json={"username": "dave", "password": "supersecret"}
    )
    assert login.status_code == 200
    assert login.json()["username"] == "dave"


def test_accounts_have_independent_boards(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    token = client.post(
        "/api/auth/register", json={"username": "erin", "password": "supersecret"}
    ).json()["token"]
    erin = {"Authorization": f"Bearer {token}"}

    board = client.get("/api/board", headers=erin).json()["board"]
    board["columns"][0]["title"] = "Erin's column"
    client.put("/api/board", json={"board": board}, headers=erin)

    # The seeded default user's board is unaffected.
    default_headers = _auth_headers(client)
    default_board = client.get("/api/board", headers=default_headers).json()["board"]
    assert default_board["columns"][0]["title"] != "Erin's column"


def test_board_routes_require_authentication(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    assert client.get("/api/board").status_code == 401
    assert client.put("/api/board", json={"board": {"columns": [], "cards": {}}}).status_code == 401
    assert client.post("/api/ai/connectivity").status_code == 401
    assert client.post("/api/ai/board", json={"question": "hi"}).status_code == 401


def test_logout_revokes_token(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    headers = _auth_headers(client)
    assert client.get("/api/board", headers=headers).status_code == 200
    assert client.post("/api/auth/logout", headers=headers).status_code == 200
    assert client.get("/api/board", headers=headers).status_code == 401


def test_get_board_route_returns_seeded_board(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    headers = _auth_headers(client)
    response = client.get("/api/board", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["username"] == "user"
    assert payload["version"] == 1
    assert "columns" in payload["board"]
    assert "cards" in payload["board"]


def test_put_board_route_updates_board_and_version(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    headers = _auth_headers(client)
    original = client.get("/api/board", headers=headers).json()["board"]
    original["columns"][0]["title"] = "Updated by API test"

    update_response = client.put(
        "/api/board", json={"board": original}, headers=headers
    )
    assert update_response.status_code == 200
    assert update_response.json()["version"] == 2
    assert update_response.json()["board"]["columns"][0]["title"] == "Updated by API test"


def test_put_board_route_rejects_stale_version_with_409(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    headers = _auth_headers(client)
    board = client.get("/api/board", headers=headers).json()["board"]

    first = client.put(
        "/api/board",
        json={"board": board, "expected_version": 1},
        headers=headers,
    )
    assert first.status_code == 200

    stale = client.put(
        "/api/board",
        json={"board": board, "expected_version": 1},
        headers=headers,
    )
    assert stale.status_code == 409


def test_board_route_validation_failure_returns_422(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    headers = _auth_headers(client)
    response = client.put("/api/board", json={"board": {"columns": []}}, headers=headers)
    assert response.status_code == 422


def test_board_route_rejects_dangling_card_reference_with_422(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    headers = _auth_headers(client)
    broken = {
        "columns": [{"id": "col-a", "title": "A", "cardIds": ["ghost"]}],
        "cards": {},
    }
    response = client.put("/api/board", json={"board": broken}, headers=headers)
    assert response.status_code == 422


def test_board_route_rejects_orphan_card_with_422(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    headers = _auth_headers(client)
    broken = {
        "columns": [{"id": "col-a", "title": "A", "cardIds": []}],
        "cards": {"card-1": {"id": "card-1", "title": "T", "details": "D"}},
    }
    response = client.put("/api/board", json={"board": broken}, headers=headers)
    assert response.status_code == 422


def test_board_route_returns_404_for_missing_board_state(tmp_path: Path) -> None:
    client = _make_client(tmp_path)
    headers = _auth_headers(client)

    db_path = tmp_path / "app.db"
    with sqlite3.connect(db_path) as conn:
        user_id = conn.execute(
            "SELECT id FROM users WHERE username = ?", ("user",)
        ).fetchone()[0]
        conn.execute("DELETE FROM boards WHERE user_id = ?", (user_id,))
        conn.commit()

    response = client.get("/api/board", headers=headers)
    assert response.status_code == 404


def test_ai_connectivity_returns_503_when_api_key_missing(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    client = _make_client(tmp_path)
    headers = _auth_headers(client)

    response = client.post("/api/ai/connectivity", headers=headers)

    assert response.status_code == 503
    assert "OPENAI_API_KEY" in response.json()["detail"]


def test_ai_connectivity_returns_success_with_mocked_openai(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    def fake_openai_call(prompt: str, api_key: str) -> str:
        _ = prompt, api_key
        return "4"

    monkeypatch.setattr("backend.main.call_openai_chat", fake_openai_call)
    client = _make_client(tmp_path)
    headers = _auth_headers(client)

    response = client.post("/api/ai/connectivity", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["model"] == "gpt-4o-mini"
    assert payload["answer"] == "4"
    assert payload["is_correct"] is True


def test_ai_board_chat_message_only_does_not_update_board(
    monkeypatch, tmp_path: Path
) -> None:
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
    client = _make_client(tmp_path)
    headers = _auth_headers(client)

    before = client.get("/api/board", headers=headers).json()
    response = client.post(
        "/api/ai/board",
        json={"question": "summarize", "conversation": []},
        headers=headers,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["board_updated"] is False
    assert payload["version"] == before["version"]
    assert payload["board"] == before["board"]


def test_ai_board_chat_updates_and_persists_board(monkeypatch, tmp_path: Path) -> None:
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
    client = _make_client(tmp_path)
    headers = _auth_headers(client)

    response = client.post(
        "/api/ai/board",
        json={
            "question": "rename first column",
            "conversation": [{"role": "user", "content": "Please rename it."}],
        },
        headers=headers,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["board_updated"] is True
    assert payload["version"] == 2
    assert payload["board"]["columns"][0]["title"] == "Updated by AI"

    persisted = client.get("/api/board", headers=headers).json()
    assert persisted["version"] == 2
    assert persisted["board"]["columns"][0]["title"] == "Updated by AI"


def test_ai_board_chat_invalid_output_returns_502(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    def fake_structured_call(**kwargs):
        _ = kwargs
        return {"unexpected": "shape"}

    monkeypatch.setattr(
        "backend.main.call_openai_structured_board_response",
        fake_structured_call,
    )
    client = _make_client(tmp_path)
    headers = _auth_headers(client)

    response = client.post("/api/ai/board", json={"question": "hi"}, headers=headers)
    assert response.status_code == 502
    assert "failed validation" in response.json()["detail"]


def test_ai_board_chat_rejects_inconsistent_board_update_with_502(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    def fake_structured_call(**kwargs):
        return {
            "assistant_response": "Adding a column that points at a missing card.",
            "board_update": {
                "columns": [{"id": "col-x", "title": "X", "cardIds": ["ghost"]}],
                "cards": {},
            },
        }

    monkeypatch.setattr(
        "backend.main.call_openai_structured_board_response",
        fake_structured_call,
    )
    client = _make_client(tmp_path)
    headers = _auth_headers(client)

    response = client.post("/api/ai/board", json={"question": "break it"}, headers=headers)
    assert response.status_code == 502
    assert "invalid" in response.json()["detail"]


def test_ai_board_chat_accepts_partial_board_update(monkeypatch, tmp_path: Path) -> None:
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
    client = _make_client(tmp_path)
    headers = _auth_headers(client)

    response = client.post("/api/ai/board", json={"question": "move to done"}, headers=headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["board_updated"] is True
    assert payload["board"]["cards"]["card-1"]["id"] == "card-1"
    assert "card-1" in payload["board"]["columns"][-1]["cardIds"]
