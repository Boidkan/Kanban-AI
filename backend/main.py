import os
import secrets
from pathlib import Path
from typing import Any, Literal, Optional

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, ValidationError, model_validator
from fastapi.responses import FileResponse, PlainTextResponse, Response

from backend.ai import (
    OPENAI_MODEL,
    OpenAIResponseError,
    call_openai_chat,
    call_openai_structured_board_response,
)
from backend.db import (
    DEFAULT_DB_PATH,
    BoardNotFoundError,
    BoardVersionConflictError,
    UserNotFoundError,
    create_user_with_board,
    get_board_for_user,
    initialize_database,
    update_board_for_user,
)

DEFAULT_FRONTEND_DIR = Path("/app/frontend-out")

# MVP credentials. The user table supports multiple users, but only this
# account can authenticate for now (see docs/PLAN.md).
AUTH_USERNAME = "user"
AUTH_PASSWORD = "password"


class CardModel(BaseModel):
    id: str
    title: str
    details: str


class ColumnModel(BaseModel):
    id: str
    title: str
    cardIds: list[str]


class BoardModel(BaseModel):
    columns: list[ColumnModel]
    cards: dict[str, CardModel]

    @model_validator(mode="after")
    def _check_referential_integrity(self) -> "BoardModel":
        referenced: list[str] = [
            card_id for column in self.columns for card_id in column.cardIds
        ]
        referenced_set = set(referenced)
        card_keys = set(self.cards.keys())

        missing = referenced_set - card_keys
        if missing:
            raise ValueError(f"Columns reference unknown cards: {sorted(missing)}")

        if len(referenced) != len(referenced_set):
            raise ValueError("A card is referenced by more than one column position.")

        orphans = card_keys - referenced_set
        if orphans:
            raise ValueError(f"Cards not referenced by any column: {sorted(orphans)}")

        mismatched = sorted(key for key, card in self.cards.items() if card.id != key)
        if mismatched:
            raise ValueError(f"Card id does not match its key for: {mismatched}")

        return self


class BoardResponseModel(BaseModel):
    username: str
    version: int
    board: BoardModel


class BoardUpdateRequestModel(BaseModel):
    board: BoardModel
    expected_version: Optional[int] = None


class LoginRequestModel(BaseModel):
    username: str
    password: str


class LoginResponseModel(BaseModel):
    token: str
    username: str


class AIConnectivityResponseModel(BaseModel):
    model: str
    prompt: str
    answer: str
    is_correct: bool


