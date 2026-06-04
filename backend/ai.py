from __future__ import annotations

import json
from typing import Any

import httpx

OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
OPENAI_MODEL = "gpt-4o-mini"


class OpenAIResponseError(Exception):
    pass


def call_openai_chat(prompt: str, api_key: str, model: str = OPENAI_MODEL) -> str:
    response = httpx.post(
        OPENAI_API_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=30.0,
    )

    if response.status_code >= 400:
        raise OpenAIResponseError(
            f"OpenAI request failed with status {response.status_code}: {response.text}"
        )

    payload = response.json()
    try:
        content = payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise OpenAIResponseError("OpenAI response missing message content.") from exc

    if not isinstance(content, str) or not content.strip():
        raise OpenAIResponseError("OpenAI returned empty message content.")

    return content.strip()


def call_openai_structured_board_response(
    *,
    question: str,
    board: dict[str, Any],
    conversation: list[dict[str, str]],
    api_key: str,
    model: str = OPENAI_MODEL,
) -> dict[str, Any]:
    response = httpx.post(
        OPENAI_API_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a Kanban assistant. Return only JSON that follows the schema. "
                        "If no board change is needed, set board_update to null."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "Question:\n"
                        f"{question}\n\n"
                        "Conversation history:\n"
                        f"{json.dumps(conversation, ensure_ascii=True)}\n\n"
                        "Current board JSON:\n"
                        f"{json.dumps(board, ensure_ascii=True)}"
                    ),
                },
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "kanban_assistant_response",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "assistant_response": {"type": "string"},
                            "board_update": {
                                "type": ["object", "null"],
                                "additionalProperties": True,
                            },
                        },
                        "required": ["assistant_response", "board_update"],
                        "additionalProperties": False,
                    },
                },
            },
        },
        timeout=45.0,
    )

    if response.status_code >= 400:
        raise OpenAIResponseError(
            f"OpenAI request failed with status {response.status_code}: {response.text}"
        )

    payload = response.json()
    try:
        content = payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise OpenAIResponseError("OpenAI response missing structured content.") from exc

    if not isinstance(content, str) or not content.strip():
        raise OpenAIResponseError("OpenAI returned empty structured content.")

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as exc:
        raise OpenAIResponseError("OpenAI returned invalid JSON content.") from exc

    if not isinstance(parsed, dict):
        raise OpenAIResponseError("OpenAI structured response must be a JSON object.")

    return parsed
