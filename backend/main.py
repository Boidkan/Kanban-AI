from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.responses import FileResponse, PlainTextResponse, Response

from backend.db import (
    DEFAULT_DB_PATH,
    BoardNotFoundError,
    UserNotFoundError,
    get_board_for_user,
    initialize_database,
    update_board_for_user,
)

DEFAULT_FRONTEND_DIR = Path("/app/frontend-out")


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


class BoardResponseModel(BaseModel):
    username: str
    version: int
    board: BoardModel


class BoardUpdateRequestModel(BaseModel):
    board: BoardModel


def create_app(
    frontend_dir: Path = DEFAULT_FRONTEND_DIR,
    db_path: Path = DEFAULT_DB_PATH,
) -> FastAPI:
    app = FastAPI(title="Project Management MVP Backend")
    initialize_database(db_path=db_path)

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "message": "Hello from FastAPI"}

    @app.get("/api/board/{username}", response_model=BoardResponseModel)
    def get_board(username: str) -> BoardResponseModel:
        try:
            board, version = get_board_for_user(db_path=db_path, username=username)
        except (UserNotFoundError, BoardNotFoundError) as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return BoardResponseModel(username=username, version=version, board=board)

    @app.put("/api/board/{username}", response_model=BoardResponseModel)
    def update_board(
        username: str, payload: BoardUpdateRequestModel
    ) -> BoardResponseModel:
        try:
            version = update_board_for_user(
                db_path=db_path,
                username=username,
                board=payload.board.model_dump(),
            )
            board, _ = get_board_for_user(db_path=db_path, username=username)
        except (UserNotFoundError, BoardNotFoundError) as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return BoardResponseModel(username=username, version=version, board=board)

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
