## Backend overview

The backend is a FastAPI service in `backend/`.

Current scope:

- Serves the statically built Next.js frontend at `/` with SPA fallback to `index.html`.
- Exposes a health API endpoint at `/api/health`.
- Auth (multi-user, DB-backed; passwords hashed with argon2):
  - `POST /api/auth/login` -> bearer token; `POST /api/auth/logout` revokes it.
  - `POST /api/auth/register` -> open self-signup (username 3-32 `[A-Za-z0-9_-]`,
    password >= 8); 409 on a taken username; logs the new account straight in.
  - A `get_current_username` dependency gates the routes below (401 without a
    valid token); the username comes from the session, not the URL.
- Board APIs (authenticated):
  - `GET /api/board`
  - `PUT /api/board` (accepts `expected_version`; 409 on a stale write; the board
    is validated for referential integrity, 422 if inconsistent)
- AI connectivity API (authenticated):
  - `POST /api/ai/connectivity`
  - Runs a deterministic `2+2` prompt through OpenAI using model `gpt-4o-mini`.
- Structured AI board chat API (authenticated):
  - `POST /api/ai/board`
  - Sends question + conversation + board JSON to OpenAI and returns assistant message plus optional persisted board update.
- Serves static asset files directly from the built frontend output directory.
- Uses `uv` for dependency management inside the Docker image via `backend/pyproject.toml`.
- Uses SQLite persistence in `backend/data/app.db` with initialization + repository helpers in `backend/db.py`.

Core files:

- `backend/main.py`: FastAPI app, API routes, auth/session handling, and frontend static/fallback serving.
- `backend/auth.py`: argon2 password hashing/verification helpers.
- `backend/ai.py`: OpenAI client helper for connectivity and structured board responses.
- `backend/db.py`: Database schema/bootstrap, migrations, and user/board repository operations.
- `backend/pyproject.toml`: Python project metadata and dependencies.
- `backend/tests/test_app.py`: Route tests for health, frontend serving, auth, and board/AI APIs.
- `backend/tests/test_auth.py`: Password hashing unit tests.
- `backend/tests/test_ai.py`: OpenAI request builder/response error tests.
- `backend/tests/test_db.py`: Repository, migration, and initialization unit tests.