from typing import Any

import pytest

from backend.ai import (
    OPENAI_MODEL,
    OpenAIResponseError,
    call_openai_chat,
    call_openai_structured_board_response,
)


class DummyResponse:
    def __init__(self, status_code: int, json_payload: dict[str, Any], text: str = "") -> None:
        self.status_code = status_code
        self._json_payload = json_payload
        self.text = text

    def json(self) -> dict[str, Any]:
        return self._json_payload


def test_call_openai_chat_builds_expected_request(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    def fake_post(url: str, **kwargs: Any) -> DummyResponse:
        captured["url"] = url
        captured["kwargs"] = kwargs
        return DummyResponse(
            status_code=200,
            json_payload={"choices": [{"message": {"content": "4"}}]},
        )

    monkeypatch.setattr("backend.ai.httpx.post", fake_post)

    result = call_openai_chat(prompt="What is 2+2?", api_key="test-key")

    assert result == "4"
    assert "api.openai.com/v1/chat/completions" in captured["url"]
    assert captured["kwargs"]["headers"]["Authorization"] == "Bearer test-key"
    assert captured["kwargs"]["json"]["model"] == OPENAI_MODEL
    assert captured["kwargs"]["json"]["messages"][0]["content"] == "What is 2+2?"


def test_call_openai_chat_raises_for_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_post(url: str, **kwargs: Any) -> DummyResponse:
        _ = url, kwargs
        return DummyResponse(
            status_code=401,
            json_payload={"error": {"message": "unauthorized"}},
            text="unauthorized",
        )

    monkeypatch.setattr("backend.ai.httpx.post", fake_post)

    with pytest.raises(OpenAIResponseError):
        call_openai_chat(prompt="What is 2+2?", api_key="bad-key")


def test_call_openai_structured_board_response_parses_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_post(url: str, **kwargs: Any) -> DummyResponse:
        _ = url
        assert kwargs["json"]["response_format"]["type"] == "json_schema"
        return DummyResponse(
            status_code=200,
            json_payload={
                "choices": [
                    {
                        "message": {
                            "content": '{"assistant_response":"ok","board_update":null}'
                        }
                    }
                ]
            },
        )

    monkeypatch.setattr("backend.ai.httpx.post", fake_post)

    payload = call_openai_structured_board_response(
        question="Any updates?",
        board={"columns": [], "cards": {}},
        conversation=[],
        api_key="test-key",
    )

    assert payload["assistant_response"] == "ok"
    assert payload["board_update"] is None


def test_call_openai_structured_board_response_raises_for_invalid_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_post(url: str, **kwargs: Any) -> DummyResponse:
        _ = url, kwargs
        return DummyResponse(
            status_code=200,
            json_payload={
                "choices": [{"message": {"content": "{not-valid-json"}}],
            },
        )

    monkeypatch.setattr("backend.ai.httpx.post", fake_post)

    with pytest.raises(OpenAIResponseError):
        call_openai_structured_board_response(
            question="Any updates?",
            board={"columns": [], "cards": {}},
            conversation=[],
            api_key="test-key",
        )