class AIConversationMessageModel(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class AIChatRequestModel(BaseModel):
    question: str
    conversation: list[AIConversationMessageModel] = []


class AIStructuredOutputModel(BaseModel):
    assistant_response: str
    board_update: Optional[dict[str, Any]] = None


class AIChatResponseModel(BaseModel):
    model: str
    message: str
    board: BoardModel
    version: int
    board_updated: bool


def _merge_board_update(
    current_board: dict[str, Any], board_update: dict[str, Any]
) -> dict[str, Any]:
    merged = {
        "columns": board_update.get("columns", current_board.get("columns")),
        "cards": board_update.get("cards", current_board.get("cards")),
    }
    return merged


def create_app(
    frontend_dir: Path = DEFAULT_FRONTEND_DIR,
    db_path: Path = DEFAULT_DB_PATH,
) -> FastAPI:
    app = FastAPI(title="Project Management MVP Backend")
    initialize_database(db_path=db_path)

    # token -> username. In-memory is fine for the single-container MVP;
    # sessions reset on restart.
    sessions: dict[str, str] = {}

    def _token_from_header(authorization: Optional[str]) -> Optional[str]:
        if authorization and authorization.startswith("Bearer "):
            return authorization[len("Bearer ") :]
        return None

    def get_current_username(
        authorization: Optional[str] = Header(default=None),
    ) -> str:
        token = _token_from_header(authorization)
        username = sessions.get(token) if token else None
        if not username:
            raise HTTPException(status_code=401, detail="Authentication required.")
        return username

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "message": "Hello from FastAPI"}

    @app.post("/api/auth/login", response_model=LoginResponseModel)
    def login(payload: LoginRequestModel) -> LoginResponseModel:
        if payload.username != AUTH_USERNAME or payload.password != AUTH_PASSWORD:
            raise HTTPException(status_code=401, detail="Invalid credentials.")
        create_user_with_board(db_path=db_path, username=payload.username)
        token = secrets.token_urlsafe(32)
        sessions[token] = payload.username
        return LoginResponseModel(token=token, username=payload.username)

    @app.post("/api/auth/logout")
    def logout(authorization: Optional[str] = Header(default=None)) -> dict[str, str]:
        token = _token_from_header(authorization)
        if token:
            sessions.pop(token, None)
        return {"status": "ok"}

    @app.get("/api/board", response_model=BoardResponseModel)
    def get_board(
        username: str = Depends(get_current_username),
    ) -> BoardResponseModel:
        try:
            board, version = get_board_for_user(db_path=db_path, username=username)
        except (UserNotFoundError, BoardNotFoundError) as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return BoardResponseModel(username=username, version=version, board=board)

    @app.put("/api/board", response_model=BoardResponseModel)
    def update_board(
        payload: BoardUpdateRequestModel,
        username: str = Depends(get_current_username),
    ) -> BoardResponseModel:
        try:
            version = update_board_for_user(
                db_path=db_path,
                username=username,
                board=payload.board.model_dump(),
                expected_version=payload.expected_version,
            )
            board, _ = get_board_for_user(db_path=db_path, username=username)
        except BoardVersionConflictError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except (UserNotFoundError, BoardNotFoundError) as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return BoardResponseModel(username=username, version=version, board=board)

    @app.post("/api/ai/connectivity", response_model=AIConnectivityResponseModel)
    def ai_connectivity_test(
        username: str = Depends(get_current_username),
    ) -> AIConnectivityResponseModel:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise HTTPException(
                status_code=503,
                detail="OPENAI_API_KEY is not configured.",
            )

        prompt = "What is 2+2? Reply with only the number."

        try:
            answer = call_openai_chat(prompt=prompt, api_key=api_key)
        except OpenAIResponseError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

        normalized = "".join(ch for ch in answer if ch.isdigit())
        return AIConnectivityResponseModel(
            model=OPENAI_MODEL,
            prompt=prompt,
            answer=answer,
            is_correct=normalized == "4",
        )

    @app.post("/api/ai/board", response_model=AIChatResponseModel)
    def ai_board_chat(
        payload: AIChatRequestModel,
        username: str = Depends(get_current_username),
    ) -> AIChatResponseModel:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise HTTPException(
                status_code=503,
                detail="OPENAI_API_KEY is not configured.",
            )

        try:
            current_board, current_version = get_board_for_user(
                db_path=db_path, username=username
            )
        except (UserNotFoundError, BoardNotFoundError) as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

        try:
            raw_response = call_openai_structured_board_response(
                question=payload.question,
                board=current_board,
                conversation=[message.model_dump() for message in payload.conversation],
                api_key=api_key,
            )
            structured = AIStructuredOutputModel.model_validate(raw_response)
        except OpenAIResponseError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        except ValidationError as exc:
            raise HTTPException(
                status_code=502,
                detail=f"OpenAI structured output failed validation: {exc}",
            ) from exc

        if structured.board_update is None:
            return AIChatResponseModel(
                model=OPENAI_MODEL,
                message=structured.assistant_response,
                board=current_board,
                version=current_version,
                board_updated=False,
            )

        try:
            merged_board_update = _merge_board_update(current_board, structured.board_update)
            validated_board = BoardModel.model_validate(merged_board_update)
            next_version = update_board_for_user(
                board=validated_board.model_dump(),
                db_path=db_path,
                username=username,
                expected_version=current_version,
            )
            next_board, _ = get_board_for_user(db_path=db_path, username=username)
        except ValidationError as exc:
            raise HTTPException(
                status_code=502,
                detail=f"OpenAI board_update is invalid: {exc}",
            ) from exc
        except BoardVersionConflictError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except (UserNotFoundError, BoardNotFoundError) as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

        return AIChatResponseModel(
            model=OPENAI_MODEL,
            message=structured.assistant_response,
            board=next_board,
            version=next_version,
            board_updated=True,
        )

    @app.get("/{full_path:path}")
    def frontend(full_path: str) -> Response:
        if not frontend_dir.exists():
            return PlainTextResponse("Frontend build not found.", status_code=503)

        requested_file = (frontend_dir / full_path).resolve()
        if requested_file.is_file() and requested_file.is_relative_to(frontend_dir):
            return FileResponse(requested_file)

        index_file = frontend_dir / "index.html"
        if index_file.is_file():
            return FileResponse(index_file)

        return PlainTextResponse("Frontend index not found.", status_code=503)

    return app


app = create_app()
